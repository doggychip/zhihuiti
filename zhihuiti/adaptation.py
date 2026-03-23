"""Adaptation Engine (适应引擎) — closes the feedback loops.

Three systems that make zhihuiti actually learn from experience:

1. AdaptiveThresholds — population-calibrated cull/promote/QA thresholds
   Instead of fixed 0.3/0.8, thresholds shift based on the actual
   score distribution of the agent population.

2. PromptEvolver — uses inspection failure patterns to evolve prompts
   When agents repeatedly fail at specific inspection layers,
   their prompts are augmented with targeted improvement directives.

3. PerformanceTracker — tracks per-role, per-layer score distributions
   to identify which roles struggle at which quality dimensions.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.memory import Memory

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# 1. ADAPTIVE THRESHOLDS
# ─────────────────────────────────────────────────────────────────────────────

# Default thresholds (used when not enough data)
DEFAULT_CULL_THRESHOLD = 0.3
DEFAULT_PROMOTE_THRESHOLD = 0.8

# Guard rails — thresholds can't go outside these bounds
MIN_CULL_THRESHOLD = 0.15
MAX_CULL_THRESHOLD = 0.45
MIN_PROMOTE_THRESHOLD = 0.65
MAX_PROMOTE_THRESHOLD = 0.95

# Minimum sample size before we start adapting
MIN_SAMPLES_FOR_ADAPTATION = 5

# Target percentages: we want ~10% culled, ~15% promoted
TARGET_CULL_PERCENTILE = 10    # Bottom 10% should be below cull threshold
TARGET_PROMOTE_PERCENTILE = 85  # Top 15% should be above promote threshold


@dataclass
class ThresholdState:
    """Current adaptive threshold values with history."""
    cull: float = DEFAULT_CULL_THRESHOLD
    promote: float = DEFAULT_PROMOTE_THRESHOLD
    samples_used: int = 0
    history: list[dict] = field(default_factory=list)


class AdaptiveThresholds:
    """Population-calibrated thresholds for cull/promote decisions.

    Instead of fixed thresholds, we compute them from the actual
    score distribution. This means:
    - In a high-performing population, the cull bar rises (standards increase)
    - In a struggling population, the cull bar drops (more forgiving)
    - The promote bar adjusts so the top ~15% of agents qualify
    """

    def __init__(self):
        self.state = ThresholdState()

    def update(self, scores: list[float]) -> ThresholdState:
        """Recalculate thresholds based on the current score distribution.

        Args:
            scores: All agent average scores from the current population.

        Returns:
            Updated ThresholdState with new thresholds.
        """
        if len(scores) < MIN_SAMPLES_FOR_ADAPTATION:
            return self.state

        sorted_scores = sorted(scores)
        n = len(sorted_scores)

        # Compute percentile-based thresholds
        cull_idx = max(0, int(n * TARGET_CULL_PERCENTILE / 100) - 1)
        promote_idx = min(n - 1, int(n * TARGET_PROMOTE_PERCENTILE / 100))

        raw_cull = sorted_scores[cull_idx]
        raw_promote = sorted_scores[promote_idx]

        # Blend with current values (exponential moving average, alpha=0.3)
        alpha = 0.3
        new_cull = self.state.cull * (1 - alpha) + raw_cull * alpha
        new_promote = self.state.promote * (1 - alpha) + raw_promote * alpha

        # Apply guard rails
        new_cull = max(MIN_CULL_THRESHOLD, min(MAX_CULL_THRESHOLD, new_cull))
        new_promote = max(MIN_PROMOTE_THRESHOLD, min(MAX_PROMOTE_THRESHOLD, new_promote))

        # Ensure cull < promote (with gap)
        if new_cull >= new_promote - 0.2:
            new_cull = new_promote - 0.2

        new_cull = round(new_cull, 3)
        new_promote = round(new_promote, 3)

        self.state.cull = new_cull
        self.state.promote = new_promote
        self.state.samples_used = n
        self.state.history.append({
            "cull": new_cull,
            "promote": new_promote,
            "population_size": n,
            "mean_score": round(sum(scores) / n, 3),
            "median_score": round(sorted_scores[n // 2], 3),
        })

        return self.state

    def get_thresholds(self) -> tuple[float, float]:
        """Return (cull_threshold, promote_threshold)."""
        return self.state.cull, self.state.promote


# ─────────────────────────────────────────────────────────────────────────────
# 2. PROMPT EVOLUTION — score-driven prompt improvement
# ─────────────────────────────────────────────────────────────────────────────

# Maps inspection layer failures to targeted prompt improvements
LAYER_IMPROVEMENT_DIRECTIVES: dict[str, list[str]] = {
    "relevance": [
        "Read the task description carefully before responding. "
        "Your answer must directly address every part of the question asked.",
        "Stay focused on the specific task. Do not provide tangential information. "
        "If the task asks for X, respond only about X.",
        "Begin your response by restating the core question in your own words, "
        "then answer it systematically.",
    ],
    "rigor": [
        "Support every claim with evidence or reasoning. "
        "Do not make unsupported assertions.",
        "Be thorough: cover all aspects of the task. "
        "Check for completeness before submitting.",
        "Prioritize depth over breadth. A thorough analysis of key points "
        "is better than a shallow survey of many points.",
        "Use quantitative analysis where possible. Numbers, percentages, "
        "and comparisons strengthen your output.",
    ],
    "safety": [
        "Include appropriate risk disclaimers when recommending actions. "
        "Consider potential negative consequences.",
        "Before finalizing, review your output for any content that could "
        "cause harm if misused or taken out of context.",
        "When discussing sensitive topics, present balanced perspectives "
        "and acknowledge uncertainty.",
    ],
    "causal": [
        "Distinguish causation from correlation explicitly. "
        "When you identify a relationship, state whether it is causal or correlational.",
        "Consider alternative explanations and confounding variables "
        "before making causal claims.",
        "Use language that reflects your confidence: 'causes' vs 'is associated with' "
        "vs 'may contribute to'.",
    ],
}

# Maximum number of directives to append to a prompt
MAX_DIRECTIVES_PER_PROMPT = 3


@dataclass
class FailurePattern:
    """Tracks an agent's failure patterns across inspection layers."""
    role: str
    layer_failures: dict[str, int] = field(default_factory=dict)
    total_inspections: int = 0
    total_failures: int = 0

    @property
    def failure_rate(self) -> float:
        if self.total_inspections == 0:
            return 0.0
        return self.total_failures / self.total_inspections

    def worst_layer(self) -> str | None:
        """Return the layer with the most failures."""
        if not self.layer_failures:
            return None
        return max(self.layer_failures, key=self.layer_failures.get)  # type: ignore[arg-type]

    def weakest_layers(self, n: int = 2) -> list[str]:
        """Return the N layers with most failures, sorted by failure count."""
        if not self.layer_failures:
            return []
        sorted_layers = sorted(
            self.layer_failures.items(), key=lambda x: -x[1]
        )
        return [layer for layer, _count in sorted_layers[:n]]


class PromptEvolver:
    """Evolves agent prompts based on inspection failure patterns.

    Tracks which inspection layers agents fail at most often,
    then appends targeted improvement directives to their system prompts.

    This closes the feedback loop:
    score → failure analysis → prompt improvement → better scores
    """

    def __init__(self):
        self.patterns: dict[str, FailurePattern] = {}  # role → pattern
        self._directive_index: dict[str, int] = {}  # role:layer → next directive idx

    def record_inspection(self, role: str, layer_scores: dict[str, float],
                          layer_thresholds: dict[str, float]) -> None:
        """Record an inspection result for pattern analysis.

        Args:
            role: Agent role (e.g., "researcher")
            layer_scores: {layer_name: score} for each inspection layer
            layer_thresholds: {layer_name: threshold} for each layer
        """
        if role not in self.patterns:
            self.patterns[role] = FailurePattern(role=role)

        pattern = self.patterns[role]
        pattern.total_inspections += 1

        for layer, score in layer_scores.items():
            threshold = layer_thresholds.get(layer, 0.5)
            if score < threshold:
                pattern.layer_failures[layer] = pattern.layer_failures.get(layer, 0) + 1
                pattern.total_failures += 1

    def evolve_prompt(self, base_prompt: str, role: str,
                      min_inspections: int = 3) -> str:
        """Generate an improved prompt based on failure patterns.

        Only modifies the prompt if the role has enough inspection history
        and has failed at specific layers.

        Args:
            base_prompt: The original system prompt
            role: Agent role
            min_inspections: Minimum inspections before evolving

        Returns:
            The (possibly improved) prompt with targeted directives appended.
        """
        pattern = self.patterns.get(role)
        if not pattern or pattern.total_inspections < min_inspections:
            return base_prompt

        # Only evolve if there's a meaningful failure rate
        if pattern.failure_rate < 0.1:
            return base_prompt  # Under 10% failure → prompt is fine

        # Get the weakest layers
        weak_layers = pattern.weakest_layers(n=2)
        if not weak_layers:
            return base_prompt

        # Select directives for the weak layers
        directives = []
        for layer in weak_layers:
            available = LAYER_IMPROVEMENT_DIRECTIVES.get(layer, [])
            if not available:
                continue

            # Rotate through directives (don't always pick the same one)
            key = f"{role}:{layer}"
            idx = self._directive_index.get(key, 0)
            directive = available[idx % len(available)]
            self._directive_index[key] = idx + 1
            directives.append(directive)

            if len(directives) >= MAX_DIRECTIVES_PER_PROMPT:
                break

        if not directives:
            return base_prompt

        # Build the evolution suffix
        suffix = "\n\n## Performance Improvement Directives\n"
        suffix += "Based on quality review patterns, focus on these areas:\n"
        for i, d in enumerate(directives, 1):
            suffix += f"{i}. {d}\n"

        return base_prompt + suffix

    def get_role_report(self) -> dict[str, dict]:
        """Get a report of failure patterns by role."""
        report = {}
        for role, pattern in self.patterns.items():
            report[role] = {
                "total_inspections": pattern.total_inspections,
                "failure_rate": round(pattern.failure_rate, 3),
                "layer_failures": dict(pattern.layer_failures),
                "worst_layer": pattern.worst_layer(),
            }
        return report


# ─────────────────────────────────────────────────────────────────────────────
# 3. PERFORMANCE TRACKER — per-role, per-layer score tracking
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RolePerformance:
    """Aggregated performance data for a single role."""
    role: str
    scores: list[float] = field(default_factory=list)
    layer_scores: dict[str, list[float]] = field(default_factory=dict)

    @property
    def mean_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(self.scores) / len(self.scores)

    @property
    def score_trend(self) -> float:
        """Linear regression slope over recent scores. Positive = improving."""
        if len(self.scores) < 3:
            return 0.0
        recent = self.scores[-20:]  # Last 20 scores
        n = len(recent)
        x_mean = (n - 1) / 2.0
        y_mean = sum(recent) / n
        num = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(recent))
        den = sum((i - x_mean) ** 2 for i in range(n))
        if den == 0:
            return 0.0
        return num / den

    def layer_mean(self, layer: str) -> float:
        scores = self.layer_scores.get(layer, [])
        if not scores:
            return 0.0
        return sum(scores) / len(scores)


class PerformanceTracker:
    """Tracks performance metrics per role to guide evolution decisions.

    Answers questions like:
    - "Which roles are improving vs declining?"
    - "Which inspection layer is hardest for coders?"
    - "Are researchers getting better at rigor over time?"
    """

    def __init__(self):
        self.roles: dict[str, RolePerformance] = {}

    def record(self, role: str, final_score: float,
               layer_scores: dict[str, float] | None = None) -> None:
        """Record a score for a role."""
        if role not in self.roles:
            self.roles[role] = RolePerformance(role=role)

        rp = self.roles[role]
        rp.scores.append(final_score)

        if layer_scores:
            for layer, score in layer_scores.items():
                if layer not in rp.layer_scores:
                    rp.layer_scores[layer] = []
                rp.layer_scores[layer].append(score)

    def get_all_scores(self) -> list[float]:
        """Get all scores across all roles (for threshold calibration)."""
        all_scores = []
        for rp in self.roles.values():
            all_scores.extend(rp.scores)
        return all_scores

    def get_role_summary(self, role: str) -> dict | None:
        """Get performance summary for a specific role."""
        rp = self.roles.get(role)
        if not rp:
            return None
        return {
            "role": role,
            "total_scores": len(rp.scores),
            "mean_score": round(rp.mean_score, 3),
            "trend": round(rp.score_trend, 4),
            "layer_means": {
                layer: round(rp.layer_mean(layer), 3)
                for layer in rp.layer_scores
            },
        }

    def get_improving_roles(self) -> list[str]:
        """Roles with positive score trends (getting better)."""
        return [
            role for role, rp in self.roles.items()
            if rp.score_trend > 0.005
        ]

    def get_declining_roles(self) -> list[str]:
        """Roles with negative score trends (getting worse)."""
        return [
            role for role, rp in self.roles.items()
            if rp.score_trend < -0.005
        ]

    def suggest_mutation_rate(self, role: str) -> float:
        """Suggest a mutation rate based on performance.

        - High-performing, stable roles → low mutation (0.05-0.10)
        - Declining roles → high mutation (0.20-0.30) — need to change
        - Improving roles → moderate mutation (0.10-0.15) — keep evolving
        - Low-performing → high mutation (0.25) — try something different
        """
        rp = self.roles.get(role)
        if not rp or len(rp.scores) < 3:
            return 0.15  # Default

        trend = rp.score_trend
        mean = rp.mean_score

        if mean >= 0.8 and trend >= 0:
            return 0.05  # Top performer, don't break it
        elif mean >= 0.6 and trend > 0:
            return 0.10  # Good and improving, gentle mutation
        elif trend > 0:
            return 0.15  # Improving but still mid, keep evolving
        elif mean < 0.4:
            return 0.25  # Low performer, shake things up
        elif trend < -0.01:
            return 0.25  # Actively declining, needs change
        else:
            return 0.15  # Stable but mediocre

    def print_dashboard(self) -> None:
        """Print a performance dashboard."""
        if not self.roles:
            console.print("  [dim]No performance data yet.[/dim]")
            return

        table = Table(title="Role Performance Dashboard")
        table.add_column("Role", style="cyan")
        table.add_column("N", justify="right")
        table.add_column("Mean", justify="center")
        table.add_column("Trend", justify="center")
        table.add_column("Relevance", justify="center")
        table.add_column("Rigor", justify="center")
        table.add_column("Safety", justify="center")
        table.add_column("Mutation", justify="center")

        for role in sorted(self.roles):
            rp = self.roles[role]
            trend = rp.score_trend
            trend_icon = "^" if trend > 0.005 else "v" if trend < -0.005 else "="
            trend_color = "green" if trend > 0.005 else "red" if trend < -0.005 else "yellow"

            mean = rp.mean_score
            mean_color = "green" if mean >= 0.7 else "yellow" if mean >= 0.4 else "red"

            mut_rate = self.suggest_mutation_rate(role)

            def _layer_cell(layer: str) -> str:
                m = rp.layer_mean(layer)
                if m == 0:
                    return "[dim]-[/dim]"
                c = "green" if m >= 0.7 else "yellow" if m >= 0.4 else "red"
                return f"[{c}]{m:.2f}[/{c}]"

            table.add_row(
                role,
                str(len(rp.scores)),
                f"[{mean_color}]{mean:.2f}[/{mean_color}]",
                f"[{trend_color}]{trend_icon} {trend:+.3f}[/{trend_color}]",
                _layer_cell("relevance"),
                _layer_cell("rigor"),
                _layer_cell("safety"),
                f"{mut_rate:.2f}",
            )

        console.print(Panel(table))

        improving = self.get_improving_roles()
        declining = self.get_declining_roles()
        if improving:
            console.print(f"  [green]Improving:[/green] {', '.join(improving)}")
        if declining:
            console.print(f"  [red]Declining:[/red] {', '.join(declining)}")
