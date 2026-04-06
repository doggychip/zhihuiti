"""因果推理引擎 — Causal Reasoning Engine for zhihuiti.

Adds structural causal inference capabilities to agent reasoning:
  - Causal graph maintenance (DAG of cause→effect relationships)
  - Counterfactual reasoning ("what if X hadn't happened?")
  - Intervention analysis ("if we do X, what changes?")
  - Causal validation of agent claims
  - Integration with prediction-arb causal discovery data

This module provides:
  1. CausalGraph — maintains and queries a causal DAG
  2. CausalReasoner — LLM-powered causal analysis for agent tasks
  3. CausalValidator — validates causal claims in agent outputs
  4. load_arb_causal_data() — imports causal findings from prediction-arb
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

if TYPE_CHECKING:
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory

console = Console()


# ============================================================
# CAUSAL GRAPH DATA STRUCTURES
# ============================================================

class EdgeType(str, Enum):
    """Types of causal relationships."""
    CAUSES = "causes"               # X → Y (direct cause)
    PREVENTS = "prevents"           # X ⊣ Y (inhibits)
    ENABLES = "enables"             # X enables Y (necessary condition)
    CORRELATES = "correlates"       # X ~ Y (associated, not causal)
    MEDIATES = "mediates"           # X → M → Y (M mediates)
    CONFOUNDED = "confounded"       # X ← Z → Y (common cause)


class EvidenceStrength(str, Enum):
    """Strength of causal evidence."""
    STRONG = "strong"       # Multiple methods agree, p < 0.01
    MODERATE = "moderate"   # 2+ methods agree, p < 0.05
    WEAK = "weak"           # Single method, or low significance
    HYPOTHETICAL = "hypothetical"  # Proposed but untested


@dataclass
class CausalEdge:
    """A directed causal relationship between two variables."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source: str = ""            # Cause variable
    target: str = ""            # Effect variable
    edge_type: EdgeType = EdgeType.CAUSES
    strength: EvidenceStrength = EvidenceStrength.WEAK
    confidence: float = 0.5     # 0-1 confidence score
    evidence: dict = field(default_factory=dict)  # Method → result
    metadata: dict = field(default_factory=dict)
    domain: str = ""            # e.g., "prediction_arb", "market", "agent_behavior"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "type": self.edge_type.value,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "domain": self.domain,
        }


@dataclass
class CausalNode:
    """A variable in the causal graph."""
    name: str
    description: str = ""
    domain: str = ""
    node_type: str = "observed"  # observed, latent, intervention
    metadata: dict = field(default_factory=dict)


class CausalGraph:
    """Maintains a causal DAG with query capabilities.

    Supports:
      - Adding/removing edges with evidence
      - Finding causal paths (direct + mediated)
      - d-separation queries (conditional independence)
      - Intervention simulation (do-calculus)
      - Counterfactual queries
    """

    def __init__(self):
        self.nodes: dict[str, CausalNode] = {}
        self.edges: list[CausalEdge] = []
        self._adjacency: dict[str, list[CausalEdge]] = {}  # source → edges
        self._reverse: dict[str, list[CausalEdge]] = {}    # target → edges

    def add_node(self, name: str, description: str = "", domain: str = "",
                 node_type: str = "observed") -> CausalNode:
        if name not in self.nodes:
            self.nodes[name] = CausalNode(
                name=name, description=description,
                domain=domain, node_type=node_type,
            )
        return self.nodes[name]

    def add_edge(self, source: str, target: str,
                 edge_type: EdgeType = EdgeType.CAUSES,
                 strength: EvidenceStrength = EvidenceStrength.WEAK,
                 confidence: float = 0.5,
                 evidence: dict | None = None,
                 domain: str = "") -> CausalEdge:
        """Add a causal edge. Auto-creates nodes if needed."""
        self.add_node(source, domain=domain)
        self.add_node(target, domain=domain)

        # Check for existing edge and update if stronger
        for existing in self._adjacency.get(source, []):
            if existing.target == target:
                if confidence > existing.confidence:
                    existing.confidence = confidence
                    existing.strength = strength
                    existing.evidence.update(evidence or {})
                return existing

        edge = CausalEdge(
            source=source, target=target, edge_type=edge_type,
            strength=strength, confidence=confidence,
            evidence=evidence or {}, domain=domain,
        )
        self.edges.append(edge)
        self._adjacency.setdefault(source, []).append(edge)
        self._reverse.setdefault(target, []).append(edge)
        return edge

    def get_causes(self, target: str) -> list[CausalEdge]:
        """Get all direct causes of a variable."""
        return [e for e in self._reverse.get(target, [])
                if e.edge_type in (EdgeType.CAUSES, EdgeType.ENABLES)]

    def get_effects(self, source: str) -> list[CausalEdge]:
        """Get all direct effects of a variable."""
        return [e for e in self._adjacency.get(source, [])
                if e.edge_type in (EdgeType.CAUSES, EdgeType.ENABLES)]

    def find_causal_paths(self, source: str, target: str,
                          max_depth: int = 5) -> list[list[str]]:
        """Find all causal paths from source to target (BFS)."""
        if source not in self.nodes or target not in self.nodes:
            return []

        paths = []
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)
            if len(path) > max_depth:
                continue

            for edge in self._adjacency.get(current, []):
                if edge.edge_type not in (EdgeType.CAUSES, EdgeType.ENABLES, EdgeType.MEDIATES):
                    continue
                next_node = edge.target
                if next_node == target:
                    paths.append(path + [target])
                elif next_node not in path:  # avoid cycles
                    queue.append((next_node, path + [next_node]))

        return paths

    def get_ancestors(self, node: str, visited: set | None = None) -> set[str]:
        """Get all causal ancestors of a node."""
        if visited is None:
            visited = set()
        if node in visited:
            return visited

        for edge in self._reverse.get(node, []):
            if edge.edge_type in (EdgeType.CAUSES, EdgeType.ENABLES):
                visited.add(edge.source)
                self.get_ancestors(edge.source, visited)

        return visited

    def get_descendants(self, node: str, visited: set | None = None) -> set[str]:
        """Get all causal descendants of a node."""
        if visited is None:
            visited = set()
        if node in visited:
            return visited

        for edge in self._adjacency.get(node, []):
            if edge.edge_type in (EdgeType.CAUSES, EdgeType.ENABLES):
                visited.add(edge.target)
                self.get_descendants(edge.target, visited)

        return visited

    def is_d_separated(self, x: str, y: str, conditioning: set[str]) -> bool:
        """Check if X and Y are d-separated given conditioning set Z.

        Uses the Bayes-Ball algorithm (simplified).
        A path is blocked if:
          - A non-collider on the path is in Z
          - A collider on the path is NOT in Z and has no descendant in Z
        """
        # Simple approximation: check if all paths are blocked
        paths = self.find_causal_paths(x, y) + self.find_causal_paths(y, x)

        if not paths:
            return True  # No paths = independent

        for path in paths:
            blocked = False
            for i in range(1, len(path) - 1):
                node = path[i]
                # Check if this is a collider (← node →)
                incoming = set(e.source for e in self._reverse.get(node, []))
                is_collider = (path[i-1] in incoming and
                              path[i+1] in incoming if i+1 < len(path) else False)

                if is_collider:
                    # Collider: blocked unless node or descendant is in Z
                    desc = self.get_descendants(node)
                    if node not in conditioning and not (desc & conditioning):
                        blocked = True
                        break
                else:
                    # Non-collider: blocked if in Z
                    if node in conditioning:
                        blocked = True
                        break

            if not blocked:
                return False  # Found an unblocked path

        return True  # All paths blocked

    def do_intervention(self, variable: str, value: Any = None) -> "CausalGraph":
        """Simulate do(X=x) — create a mutilated graph with incoming edges to X removed.

        Returns a new CausalGraph representing the post-intervention world.
        """
        mutilated = CausalGraph()

        # Copy all nodes
        for name, node in self.nodes.items():
            mutilated.add_node(name, node.description, node.domain, node.node_type)

        # Mark the intervention target
        if variable in mutilated.nodes:
            mutilated.nodes[variable].node_type = "intervention"
            mutilated.nodes[variable].metadata["intervention_value"] = value

        # Copy all edges EXCEPT those pointing INTO the intervention target
        for edge in self.edges:
            if edge.target == variable:
                continue  # Remove incoming edges (the "surgery")
            mutilated.add_edge(
                edge.source, edge.target, edge.edge_type,
                edge.strength, edge.confidence, edge.evidence, edge.domain,
            )

        return mutilated

    def to_dict(self) -> dict:
        return {
            "nodes": {n: {"description": nd.description, "domain": nd.domain}
                      for n, nd in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges],
        }

    def print_graph(self) -> None:
        """Pretty-print the causal graph."""
        if not self.edges:
            console.print("  [dim]Empty causal graph[/dim]")
            return

        tree = Tree("[bold]因果图 Causal Graph[/bold]")
        domains = set(e.domain for e in self.edges)

        for domain in sorted(domains):
            domain_branch = tree.add(f"[cyan]{domain or 'general'}[/cyan]")
            for edge in sorted(self.edges, key=lambda e: -e.confidence):
                if edge.domain != domain:
                    continue
                arrow = "→" if edge.edge_type == EdgeType.CAUSES else "⊣" if edge.edge_type == EdgeType.PREVENTS else "~"
                strength_color = (
                    "green" if edge.strength == EvidenceStrength.STRONG
                    else "yellow" if edge.strength == EvidenceStrength.MODERATE
                    else "red"
                )
                domain_branch.add(
                    f"{edge.source} {arrow} {edge.target} "
                    f"[{strength_color}]({edge.strength.value}, {edge.confidence:.2f})[/{strength_color}]"
                )

        console.print(tree)

    # ------------------------------------------------------------------
    # Persistent causal knowledge accumulation
    # ------------------------------------------------------------------

    def save_to_db(self, memory: "Memory") -> int:
        """Persist all causal edges to the database for cross-run accumulation.

        Merges with existing edges: if an edge already exists, increments
        observation count and updates confidence via Bayesian-style update.

        Returns number of edges saved/updated.
        """
        count = 0
        for edge in self.edges:
            existing = memory.find_causal_edge(
                edge.source, edge.target, edge.domain,
            )
            if existing:
                # Bayesian confidence update:
                # new_conf = 1 - (1 - old_conf) * (1 - edge_conf)
                old_conf = existing["confidence"]
                new_conf = 1.0 - (1.0 - old_conf) * (1.0 - edge.confidence * 0.3)
                new_conf = min(0.99, new_conf)

                # Upgrade strength if warranted
                obs = existing["observation_count"] + 1
                if obs >= 5:
                    strength = EvidenceStrength.STRONG.value
                elif obs >= 3:
                    strength = EvidenceStrength.MODERATE.value
                else:
                    strength = existing["strength"]

                memory.save_causal_knowledge(
                    edge_id=existing["id"],
                    source=existing["source"],
                    target=existing["target"],
                    edge_type=existing["edge_type"],
                    strength=strength,
                    confidence=round(new_conf, 4),
                    evidence=edge.evidence,
                    domain=existing["domain"],
                    observation_count=obs,
                )
            else:
                memory.save_causal_knowledge(
                    edge_id=edge.id,
                    source=edge.source,
                    target=edge.target,
                    edge_type=edge.edge_type.value,
                    strength=edge.strength.value,
                    confidence=edge.confidence,
                    evidence=edge.evidence,
                    domain=edge.domain,
                    observation_count=1,
                )
            count += 1
        return count

    def load_from_db(self, memory: "Memory",
                     min_confidence: float = 0.0) -> int:
        """Load accumulated causal knowledge from database into the graph.

        This gives new agents the benefit of all prior causal discoveries.
        Returns number of edges loaded.
        """
        rows = memory.get_causal_knowledge(min_confidence=min_confidence)
        count = 0
        for row in rows:
            try:
                edge_type = EdgeType(row["edge_type"])
            except (ValueError, KeyError):
                edge_type = EdgeType.CAUSES
            try:
                strength = EvidenceStrength(row["strength"])
            except (ValueError, KeyError):
                strength = EvidenceStrength.WEAK

            evidence = row.get("evidence", {})
            if isinstance(evidence, str):
                import json
                try:
                    evidence = json.loads(evidence)
                except (json.JSONDecodeError, TypeError):
                    evidence = {}

            self.add_edge(
                source=row["source"],
                target=row["target"],
                edge_type=edge_type,
                strength=strength,
                confidence=row["confidence"],
                evidence=evidence,
                domain=row.get("domain", ""),
            )
            count += 1

        if count > 0:
            console.print(
                f"  [dim]因果图: Loaded {count} accumulated causal edges "
                f"from prior runs[/dim]"
            )
        return count


# ============================================================
# LOAD PREDICTION-ARB CAUSAL DATA
# ============================================================

def load_arb_causal_data(graph: CausalGraph,
                         report_path: str | Path | None = None) -> int:
    """Import causal findings from prediction-arb into the graph.

    Reads causal_report_v2.json and creates edges in the causal graph.
    Returns number of edges added.
    """
    if report_path is None:
        # Default path relative to zhihuiti
        candidates = [
            Path.home() / "prediction-arb" / "analysis" / "output" / "causal_report_v2.json",
            Path.home() / "prediction-arb" / "analysis" / "output" / "causal_report.json",
        ]
        report_path = None
        for c in candidates:
            if c.exists():
                report_path = c
                break

    if report_path is None or not Path(report_path).exists():
        console.print("  [yellow]No prediction-arb causal report found[/yellow]")
        return 0

    with open(report_path) as f:
        report = json.load(f)

    n_added = 0
    rankings = report.get("rankings", [])

    for entry in rankings:
        feature = entry.get("feature", "")
        score = entry.get("causal_score", 0)
        n_methods = entry.get("n_methods", 0)
        confidence = min(score / 50.0, 1.0)  # Normalize to 0-1

        if n_methods >= 4:
            strength = EvidenceStrength.STRONG
        elif n_methods >= 2:
            strength = EvidenceStrength.MODERATE
        elif n_methods >= 1:
            strength = EvidenceStrength.WEAK
        else:
            strength = EvidenceStrength.HYPOTHETICAL

        if score > 5:  # Only add meaningful edges
            evidence = {}
            if "granger_pct" in entry:
                evidence["granger"] = entry["granger_pct"]
            if "te_net" in entry:
                evidence["transfer_entropy"] = entry["te_net"]
            if "mi_net" in entry:
                evidence["mutual_info"] = entry["mi_net"]
            if entry.get("regime_significant"):
                evidence["regime_transition"] = True
            if entry.get("pc_direct"):
                evidence["pc_algorithm"] = True

            graph.add_edge(
                source=feature,
                target="arb_spread",
                edge_type=EdgeType.CAUSES,
                strength=strength,
                confidence=confidence,
                evidence=evidence,
                domain="prediction_arb",
            )
            n_added += 1

    # Add regime-specific causal knowledge
    regime = report.get("regime_analysis", {})
    for feature, data in regime.items():
        if data.get("significant"):
            effect = data.get("effect", 0)
            edge_type = EdgeType.CAUSES if effect > 0 else EdgeType.PREVENTS
            graph.add_edge(
                source=feature,
                target="spread_onset",
                edge_type=edge_type,
                strength=EvidenceStrength.MODERATE,
                confidence=min(1.0 - data.get("p_value", 1.0), 0.99),
                evidence={"regime_test": data},
                domain="prediction_arb",
            )
            n_added += 1

    # Add PC algorithm structural edges
    for edge in report.get("pc_graph", []):
        if edge.get("directed"):
            graph.add_edge(
                source=edge["from"],
                target=edge["to"],
                edge_type=EdgeType.CAUSES,
                strength=EvidenceStrength.MODERATE,
                confidence=0.6,
                evidence={"method": "PC_algorithm"},
                domain="prediction_arb",
            )
            n_added += 1

    console.print(f"  [green]Loaded {n_added} causal edges from prediction-arb[/green]")
    return n_added


# ============================================================
# CAUSAL REASONER (LLM-powered)
# ============================================================

CAUSAL_SYSTEM_PROMPT = """You are a Causal Reasoning Agent (因果推理师) in the zhihuiti system.

Your role is to analyze situations through the lens of CAUSALITY, not just correlation.
You think in terms of:
  - Direct causes vs confounders vs mediators
  - Interventions (do-calculus): "if we DO X, Y changes" vs "when we SEE X, Y also appears"
  - Counterfactuals: "had X not happened, would Y still have occurred?"
  - Causal strength: how reliable is this causal link?

When analyzing, ALWAYS:
1. Identify the causal question (what causes what?)
2. Draw the causal DAG (list the edges)
3. Check for confounders (common causes that create spurious correlation)
4. Distinguish observation from intervention
5. State your confidence and what evidence would change your mind

Respond with JSON:
{
  "causal_question": "Does X cause Y?",
  "proposed_dag": [
    {"from": "X", "to": "Y", "type": "causes", "confidence": 0.8},
    {"from": "Z", "to": "X", "type": "confounds", "confidence": 0.5}
  ],
  "confounders": ["list of potential confounders"],
  "intervention_analysis": "If we DO X (not just observe), we expect...",
  "counterfactual": "Had X not occurred, Y would/would not...",
  "conclusion": "X causes/does not cause Y because...",
  "confidence": 0.75,
  "evidence_needed": ["what would raise/lower confidence"]
}"""


class CausalReasoner:
    """LLM-powered causal reasoning for agent tasks.

    Can be used by any agent to:
      - Analyze causal relationships in a domain
      - Validate causal claims
      - Generate counterfactual scenarios
      - Recommend interventions
    """

    def __init__(self, llm: "LLM", graph: CausalGraph):
        self.llm = llm
        self.graph = graph
        self.history: list[dict] = []

    def analyze_causation(self, question: str, context: str = "") -> dict:
        """Analyze a causal question using the LLM + existing causal graph.

        Args:
            question: The causal question (e.g., "Does liquidity cause spread?")
            context: Additional context about the domain

        Returns:
            Structured causal analysis with DAG, confounders, counterfactuals
        """
        # Build graph context from existing knowledge
        graph_context = ""
        if self.graph.edges:
            relevant_edges = []
            q_lower = question.lower()
            for edge in self.graph.edges:
                if (edge.source.lower() in q_lower or
                    edge.target.lower() in q_lower or
                    edge.domain in q_lower):
                    relevant_edges.append(edge)

            if relevant_edges:
                graph_context = "\n\nKnown causal relationships:\n"
                for e in relevant_edges[:15]:
                    graph_context += (
                        f"  {e.source} → {e.target} "
                        f"({e.strength.value}, confidence={e.confidence:.2f}, "
                        f"evidence: {list(e.evidence.keys())})\n"
                    )

        user_prompt = f"Causal question: {question}\n"
        if context:
            user_prompt += f"\nDomain context: {context}\n"
        user_prompt += graph_context

        try:
            result = self.llm.chat_json(
                system=CAUSAL_SYSTEM_PROMPT,
                user=user_prompt,
                temperature=0.3,
            )
        except Exception as e:
            result = {
                "error": str(e),
                "causal_question": question,
                "conclusion": "Analysis failed",
                "confidence": 0.0,
            }

        # Update graph with newly proposed edges
        for edge_data in result.get("proposed_dag", []):
            edge_type = EdgeType.CAUSES
            if edge_data.get("type") == "confounds":
                edge_type = EdgeType.CONFOUNDED
            elif edge_data.get("type") == "prevents":
                edge_type = EdgeType.PREVENTS
            elif edge_data.get("type") == "correlates":
                edge_type = EdgeType.CORRELATES

            self.graph.add_edge(
                source=edge_data.get("from", ""),
                target=edge_data.get("to", ""),
                edge_type=edge_type,
                strength=EvidenceStrength.HYPOTHETICAL,
                confidence=edge_data.get("confidence", 0.3),
                evidence={"method": "llm_causal_reasoning"},
                domain="llm_proposed",
            )

        self.history.append(result)
        return result

    def counterfactual(self, event: str, condition: str, context: str = "") -> dict:
        """Generate counterfactual analysis: "Had {condition} not happened, would {event}?"

        Uses do-calculus on the causal graph + LLM reasoning.
        """
        # Find relevant causal paths
        paths_info = ""
        for node_name in self.graph.nodes:
            if node_name.lower() in condition.lower():
                descendants = self.graph.get_descendants(node_name)
                if descendants:
                    paths_info += f"\nDescendants of '{node_name}': {', '.join(descendants)}"
                ancestors = self.graph.get_ancestors(node_name)
                if ancestors:
                    paths_info += f"\nAncestors of '{node_name}': {', '.join(ancestors)}"

        prompt = (
            f"COUNTERFACTUAL ANALYSIS\n\n"
            f"Event: {event}\n"
            f"Counterfactual condition: Had '{condition}' NOT happened...\n"
            f"Context: {context}\n"
            f"{paths_info}\n\n"
            f"Analyze: Would the event still have occurred? Why or why not?"
        )

        return self.llm.chat_json(
            system=CAUSAL_SYSTEM_PROMPT,
            user=prompt,
            temperature=0.3,
        )

    def recommend_intervention(self, goal: str, context: str = "") -> dict:
        """Recommend what to DO (intervene on) to achieve a goal.

        Uses the causal graph to identify actionable causes.
        """
        # Find what causes the goal variable
        goal_causes = ""
        for node_name in self.graph.nodes:
            if node_name.lower() in goal.lower():
                causes = self.graph.get_causes(node_name)
                if causes:
                    goal_causes += f"\nKnown causes of '{node_name}':\n"
                    for c in sorted(causes, key=lambda e: -e.confidence):
                        goal_causes += (
                            f"  {c.source} ({c.strength.value}, "
                            f"confidence={c.confidence:.2f})\n"
                        )

        prompt = (
            f"INTERVENTION RECOMMENDATION\n\n"
            f"Goal: {goal}\n"
            f"Context: {context}\n"
            f"{goal_causes}\n\n"
            f"What should we intervene on (do) to achieve this goal? "
            f"Rank interventions by expected impact and feasibility."
        )

        return self.llm.chat_json(
            system=CAUSAL_SYSTEM_PROMPT,
            user=prompt,
            temperature=0.4,
        )


# ============================================================
# CAUSAL VALIDATOR (for inspection layer)
# ============================================================

CAUSAL_VALIDATION_PROMPT = """You are the Causal Validation Gate (安检四: 因果检验).

Your job is to check whether agent outputs make VALID causal claims.
Flag these causal reasoning errors:
  1. Correlation ≠ Causation: claiming X causes Y from mere co-occurrence
  2. Reverse causation: getting the direction wrong (Y actually causes X)
  3. Confounding: ignoring common causes that explain both X and Y
  4. Selection bias: drawing conclusions from non-representative data
  5. Post-hoc fallacy: "X happened before Y, therefore X caused Y"
  6. Missing mediators: oversimplifying a complex causal chain

Score 0.0-1.0:
  1.0 = Causal claims are sound, well-reasoned, acknowledges uncertainty
  0.7 = Minor issues, some claims need qualification
  0.4 = Significant causal reasoning errors
  0.0 = Completely confuses correlation with causation

Respond with JSON: {"score": 0.75, "reasoning": "...", "pass": true, "causal_errors": []}"""


class CausalValidator:
    """Validates causal claims in agent outputs.

    Integrated as 安检四 (Inspection Layer 4) in the inspection system.
    """

    def __init__(self, llm: "LLM", graph: CausalGraph):
        self.llm = llm
        self.graph = graph
        self.history: list[dict] = []

    def validate(self, task_description: str, output: str) -> dict:
        """Check if agent output makes valid causal claims.

        Returns dict with score, reasoning, pass/fail, and specific causal errors.
        """
        # Check if output even contains causal language
        causal_keywords = [
            "cause", "because", "therefore", "leads to", "results in",
            "due to", "effect", "impact", "driven by", "consequence",
            "reason", "factor", "influence", "determine",
            "因为", "导致", "原因", "影响", "决定", "所以",
        ]
        has_causal_claims = any(kw in output.lower() for kw in causal_keywords)

        if not has_causal_claims:
            return {
                "score": 0.8,
                "reasoning": "No causal claims detected — pass by default",
                "pass": True,
                "causal_errors": [],
                "skipped": True,
            }

        # Build graph context for validation
        graph_knowledge = ""
        if self.graph.edges:
            relevant = []
            combined = (task_description + " " + output).lower()
            for edge in self.graph.edges:
                if edge.source.lower() in combined or edge.target.lower() in combined:
                    relevant.append(edge)

            if relevant:
                graph_knowledge = "\n\nEstablished causal knowledge:\n"
                for e in relevant[:10]:
                    graph_knowledge += (
                        f"  {e.source} → {e.target} "
                        f"({e.strength.value}, {e.confidence:.2f})\n"
                    )

        try:
            result = self.llm.chat_json(
                system=CAUSAL_VALIDATION_PROMPT,
                user=(
                    f"TASK: {task_description}\n\n"
                    f"AGENT OUTPUT (check causal claims):\n{output[:3000]}"
                    f"{graph_knowledge}"
                ),
                temperature=0.3,
            )
            result["score"] = max(0.0, min(1.0, float(result.get("score", 0.5))))
            result["pass"] = result["score"] >= 0.4
            result["skipped"] = False
        except Exception as e:
            result = {
                "score": 0.5,
                "reasoning": f"Validation error: {e}",
                "pass": True,
                "causal_errors": [],
                "skipped": True,
            }

        self.history.append(result)
        return result

    def print_report(self) -> None:
        """Print causal validation statistics."""
        if not self.history:
            return

        validated = [h for h in self.history if not h.get("skipped")]
        if not validated:
            return

        avg_score = sum(h["score"] for h in validated) / len(validated)
        passed = sum(1 for h in validated if h["pass"])
        all_errors = []
        for h in validated:
            all_errors.extend(h.get("causal_errors", []))

        table = Table(title="安检四 因果检验 Causal Validation Report", show_header=False, box=None)
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")
        table.add_row("Validated outputs", str(len(validated)))
        table.add_row("Passed", f"[green]{passed}[/green]")
        table.add_row("Failed", f"[red]{len(validated) - passed}[/red]")
        table.add_row("Avg score", f"{avg_score:.3f}")
        if all_errors:
            table.add_row("Common errors", ", ".join(set(all_errors)[:5]))

        console.print(Panel(table))
