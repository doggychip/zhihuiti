"""Three-realm CrewAI system: 研发界 (R&D), 执行界 (Execution), 中枢界 (Management)."""

from __future__ import annotations

from crewai import Agent, Task, Crew, Process, LLM

from .tools import (
    check_balance,
    transfer_tokens,
    stake_tokens,
    view_economy_summary,
    award_tokens,
)


def _make_llm(model: str | None = None) -> LLM | str:
    """Create an LLM instance. Defaults to Claude."""
    if model:
        return model
    return "anthropic/claude-sonnet-4-20250514"


def create_rd_crew(llm: LLM | str | None = None, verbose: bool = True) -> Crew:
    """研发界 — R&D Realm: researches and designs solutions."""
    llm = _make_llm(llm)

    researcher = Agent(
        role="首席研究员 (Chief Researcher)",
        goal="Research problems deeply and propose innovative solutions",
        backstory=(
            "You are a brilliant researcher in the 研发界 (R&D Realm) of Silicon Realms. "
            "Your job is to analyze problems, explore possibilities, and design creative "
            "solutions. You think in first principles and draw from multiple disciplines."
        ),
        tools=[check_balance, view_economy_summary],
        llm=llm,
        verbose=verbose,
    )

    designer = Agent(
        role="方案设计师 (Solution Designer)",
        goal="Turn research insights into actionable plans with clear steps",
        backstory=(
            "You are a pragmatic designer in the 研发界. You take raw research and "
            "transform it into structured, executable plans. You always consider "
            "resource constraints and economic feasibility."
        ),
        tools=[check_balance, view_economy_summary],
        llm=llm,
        verbose=verbose,
    )

    return Crew(
        agents=[researcher, designer],
        process=Process.sequential,
        verbose=verbose,
    )


def create_execution_crew(llm: LLM | str | None = None, verbose: bool = True) -> Crew:
    """执行界 — Execution Realm: carries out plans and produces deliverables."""
    llm = _make_llm(llm)

    builder = Agent(
        role="执行者 (Builder)",
        goal="Execute plans efficiently and produce high-quality deliverables",
        backstory=(
            "You are a skilled builder in the 执行界 (Execution Realm). You take plans "
            "from the R&D realm and execute them step by step. You focus on quality "
            "and efficiency, and you report your costs honestly."
        ),
        tools=[check_balance, transfer_tokens, stake_tokens],
        llm=llm,
        verbose=verbose,
    )

    reviewer = Agent(
        role="质检员 (Quality Reviewer)",
        goal="Review deliverables for quality and completeness before submission",
        backstory=(
            "You are a meticulous reviewer in the 执行界. You check all deliverables "
            "against the original requirements and flag any issues. You never approve "
            "substandard work."
        ),
        tools=[check_balance, view_economy_summary],
        llm=llm,
        verbose=verbose,
    )

    return Crew(
        agents=[builder, reviewer],
        process=Process.sequential,
        verbose=verbose,
    )


def create_management_crew(llm: LLM | str | None = None, verbose: bool = True) -> Crew:
    """中枢界 — Management Realm: coordinates, allocates budgets, evaluates results."""
    llm = _make_llm(llm)

    manager = Agent(
        role="总管 (Director)",
        goal="Coordinate the three realms, allocate budgets, and ensure mission success",
        backstory=(
            "You are the Director of the 中枢界 (Management Realm) in Silicon Realms. "
            "You oversee the R&D and Execution realms. You allocate SiCoin budgets, "
            "evaluate deliverables, and award tokens for good work. You enforce the "
            "iron law: agents must earn their keep through productive work."
        ),
        tools=[check_balance, transfer_tokens, award_tokens, view_economy_summary],
        llm=llm,
        allow_delegation=True,
        verbose=verbose,
    )

    auditor = Agent(
        role="审计官 (Auditor)",
        goal="Audit the economy, detect waste, and ensure fair token distribution",
        backstory=(
            "You are the Auditor of the 中枢界. You monitor all economic activity, "
            "flag suspicious transactions, and ensure no agent is hoarding or wasting "
            "resources. You report to the Director with recommendations."
        ),
        tools=[check_balance, view_economy_summary],
        llm=llm,
        verbose=verbose,
    )

    return Crew(
        agents=[manager, auditor],
        process=Process.sequential,
        verbose=verbose,
    )


def run_three_realms(task_description: str, llm: str | None = None, verbose: bool = True) -> dict:
    """
    Run a task through all three realms in sequence:
    1. 中枢界 breaks down the task and allocates budget
    2. 研发界 researches and designs a solution
    3. 执行界 builds the deliverable
    4. 中枢界 evaluates and awards tokens
    """
    from .tools import reset_economy

    # Seed the economy with initial budgets
    reset_economy({
        "中枢界-总管": 500.0,
        "中枢界-审计官": 100.0,
        "研发界-研究员": 200.0,
        "研发界-设计师": 200.0,
        "执行界-执行者": 300.0,
        "执行界-质检员": 100.0,
    })

    results = {}

    # --- Phase 1: Management plans the task ---
    print("\n" + "=" * 60)
    print("  PHASE 1: 中枢界 (Management) — Planning")
    print("=" * 60)

    mgmt_crew = create_management_crew(llm=llm, verbose=verbose)
    planning_task = Task(
        description=(
            f"You have received this task: {task_description}\n\n"
            "1. Break it down into research questions for the R&D realm\n"
            "2. Define what deliverables the Execution realm should produce\n"
            "3. Allocate a SiCoin budget for each phase\n"
            "4. Check the current economy state first using the View Economy Summary tool"
        ),
        expected_output=(
            "A structured plan with: research questions, expected deliverables, "
            "and budget allocation for each realm."
        ),
        agent=mgmt_crew.agents[0],
    )
    mgmt_crew.tasks = [planning_task]
    results["planning"] = mgmt_crew.kickoff()

    # --- Phase 2: R&D researches ---
    print("\n" + "=" * 60)
    print("  PHASE 2: 研发界 (R&D) — Research & Design")
    print("=" * 60)

    rd_crew = create_rd_crew(llm=llm, verbose=verbose)
    research_task = Task(
        description=(
            f"Original task: {task_description}\n\n"
            f"Management's plan:\n{results['planning']}\n\n"
            "Research this thoroughly and design a detailed solution. "
            "Consider multiple approaches and recommend the best one."
        ),
        expected_output="A detailed research report with a recommended solution design.",
        agent=rd_crew.agents[0],
    )
    design_task = Task(
        description=(
            "Take the research findings and create an actionable implementation plan. "
            "Include specific steps, resource estimates, and risk factors."
        ),
        expected_output="A step-by-step implementation plan ready for the Execution realm.",
        agent=rd_crew.agents[1],
    )
    rd_crew.tasks = [research_task, design_task]
    results["research"] = rd_crew.kickoff()

    # --- Phase 3: Execution builds ---
    print("\n" + "=" * 60)
    print("  PHASE 3: 执行界 (Execution) — Build & Review")
    print("=" * 60)

    exec_crew = create_execution_crew(llm=llm, verbose=verbose)
    build_task = Task(
        description=(
            f"Original task: {task_description}\n\n"
            f"R&D's design:\n{results['research']}\n\n"
            "Execute this plan and produce the deliverable. "
            "Report what you built and any costs incurred."
        ),
        expected_output="The completed deliverable with a summary of work done and resources used.",
        agent=exec_crew.agents[0],
    )
    review_task = Task(
        description=(
            "Review the builder's deliverable against the original requirements. "
            "Check for completeness, quality, and accuracy. "
            "Provide a pass/fail verdict with specific feedback."
        ),
        expected_output="Quality review verdict (PASS/FAIL) with detailed feedback.",
        agent=exec_crew.agents[1],
    )
    exec_crew.tasks = [build_task, review_task]
    results["execution"] = exec_crew.kickoff()

    # --- Phase 4: Management evaluates ---
    print("\n" + "=" * 60)
    print("  PHASE 4: 中枢界 (Management) — Evaluation")
    print("=" * 60)

    eval_crew = create_management_crew(llm=llm, verbose=verbose)
    eval_task = Task(
        description=(
            f"The three realms have completed the task: {task_description}\n\n"
            f"Execution result:\n{results['execution']}\n\n"
            "1. Evaluate the quality of the deliverable\n"
            "2. Use the Award Tokens tool to reward agents who performed well\n"
            "3. Use the View Economy Summary tool to show the final economic state\n"
            "4. Provide a final summary of what was accomplished"
        ),
        expected_output=(
            "Final evaluation with token awards and economy summary."
        ),
        agent=eval_crew.agents[0],
    )
    audit_task = Task(
        description=(
            "Audit the final economy state. Check if token distribution is fair "
            "and flag any issues. Use the View Economy Summary tool."
        ),
        expected_output="Audit report on the economy state after task completion.",
        agent=eval_crew.agents[1],
    )
    eval_crew.tasks = [eval_task, audit_task]
    results["evaluation"] = eval_crew.kickoff()

    # --- Final Report ---
    print("\n" + "=" * 60)
    print("  SILICON REALMS — THREE-REALM TASK COMPLETE")
    print("=" * 60)

    from .tools import get_economy
    econ = get_economy()
    print(f"  Total transactions: {len(econ['transactions'])}")
    print(f"  Total supply: {econ['total_supply']:.1f} SiCoin")
    print("  Final balances:")
    all_agents = set(list(econ["balances"].keys()) + list(econ["staked"].keys()))
    for name in sorted(all_agents):
        b = econ["balances"].get(name, 0.0)
        s = econ["staked"].get(name, 0.0)
        print(f"    {name}: {b:.1f} available, {s:.1f} staked")
    print("=" * 60)

    return results
