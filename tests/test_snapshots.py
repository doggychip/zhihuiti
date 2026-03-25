"""Tests for the versioned state / checkpoint / rollback layer."""

from zhihuiti.memory import Memory


def _make_mem() -> Memory:
    return Memory(":memory:")


def test_checkpoint_creates_snapshot():
    mem = _make_mem()
    mem.save_agent("a1", "researcher", 100.0, 0, 0.8, True)
    sid = mem.checkpoint(phase="test", goal_id="g1", tags=["init"])
    assert sid
    snaps = mem.recall(goal_id="g1")
    assert len(snaps) == 1
    assert snaps[0]["phase"] == "test"
    mem.close()


def test_checkpoint_captures_state():
    mem = _make_mem()
    mem.save_agent("a1", "researcher", 100.0, 0, 0.8, True)
    sid = mem.checkpoint(phase="p1")
    data = mem.get_snapshot_data(sid)
    assert data is not None
    assert len(data["agents"]) == 1
    assert data["agents"][0]["id"] == "a1"
    assert data["agents"][0]["budget"] == 100.0
    mem.close()


def test_rollback_restores_state():
    mem = _make_mem()
    mem.save_agent("a1", "researcher", 100.0, 0, 0.8, True)
    sid = mem.checkpoint(phase="before_change")

    # Mutate state
    mem.save_agent("a1", "researcher", 50.0, 0, 0.3, True)
    mem.save_agent("a2", "coder", 200.0, 0, 0.9, True)

    # Verify mutation
    stats = mem.get_stats()
    assert stats["total_agents"] == 2

    # Rollback
    mem.rollback(sid)

    # Verify rollback
    stats = mem.get_stats()
    assert stats["total_agents"] == 1
    row = mem._query_one("SELECT budget FROM agents WHERE id = 'a1'")
    assert row["budget"] == 100.0
    mem.close()


def test_rollback_invalid_id_raises():
    mem = _make_mem()
    try:
        mem.rollback("nonexistent")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    mem.close()


def test_recall_filters_by_goal():
    mem = _make_mem()
    mem.checkpoint(phase="p1", goal_id="g1", tags=["a"])
    mem.checkpoint(phase="p2", goal_id="g2", tags=["b"])
    mem.checkpoint(phase="p3", goal_id="g1", tags=["c"])

    g1_snaps = mem.recall(goal_id="g1")
    assert len(g1_snaps) == 2
    assert all(s["goal_id"] == "g1" for s in g1_snaps)

    g2_snaps = mem.recall(goal_id="g2")
    assert len(g2_snaps) == 1
    mem.close()


def test_recall_filters_by_phase():
    mem = _make_mem()
    mem.checkpoint(phase="wave_0_complete", goal_id="g1")
    mem.checkpoint(phase="wave_1_complete", goal_id="g1")
    mem.checkpoint(phase="pre_execution", goal_id="g1")

    snaps = mem.recall(phase="wave_0_complete")
    assert len(snaps) == 1
    assert snaps[0]["phase"] == "wave_0_complete"
    mem.close()


def test_search_snapshots_by_tags():
    mem = _make_mem()
    mem.checkpoint(phase="p1", tags=["backend", "api_design"])
    mem.checkpoint(phase="p2", tags=["frontend", "ui"])
    mem.checkpoint(phase="p3", tags=["backend", "database"])

    results = mem.search_snapshots(["backend"])
    assert len(results) == 2

    results = mem.search_snapshots(["ui"])
    assert len(results) == 1

    results = mem.search_snapshots(["backend", "ui"])
    assert len(results) == 3
    mem.close()


def test_snapshot_chain():
    mem = _make_mem()
    s1 = mem.checkpoint(phase="wave_0", goal_id="g1")
    s2 = mem.checkpoint(phase="wave_1", goal_id="g1")
    s3 = mem.checkpoint(phase="wave_2", goal_id="g1")

    chain = mem.get_snapshot_chain(s3)
    assert len(chain) == 3
    assert chain[0]["id"] == s3
    assert chain[1]["id"] == s2
    assert chain[2]["id"] == s1
    mem.close()


def test_rollback_preserves_economy_state():
    mem = _make_mem()
    mem.save_economy_state("treasury", {"balance": 1000})
    sid = mem.checkpoint(phase="before")

    mem.save_economy_state("treasury", {"balance": 200})
    assert mem.get_economy_state("treasury")["balance"] == 200

    mem.rollback(sid)
    assert mem.get_economy_state("treasury")["balance"] == 1000
    mem.close()


def test_rollback_preserves_tasks():
    mem = _make_mem()
    mem.save_task("t1", "task one", "completed", score=0.9)
    sid = mem.checkpoint(phase="before", include=["tasks"])

    mem.save_task("t1", "task one", "failed", score=0.1)
    mem.save_task("t2", "task two", "completed", score=0.8)

    mem.rollback(sid)
    stats = mem.get_stats()
    assert stats["total_tasks"] == 1
    mem.close()


def test_checkpoint_custom_include():
    mem = _make_mem()
    mem.save_agent("a1", "researcher", 100.0, 0, 0.8, True)
    mem.save_economy_state("treasury", {"balance": 500})

    sid = mem.checkpoint(phase="partial", include=["agents"])
    data = mem.get_snapshot_data(sid)
    assert "agents" in data
    assert "economy_state" not in data
    mem.close()


def test_multiple_rollbacks():
    """Rollback to different points in time."""
    mem = _make_mem()
    mem.save_agent("a1", "researcher", 100.0, 0, 0.5, True)
    s1 = mem.checkpoint(phase="v1")

    mem.save_agent("a1", "researcher", 80.0, 0, 0.6, True)
    s2 = mem.checkpoint(phase="v2")

    mem.save_agent("a1", "researcher", 60.0, 0, 0.7, True)

    # Rollback to v2
    mem.rollback(s2)
    row = mem._query_one("SELECT budget FROM agents WHERE id = 'a1'")
    assert row["budget"] == 80.0

    # Rollback to v1
    mem.rollback(s1)
    row = mem._query_one("SELECT budget FROM agents WHERE id = 'a1'")
    assert row["budget"] == 100.0
    mem.close()


def test_get_snapshot_data_nonexistent():
    mem = _make_mem()
    assert mem.get_snapshot_data("nope") is None
    mem.close()


def test_snapshot_chain_single():
    mem = _make_mem()
    s1 = mem.checkpoint(phase="only")
    chain = mem.get_snapshot_chain(s1)
    assert len(chain) == 1
    mem.close()


def test_recall_limit():
    mem = _make_mem()
    for i in range(10):
        mem.checkpoint(phase=f"p{i}", goal_id="g1")

    snaps = mem.recall(goal_id="g1", limit=3)
    assert len(snaps) == 3
    mem.close()
