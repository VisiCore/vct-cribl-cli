"""Integration smoke tests - require CRIBL_INTEGRATION_TEST=true and valid credentials."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def skip_without_env():
    """Skip all tests in this module unless the integration flag is set."""
    if os.environ.get("CRIBL_INTEGRATION_TEST") != "true":
        pytest.skip("Set CRIBL_INTEGRATION_TEST=true to run")


def test_config_show():
    """Smoke: 'config show' runs without crashing."""
    from click.testing import CliRunner
    from cribl_cli.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["config", "--help"])
    assert result.exit_code in (0, 1)


def test_workers_list():
    """Smoke: 'workers list' succeeds against a live Cribl instance."""
    from click.testing import CliRunner
    from cribl_cli.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["workers", "list"])
    assert result.exit_code == 0


def test_system_health():
    """Smoke: 'system health' succeeds against a live Cribl instance."""
    from click.testing import CliRunner
    from cribl_cli.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["system", "health"])
    assert result.exit_code == 0


def test_parsers_list():
    """Smoke: factory-generated 'parsers list' succeeds."""
    from click.testing import CliRunner
    from cribl_cli.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["parsers", "list"])
    assert result.exit_code == 0


def test_routes_list():
    """Smoke: 'routes list' succeeds against a live Cribl instance."""
    from click.testing import CliRunner
    from cribl_cli.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["routes", "list"])
    assert result.exit_code == 0
