"""Entry point for `python -m cribl_cli` and the `cribl` console script."""

from cribl_cli.cli import cli


def main() -> None:
    cli(standalone_mode=True)


if __name__ == "__main__":
    main()
