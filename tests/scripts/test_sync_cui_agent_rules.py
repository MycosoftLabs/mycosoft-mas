from pathlib import Path

from scripts.sync_cui_agent_rules import MARKER, bind_agent_files


def test_binds_markdown_after_frontmatter(tmp_path: Path) -> None:
    agent = tmp_path / ".cursor" / "agents" / "backend.md"
    agent.parent.mkdir(parents=True)
    agent.write_text("---\nname: backend\n---\n\n# Backend\n", encoding="utf-8")
    changed = bind_agent_files(tmp_path)
    text = agent.read_text(encoding="utf-8")
    assert changed == [".cursor/agents/backend.md"]
    assert text.startswith("---\nname: backend\n---\n")
    assert MARKER in text
    assert "# Backend" in text


def test_binding_is_idempotent(tmp_path: Path) -> None:
    agent = tmp_path / ".claude" / "agents" / "agent.md"
    agent.parent.mkdir(parents=True)
    agent.write_text("# Agent\n", encoding="utf-8")
    assert bind_agent_files(tmp_path)
    assert bind_agent_files(tmp_path) == []
    assert agent.read_text(encoding="utf-8").count(MARKER) == 1
