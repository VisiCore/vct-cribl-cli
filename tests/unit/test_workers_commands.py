"""Tests for workers command — rm error handling and add dry-run."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
from click.testing import CliRunner

from cribl_cli.cli import cli


def _mock_response(json_data, status_code=200):
    resp = MagicMock(spec=httpx.Response)
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status.return_value = None
    return resp


def _completed(returncode, stdout="", stderr=""):
    """Build a subprocess.CompletedProcess mock."""
    cp = MagicMock()
    cp.returncode = returncode
    cp.stdout = stdout
    cp.stderr = stderr
    return cp


# ---------------------------------------------------------------------------
# workers rm
# ---------------------------------------------------------------------------


@patch("cribl_cli.commands.workers.subprocess.run")
@patch("cribl_cli.commands.workers.get_client")
def test_rm_success(mock_client, mock_run):
    """Both docker stop and docker rm succeed."""
    mock_run.side_effect = [
        _completed(0),  # docker stop
        _completed(0),  # docker rm
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["workers", "rm", "my-container"], catch_exceptions=False)

    assert result.exit_code == 0
    assert '"removed"' in result.output
    assert mock_run.call_count == 2


@patch("cribl_cli.commands.workers.subprocess.run")
@patch("cribl_cli.commands.workers.get_client")
def test_rm_stop_fails_rm_succeeds(mock_client, mock_run):
    """Container already stopped — stop fails with 'not running', rm succeeds."""
    mock_run.side_effect = [
        _completed(1, stderr="Error: container is not running"),  # docker stop
        _completed(0),  # docker rm
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["workers", "rm", "my-container"], catch_exceptions=False)

    assert result.exit_code == 0
    assert '"removed"' in result.output


@patch("cribl_cli.commands.workers.subprocess.run")
@patch("cribl_cli.commands.workers.get_client")
def test_rm_container_not_found(mock_client, mock_run):
    """Container doesn't exist — docker rm reports 'No such container'."""
    mock_run.side_effect = [
        _completed(1, stderr="No such container: foo"),  # docker stop
        _completed(1, stderr="Error: No such container: foo"),  # docker rm
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["workers", "rm", "foo"])

    assert result.exit_code != 0
    assert "does not exist" in result.output or "does not exist" in (result.output + getattr(result, "stderr", ""))


@patch("cribl_cli.commands.workers.subprocess.run")
@patch("cribl_cli.commands.workers.get_client")
def test_rm_docker_rm_other_error(mock_client, mock_run):
    """docker rm fails for an unexpected reason — reports stderr."""
    mock_run.side_effect = [
        _completed(0),  # docker stop ok
        _completed(1, stderr="permission denied"),  # docker rm fails
    ]
    runner = CliRunner()
    result = runner.invoke(cli, ["workers", "rm", "my-container"])

    assert result.exit_code != 0


@patch("cribl_cli.commands.workers.subprocess.run", side_effect=FileNotFoundError)
@patch("cribl_cli.commands.workers.get_client")
def test_rm_docker_not_installed(mock_client, mock_run):
    """Docker not installed — FileNotFoundError caught, clear message."""
    runner = CliRunner()
    result = runner.invoke(cli, ["workers", "rm", "my-container"])

    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# workers add --dry-run
# ---------------------------------------------------------------------------


@patch("cribl_cli.commands.workers.subprocess.run")
@patch("cribl_cli.commands.workers.get_client")
@patch("cribl_cli.commands.workers.load_config")
def test_add_dry_run_prints_command(mock_config, mock_get_client, mock_run):
    """--dry-run prints docker command without calling subprocess."""
    # Setup config mock
    cfg = MagicMock()
    cfg.base_url = "https://myorg.cribl.cloud"
    mock_config.return_value = cfg

    # Setup client mock — version info + group list
    client = MagicMock(spec=httpx.Client)
    client.get.side_effect = [
        _mock_response({"items": [{"BUILD": {"VERSION": "4.17.0-abc123"}}]}),
        _mock_response({"items": [{"id": "default"}]}),
    ]
    mock_get_client.return_value = client

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["workers", "add", "default", "--token", "test-token", "--dry-run"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
    assert "docker run -d" in result.output
    # subprocess should not have been called
    mock_run.assert_not_called()


@patch("cribl_cli.commands.workers.get_client")
@patch("cribl_cli.commands.workers.load_config")
def test_add_group_not_found(mock_config, mock_get_client):
    """Invalid group — error reported."""
    cfg = MagicMock()
    cfg.base_url = "https://myorg.cribl.cloud"
    mock_config.return_value = cfg

    client = MagicMock(spec=httpx.Client)
    client.get.side_effect = [
        _mock_response({"items": [{"BUILD": {"VERSION": "4.17.0-abc"}}]}),
        _mock_response({"items": [{"id": "default"}, {"id": "prod"}]}),
    ]
    mock_get_client.return_value = client

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["workers", "add", "nonexistent", "--token", "test-token"],
    )

    assert result.exit_code != 0
