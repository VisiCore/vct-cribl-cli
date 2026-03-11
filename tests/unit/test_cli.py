"""Tests for CLI command registration and help output."""

from __future__ import annotations

from click.testing import CliRunner

from cribl_cli.cli import cli


def test_cli_has_help():
    """The root CLI responds to --help and contains the description."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Cribl CLI" in result.output


def test_cli_help_lists_global_options():
    """The root --help shows global options like --dry-run and --profile."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    assert "--dry-run" in result.output
    assert "--profile" in result.output
    assert "--base-url" in result.output
    assert "--verbose" in result.output


def test_config_subcommands_exist():
    """The 'config' command group is registered and has help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])

    assert result.exit_code == 0


def test_workers_subcommands_exist():
    """The 'workers' command group is registered and has help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["workers", "--help"])

    assert result.exit_code == 0


def test_routes_subcommands_exist():
    """The 'routes' command group has list, get, create, update, delete."""
    runner = CliRunner()
    result = runner.invoke(cli, ["routes", "--help"])

    assert result.exit_code == 0
    for sub in ("list", "get", "create", "update", "delete"):
        assert sub in result.output


def test_factory_commands_registered():
    """Factory-generated commands from the registry are present on the CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])

    # Spot-check a few factory-generated command names
    for cmd_name in ("parsers", "users", "roles", "macros", "lake-datasets"):
        assert cmd_name in result.output, f"Expected '{cmd_name}' in CLI help"


def test_factory_command_has_crud_subcommands():
    """A factory-generated command group exposes CRUD subcommands."""
    runner = CliRunner()
    result = runner.invoke(cli, ["parsers", "--help"])

    assert result.exit_code == 0
    for sub in ("list", "get", "create", "update", "delete"):
        assert sub in result.output
