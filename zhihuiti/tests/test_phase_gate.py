"""Tests for the phase gate system."""

import pytest
from zhihuiti.phase_gate import PhaseGate, GateMode, GateResult


class TestPhaseGate:
    def test_pass_on_good_results(self):
        gate = PhaseGate(mode=GateMode.SOFT)
        results = [
            {"status": "completed", "score": 0.8},
            {"status": "completed", "score": 0.7},
        ]
        result = gate.evaluate(0, results)
        assert result.passed
        assert result.acceptance_rate == 1.0
        assert result.avg_score == 0.75

    def test_fail_on_low_acceptance(self):
        gate = PhaseGate(mode=GateMode.SOFT, min_acceptance_rate=0.7)
        results = [
            {"status": "completed", "score": 0.8},
            {"status": "failed", "score": 0.2},
            {"status": "failed", "score": 0.1},
        ]
        result = gate.evaluate(0, results)
        assert not result.passed
        assert result.failed_tasks == 2
        assert any("Acceptance rate" in i for i in result.issues)

    def test_fail_on_low_avg_score(self):
        gate = PhaseGate(mode=GateMode.SOFT, min_avg_score=0.6)
        results = [
            {"status": "completed", "score": 0.5},
            {"status": "completed", "score": 0.4},
        ]
        result = gate.evaluate(0, results)
        assert not result.passed
        assert any("Average score" in i for i in result.issues)

    def test_fail_on_fuse_trip(self):
        gate = PhaseGate(mode=GateMode.SOFT, block_on_fuse=True)
        results = [
            {"status": "completed", "score": 0.8},
            {"status": "fuse_tripped", "score": 0.0},
        ]
        result = gate.evaluate(0, results)
        assert not result.passed
        assert result.fuse_trips == 1

    def test_soft_mode_always_continues(self):
        gate = PhaseGate(mode=GateMode.SOFT)
        result = GateResult(
            wave_idx=0, passed=False, acceptance_rate=0.0,
            avg_score=0.0, total_tasks=1, passed_tasks=0,
            failed_tasks=1, fuse_trips=0,
        )
        assert gate.should_continue(result)

    def test_hard_mode_halts_on_failure(self):
        gate = PhaseGate(mode=GateMode.HARD)
        result = GateResult(
            wave_idx=0, passed=False, acceptance_rate=0.0,
            avg_score=0.0, total_tasks=1, passed_tasks=0,
            failed_tasks=1, fuse_trips=0,
        )
        assert not gate.should_continue(result)

    def test_hard_mode_continues_on_pass(self):
        gate = PhaseGate(mode=GateMode.HARD)
        result = GateResult(
            wave_idx=0, passed=True, acceptance_rate=1.0,
            avg_score=0.8, total_tasks=1, passed_tasks=1,
            failed_tasks=0, fuse_trips=0,
        )
        assert gate.should_continue(result)

    def test_off_mode_always_continues(self):
        gate = PhaseGate(mode=GateMode.OFF)
        result = GateResult(
            wave_idx=0, passed=False, acceptance_rate=0.0,
            avg_score=0.0, total_tasks=1, passed_tasks=0,
            failed_tasks=1, fuse_trips=0,
        )
        assert gate.should_continue(result)

    def test_empty_wave_passes(self):
        gate = PhaseGate(mode=GateMode.HARD)
        result = gate.evaluate(0, [])
        assert result.passed

    def test_history_tracked(self):
        gate = PhaseGate(mode=GateMode.SOFT)
        gate.evaluate(0, [{"status": "completed", "score": 0.8}])
        gate.evaluate(1, [{"status": "completed", "score": 0.6}])
        assert len(gate.history) == 2

    def test_accepted_with_issues_counts_as_passed(self):
        gate = PhaseGate(mode=GateMode.SOFT)
        results = [
            {"status": "accepted_with_issues", "score": 0.55},
        ]
        result = gate.evaluate(0, results)
        assert result.passed_tasks == 1


class TestRICEScore:
    def test_score_calculation(self):
        from zhihuiti.rice import RICEScore
        score = RICEScore(
            task_id="t1", description="test",
            reach=3, impact=2, confidence=0.8, effort=2,
        )
        # (3 * 2 * 0.8) / 2 = 2.4
        assert abs(score.score - 2.4) < 0.001

    def test_zero_effort(self):
        from zhihuiti.rice import RICEScore
        score = RICEScore(
            task_id="t1", description="test", effort=0,
        )
        assert score.score == 0.0
