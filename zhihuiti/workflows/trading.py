"""Trading workflow — 梅教授 agent team pattern for signal discovery and backtest review.

Implements the multi-agent research pipeline:
  Governor → N Researchers → Coder → Auditor → Judge → Governor (synthesis)

Usage:
  wf = TradingWorkflow(model="deepseek-chat")
  result = wf.search_signals("BTC 4H momentum divergence")
  review = wf.backtest_review(pasted_results="...")
"""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zhihuiti.llm import LLM

console = Console()

# ---------------------------------------------------------------------------
# Signal types explored by the researcher agents
# ---------------------------------------------------------------------------

SIGNAL_TYPES: list[str] = [
    "momentum",
    "volume",
    "order_flow",
    "volatility",
    "sentiment",
]

# ---------------------------------------------------------------------------
# Prompts for each role in the 梅教授 team
# ---------------------------------------------------------------------------

_GOVERNOR_DECOMPOSE_PROMPT = """\
You are the Governor (总督) of a quantitative trading signal research team.
Your job is to decompose a signal-search request into concrete research tasks,
one per signal type: {signal_types}.

For each signal type, output a JSON array of objects:
[
  {{"signal_type": "momentum", "hypothesis": "...", "search_guidance": "..."}},
  ...
]

Be specific. Each hypothesis should be a testable claim about price behaviour.
"""

_RESEARCHER_PROMPT = """\
You are a quantitative Researcher (研究员) specialising in **{signal_type}** signals.

Given the hypothesis and guidance below, explore the signal space and produce:
1. A refined hypothesis with entry/exit logic
2. Key indicators and thresholds
3. Edge cases and failure modes
4. Suggested Pine Script indicator names / built-in functions

Respond in JSON:
{{
  "signal_type": "{signal_type}",
  "hypothesis": "...",
  "entry_logic": "...",
  "exit_logic": "...",
  "indicators": ["..."],
  "edge_cases": ["..."],
  "pine_hints": ["..."]
}}
"""

_CODER_PROMPT = """\
You are a Pine Script Coder (编码员).
Given the research findings below, write a complete TradingView Pine Script v5 strategy.

Requirements:
- Use //@version=5 and strategy() declaration
- Include proper entry and exit conditions
- Add reasonable default parameters with input()
- Include basic risk management (stop loss / take profit)
- Add overlay plots and background highlighting for signals

Return ONLY the Pine Script code, no markdown fences.
"""

_AUDITOR_PROMPT = """\
You are a Code Auditor (审计员) reviewing Pine Script for correctness and quality.

Check for:
1. Syntax errors or deprecated functions
2. Look-ahead bias (using future data)
3. Repainting issues
4. Missing null/na checks
5. Overfitting risks (too many hard-coded magic numbers)
6. Risk management completeness

Return JSON:
{{
  "passed": true/false,
  "issues": ["..."],
  "suggestions": ["..."],
  "severity": "low|medium|high",
  "corrected_code": "..." // only if passed is false
}}
"""

_JUDGE_PROMPT = """\
You are the Judge (裁判) scoring a trading signal on two dimensions.

Score each 0-10:
- **novelty**: How original is this signal vs. common retail strategies?
- **soundness**: How theoretically and empirically grounded is the logic?

Return JSON:
{{
  "novelty": 0-10,
  "soundness": 0-10,
  "verdict": "...",
  "strengths": ["..."],
  "weaknesses": ["..."]
}}
"""

_GOVERNOR_SYNTHESIZE_PROMPT = """\
You are the Governor (总督) synthesizing the final report.
You have received research from multiple signal types, coded strategies,
audit results, and judge scores.

Produce a concise executive summary in JSON:
{{
  "top_signals": [
    {{
      "signal_type": "...",
      "score": 0-10,
      "summary": "...",
      "pine_script": "..."
    }}
  ],
  "overall_assessment": "...",
  "recommended_next_steps": ["..."]
}}

Rank signals by combined novelty + soundness. Include the best Pine Script.
"""

_BACKTEST_REVIEW_PROMPT = """\
You are a quantitative trading analyst reviewing TradingView backtest results.

Analyze the pasted results and provide:
1. Performance summary (win rate, profit factor, max drawdown, Sharpe estimate)
2. Identified weaknesses (curve fitting, low trade count, drawdown risk)
3. Suggested improvements (parameter tuning, filters, risk management)
4. Overall verdict: deploy / paper-trade / reject

Return JSON:
{{
  "performance": {{
    "win_rate": "...",
    "profit_factor": "...",
    "max_drawdown": "...",
    "sharpe_estimate": "...",
    "total_trades": "...",
    "net_profit": "..."
  }},
  "weaknesses": ["..."],
  "improvements": ["..."],
  "verdict": "deploy|paper_trade|reject",
  "explanation": "..."
}}
"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ResearchResult:
    """Output from a single researcher agent."""

    signal_type: str
    hypothesis: str
    entry_logic: str = ""
    exit_logic: str = ""
    indicators: list[str] = field(default_factory=list)
    edge_cases: list[str] = field(default_factory=list)
    pine_hints: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditResult:
    """Output from the auditor agent."""

    passed: bool
    issues: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    severity: str = "low"
    corrected_code: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgeScore:
    """Output from the judge agent."""

    novelty: float = 0.0
    soundness: float = 0.0
    verdict: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SignalSearchResult:
    """Complete output of a search_signals() run."""

    run_id: str
    query: str
    research: list[ResearchResult]
    pine_script: str
    audit: AuditResult
    score: JudgeScore
    synthesis: dict[str, Any]


@dataclass
class BacktestReviewResult:
    """Output of a backtest_review() run."""

    run_id: str
    performance: dict[str, str]
    weaknesses: list[str]
    improvements: list[str]
    verdict: str
    explanation: str
    raw: dict[str, Any]


# ---------------------------------------------------------------------------
# TradingWorkflow
# ---------------------------------------------------------------------------

class TradingWorkflow:
    """Multi-agent trading signal discovery and backtest review workflow.

    Implements the 梅教授 (Professor Mei) agent team pattern:

    1. **Governor** decomposes the signal search request
    2. **N Researchers** explore different signal types in parallel
       (momentum, volume, order_flow, volatility, sentiment)
    3. **Coder** converts the best hypotheses into Pine Script
    4. **Auditor** reviews the code for correctness and bias
    5. **Judge** scores on novelty + soundness
    6. **Governor** synthesizes the final report

    Example::

        wf = TradingWorkflow(model="deepseek-chat")
        result = wf.search_signals("BTC 4H mean-reversion after volume spike")
        print(result.pine_script)
    """

    def __init__(
        self,
        model: str | None = None,
        max_workers: int = 4,
        signal_types: list[str] | None = None,
    ) -> None:
        """Initialise the trading workflow.

        Args:
            model: LLM model name (uses LLM auto-detection if None).
            max_workers: Maximum parallel researcher agents.
            signal_types: Override default signal types to explore.
        """
        self.llm = LLM(model=model)
        self.max_workers = max_workers
        self.signal_types = signal_types or SIGNAL_TYPES

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search_signals(self, query: str) -> SignalSearchResult:
        """Run the full 梅教授 agent team pipeline to discover trading signals.

        Args:
            query: Natural-language description of the desired signal
                   (e.g. "BTC 4H momentum divergence with volume confirmation").

        Returns:
            SignalSearchResult with research, Pine Script, audit, and scores.
        """
        run_id = uuid.uuid4().hex[:12]
        console.print(Panel(
            f"[bold]Signal Search:[/bold] {query}",
            title="梅教授 Trading Workflow",
            border_style="cyan",
        ))

        # Step 1: Governor decomposes
        console.print("\n[bold cyan]Step 1/6:[/bold cyan] Governor decomposing request...")
        tasks = self._governor_decompose(query)

        # Step 2: Researchers explore in parallel
        console.print(f"\n[bold cyan]Step 2/6:[/bold cyan] {len(tasks)} researchers exploring signals...")
        research_results = self._run_researchers(tasks)

        # Step 3: Coder generates Pine Script
        console.print("\n[bold cyan]Step 3/6:[/bold cyan] Coder generating Pine Script...")
        pine_script = self._coder_generate(query, research_results)

        # Step 4: Auditor reviews
        console.print("\n[bold cyan]Step 4/6:[/bold cyan] Auditor reviewing code...")
        audit = self._auditor_review(pine_script)

        # Use corrected code if auditor provided one
        if not audit.passed and audit.corrected_code:
            console.print("  [yellow]Auditor provided corrections, using corrected code[/yellow]")
            pine_script = audit.corrected_code

        # Step 5: Judge scores
        console.print("\n[bold cyan]Step 5/6:[/bold cyan] Judge scoring signal...")
        score = self._judge_score(query, research_results, pine_script)

        # Step 6: Governor synthesizes
        console.print("\n[bold cyan]Step 6/6:[/bold cyan] Governor synthesizing report...")
        synthesis = self._governor_synthesize(query, research_results, pine_script, audit, score)

        result = SignalSearchResult(
            run_id=run_id,
            query=query,
            research=research_results,
            pine_script=pine_script,
            audit=audit,
            score=score,
            synthesis=synthesis,
        )

        self._print_search_summary(result)
        return result

    def backtest_review(self, pasted_results: str) -> BacktestReviewResult:
        """Analyze pasted TradingView backtest results.

        Args:
            pasted_results: Raw text copied from TradingView's strategy tester
                            (performance summary, trade list, etc.).

        Returns:
            BacktestReviewResult with performance metrics, weaknesses, and verdict.
        """
        run_id = uuid.uuid4().hex[:12]
        console.print(Panel(
            f"[bold]Backtest Review[/bold] ({len(pasted_results)} chars)",
            title="梅教授 Trading Workflow",
            border_style="green",
        ))

        raw = self.llm.chat_json(
            system=_BACKTEST_REVIEW_PROMPT,
            user=f"Here are the TradingView backtest results to analyze:\n\n{pasted_results}",
            temperature=0.3,
        )
        if not isinstance(raw, dict):
            raw = {"error": str(raw)}

        result = BacktestReviewResult(
            run_id=run_id,
            performance=raw.get("performance", {}),
            weaknesses=raw.get("weaknesses", []),
            improvements=raw.get("improvements", []),
            verdict=raw.get("verdict", "unknown"),
            explanation=raw.get("explanation", ""),
            raw=raw,
        )

        self._print_review_summary(result)
        return result

    # ------------------------------------------------------------------
    # Internal pipeline steps
    # ------------------------------------------------------------------

    def _governor_decompose(self, query: str) -> list[dict[str, Any]]:
        """Governor agent decomposes the query into per-signal-type research tasks."""
        prompt = _GOVERNOR_DECOMPOSE_PROMPT.format(
            signal_types=", ".join(self.signal_types),
        )
        raw = self.llm.chat_json(
            system=prompt,
            user=f"Signal search request: {query}",
            temperature=0.5,
        )
        if not isinstance(raw, list):
            raw = [raw]

        for task in raw:
            st = task.get("signal_type", "")
            hyp = task.get("hypothesis", "")[:80]
            console.print(f"  [dim]{st}:[/dim] {hyp}")

        return raw

    def _run_researchers(self, tasks: list[dict[str, Any]]) -> list[ResearchResult]:
        """Run researcher agents in parallel, one per signal type."""
        results: list[ResearchResult] = []

        def _research_one(task: dict[str, Any]) -> ResearchResult:
            signal_type = task.get("signal_type", "unknown")
            prompt = _RESEARCHER_PROMPT.format(signal_type=signal_type)
            user_msg = (
                f"Hypothesis: {task.get('hypothesis', 'N/A')}\n"
                f"Guidance: {task.get('search_guidance', 'N/A')}"
            )
            raw = self.llm.chat_json(system=prompt, user=user_msg, temperature=0.6)
            if not isinstance(raw, dict):
                raw = {"signal_type": signal_type, "hypothesis": str(raw)}

            res = ResearchResult(
                signal_type=raw.get("signal_type", signal_type),
                hypothesis=raw.get("hypothesis", ""),
                entry_logic=raw.get("entry_logic", ""),
                exit_logic=raw.get("exit_logic", ""),
                indicators=raw.get("indicators", []),
                edge_cases=raw.get("edge_cases", []),
                pine_hints=raw.get("pine_hints", []),
                raw=raw,
            )
            console.print(f"  [green]Done:[/green] {signal_type} — {res.hypothesis[:60]}")
            return res

        if len(tasks) > 1:
            with ThreadPoolExecutor(max_workers=min(len(tasks), self.max_workers)) as pool:
                futures = {pool.submit(_research_one, t): t for t in tasks}
                for future in as_completed(futures):
                    results.append(future.result())
        else:
            results = [_research_one(t) for t in tasks]

        return results

    def _coder_generate(self, query: str, research: list[ResearchResult]) -> str:
        """Coder agent converts research findings into Pine Script."""
        research_summary = "\n\n".join(
            f"## {r.signal_type}\n"
            f"Hypothesis: {r.hypothesis}\n"
            f"Entry: {r.entry_logic}\n"
            f"Exit: {r.exit_logic}\n"
            f"Indicators: {', '.join(r.indicators)}\n"
            f"Pine hints: {', '.join(r.pine_hints)}"
            for r in research
        )

        pine_script = self.llm.chat(
            system=_CODER_PROMPT,
            user=(
                f"Original request: {query}\n\n"
                f"Research findings:\n{research_summary}"
            ),
            temperature=0.3,
        )

        # Strip markdown fences if the LLM added them anyway
        cleaned = pine_script.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines)

        line_count = len(cleaned.split("\n"))
        console.print(f"  [green]Generated {line_count} lines of Pine Script[/green]")
        return cleaned

    def _auditor_review(self, pine_script: str) -> AuditResult:
        """Auditor agent reviews the Pine Script for correctness."""
        raw = self.llm.chat_json(
            system=_AUDITOR_PROMPT,
            user=f"Review this Pine Script:\n\n{pine_script}",
            temperature=0.2,
        )
        if not isinstance(raw, dict):
            raw = {"passed": False, "issues": [str(raw)]}

        result = AuditResult(
            passed=bool(raw.get("passed", False)),
            issues=raw.get("issues", []),
            suggestions=raw.get("suggestions", []),
            severity=raw.get("severity", "low"),
            corrected_code=raw.get("corrected_code"),
            raw=raw,
        )

        status = "[green]PASSED[/green]" if result.passed else f"[red]FAILED ({result.severity})[/red]"
        console.print(f"  Audit: {status}")
        for issue in result.issues[:3]:
            console.print(f"    [yellow]- {issue}[/yellow]")

        return result

    def _judge_score(
        self,
        query: str,
        research: list[ResearchResult],
        pine_script: str,
    ) -> JudgeScore:
        """Judge agent scores the signal on novelty and soundness."""
        research_summary = "\n".join(
            f"- {r.signal_type}: {r.hypothesis[:100]}" for r in research
        )
        raw = self.llm.chat_json(
            system=_JUDGE_PROMPT,
            user=(
                f"Query: {query}\n\n"
                f"Research:\n{research_summary}\n\n"
                f"Pine Script:\n{pine_script[:2000]}"
            ),
            temperature=0.3,
        )
        if not isinstance(raw, dict):
            raw = {"novelty": 0, "soundness": 0, "verdict": str(raw)}

        result = JudgeScore(
            novelty=float(raw.get("novelty", 0)),
            soundness=float(raw.get("soundness", 0)),
            verdict=raw.get("verdict", ""),
            strengths=raw.get("strengths", []),
            weaknesses=raw.get("weaknesses", []),
            raw=raw,
        )

        combined = (result.novelty + result.soundness) / 2
        style = "green" if combined >= 7 else "yellow" if combined >= 5 else "red"
        console.print(
            f"  Novelty: [{style}]{result.novelty:.0f}/10[/{style}] | "
            f"Soundness: [{style}]{result.soundness:.0f}/10[/{style}] | "
            f"Combined: [{style}]{combined:.1f}[/{style}]"
        )

        return result

    def _governor_synthesize(
        self,
        query: str,
        research: list[ResearchResult],
        pine_script: str,
        audit: AuditResult,
        score: JudgeScore,
    ) -> dict[str, Any]:
        """Governor agent synthesizes all outputs into a final report."""
        context = (
            f"Original query: {query}\n\n"
            f"Research findings ({len(research)} signal types):\n"
            + "\n".join(
                f"- {r.signal_type}: {r.hypothesis}" for r in research
            )
            + f"\n\nPine Script ({len(pine_script.split(chr(10)))} lines):\n{pine_script[:3000]}\n\n"
            f"Audit: {'PASSED' if audit.passed else 'FAILED'} "
            f"(severity={audit.severity}, issues={len(audit.issues)})\n\n"
            f"Judge: novelty={score.novelty}, soundness={score.soundness}\n"
            f"Verdict: {score.verdict}"
        )

        raw = self.llm.chat_json(
            system=_GOVERNOR_SYNTHESIZE_PROMPT,
            user=context,
            temperature=0.4,
        )
        if not isinstance(raw, dict):
            raw = {"overall_assessment": str(raw)}

        console.print(f"  [green]Synthesis complete[/green]")
        return raw

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def _print_search_summary(self, result: SignalSearchResult) -> None:
        """Print a rich summary table for signal search results."""
        console.print()

        # Research table
        table = Table(title="Signal Research Summary")
        table.add_column("Signal Type", style="cyan")
        table.add_column("Hypothesis", max_width=50)
        table.add_column("Indicators")

        for r in result.research:
            table.add_row(
                r.signal_type,
                r.hypothesis[:50],
                ", ".join(r.indicators[:3]) if r.indicators else "—",
            )
        console.print(table)

        # Score panel
        combined = (result.score.novelty + result.score.soundness) / 2
        style = "green" if combined >= 7 else "yellow" if combined >= 5 else "red"
        console.print(Panel(
            f"Novelty: {result.score.novelty:.0f}/10 | "
            f"Soundness: {result.score.soundness:.0f}/10 | "
            f"Combined: [{style}]{combined:.1f}/10[/{style}]\n"
            f"Audit: {'PASSED' if result.audit.passed else 'FAILED'} "
            f"({result.audit.severity})\n"
            f"Verdict: {result.score.verdict}",
            title="Judge Score",
            border_style=style,
        ))

        # Pine Script preview
        lines = result.pine_script.split("\n")
        preview = "\n".join(lines[:15])
        if len(lines) > 15:
            preview += f"\n... ({len(lines) - 15} more lines)"
        console.print(Panel(preview, title="Pine Script (preview)", border_style="dim"))

        # Synthesis
        synthesis = result.synthesis
        if "overall_assessment" in synthesis:
            console.print(Panel(
                synthesis["overall_assessment"],
                title="Governor Assessment",
                border_style="cyan",
            ))

        console.print(f"\n[dim]Run ID: {result.run_id}[/dim]\n")

    def _print_review_summary(self, result: BacktestReviewResult) -> None:
        """Print a rich summary for backtest review results."""
        console.print()

        # Performance table
        if result.performance:
            table = Table(title="Backtest Performance")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", justify="right")
            for k, v in result.performance.items():
                table.add_row(k.replace("_", " ").title(), str(v))
            console.print(table)

        # Verdict
        verdict_style = {
            "deploy": "green",
            "paper_trade": "yellow",
            "reject": "red",
        }.get(result.verdict, "white")

        console.print(Panel(
            f"[{verdict_style}]{result.verdict.upper()}[/{verdict_style}]\n\n"
            f"{result.explanation}",
            title="Verdict",
            border_style=verdict_style,
        ))

        # Weaknesses and improvements
        if result.weaknesses:
            console.print("\n[bold]Weaknesses:[/bold]")
            for w in result.weaknesses:
                console.print(f"  [red]- {w}[/red]")

        if result.improvements:
            console.print("\n[bold]Suggested Improvements:[/bold]")
            for imp in result.improvements:
                console.print(f"  [green]- {imp}[/green]")

        console.print(f"\n[dim]Run ID: {result.run_id}[/dim]\n")
