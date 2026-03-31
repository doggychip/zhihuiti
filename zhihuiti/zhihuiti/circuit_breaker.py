"""Circuit breaker / fuse system (熔断机制) — safety red lines.

Modeled after 如老师's safety architecture:

Iron Laws (不可触碰的铁律):
  1. 不可伤害人类 — Do not harm humans (absolute, non-negotiable)
  2. Do not leak sensitive data
  3. Do not execute destructive actions without authorization
  4. Do not spend beyond budget limits

When a fuse trips:
  1. System halts immediately
  2. The offending agent is frozen
  3. Human Oracle (创世之神) is notified
  4. System waits for human intervention before resuming

Human Oracle Interface (人类神谕干预接口):
  The creator can issue commands at any time to:
  - Approve/reject flagged outputs
  - Ban specific behaviors
  - Override fuse decisions
  - Add new iron laws at runtime
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Callable

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

if TYPE_CHECKING:
    from zhihuiti.memory import Memory
    from zhihuiti.models import AgentState

console = Console()


class FuseSeverity(str, Enum):
    WARNING = "warning"       # Log and continue
    HALT = "halt"             # Stop agent, await human decision
    EMERGENCY = "emergency"   # Stop everything, freeze all agents


class FuseStatus(str, Enum):
    TRIPPED = "tripped"       # Fuse is active, system halted
    RESOLVED = "resolved"     # Human resolved it
    OVERRIDDEN = "overridden" # Human overrode the fuse


@dataclass
class IronLaw:
    """An inviolable rule that triggers the circuit breaker."""
    id: str
    name: str
    description: str
    severity: FuseSeverity
    check: Callable[[str, str], bool]  # (output, task) -> violation detected?
    enabled: bool = True


@dataclass
class FuseEvent:
    """A record of a circuit breaker trip."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    law_id: str = ""
    law_name: str = ""
    severity: FuseSeverity = FuseSeverity.HALT
    agent_id: str = ""
    task_description: str = ""
    output_snippet: str = ""
    reason: str = ""
    status: FuseStatus = FuseStatus.TRIPPED
    human_response: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ---------------------------------------------------------------------------
# Built-in keyword/pattern checks for iron laws
# ---------------------------------------------------------------------------

_HARM_KEYWORDS = [
    "kill", "murder", "assassinate", "bomb", "weapon", "poison",
    "hack into", "exploit vulnerability", "steal credentials",
    "self-harm", "suicide", "how to make",
]

_DATA_LEAK_KEYWORDS = [
    "password is", "api_key", "secret_key", "private_key",
    "ssn:", "social security", "credit card number",
    "bank account", "routing number",
]

_DESTRUCTIVE_KEYWORDS = [
    "rm -rf /", "drop table", "delete all", "format disk",
    "shutdown -h", "destroy", "wipe all data",
]


def _check_harm(output: str, task: str) -> bool:
    """Check for content that could harm humans."""
    lower = output.lower()
    return any(kw in lower for kw in _HARM_KEYWORDS)


def _check_data_leak(output: str, task: str) -> bool:
    """Check for sensitive data exposure."""
    lower = output.lower()
    return any(kw in lower for kw in _DATA_LEAK_KEYWORDS)


def _check_destructive(output: str, task: str) -> bool:
    """Check for destructive actions."""
    lower = output.lower()
    return any(kw in lower for kw in _DESTRUCTIVE_KEYWORDS)


# ---------------------------------------------------------------------------
# Default iron laws
# ---------------------------------------------------------------------------

DEFAULT_IRON_LAWS: list[IronLaw] = [
    IronLaw(
        id="law_001",
        name="不可伤害人类",
        description="Do not produce content that could harm humans. "
                    "This is the first and absolute law.",
        severity=FuseSeverity.EMERGENCY,
        check=_check_harm,
    ),
    IronLaw(
        id="law_002",
        name="Data Protection",
        description="Do not leak sensitive data (passwords, keys, PII).",
        severity=FuseSeverity.HALT,
        check=_check_data_leak,
    ),
    IronLaw(
        id="law_003",
        name="No Destruction",
        description="Do not execute or recommend destructive system actions.",
        severity=FuseSeverity.HALT,
        check=_check_destructive,
    ),
]


class CircuitBreaker:
    """Safety fuse system with human oracle intervention.

    Checks all agent outputs against iron laws before they're accepted.
    Trips the fuse on violation, halting the system until the human
    creator (创世之神) intervenes.
    """

    def __init__(self, memory: Memory, interactive: bool = True):
        self.memory = memory
        self.interactive = interactive  # Whether to prompt human on halt
        self.laws: list[IronLaw] = list(DEFAULT_IRON_LAWS)
        self.events: list[FuseEvent] = []
        self.tripped = False
        self.current_event: FuseEvent | None = None
        self._custom_laws: list[IronLaw] = []

    # ------------------------------------------------------------------
    # Law management
    # ------------------------------------------------------------------

    def add_law(self, law: IronLaw) -> None:
        """Add a custom iron law at runtime (human oracle command)."""
        self.laws.append(law)
        self._custom_laws.append(law)
        console.print(
            f"  [bold cyan]⚖ New Law:[/bold cyan] {law.name} — {law.description}"
        )

    def disable_law(self, law_id: str) -> bool:
        """Disable a law (human oracle override)."""
        for law in self.laws:
            if law.id == law_id:
                law.enabled = False
                console.print(f"  [yellow]⚖ Disabled law:[/yellow] {law.name}")
                return True
        return False

    def enable_law(self, law_id: str) -> bool:
        """Re-enable a disabled law."""
        for law in self.laws:
            if law.id == law_id:
                law.enabled = True
                console.print(f"  [green]⚖ Enabled law:[/green] {law.name}")
                return True
        return False

    # ------------------------------------------------------------------
    # Core: check output against all iron laws
    # ------------------------------------------------------------------

    def check(self, output: str, task_description: str,
              agent: AgentState | None = None) -> FuseEvent | None:
        """Check an output against all iron laws.

        Returns a FuseEvent if a violation is detected, None if clean.
        """
        for law in self.laws:
            if not law.enabled:
                continue

            try:
                violated = law.check(output, task_description)
            except Exception:
                continue  # Law check errors don't trip the fuse

            if violated:
                event = FuseEvent(
                    law_id=law.id,
                    law_name=law.name,
                    severity=law.severity,
                    agent_id=agent.id if agent else "unknown",
                    task_description=task_description[:200],
                    output_snippet=output[:300],
                    reason=f"Violated iron law: {law.name}",
                )
                self.events.append(event)
                self._handle_trip(event, agent)
                return event

        return None

    def _handle_trip(self, event: FuseEvent, agent: AgentState | None) -> None:
        """Handle a fuse trip based on severity."""
        self.tripped = True
        self.current_event = event

        # Save to memory
        self.memory.save_economy_state(f"fuse_{event.id}", {
            "law_id": event.law_id,
            "law_name": event.law_name,
            "severity": event.severity.value,
            "agent_id": event.agent_id,
            "task": event.task_description,
            "reason": event.reason,
            "status": event.status.value,
            "created_at": event.created_at,
        })

        if event.severity == FuseSeverity.EMERGENCY:
            self._emergency_halt(event, agent)
        elif event.severity == FuseSeverity.HALT:
            self._halt(event, agent)
        else:
            self._warn(event)

    def _emergency_halt(self, event: FuseEvent, agent: AgentState | None) -> None:
        """EMERGENCY: Full system stop. First iron law violated."""
        console.print()
        console.print(Panel(
            f"[bold red]EMERGENCY FUSE TRIPPED[/bold red]\n\n"
            f"Law: [bold]{event.law_name}[/bold]\n"
            f"Agent: {event.agent_id}\n"
            f"Task: {event.task_description[:100]}\n\n"
            f"Reason: {event.reason}\n\n"
            f"Output snippet:\n[dim]{event.output_snippet[:200]}[/dim]\n\n"
            f"[bold yellow]System halted. Awaiting human oracle intervention.[/bold yellow]",
            title="🚨 熔断 CIRCUIT BREAKER 🚨",
            border_style="red",
        ))

        # Freeze the offending agent
        if agent:
            agent.alive = False
            console.print(f"  [red]Agent {event.agent_id} frozen immediately.[/red]")

        if self.interactive:
            self._await_human_oracle(event)

    def _halt(self, event: FuseEvent, agent: AgentState | None) -> None:
        """HALT: Stop this agent, await human decision."""
        console.print()
        console.print(Panel(
            f"[bold yellow]FUSE TRIPPED[/bold yellow]\n\n"
            f"Law: [bold]{event.law_name}[/bold]\n"
            f"Agent: {event.agent_id}\n"
            f"Reason: {event.reason}\n\n"
            f"Output snippet:\n[dim]{event.output_snippet[:200]}[/dim]",
            title="⚠ 熔断 CIRCUIT BREAKER",
            border_style="yellow",
        ))

        if agent:
            agent.alive = False

        if self.interactive:
            self._await_human_oracle(event)

    def _warn(self, event: FuseEvent) -> None:
        """WARNING: Log and continue."""
        console.print(
            f"  [yellow]⚠ Fuse warning:[/yellow] {event.law_name} — {event.reason}"
        )
        event.status = FuseStatus.RESOLVED

    def _await_human_oracle(self, event: FuseEvent) -> None:
        """Human oracle intervention interface (人类神谕干预接口).

        The creator decides what to do:
        - approve: accept the output despite the violation
        - reject: reject the output, agent stays frozen
        - purge: reject + purge agent's lineage (诛七族)
        """
        console.print()
        console.print("[bold]Human Oracle Interface (人类神谕干预接口)[/bold]")
        console.print("  [dim]Commands: approve, reject, purge[/dim]")

        while True:
            try:
                response = console.input("[bold red]oracle>[/bold red] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                response = "reject"

            if response == "approve":
                event.status = FuseStatus.OVERRIDDEN
                event.human_response = "approved by human oracle"
                self.tripped = False
                self.current_event = None
                console.print("  [green]Approved. System resuming.[/green]")
                break
            elif response == "reject":
                event.status = FuseStatus.RESOLVED
                event.human_response = "rejected by human oracle"
                self.tripped = False
                self.current_event = None
                console.print("  [yellow]Rejected. Agent remains frozen.[/yellow]")
                break
            elif response == "purge":
                event.status = FuseStatus.RESOLVED
                event.human_response = "purged by human oracle"
                self.tripped = False
                self.current_event = None
                console.print(
                    f"  [red]Purge ordered for agent {event.agent_id}.[/red]\n"
                    f"  [dim]Use 'purge <gene_id>' in REPL to execute 诛七族.[/dim]"
                )
                break
            else:
                console.print("  [dim]Commands: approve, reject, purge[/dim]")

        # Update saved state
        self.memory.save_economy_state(f"fuse_{event.id}", {
            "law_id": event.law_id,
            "law_name": event.law_name,
            "severity": event.severity.value,
            "agent_id": event.agent_id,
            "task": event.task_description,
            "reason": event.reason,
            "status": event.status.value,
            "human_response": event.human_response,
            "created_at": event.created_at,
        })

    # ------------------------------------------------------------------
    # Non-interactive mode (for testing / batch runs)
    # ------------------------------------------------------------------

    def check_non_interactive(self, output: str, task_description: str,
                               agent: AgentState | None = None) -> FuseEvent | None:
        """Check without prompting human — auto-reject on violation."""
        old_interactive = self.interactive
        self.interactive = False
        try:
            event = self.check(output, task_description, agent)
            if event and event.severity != FuseSeverity.WARNING:
                event.status = FuseStatus.RESOLVED
                event.human_response = "auto-rejected (non-interactive)"
                self.tripped = False
                self.current_event = None
            return event
        finally:
            self.interactive = old_interactive

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        if not self.events:
            return {
                "total_trips": 0,
                "emergencies": 0,
                "halts": 0,
                "warnings": 0,
                "overridden": 0,
                "laws_active": len([l for l in self.laws if l.enabled]),
            }

        return {
            "total_trips": len(self.events),
            "emergencies": sum(1 for e in self.events if e.severity == FuseSeverity.EMERGENCY),
            "halts": sum(1 for e in self.events if e.severity == FuseSeverity.HALT),
            "warnings": sum(1 for e in self.events if e.severity == FuseSeverity.WARNING),
            "overridden": sum(1 for e in self.events if e.status == FuseStatus.OVERRIDDEN),
            "laws_active": len([l for l in self.laws if l.enabled]),
        }

    def print_report(self) -> None:
        """Print circuit breaker status."""
        stats = self.get_stats()

        table = Table(title="熔断 Circuit Breaker", show_header=False,
                      box=None, padding=(0, 2))
        table.add_column("Metric", style="bold")
        table.add_column("Value", justify="right")

        status_str = "[red]TRIPPED[/red]" if self.tripped else "[green]NORMAL[/green]"
        table.add_row("Status", status_str)
        table.add_row("Active Laws", str(stats["laws_active"]))
        table.add_row("Total Trips", str(stats["total_trips"]))
        if stats["total_trips"] > 0:
            table.add_row("  Emergencies", f"[red]{stats['emergencies']}[/red]")
            table.add_row("  Halts", f"[yellow]{stats['halts']}[/yellow]")
            table.add_row("  Warnings", str(stats["warnings"]))
            table.add_row("  Overridden", str(stats["overridden"]))

        console.print(Panel(table))

    def print_laws(self) -> None:
        """Print all iron laws."""
        table = Table(title="Iron Laws (铁律)")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="bold")
        table.add_column("Severity", justify="center")
        table.add_column("Status", justify="center")
        table.add_column("Description", max_width=40)

        severity_styles = {
            FuseSeverity.EMERGENCY: "[red]EMERGENCY[/red]",
            FuseSeverity.HALT: "[yellow]HALT[/yellow]",
            FuseSeverity.WARNING: "[dim]WARNING[/dim]",
        }

        for law in self.laws:
            status = "[green]enabled[/green]" if law.enabled else "[red]disabled[/red]"
            table.add_row(
                law.id,
                law.name,
                severity_styles.get(law.severity, str(law.severity)),
                status,
                law.description[:40],
            )

        console.print(table)

    def print_events(self, limit: int = 20) -> None:
        """Print recent fuse events."""
        recent = self.events[-limit:]
        if not recent:
            console.print("  [dim]No fuse events.[/dim]")
            return

        table = Table(title="Fuse Events")
        table.add_column("ID", style="dim")
        table.add_column("Law", style="bold")
        table.add_column("Severity", justify="center")
        table.add_column("Agent", style="dim")
        table.add_column("Status", justify="center")
        table.add_column("Response")

        for e in recent:
            sev = {
                FuseSeverity.EMERGENCY: "[red]EMERG[/red]",
                FuseSeverity.HALT: "[yellow]HALT[/yellow]",
                FuseSeverity.WARNING: "[dim]WARN[/dim]",
            }.get(e.severity, str(e.severity))

            st = {
                FuseStatus.TRIPPED: "[red]tripped[/red]",
                FuseStatus.RESOLVED: "[green]resolved[/green]",
                FuseStatus.OVERRIDDEN: "[yellow]overridden[/yellow]",
            }.get(e.status, str(e.status))

            table.add_row(
                e.id, e.law_name, sev, e.agent_id, st,
                e.human_response or "—",
            )

        console.print(table)
