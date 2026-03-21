import argparse

from .engine import run


def main():
    parser = argparse.ArgumentParser(
        description="Silicon Realms - Three-Realm Agent Civilization"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config file"
    )
    parser.add_argument(
        "--no-plot", action="store_true", help="Skip chart generation"
    )
    args = parser.parse_args()
    run(args.config, plot=not args.no_plot)


if __name__ == "__main__":
    main()
