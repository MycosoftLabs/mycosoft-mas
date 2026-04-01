"""Tests for the myca CLI.

Tests CLI command structure, output formatting, error handling, and stdin support.
Uses typer's CliRunner to invoke commands without a real HTTP backend.
"""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from mycosoft_mas.cli import app
from mycosoft_mas.cli._client import APIConfig, APIResult
from mycosoft_mas.cli._output import _to_rows, print_result

runner = CliRunner()


# ── App Structure Tests ─────────────────────────────────────────────────


class TestAppStructure:
    """Verify the CLI app has correct subcommands and help text."""

    def test_help_shows_subcommands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for group in ("agent", "task", "system", "memory", "raas", "workflow", "registry", "deploy"):
            assert group in result.output

    def test_version_command(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "myca" in result.output
        assert "1.0.0" in result.output

    def test_agent_help(self):
        result = runner.invoke(app, ["agent", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "invoke" in result.output
        assert "status" in result.output

    def test_task_help(self):
        result = runner.invoke(app, ["task", "--help"])
        assert result.exit_code == 0
        assert "create" in result.output
        assert "list" in result.output
        assert "update" in result.output
        assert "assign" in result.output

    def test_system_help(self):
        result = runner.invoke(app, ["system", "--help"])
        assert result.exit_code == 0
        assert "health" in result.output
        assert "services" in result.output
        assert "info" in result.output

    def test_memory_help(self):
        result = runner.invoke(app, ["memory", "--help"])
        assert result.exit_code == 0
        for cmd in ("write", "read", "search", "list", "delete"):
            assert cmd in result.output

    def test_raas_help(self):
        result = runner.invoke(app, ["raas", "--help"])
        assert result.exit_code == 0
        for cmd in ("catalog", "register", "balance", "packages", "invoke"):
            assert cmd in result.output

    def test_workflow_help(self):
        result = runner.invoke(app, ["workflow", "--help"])
        assert result.exit_code == 0
        assert "trigger" in result.output
        assert "list" in result.output

    def test_registry_help(self):
        result = runner.invoke(app, ["registry", "--help"])
        assert result.exit_code == 0
        for cmd in ("add-agent", "add-api", "add-skill", "sync", "list"):
            assert cmd in result.output

    def test_deploy_help(self):
        result = runner.invoke(app, ["deploy", "--help"])
        assert result.exit_code == 0
        for cmd in ("mas", "mindex", "website", "status"):
            assert cmd in result.output

    def test_subcommand_help_has_examples(self):
        """Agent-friendly CLIs include examples in every --help."""
        result = runner.invoke(app, ["agent", "list", "--help"])
        assert result.exit_code == 0
        assert "Examples:" in result.output or "myca agent list" in result.output

    def test_no_args_shows_help(self):
        """No args should show help, not hang (exit code 0 or 2 both acceptable)."""
        result = runner.invoke(app, [])
        assert result.exit_code in (0, 2)
        assert "agent" in result.output


# ── Output Formatting Tests ─────────────────────────────────────────────


class TestOutputFormatting:
    """Verify JSON, table, and plain output modes."""

    def test_to_rows_from_list(self):
        rows = _to_rows([{"a": 1}, {"a": 2}])
        assert len(rows) == 2
        assert rows[0]["a"] == 1

    def test_to_rows_from_dict_with_agents_key(self):
        rows = _to_rows({"agents": [{"id": "x"}, {"id": "y"}]})
        assert len(rows) == 2

    def test_to_rows_from_single_dict(self):
        rows = _to_rows({"status": "ok"})
        assert len(rows) == 1
        assert rows[0]["status"] == "ok"

    def test_to_rows_from_scalar(self):
        rows = _to_rows("hello")
        assert rows == [{"value": "hello"}]

    def test_json_output(self, capsys):
        print_result({"key": "val"}, "json")
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert parsed["key"] == "val"

    def test_table_output(self, capsys):
        print_result(
            [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}],
            "table",
            keys=["name", "age"],
            headers=["NAME", "AGE"],
        )
        captured = capsys.readouterr()
        assert "NAME" in captured.out
        assert "Alice" in captured.out
        assert "Bob" in captured.out

    def test_plain_output(self, capsys):
        print_result(
            [{"id": "x", "status": "ok"}],
            "plain",
            keys=["id", "status"],
        )
        captured = capsys.readouterr()
        assert "id=x" in captured.out
        assert "status=ok" in captured.out

    def test_empty_table(self, capsys):
        print_result([], "table")
        captured = capsys.readouterr()
        assert "no results" in captured.out.lower()


# ── Client Tests ────────────────────────────────────────────────────────


class TestClient:
    """Test HTTP client configuration and helpers."""

    def test_api_config_defaults(self):
        config = APIConfig()
        assert "192.168.0.188:8001" in config.mas_url
        assert "192.168.0.189:8000" in config.mindex_url
        assert "192.168.0.191:8100" in config.gateway_url

    def test_api_config_env_override(self):
        with patch.dict("os.environ", {"MAS_API_URL": "http://localhost:9999"}):
            config = APIConfig()
            assert config.mas_url == "http://localhost:9999"

    def test_api_result_ok(self):
        r = APIResult(ok=True, status_code=200, data={"status": "ok"})
        assert r.ok
        assert r.data["status"] == "ok"

    def test_api_result_error(self):
        r = APIResult(ok=False, error="Connection refused")
        assert not r.ok
        assert "refused" in r.error.lower()


# ── Command Behavior Tests (with mocked HTTP) ──────────────────────────


def _mock_get_success(*args, **kwargs):
    """Mock client.get that returns success."""
    return APIResult(ok=True, status_code=200, data={
        "agents": [
            {"agent_id": "coding_agent", "name": "CodingAgent", "category": "core", "status": "active"},
            {"agent_id": "research_agent", "name": "ResearchAgent", "category": "core", "status": "active"},
        ],
        "count": 2,
    })


def _mock_get_error(*args, **kwargs):
    """Mock client.get that returns error."""
    return APIResult(ok=False, error="Cannot connect to http://192.168.0.188:8001")


def _mock_post_success(*args, **kwargs):
    """Mock client.post that returns success."""
    return APIResult(ok=True, status_code=200, data={
        "task_id": "task_001",
        "status": "submitted",
        "agent_id": "coding_agent",
    })


class TestAgentCommands:
    """Test agent subcommands with mocked backend."""

    @patch("mycosoft_mas.cli.agent.client.get", side_effect=_mock_get_success)
    def test_agent_list_json(self, mock_get):
        result = runner.invoke(app, ["agent", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "agents" in data
        assert len(data["agents"]) == 2

    @patch("mycosoft_mas.cli.agent.client.get", side_effect=_mock_get_success)
    def test_agent_list_table(self, mock_get):
        result = runner.invoke(app, ["--output", "table", "agent", "list"])
        assert result.exit_code == 0
        assert "coding_agent" in result.output

    @patch("mycosoft_mas.cli.agent.client.get", side_effect=_mock_get_error)
    def test_agent_list_connection_error(self, mock_get):
        result = runner.invoke(app, ["agent", "list"])
        assert result.exit_code != 0

    @patch("mycosoft_mas.cli.agent.client.post", side_effect=_mock_post_success)
    def test_agent_invoke(self, mock_post):
        result = runner.invoke(app, [
            "agent", "invoke", "coding_agent",
            "--type", "code_review",
            "--description", "Review auth module",
        ])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["task_id"] == "task_001"

    @patch("mycosoft_mas.cli.agent.client.get", side_effect=_mock_get_success)
    def test_agent_status(self, mock_get):
        result = runner.invoke(app, ["agent", "status", "coding_agent", "--no-metrics"])
        assert result.exit_code == 0


class TestTaskCommands:
    """Test task subcommands."""

    @patch("mycosoft_mas.cli.task.client.post", side_effect=_mock_post_success)
    def test_task_create(self, mock_post):
        result = runner.invoke(app, [
            "task", "create",
            "--title", "Deploy website",
            "--priority", "high",
        ])
        assert result.exit_code == 0

    def test_task_create_no_title_fails(self):
        result = runner.invoke(app, ["task", "create"])
        assert result.exit_code != 0

    @patch("mycosoft_mas.cli.task.client.get", side_effect=_mock_get_success)
    def test_task_list(self, mock_get):
        result = runner.invoke(app, ["task", "list"])
        assert result.exit_code == 0


class TestSystemCommands:
    """Test system subcommands."""

    @patch("mycosoft_mas.cli.system.client.get", side_effect=_mock_get_success)
    def test_system_health(self, mock_get):
        result = runner.invoke(app, ["system", "health"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "overall" in data

    @patch("mycosoft_mas.cli.system.client.get", side_effect=_mock_get_success)
    def test_system_info(self, mock_get):
        result = runner.invoke(app, ["system", "info"])
        assert result.exit_code == 0


class TestDeployCommands:
    """Test deploy subcommands with dry-run."""

    def test_deploy_dry_run(self):
        result = runner.invoke(app, ["deploy", "mas", "--tag", "v1.2.3", "--dry-run"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["dry_run"] is True
        assert "v1.2.3" in data["tag"]
        assert len(data["steps"]) > 0
        assert "No changes made." in data["message"]

    def test_deploy_requires_confirmation(self):
        """Deploy without --yes should fail with actionable error."""
        result = runner.invoke(app, ["deploy", "mas", "--tag", "v1.2.3"])
        assert result.exit_code != 0

    @patch("mycosoft_mas.cli.deploy.client.post", side_effect=_mock_post_success)
    def test_deploy_with_yes(self, mock_post):
        result = runner.invoke(app, ["deploy", "mas", "--tag", "v1.2.3", "--yes"])
        assert result.exit_code == 0

    @patch("mycosoft_mas.cli.deploy.client.get", side_effect=_mock_get_success)
    def test_deploy_status(self, mock_get):
        result = runner.invoke(app, ["deploy", "status"])
        assert result.exit_code == 0


class TestMemoryCommands:
    """Test memory subcommands."""

    @patch("mycosoft_mas.cli.memory.client.post", side_effect=_mock_post_success)
    def test_memory_write(self, mock_post):
        result = runner.invoke(app, [
            "memory", "write",
            "--content", "test fact",
            "--layer", "semantic",
        ])
        assert result.exit_code == 0

    def test_memory_write_no_content_fails(self):
        result = runner.invoke(app, ["memory", "write"])
        assert result.exit_code != 0

    def test_memory_delete_requires_confirmation(self):
        result = runner.invoke(app, ["memory", "delete", "mem_123"])
        assert result.exit_code != 0


class TestRaaSCommands:
    """Test RaaS subcommands."""

    @patch("mycosoft_mas.cli.raas.client.get", side_effect=_mock_get_success)
    def test_raas_catalog(self, mock_get):
        result = runner.invoke(app, ["raas", "catalog"])
        assert result.exit_code == 0

    @patch("mycosoft_mas.cli.raas.client.post", side_effect=_mock_post_success)
    def test_raas_register(self, mock_post):
        result = runner.invoke(app, [
            "raas", "register",
            "--name", "TestBot",
        ])
        assert result.exit_code == 0


class TestGlobalOptions:
    """Test global --output, --url, --yes flags."""

    @patch("mycosoft_mas.cli.agent.client.get", side_effect=_mock_get_success)
    def test_global_output_table(self, mock_get):
        result = runner.invoke(app, ["--output", "table", "agent", "list"])
        assert result.exit_code == 0
        # Table output should have column headers
        assert "ID" in result.output or "coding_agent" in result.output

    @patch("mycosoft_mas.cli.agent.client.get", side_effect=_mock_get_success)
    def test_global_output_plain(self, mock_get):
        result = runner.invoke(app, ["--output", "plain", "agent", "list"])
        assert result.exit_code == 0

    @patch("mycosoft_mas.cli.deploy.client.post", side_effect=_mock_post_success)
    def test_global_yes_flag(self, mock_post):
        """Global --yes should propagate to deploy commands."""
        result = runner.invoke(app, ["--yes", "deploy", "mas", "--tag", "v1.0"])
        assert result.exit_code == 0
