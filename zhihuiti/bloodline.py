"""Bloodline system (血缘/繁衍) — multi-parent agent breeding and lineage tracing.

Modeled after 如老师's genetics architecture:
- Two agents merge into one child, inheriting both parents' strengths
- Each agent has a lineage_id (gene_id) tracked in the lineage table
- Ancestry can be traced back 7 generations
- 诛七族: when a bug is found, trace descendants to find contaminated genes
- Culled agents' knowledge survives through their children
"""

from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from zhihuiti.models import AgentConfig, AgentRole

if TYPE_CHECKING:
    from zhihuiti.memory import Memory

console = Console()

MAX_GENERATIONS = 7      # How far back ancestry can be traced
MUTATION_RATE = 0.15     # Default probability of a trait mutating during breeding
CROSSOVER_BIAS = 0.6     # Bias toward higher-scoring parent's traits

# Fitness-proportional selection constants
FITNESS_SELECTION_POWER = 2.0   # Higher = more elitist selection
MIN_MUTATION_RATE = 0.03        # Floor — even best agents get some variation
MAX_MUTATION_RATE = 0.35        # Ceiling — don't make everything random


@dataclass
class BreedResult:
    """Result of breeding two agents."""
    child_config: AgentConfig
    parent_a_gene: str
    parent_b_gene: str
    generation: int
    mutation_notes: str
    traits_from_a: list[str] = field(default_factory=list)
    traits_from_b: list[str] = field(default_factory=list)
    mutations: list[str] = field(default_factory=list)


class Bloodline:
    """Manages agent genetics — breeding, lineage tracking, and ancestry tracing."""

    def __init__(self, memory: Memory):
        self.memory = memory

    # ------------------------------------------------------------------
    # Registration: track an agent's gene in the lineage table
    # ------------------------------------------------------------------

    def register(self, config: AgentConfig, agent_id: str | None = None,
                 avg_score: float = 0.0) -> str:
        """Register an agent's gene in the lineage table. Returns gene_id."""
        gene_id = config.gene_id or uuid.uuid4().hex[:12]
        config.gene_id = gene_id
        config.lineage_id = gene_id

        self.memory.save_lineage(
            gene_id=gene_id,
            role=config.role.value,
            generation=config.generation,
            parent_a_gene=config.parent_a_gene,
            parent_b_gene=config.parent_b_gene,
            avg_score=avg_score,
            alive=True,
            agent_id=agent_id,
            temperature=config.temperature,
            mutation_notes=config.mutation_notes,
        )
        return gene_id

    def update_score(self, gene_id: str, avg_score: float, alive: bool = True) -> None:
        """Update a gene's performance score."""
        self.memory.update_lineage_score(gene_id, avg_score, alive)

    def mark_dead(self, gene_id: str, avg_score: float) -> None:
        """Mark a gene as dead (agent culled)."""
        self.update_score(gene_id, avg_score, alive=False)

    # ------------------------------------------------------------------
    # Breeding: sexual reproduction — merge two agents into one child
    # ------------------------------------------------------------------

    def breed(self, parent_a: AgentConfig, parent_b: AgentConfig,
              score_a: float = 0.5, score_b: float = 0.5,
              mutation_rate: float | None = None) -> BreedResult:
        """Breed two agents into a new child agent.

        Crossover logic:
        - Temperature: weighted average biased toward better parent
        - System prompt: merge the stronger parent's prompt with mutations
        - Budget/depth: inherit from better parent
        - Gene ID: new unique ID with both parents tracked

        Mutation:
        - Rate is adaptive (from PerformanceTracker) or default MUTATION_RATE
        - Small random changes to temperature
        - Possible prompt emphasis shifts
        """
        effective_mutation_rate = mutation_rate if mutation_rate is not None else MUTATION_RATE
        # Clamp to bounds
        effective_mutation_rate = max(MIN_MUTATION_RATE, min(MAX_MUTATION_RATE, effective_mutation_rate))

        # Determine which parent is dominant (higher score)
        if score_a >= score_b:
            dominant, recessive = parent_a, parent_b
            dom_score, rec_score = score_a, score_b
        else:
            dominant, recessive = parent_b, parent_a
            dom_score, rec_score = score_b, score_a

        traits_from_dom = []
        traits_from_rec = []
        mutations = []

        # --- Temperature crossover ---
        weight = CROSSOVER_BIAS if dom_score > rec_score else 0.5
        child_temp = dominant.temperature * weight + recessive.temperature * (1 - weight)

        # Mutation on temperature (uses adaptive rate)
        if random.random() < effective_mutation_rate:
            # Scale delta by mutation rate — higher rate = bigger jumps
            max_delta = 0.1 + 0.2 * effective_mutation_rate
            delta = random.uniform(-max_delta, max_delta)
            child_temp = max(0.1, min(1.0, child_temp + delta))
            mutations.append(f"temp_mutation({delta:+.2f})")
        child_temp = round(child_temp, 2)
        traits_from_dom.append(f"temperature_base({dominant.temperature})")

        # --- System prompt crossover ---
        # Use dominant parent's prompt as base, but append recessive's
        # unique capabilities if any
        child_prompt = dominant.system_prompt
        traits_from_dom.append("system_prompt_base")

        # Extract any unique instructions from recessive parent
        rec_unique = _extract_unique_segments(recessive.system_prompt, dominant.system_prompt)
        if rec_unique and random.random() < 0.5:
            child_prompt += f"\n\nInherited trait: {rec_unique[:200]}"
            traits_from_rec.append("inherited_prompt_segment")

        # Mutation on prompt emphasis (uses adaptive rate)
        if random.random() < effective_mutation_rate:
            emphasis = random.choice([
                "\nFocus especially on accuracy and verification.",
                "\nPrioritize efficiency and conciseness.",
                "\nEmphasize creative and novel approaches.",
                "\nFocus on practical, actionable outputs.",
                "\nPrioritize structured, well-organized responses.",
                "\nEmphasize quantitative reasoning and evidence.",
            ])
            child_prompt += emphasis
            mutations.append(f"prompt_emphasis(rate={effective_mutation_rate:.2f})")

        # --- Role: inherit from dominant ---
        child_role = dominant.role
        traits_from_dom.append(f"role({child_role.value})")

        # --- Generation: max of parents + 1 ---
        child_generation = max(parent_a.generation, parent_b.generation) + 1

        # --- StrategyGenome crossover ---
        child_genome = None
        if parent_a.genome is not None and parent_b.genome is not None:
            from zhihuiti.genome import crossover as genome_crossover
            from zhihuiti.genome import mutate as genome_mutate
            child_genome = genome_crossover(
                dominant.genome, recessive.genome, bias=weight,
            )
            child_genome = genome_mutate(child_genome, rate=effective_mutation_rate)
            mutations.append("genome_crossover+mutate")
        elif parent_a.genome is not None:
            child_genome = parent_a.genome
        elif parent_b.genome is not None:
            child_genome = parent_b.genome

        # --- Build child config ---
        child_gene_id = uuid.uuid4().hex[:12]
        child_config = AgentConfig(
            role=child_role,
            system_prompt=child_prompt,
            budget=dominant.budget,
            max_depth=dominant.max_depth,
            temperature=child_temp,
            gene_id=child_gene_id,
            parent_gene_id=dominant.gene_id,  # backward compat
            mutation_notes=f"bred from {parent_a.gene_id}+{parent_b.gene_id}",
            lineage_id=child_gene_id,
            parent_a_gene=parent_a.gene_id,
            parent_b_gene=parent_b.gene_id,
            generation=child_generation,
            genome=child_genome,
        )

        result = BreedResult(
            child_config=child_config,
            parent_a_gene=parent_a.gene_id or "unknown",
            parent_b_gene=parent_b.gene_id or "unknown",
            generation=child_generation,
            mutation_notes=", ".join(mutations) if mutations else "clean crossover",
            traits_from_a=traits_from_dom if score_a >= score_b else traits_from_rec,
            traits_from_b=traits_from_rec if score_a >= score_b else traits_from_dom,
            mutations=mutations,
        )

        console.print(
            f"  [magenta]🧬 Bred[/magenta] gen-{child_generation} "
            f"{child_role.value} [dim]{child_gene_id}[/dim] "
            f"from {parent_a.gene_id} × {parent_b.gene_id}"
        )
        if mutations:
            console.print(f"    [dim]Mutations: {', '.join(mutations)}[/dim]")

        return result

    def breed_from_pool(self, role: AgentRole,
                        mutation_rate: float | None = None) -> AgentConfig | None:
        """Select two parents via fitness-proportional selection and breed them.

        Uses fitness^FITNESS_SELECTION_POWER weighting so top performers breed
        disproportionately more often. This is tournament selection with
        continuous weights — better than uniform random.

        Args:
            role: The agent role to breed for.
            mutation_rate: Adaptive mutation rate (from PerformanceTracker).
                If None, uses the default MUTATION_RATE.

        Returns a new child AgentConfig, or None if not enough parents.
        """
        candidates = self.memory.get_top_lineage_genes(role.value, limit=10)
        if len(candidates) < 2:
            return None

        # Fitness-proportional selection — score^power weighting
        weights = [
            (max(c["avg_score"], 0.01)) ** FITNESS_SELECTION_POWER
            for c in candidates
        ]

        # Weighted sampling without replacement
        parent_a_info, parent_b_info = _weighted_sample_two(candidates, weights)

        # Reconstruct AgentConfigs from lineage data
        from zhihuiti.prompts import get_prompt
        parent_a = AgentConfig(
            role=role,
            system_prompt=get_prompt(role.value),
            temperature=parent_a_info.get("temperature", 0.7),
            gene_id=parent_a_info["gene_id"],
            generation=parent_a_info["generation"],
            parent_a_gene=parent_a_info.get("parent_a_gene"),
            parent_b_gene=parent_a_info.get("parent_b_gene"),
        )
        parent_b = AgentConfig(
            role=role,
            system_prompt=get_prompt(role.value),
            temperature=parent_b_info.get("temperature", 0.7),
            gene_id=parent_b_info["gene_id"],
            generation=parent_b_info["generation"],
            parent_a_gene=parent_b_info.get("parent_a_gene"),
            parent_b_gene=parent_b_info.get("parent_b_gene"),
        )

        result = self.breed(
            parent_a, parent_b,
            score_a=parent_a_info["avg_score"],
            score_b=parent_b_info["avg_score"],
            mutation_rate=mutation_rate,
        )

        # Register the child in lineage
        self.register(result.child_config)

        return result.child_config

    # ------------------------------------------------------------------
    # Ancestry tracing — trace_ancestors / trace_descendants / 诛七族
    # ------------------------------------------------------------------

    def trace_ancestors(self, gene_id: str, max_depth: int = MAX_GENERATIONS) -> list[dict]:
        """Trace an agent's ancestry up to max_depth generations."""
        return self.memory.get_lineage_ancestors(gene_id, max_depth)

    def trace_descendants(self, gene_id: str, max_depth: int = MAX_GENERATIONS) -> list[dict]:
        """Find all descendants of a gene."""
        return self.memory.get_lineage_descendants(gene_id, max_depth)

    def zhu_qi_zu(self, gene_id: str) -> list[dict]:
        """诛七族 — purge all descendants of a problematic gene.

        Marks all descendants as dead. Returns the list of purged genes.
        """
        descendants = self.trace_descendants(gene_id, max_depth=MAX_GENERATIONS)

        purged = []
        for desc in descendants:
            self.mark_dead(desc["gene_id"], desc["avg_score"])
            purged.append(desc)

        # Also mark the source gene itself
        self.mark_dead(gene_id, 0.0)

        if purged:
            console.print(
                f"\n  [bold red]⚔ 诛七族:[/bold red] Purged {len(purged)} descendants "
                f"of gene [dim]{gene_id}[/dim]"
            )
            for p in purged:
                console.print(
                    f"    [red]☠[/red] gen-{p['generation']} "
                    f"{p['role']} [dim]{p['gene_id']}[/dim] "
                    f"(score={p['avg_score']:.2f})"
                )
        else:
            console.print(
                f"  [dim]Gene {gene_id} has no descendants to purge.[/dim]"
            )

        return purged

    # ------------------------------------------------------------------
    # Visualization
    # ------------------------------------------------------------------

    def print_ancestry_tree(self, gene_id: str) -> None:
        """Print a visual ancestry tree for a gene."""
        ancestors = self.trace_ancestors(gene_id)
        if not ancestors:
            console.print(f"  [dim]No lineage found for gene {gene_id}[/dim]")
            return

        # Build tree starting from the target gene
        root_data = next((a for a in ancestors if a["gene_id"] == gene_id), None)
        if not root_data:
            console.print(f"  [dim]Gene {gene_id} not found in lineage.[/dim]")
            return

        alive_marker = "[green]●[/green]" if root_data["alive"] else "[red]●[/red]"
        tree = Tree(
            f"{alive_marker} [bold]{root_data['role']}[/bold] "
            f"[dim]{gene_id}[/dim] gen-{root_data['generation']} "
            f"score={root_data['avg_score']:.2f}"
        )

        # Add ancestors recursively
        ancestor_map = {a["gene_id"]: a for a in ancestors}
        self._add_ancestors_to_tree(tree, root_data, ancestor_map, set())

        console.print(Panel(tree, title=f"Ancestry of {gene_id}"))

    def _add_ancestors_to_tree(self, tree: Tree, node: dict,
                                ancestor_map: dict, visited: set) -> None:
        for parent_key in ("parent_a_gene", "parent_b_gene"):
            parent_id = node.get(parent_key)
            if not parent_id or parent_id in visited:
                continue
            visited.add(parent_id)

            parent = ancestor_map.get(parent_id)
            if parent:
                alive_marker = "[green]●[/green]" if parent["alive"] else "[red]●[/red]"
                label = (
                    f"{alive_marker} {parent['role']} [dim]{parent_id}[/dim] "
                    f"gen-{parent['generation']} score={parent['avg_score']:.2f}"
                )
                branch = tree.add(f"← {label}")
                self._add_ancestors_to_tree(branch, parent, ancestor_map, visited)
            else:
                tree.add(f"← [dim]{parent_id}[/dim] (not in lineage)")

    def print_lineage_stats(self) -> None:
        """Print lineage statistics."""
        stats = self.memory.get_lineage_stats()

        table = Table(title="Bloodline Stats", show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Genes", str(stats["total_genes"]))
        table.add_row("Alive Genes", str(stats["alive_genes"]))
        table.add_row("Max Generation", str(stats["max_generation"]))
        table.add_row("Avg Score (alive)", f"{stats['avg_score']:.3f}")

        console.print(Panel(table, title="🧬 Bloodline"))

    def print_living_lineage(self, role: str | None = None) -> None:
        """Print all living genes, optionally filtered by role."""
        query = "SELECT * FROM lineage WHERE alive = 1"
        params: tuple = ()
        if role:
            query += " AND role = ?"
            params = (role,)
        query += " ORDER BY avg_score DESC LIMIT 30"

        rows = self.memory.conn.execute(query, params).fetchall()
        if not rows:
            console.print("  [dim]No living genes in lineage.[/dim]")
            return

        table = Table(title=f"Living Genes ({len(rows)})")
        table.add_column("Gene ID", style="dim")
        table.add_column("Role", style="cyan")
        table.add_column("Gen", justify="center")
        table.add_column("Score", justify="center")
        table.add_column("Parents", style="dim")
        table.add_column("Mutations")

        for r in rows:
            parents = ""
            if r["parent_a_gene"] and r["parent_b_gene"]:
                parents = f"{r['parent_a_gene']} × {r['parent_b_gene']}"
            elif r["parent_a_gene"]:
                parents = r["parent_a_gene"]

            table.add_row(
                r["gene_id"],
                r["role"],
                str(r["generation"]),
                f"{r['avg_score']:.2f}",
                parents,
                r["mutation_notes"] or "—",
            )

        console.print(table)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _weighted_sample_two(items: list, weights: list[float]) -> tuple:
    """Select two distinct items via fitness-proportional sampling.

    Uses roulette-wheel selection: probability of selection is proportional
    to weight. Samples without replacement.
    """
    if len(items) < 2:
        raise ValueError("Need at least 2 items to sample")

    total = sum(weights)
    if total <= 0:
        # All weights zero — fall back to uniform random
        chosen = random.sample(range(len(items)), 2)
        return items[chosen[0]], items[chosen[1]]

    # First parent
    r = random.uniform(0, total)
    cumulative = 0
    idx_a = 0
    for i, w in enumerate(weights):
        cumulative += w
        if cumulative >= r:
            idx_a = i
            break

    # Second parent (exclude first)
    remaining_weights = weights[:idx_a] + weights[idx_a + 1:]
    remaining_items = items[:idx_a] + items[idx_a + 1:]
    total_b = sum(remaining_weights)

    if total_b <= 0:
        idx_b = 0
    else:
        r = random.uniform(0, total_b)
        cumulative = 0
        idx_b = 0
        for i, w in enumerate(remaining_weights):
            cumulative += w
            if cumulative >= r:
                idx_b = i
                break

    return items[idx_a], remaining_items[idx_b]


def _extract_unique_segments(source: str, reference: str) -> str:
    """Extract sentences from source that don't appear in reference."""
    source_sentences = [s.strip() for s in source.split(".") if len(s.strip()) > 20]
    ref_lower = reference.lower()
    unique = [s for s in source_sentences if s.lower() not in ref_lower]
    if unique:
        return ". ".join(unique[:2])
    return ""
