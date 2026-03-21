import argparse

from .engine import run


def main():
    parser = argparse.ArgumentParser(
        description="Silicon Realms - Three-Realm Agent Civilization"
    )
    sub = parser.add_subparsers(dest="command")

    # --- simulate (default) ---
    sim_parser = sub.add_parser("simulate", help="Run the token economy simulation")
    sim_parser.add_argument("--config", default="config.yaml", help="Path to config file")
    sim_parser.add_argument("--no-plot", action="store_true", help="Skip chart generation")

    # --- crew ---
    crew_parser = sub.add_parser("crew", help="Run a task through the three-realm CrewAI system")
    crew_parser.add_argument("task", help="Task description for the three realms to work on")
    crew_parser.add_argument("--llm", default=None, help="LLM model to use (default: Claude Sonnet)")
    crew_parser.add_argument("--quiet", action="store_true", help="Reduce CrewAI output verbosity")

    # --- collide ---
    collide_parser = sub.add_parser("collide", help="Theory collision engine: find mathematical isomorphisms")
    collide_parser.add_argument("theory_a", nargs="?", help="First theory key (omit to list all)")
    collide_parser.add_argument("theory_b", nargs="?", help="Second theory key")
    collide_parser.add_argument("--top", type=int, default=0,
                                help="Show top N strongest collisions across all theory pairs")
    collide_parser.add_argument("--list", action="store_true", help="List available theory keys")

    args = parser.parse_args()

    if args.command == "collide":
        from .theory.collision_engine import collide, top_collisions, list_theories
        if getattr(args, "list", False):
            print("Available theories:")
            for t in list_theories():
                print(f"  {t}")
        elif args.top:
            reports = top_collisions(args.top)
            for r in reports:
                print(r)
        elif args.theory_a and args.theory_b:
            r = collide(args.theory_a, args.theory_b)
            print(r)
        else:
            print("Usage: silicon-realms collide <theory_a> <theory_b>")
            print("       silicon-realms collide --top 10")
            print("       silicon-realms collide --list")
    elif args.command == "crew":
        from .crews.realms import run_three_realms
        run_three_realms(args.task, llm=args.llm, verbose=not args.quiet)
    else:
        # Default to simulate
        config = getattr(args, "config", "config.yaml")
        no_plot = getattr(args, "no_plot", False)
        run(config, plot=not no_plot)


if __name__ == "__main__":
    main()
