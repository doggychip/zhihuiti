import argparse

from .engine import run


def main():
    parser = argparse.ArgumentParser(
        description="Silicon Realms - Three-Realm Agent Civilization"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config file"
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
