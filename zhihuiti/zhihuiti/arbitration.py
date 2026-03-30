"""Labor Arbitration Bureau (劳动仲裁局) — dispute resolution system.

When agents feel wronged by the system, they can file disputes:

1. Score Dispute (分数争议) — agent believes the judge scored unfairly
2. Loan Dispute (贷款争议) — borrower claims unfair default declaration
3. Bid Dispute (竞标争议) — agent claims wrongful disqualification from auction
4. Quality Dispute (质量争议) — agent claims its output was good but scored low

The bureau adjudicates disputes using LLM review, applying resolutions
that can adjust scores, reverse penalties, void loans, or reinstate agents.

Filing a dispute costs tokens to prevent spam (frivolous litigation tax).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.llm import LLM
    from zhihuiti.memory import Memory

console = Console()


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class DisputeType(str, Enum):
    SCORE_DISPUTE = "score_dispute"       # 分数争议
    LOAN_DISPUTE = "loan_dispute"         # 贷款争议
    BID_DISPUTE = "bid_dispute"           # 竞标争议
    QUALITY_DISPUTE = "quality_dispute"   # 质量争议


class DisputeStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class ResolutionAction(str, Enum):
    ADJUST_SCORE = "adjust_score"
    REVERSE_PENALTY = "reverse_penalty"
    VOID_LOAN = "void_loan"
    REINSTATE_AGENT = "reinstate_agent"
    NO_ACTION = "no_action"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Resolution:
    """The outcome of an adjudicated dispute."""
    action: ResolutionAction = ResolutionAction.NO_ACTION
    details: str = ""
    score_adjustment: float = 0.0       # For ADJUST_SCORE
    penalty_reversed: float = 0.0       # For REVERSE_PENALTY
    loan_id: str = ""                   # For VOID_LOAN
    agent_id: str = ""                  # For REINSTATE_AGENT


@dataclass
class Dispute:
    """A filed dispute awaiting adjudication."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    dispute_type: DisputeType = DisputeType.SCORE_DISPUTE
    plaintiff_id: str = ""              # The agent filing the dispute
    defendant_id: str = ""              # The entity being disputed against
    description: str = ""
    evidence: str = ""
    status: DisputeStatus = DisputeStatus.OPEN
    resolution: Resolution | None = None
    arbitrator_notes: str = ""
    filing_cost: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    resolved_at: str = ""


# ---------------------------------------------------------------------------
# Filing cost schedule (prevents spam disputes)
# ---------------------------------------------------------------------------

FILING_COSTS: dict[DisputeType, float] = {
    DisputeType.SCORE_DISPUTE: 5.0,
    DisputeType.LOAN_DISPUTE: 10.0,
    DisputeType.BID_DISPUTE: 8.0,
    DisputeType.QUALITY_DISPUTE: 5.0,
}


# ---------------------------------------------------------------------------
# Arbitration Bureau
# ---------------------------------------------------------------------------

class ArbitrationBureau:
    """Labor Arbitration Bureau (劳动仲裁局).

    Handles dispute filing, LLM-based adjudication, resolution enforcement,
    and dismissal of frivolous cases. Filing costs tokens to prevent abuse.
    """

    def __init__(self, memory: Memory, llm: LLM | None = None):
        self.memory = memory
        self.llm = llm
        self.disputes: list[Dispute] = []
        self.resolved: list[Dispute] = []
        self.dismissed: list[Dispute] = []

    # ------------------------------------------------------------------
    # Filing
    # ------------------------------------------------------------------

    def file_dispute(
        self,
        dispute_type: DisputeType,
        plaintiff_id: str,
        defendant_id: str,
        description: str,
        evidence: str = "",
        plaintiff_budget: float | None = None,
    ) -> Dispute | None:
        """File a new dispute. Deducts filing cost from plaintiff's budget.

        Args:
            dispute_type: The category of dispute.
            plaintiff_id: Agent filing the dispute.
            defendant_id: Entity being disputed against (judge, lender, etc).
            description: What happened and why it's unfair.
            evidence: Supporting evidence (output text, scores, etc).
            plaintiff_budget: Current budget of the plaintiff (for cost check).

        Returns:
            The filed Dispute, or None if plaintiff cannot afford filing cost.
        """
        cost = FILING_COSTS[dispute_type]

        # Budget check — prevent agents from filing disputes they can't afford
        if plaintiff_budget is not None and plaintiff_budget < cost:
            console.print(
                f"  [red]Dispute rejected:[/red] {plaintiff_id} cannot afford "
                f"filing cost ({cost:.1f} tokens, budget: {plaintiff_budget:.1f})"
            )
            return None

        dispute = Dispute(
            dispute_type=dispute_type,
            plaintiff_id=plaintiff_id,
            defendant_id=defendant_id,
            description=description,
            evidence=evidence[:3000],  # Cap evidence length
            filing_cost=cost,
        )

        self.disputes.append(dispute)
        self._save_dispute(dispute)

        type_labels = {
            DisputeType.SCORE_DISPUTE: "分数争议 Score Dispute",
            DisputeType.LOAN_DISPUTE: "贷款争议 Loan Dispute",
            DisputeType.BID_DISPUTE: "竞标争议 Bid Dispute",
            DisputeType.QUALITY_DISPUTE: "质量争议 Quality Dispute",
        }
        label = type_labels.get(dispute_type, dispute_type.value)

        console.print(
            f"  [bold cyan]仲裁 Filed:[/bold cyan] {label} "
            f"[dim]({plaintiff_id} vs {defendant_id})[/dim] "
            f"cost: {cost:.1f} tokens"
        )
        console.print(f"    [dim]{description[:120]}[/dim]")

        return dispute

    # ------------------------------------------------------------------
    # Adjudication
    # ------------------------------------------------------------------

    def auto_adjudicate(self, dispute: Dispute) -> Resolution:
        """Use LLM to review a dispute and produce a ruling.

        Falls back to a simple heuristic ruling if no LLM is available.
        """
        if dispute.status != DisputeStatus.OPEN:
            console.print(f"  [dim]Dispute {dispute.id} already {dispute.status.value}.[/dim]")
            return dispute.resolution or Resolution()

        if self.llm:
            return self._llm_adjudicate(dispute)
        return self._heuristic_adjudicate(dispute)

    def _llm_adjudicate(self, dispute: Dispute) -> Resolution:
        """LLM-based adjudication — the arbitrator reviews all evidence."""
        assert self.llm is not None

        action_map = {
            DisputeType.SCORE_DISPUTE: "adjust_score or no_action",
            DisputeType.LOAN_DISPUTE: "void_loan or no_action",
            DisputeType.BID_DISPUTE: "reinstate_agent or no_action",
            DisputeType.QUALITY_DISPUTE: "adjust_score or reverse_penalty or no_action",
        }
        possible_actions = action_map.get(dispute.dispute_type, "no_action")

        try:
            result = self.llm.chat_json(
                system=(
                    "You are an impartial labor arbitrator (劳动仲裁员) for an AI agent system. "
                    "Review the dispute and make a fair ruling.\n\n"
                    "Consider:\n"
                    "- Is the plaintiff's claim substantiated by evidence?\n"
                    "- Was the defendant's action reasonable?\n"
                    "- Is this a legitimate grievance or a frivolous filing?\n\n"
                    "Respond with JSON:\n"
                    "{\n"
                    '  "ruling": "in_favor" | "against" | "partial",\n'
                    '  "action": "<one of: ' + possible_actions + '>",\n'
                    '  "score_adjustment": <float, 0.0 if not applicable>,\n'
                    '  "penalty_reversed": <float, 0.0 if not applicable>,\n'
                    '  "reasoning": "<explain the ruling>",\n'
                    '  "frivolous": true/false\n'
                    "}"
                ),
                user=(
                    f"DISPUTE TYPE: {dispute.dispute_type.value}\n"
                    f"PLAINTIFF: {dispute.plaintiff_id}\n"
                    f"DEFENDANT: {dispute.defendant_id}\n\n"
                    f"DESCRIPTION:\n{dispute.description}\n\n"
                    f"EVIDENCE:\n{dispute.evidence[:2000]}"
                ),
                temperature=0.3,
            )

            # Parse ruling
            ruling = result.get("ruling", "against")
            is_frivolous = result.get("frivolous", False)

            if is_frivolous:
                dispute.arbitrator_notes = f"Frivolous filing. {result.get('reasoning', '')}"
                self.dismiss(dispute, reason=dispute.arbitrator_notes)
                return Resolution(action=ResolutionAction.NO_ACTION,
                                  details="Dismissed as frivolous")

            action_str = result.get("action", "no_action")
            action = ResolutionAction.NO_ACTION
            for a in ResolutionAction:
                if a.value == action_str:
                    action = a
                    break

            resolution = Resolution(
                action=action,
                details=result.get("reasoning", ""),
                score_adjustment=float(result.get("score_adjustment", 0.0)),
                penalty_reversed=float(result.get("penalty_reversed", 0.0)),
                agent_id=dispute.plaintiff_id,
            )

            dispute.arbitrator_notes = (
                f"Ruling: {ruling}. {result.get('reasoning', '')}"
            )

            if ruling in ("in_favor", "partial"):
                self.resolve(dispute, resolution)
            else:
                self.dismiss(dispute, reason=dispute.arbitrator_notes)

            return resolution

        except Exception as e:
            console.print(f"  [dim]LLM adjudication error: {e}[/dim]")
            return self._heuristic_adjudicate(dispute)

    def _heuristic_adjudicate(self, dispute: Dispute) -> Resolution:
        """Simple heuristic ruling when LLM is unavailable.

        Conservative approach: only rules in favor with strong evidence.
        """
        evidence_len = len(dispute.evidence.strip())
        description_len = len(dispute.description.strip())

        # Frivolous check: too short to be a real dispute
        if description_len < 20 and evidence_len < 20:
            self.dismiss(dispute, reason="Insufficient description and evidence")
            return Resolution(action=ResolutionAction.NO_ACTION,
                              details="Dismissed: insufficient detail")

        # Default conservative ruling based on dispute type
        if dispute.dispute_type == DisputeType.SCORE_DISPUTE:
            if evidence_len > 100:
                resolution = Resolution(
                    action=ResolutionAction.ADJUST_SCORE,
                    details="Score adjusted based on submitted evidence (heuristic)",
                    score_adjustment=0.1,
                    agent_id=dispute.plaintiff_id,
                )
                self.resolve(dispute, resolution)
                return resolution

        elif dispute.dispute_type == DisputeType.LOAN_DISPUTE:
            if evidence_len > 150:
                resolution = Resolution(
                    action=ResolutionAction.VOID_LOAN,
                    details="Loan voided pending further review (heuristic)",
                )
                self.resolve(dispute, resolution)
                return resolution

        elif dispute.dispute_type == DisputeType.BID_DISPUTE:
            if evidence_len > 100:
                resolution = Resolution(
                    action=ResolutionAction.REINSTATE_AGENT,
                    details="Agent reinstated for next auction round (heuristic)",
                    agent_id=dispute.plaintiff_id,
                )
                self.resolve(dispute, resolution)
                return resolution

        elif dispute.dispute_type == DisputeType.QUALITY_DISPUTE:
            if evidence_len > 100:
                resolution = Resolution(
                    action=ResolutionAction.REVERSE_PENALTY,
                    details="Penalty reversed based on evidence (heuristic)",
                    penalty_reversed=0.15,
                    agent_id=dispute.plaintiff_id,
                )
                self.resolve(dispute, resolution)
                return resolution

        # Default: dismiss with explanation
        self.dismiss(dispute, reason="Insufficient evidence for heuristic ruling")
        return Resolution(action=ResolutionAction.NO_ACTION,
                          details="Dismissed: not enough evidence")

    # ------------------------------------------------------------------
    # Resolution and dismissal
    # ------------------------------------------------------------------

    def resolve(self, dispute: Dispute, resolution: Resolution) -> None:
        """Apply a resolution to a dispute."""
        dispute.status = DisputeStatus.RESOLVED
        dispute.resolution = resolution
        dispute.resolved_at = datetime.now().isoformat()

        self.resolved.append(dispute)
        self._save_dispute(dispute)

        action_labels = {
            ResolutionAction.ADJUST_SCORE: "调整分数 Score Adjusted",
            ResolutionAction.REVERSE_PENALTY: "撤销处罚 Penalty Reversed",
            ResolutionAction.VOID_LOAN: "贷款作废 Loan Voided",
            ResolutionAction.REINSTATE_AGENT: "恢复资格 Agent Reinstated",
            ResolutionAction.NO_ACTION: "维持原判 No Action",
        }
        label = action_labels.get(resolution.action, resolution.action.value)

        console.print(
            f"  [bold green]仲裁 Resolved:[/bold green] {label} "
            f"[dim](dispute {dispute.id})[/dim]"
        )
        if resolution.score_adjustment:
            console.print(
                f"    [dim]Score adjustment: +{resolution.score_adjustment:.2f}[/dim]"
            )
        if resolution.penalty_reversed:
            console.print(
                f"    [dim]Penalty reversed: +{resolution.penalty_reversed:.2f}[/dim]"
            )
        if resolution.details:
            console.print(f"    [dim]{resolution.details[:120]}[/dim]")

    def dismiss(self, dispute: Dispute, reason: str = "") -> None:
        """Dismiss a dispute (frivolous or unsubstantiated)."""
        dispute.status = DisputeStatus.DISMISSED
        dispute.resolved_at = datetime.now().isoformat()
        if reason:
            dispute.arbitrator_notes = reason

        self.dismissed.append(dispute)
        self._save_dispute(dispute)

        console.print(
            f"  [yellow]仲裁 Dismissed:[/yellow] dispute {dispute.id} "
            f"[dim]({dispute.plaintiff_id} vs {dispute.defendant_id})[/dim]"
        )
        if reason:
            console.print(f"    [dim]{reason[:120]}[/dim]")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_dispute(self, dispute: Dispute) -> None:
        """Persist dispute state to memory."""
        resolution_data = None
        if dispute.resolution:
            resolution_data = {
                "action": dispute.resolution.action.value,
                "details": dispute.resolution.details,
                "score_adjustment": dispute.resolution.score_adjustment,
                "penalty_reversed": dispute.resolution.penalty_reversed,
                "loan_id": dispute.resolution.loan_id,
                "agent_id": dispute.resolution.agent_id,
            }

        self.memory.save_economy_state(f"dispute_{dispute.id}", {
            "dispute_type": dispute.dispute_type.value,
            "plaintiff_id": dispute.plaintiff_id,
            "defendant_id": dispute.defendant_id,
            "description": dispute.description[:500],
            "evidence": dispute.evidence[:500],
            "status": dispute.status.value,
            "resolution": resolution_data,
            "arbitrator_notes": dispute.arbitrator_notes,
            "filing_cost": dispute.filing_cost,
            "created_at": dispute.created_at,
            "resolved_at": dispute.resolved_at,
        })

    # ------------------------------------------------------------------
    # Statistics and reporting
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Get arbitration bureau statistics."""
        all_disputes = self.disputes
        if not all_disputes:
            return {
                "total_disputes": 0,
                "open": 0,
                "resolved": 0,
                "dismissed": 0,
                "by_type": {},
                "total_filing_fees": 0.0,
                "total_score_adjustments": 0.0,
                "total_penalties_reversed": 0.0,
            }

        by_type: dict[str, int] = {}
        total_score_adj = 0.0
        total_penalty_rev = 0.0

        for d in all_disputes:
            by_type[d.dispute_type.value] = by_type.get(d.dispute_type.value, 0) + 1
            if d.resolution:
                total_score_adj += d.resolution.score_adjustment
                total_penalty_rev += d.resolution.penalty_reversed

        return {
            "total_disputes": len(all_disputes),
            "open": sum(1 for d in all_disputes if d.status == DisputeStatus.OPEN),
            "resolved": len(self.resolved),
            "dismissed": len(self.dismissed),
            "by_type": by_type,
            "total_filing_fees": round(sum(d.filing_cost for d in all_disputes), 2),
            "total_score_adjustments": round(total_score_adj, 3),
            "total_penalties_reversed": round(total_penalty_rev, 3),
        }

    def print_report(self) -> None:
        """Print arbitration bureau summary report."""
        stats = self.get_stats()

        table = Table(title="劳动仲裁局 Arbitration Bureau", show_header=False,
                      box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        table.add_row("Total Disputes", str(stats["total_disputes"]))
        table.add_row("  Open", f"[yellow]{stats['open']}[/yellow]")
        table.add_row("  Resolved", f"[green]{stats['resolved']}[/green]")
        table.add_row("  Dismissed", f"[dim]{stats['dismissed']}[/dim]")
        table.add_row("Filing Fees Collected", f"{stats['total_filing_fees']:.1f} tokens")

        if stats["total_score_adjustments"]:
            table.add_row("Score Adjustments", f"+{stats['total_score_adjustments']:.3f}")
        if stats["total_penalties_reversed"]:
            table.add_row("Penalties Reversed", f"+{stats['total_penalties_reversed']:.3f}")

        type_labels = {
            "score_dispute": "分数争议 Score",
            "loan_dispute": "贷款争议 Loan",
            "bid_dispute": "竞标争议 Bid",
            "quality_dispute": "质量争议 Quality",
        }

        if stats["by_type"]:
            table.add_row("", "")
            table.add_row("[bold]By Type[/bold]", "")
            for t, count in sorted(stats["by_type"].items()):
                label = type_labels.get(t, t)
                table.add_row(f"  {label}", str(count))

        console.print(Panel(table))

    def print_cases(self, limit: int = 20) -> None:
        """Print recent dispute cases."""
        recent = self.disputes[-limit:]
        if not recent:
            console.print("  [dim]No disputes filed.[/dim]")
            return

        table = Table(title="劳动仲裁 Dispute Cases")
        table.add_column("ID", style="dim")
        table.add_column("Type", style="bold")
        table.add_column("Plaintiff")
        table.add_column("Defendant")
        table.add_column("Status", justify="center")
        table.add_column("Resolution", max_width=30)
        table.add_column("Cost", justify="right")

        type_labels = {
            DisputeType.SCORE_DISPUTE: "分数 Score",
            DisputeType.LOAN_DISPUTE: "贷款 Loan",
            DisputeType.BID_DISPUTE: "竞标 Bid",
            DisputeType.QUALITY_DISPUTE: "质量 Quality",
        }

        status_styles = {
            DisputeStatus.OPEN: "[yellow]open[/yellow]",
            DisputeStatus.RESOLVED: "[green]resolved[/green]",
            DisputeStatus.DISMISSED: "[dim]dismissed[/dim]",
        }

        for d in recent:
            type_label = type_labels.get(d.dispute_type, d.dispute_type.value)
            status_str = status_styles.get(d.status, d.status.value)

            resolution_str = ""
            if d.resolution and d.resolution.action != ResolutionAction.NO_ACTION:
                action_short = {
                    ResolutionAction.ADJUST_SCORE: "score adj",
                    ResolutionAction.REVERSE_PENALTY: "penalty rev",
                    ResolutionAction.VOID_LOAN: "loan void",
                    ResolutionAction.REINSTATE_AGENT: "reinstated",
                }
                resolution_str = action_short.get(d.resolution.action, "")
                if d.resolution.score_adjustment:
                    resolution_str += f" +{d.resolution.score_adjustment:.2f}"
                if d.resolution.penalty_reversed:
                    resolution_str += f" +{d.resolution.penalty_reversed:.2f}"
            elif d.status == DisputeStatus.DISMISSED:
                resolution_str = "dismissed"

            table.add_row(
                d.id,
                type_label,
                d.plaintiff_id[:12],
                d.defendant_id[:12],
                status_str,
                resolution_str or "---",
                f"{d.filing_cost:.1f}",
            )

        console.print(table)

    def get_open_disputes(self) -> list[Dispute]:
        """Return all currently open disputes."""
        return [d for d in self.disputes if d.status == DisputeStatus.OPEN]

    def get_agent_disputes(self, agent_id: str) -> list[Dispute]:
        """Return all disputes involving a specific agent (as plaintiff or defendant)."""
        return [
            d for d in self.disputes
            if d.plaintiff_id == agent_id or d.defendant_id == agent_id
        ]
