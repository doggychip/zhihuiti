"""Tests for SQLite memory system."""

from zhihuiti.memory import Memory


def test_prune_alive_agents_keeps_top_agents_with_role_diversity():
    mem = Memory(":memory:")
    for index, (role, score) in enumerate((
        ("researcher", 0.9),
        ("researcher", 0.8),
        ("researcher", 0.7),
        ("analyst", 0.85),
        ("analyst", 0.75),
    )):
        mem.save_agent(
            agent_id=f"agent-{index}", role=role, budget=100.0,
            depth=0, avg_score=score, alive=True,
        )

    assert mem.prune_alive_agents(max_alive=3, max_per_role=2) == 2
    alive = mem._query(
        "SELECT role, avg_score FROM agents WHERE alive = 1 ORDER BY avg_score DESC"
    )
    assert [(row["role"], row["avg_score"]) for row in alive] == [
        ("researcher", 0.9),
        ("analyst", 0.85),
        ("researcher", 0.8),
    ]
    mem.close()


def test_memory_init():
    mem = Memory(":memory:")
    stats = mem.get_stats()
    assert stats["total_tasks"] == 0
    assert stats["total_agents"] == 0
    mem.close()


def test_save_and_get_task():
    mem = Memory(":memory:")
    mem.save_task("t1", "test task", "completed", result="done", score=0.9, agent_id="a1")
    stats = mem.get_stats()
    assert stats["total_tasks"] == 1
    mem.close()


def test_latest_task_state_distinguishes_validated_from_legacy_work():
    mem = Memory(":memory:")
    mem.save_task(
        "legacy", "old task", "completed", result="done", agent_id="a1",
    )
    mem.save_task(
        "validated", "new task", "completed", result="done", agent_id="a2",
        metadata={"role_execution": {
            "assigned_role": "analyst",
            "execution_mode": "telemetry_analysis",
            "work_status": "validated",
            "validation_reason": "deterministic_pass",
        }},
    )

    states = mem.get_latest_task_states_by_agent()

    assert states["a1"]["work_status"] == "legacy_unvalidated"
    assert states["a2"]["work_status"] == "validated"
    assert states["a2"]["assigned_role"] == "analyst"
    mem.close()


def test_save_and_get_agent():
    mem = Memory(":memory:")
    mem.save_agent("a1", "researcher", 100.0, 0, 0.8, True)
    stats = mem.get_stats()
    assert stats["total_agents"] == 1
    mem.close()


def test_gene_pool():
    mem = Memory(":memory:")
    mem.save_to_gene_pool("g1", "researcher", "prompt", 0.7, 0.9)
    mem.save_to_gene_pool("g2", "researcher", "prompt2", 0.6, 0.8)
    genes = mem.get_best_genes("researcher", limit=5)
    assert len(genes) == 2
    assert genes[0]["avg_score"] >= genes[1]["avg_score"]
    mem.close()


def test_task_history():
    mem = Memory(":memory:")
    mem.record_task_history("task1", "researcher", "result1", 0.9)
    mem.record_task_history("task2", "researcher", "result2", 0.3)
    successes = mem.get_similar_successes("researcher")
    assert len(successes) == 1
    assert successes[0]["score"] == 0.9
    mem.close()


def test_economy_state():
    mem = Memory(":memory:")
    mem.save_economy_state("test_entity", {"balance": 100})
    state = mem.get_economy_state("test_entity")
    assert state["balance"] == 100
    mem.close()


def test_lineage():
    mem = Memory(":memory:")
    mem.save_lineage("g1", "researcher", 0, avg_score=0.8)
    mem.save_lineage("g2", "researcher", 0, avg_score=0.7)
    mem.save_lineage("g3", "researcher", 1, parent_a_gene="g1", parent_b_gene="g2", avg_score=0.85)

    ancestors = mem.get_lineage_ancestors("g3", max_depth=7)
    assert len(ancestors) == 3

    descendants = mem.get_lineage_descendants("g1", max_depth=7)
    assert len(descendants) == 1
    assert descendants[0]["gene_id"] == "g3"

    top = mem.get_top_lineage_genes("researcher", limit=2)
    assert len(top) == 2

    stats = mem.get_lineage_stats()
    assert stats["total_genes"] == 3
    assert stats["max_generation"] == 1
    mem.close()


def test_relationships():
    mem = Memory(":memory:")
    mem.save_relationship("r1", "transaction", "a1", "a2", strength=1.5)
    mem.save_relationship("r2", "competition", "a1", "a3")

    rels = mem.get_agent_relationships("a1")
    assert len(rels) == 2

    rels_typed = mem.get_agent_relationships("a1", "transaction")
    assert len(rels_typed) == 1

    all_rels = mem.get_all_relationships()
    assert len(all_rels) == 2

    mem.deactivate_relationship("r1")
    active = mem.get_all_relationships(active_only=True)
    assert len(active) == 1
    mem.close()


def test_loans():
    mem = Memory(":memory:")
    mem.save_loan("l1", "lender1", "borrower1", 50.0, 0.15)
    mem.save_loan("l2", "lender2", "borrower1", 30.0, 0.10, status="repaid", amount_repaid=33.0)

    active = mem.get_active_loans()
    assert len(active) == 1

    borrower_loans = mem.get_agent_loans("borrower1")
    assert len(borrower_loans) == 2

    lender_loans = mem.get_agent_loans("lender1", role="lender")
    assert len(lender_loans) == 1

    stats = mem.get_loan_stats()
    assert stats["total_loans"] == 2
    assert stats["active"] == 1
    assert stats["repaid"] == 1

    mem.update_loan("l1", 57.5, "repaid")
    active2 = mem.get_active_loans()
    assert len(active2) == 0
    mem.close()
