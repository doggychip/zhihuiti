"""Tests for the structured retry/escalation protocol."""

import pytest
from zhihuiti.retry import (
    RetryProtocol,
    RetryState,
    QAFeedback,
    EscalationAction,
    MAX_RETRY_ATTEMPTS,
)
from zhihuiti.models import Task


class TestRetryState:
    def test_initial_state(self):
        state = RetryState(task_id="t1")
        assert state.attempt == 0
        assert state.best_score == 0.0
        assert not state.exhausted
        assert state.escalation is None

    def test_record_attempt_increments(self):
        state = RetryState(task_id="t1")
        state.record_attempt(0.3, "result", ["issue 1"])
        assert state.attempt == 1
        assert state.best_score == 0.3
        assert len(state.feedback_history) == 1

    def test_best_score_tracked(self):
        state = RetryState(task_id="t1")
        state.record_attempt(0.3, "bad", ["issue"])
        state.record_attempt(0.6, "better", ["minor issue"])
        state.record_attempt(0.4, "worse", ["issue"])
        assert state.best_score == 0.6
        assert state.best_result == "better"

    def test_exhausted_after_max_attempts(self):
        state = RetryState(task_id="t1")
        for i in range(MAX_RETRY_ATTEMPTS):
            state.record_attempt(0.3, "result", [f"issue {i}"])
        assert state.exhausted

    def test_format_feedback_empty(self):
        state = RetryState(task_id="t1")
        assert state.format_feedback_context() == ""

    def test_format_feedback_includes_issues(self):
        state = RetryState(task_id="t1")
        state.record_attempt(0.3, "result", ["bad formatting", "missing data"])
        context = state.format_feedback_context()
        assert "bad formatting" in context
        assert "missing data" in context
        assert "Attempt 1" in context

    def test_format_feedback_includes_fuse(self):
        state = RetryState(task_id="t1")
        state.record_attempt(
            0.0, "result", ["dangerous"],
            fuse_tripped=True, fuse_law="no_harm",
        )
        context = state.format_feedback_context()
        assert "circuit breaker" in context.lower()
        assert "no_harm" in context


class TestRetryProtocol:
    def test_should_retry_initially(self):
        proto = RetryProtocol(max_retries=3)
        task = Task(description="test task")
        assert proto.should_retry(task)

    def test_should_not_retry_after_exhaustion(self):
        proto = RetryProtocol(max_retries=2)
        task = Task(description="test task")
        for _ in range(2):
            proto.record_failure(task, score=0.3, result="bad")
        assert not proto.should_retry(task)

    def test_record_failure_creates_state(self):
        proto = RetryProtocol()
        task = Task(description="test task")
        state = proto.record_failure(task, score=0.4, result="partial")
        assert state.attempt == 1
        assert len(state.feedback_history) == 1

    def test_get_retry_context(self):
        proto = RetryProtocol()
        task = Task(description="test task")
        proto.record_failure(task, score=0.3, result="bad")
        context = proto.get_retry_context(task)
        assert "QA Feedback" in context
        assert "Attempt 1" in context

    def test_escalate_defer_on_fuse(self):
        proto = RetryProtocol(max_retries=1)
        task = Task(description="test")

        class FakeFuseEvent:
            law_name = "no_harm"

        proto.record_failure(task, score=0.0, result="bad", fuse_event=FakeFuseEvent())
        action = proto.escalate(task)
        assert action == EscalationAction.DEFER

    def test_escalate_reassign_on_low_score(self):
        proto = RetryProtocol(max_retries=1)
        task = Task(description="test")
        proto.record_failure(task, score=0.2, result="bad")
        action = proto.escalate(task)
        assert action == EscalationAction.REASSIGN

    def test_escalate_decompose_on_medium_score(self):
        proto = RetryProtocol(max_retries=1)
        task = Task(description="test")
        proto.record_failure(task, score=0.4, result="ok-ish")
        action = proto.escalate(task)
        assert action == EscalationAction.DECOMPOSE

    def test_escalate_accept_on_decent_score(self):
        proto = RetryProtocol(max_retries=1)
        task = Task(description="test")
        proto.record_failure(task, score=0.6, result="decent")
        action = proto.escalate(task)
        assert action == EscalationAction.ACCEPT

    def test_get_stats(self):
        proto = RetryProtocol(max_retries=2)
        t1 = Task(description="task 1")
        t2 = Task(description="task 2")
        proto.record_failure(t1, score=0.3, result="bad")
        proto.record_failure(t1, score=0.3, result="bad")
        proto.escalate(t1)
        proto.record_failure(t2, score=0.5, result="ok")

        stats = proto.get_stats()
        assert stats["total_tasks"] == 2
        assert stats["retried"] == 1  # t1 had 2 attempts
        assert stats["escalated"] == 1
