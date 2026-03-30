"""Structured retry and escalation protocol (inspired by agency-agents Dev↔QA loop).

Instead of blindly retrying failed tasks, this module:
1. Collects structured QA feedback on why a task failed
2. Passes that feedback to the retrying agent as context
3. After max attempts, escalates with a recommendation (reassign/decompose/defer)

Protocol:
  Attempt 1 → Execute → QA feedback (PASS/FAIL)
  Attempt 2 → Execute with QA feedback injected → QA feedback
  Attempt 3 → Execute with cumulative feedback → QA feedback
  Attempt 3 FAIL → ESCALATE (choose: reassign to different role, decompose, or defer)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from rich.console import Console

if TYPE_CHECKING:
    from zhihuiti.models import Task

console = Console()

MAX_RETRY_ATTEMPTS = 3


class EscalationAction(str, Enum):
    """What to do when a task exhausts all retry attempts."""
    REASSIGN = "reassign"    # Try a different agent role
    DECOMPOSE = "decompose"  # Break into smaller subtasks
    DEFER = "defer"          # Skip this task, continue pipeline
    ACCEPT = "accept"        # Accept best attempt despite failures


@dataclass
class QAFeedback:
    """Structured feedback from a failed attempt."""
    attempt: int
    score: float
    issues: list[str]
    failed_layer: str | None = None
    fuse_tripped: bool = False
    fuse_law: str = ""


@dataclass
class RetryState:
    """Tracks retry state for a single task."""
    task_id: str
    attempt: int = 0
    feedback_history: list[QAFeedback] = field(default_factory=list)
    best_score: float = 0.0
    best_result: str = ""
    escalation: EscalationAction | None = None

    @property
    def exhausted(self) -> bool:
        return self.attempt >= MAX_RETRY_ATTEMPTS

    def record_attempt(self, score: float, result: str, issues: list[str],
                       failed_layer: str | None = None,
                       fuse_tripped: bool = False, fuse_law: str = "") -> None:
        self.attempt += 1
        feedback = QAFeedback(
            attempt=self.attempt,
            score=score,
            issues=issues,
            failed_layer=failed_layer,
            fuse_tripped=fuse_tripped,
            fuse_law=fuse_law,
        )
        self.feedback_history.append(feedback)
        if score > self.best_score:
            self.best_score = score
            self.best_result = result

    def format_feedback_context(self) -> str:
        """Format all prior feedback as context for the next attempt."""
        if not self.feedback_history:
            return ""

        lines = [
            f"## QA Feedback from Prior Attempts ({len(self.feedback_history)} attempt(s))\n"
        ]
        for fb in self.feedback_history:
            lines.append(f"### Attempt {fb.attempt} (score: {fb.score:.2f})")
            if fb.fuse_tripped:
                lines.append(f"- REJECTED by circuit breaker: {fb.fuse_law}")
            if fb.failed_layer:
                lines.append(f"- Failed at inspection layer: {fb.failed_layer}")
            if fb.issues:
                for issue in fb.issues:
                    lines.append(f"- {issue}")
            lines.append("")

        lines.append(
            "Address ALL issues listed above in your next attempt. "
            "Do not repeat the same mistakes."
        )
        return "\n".join(lines)


class RetryProtocol:
    """Manages structured retry/escalation for task execution."""

    def __init__(self, max_retries: int = MAX_RETRY_ATTEMPTS):
        self.max_retries = max_retries
        self.states: dict[str, RetryState] = {}

    def get_state(self, task: Task) -> RetryState:
        if task.id not in self.states:
            self.states[task.id] = RetryState(task_id=task.id)
        return self.states[task.id]

    def should_retry(self, task: Task) -> bool:
        state = self.get_state(task)
        return state.attempt < self.max_retries

    def record_failure(self, task: Task, score: float, result: str,
                       inspection_result=None, fuse_event=None) -> RetryState:
        """Record a failed attempt with structured feedback."""
        state = self.get_state(task)

        issues = []
        failed_layer = None
        fuse_tripped = False
        fuse_law = ""

        # Extract issues from inspection result
        if inspection_result:
            for lr in getattr(inspection_result, 'layers', []):
                if not lr.passed:
                    failed_layer = lr.layer.value
                    if lr.reasoning:
                        issues.append(f"[{lr.layer.value}] {lr.reasoning[:200]}")

        # Extract issues from circuit breaker
        if fuse_event:
            fuse_tripped = True
            fuse_law = getattr(fuse_event, 'law_name', 'unknown')
            issues.append(f"Circuit breaker tripped: {fuse_law}")

        # If no specific issues found, add generic feedback from score
        if not issues:
            if score < 0.3:
                issues.append("Output quality critically low — may be off-topic or empty")
            elif score < 0.5:
                issues.append("Output partially addresses the task but has major gaps")
            else:
                issues.append("Output is acceptable but needs improvement in thoroughness")

        state.record_attempt(score, result, issues, failed_layer, fuse_tripped, fuse_law)
        return state

    def get_retry_context(self, task: Task) -> str:
        """Get feedback context to inject into the next retry attempt."""
        state = self.get_state(task)
        return state.format_feedback_context()

    def escalate(self, task: Task) -> EscalationAction:
        """Determine escalation action when retries are exhausted.

        Logic:
        - If fuse tripped on any attempt → defer (safety issue)
        - If best score < 0.3 → reassign (fundamentally wrong approach)
        - If best score < 0.5 → decompose (task may be too complex)
        - Otherwise → accept best attempt (close enough)
        """
        state = self.get_state(task)

        any_fuse = any(fb.fuse_tripped for fb in state.feedback_history)
        if any_fuse:
            action = EscalationAction.DEFER
        elif state.best_score < 0.3:
            action = EscalationAction.REASSIGN
        elif state.best_score < 0.5:
            action = EscalationAction.DECOMPOSE
        else:
            action = EscalationAction.ACCEPT

        state.escalation = action

        console.print(
            f"\n  [bold yellow]⚠ ESCALATION[/bold yellow] after {state.attempt} attempts "
            f"(best score: {state.best_score:.2f})"
        )
        console.print(f"  [yellow]Action: {action.value}[/yellow]")

        if action == EscalationAction.REASSIGN:
            console.print("  [dim]→ Task will be re-auctioned to a different agent role[/dim]")
        elif action == EscalationAction.DECOMPOSE:
            console.print("  [dim]→ Task may be too complex — consider breaking it down[/dim]")
        elif action == EscalationAction.DEFER:
            console.print("  [dim]→ Task deferred due to safety concerns[/dim]")
        else:
            console.print("  [dim]→ Accepting best attempt despite quality concerns[/dim]")

        return action

    def get_stats(self) -> dict:
        """Return retry statistics."""
        total = len(self.states)
        retried = sum(1 for s in self.states.values() if s.attempt > 1)
        escalated = sum(1 for s in self.states.values() if s.escalation is not None)
        return {
            "total_tasks": total,
            "retried": retried,
            "escalated": escalated,
            "escalation_actions": {
                action.value: sum(
                    1 for s in self.states.values() if s.escalation == action
                )
                for action in EscalationAction
            },
        }
