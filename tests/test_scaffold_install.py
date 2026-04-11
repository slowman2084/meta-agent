"""scaffold.py 和 install.py 测试"""

import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

PROJECT_ROOT = Path(__file__).parent.parent


# ── scaffold.py ─────────────────────────────────────────────────────


class TestScaffold:
    """通过 subprocess 测试 scaffold.py。"""

    def _run(self, *args):
        import subprocess
        cmd = [sys.executable, str(PROJECT_ROOT / "scripts" / "scaffold.py"), *args]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_creates_all_files(self, tmp_path, monkeypatch):
        """scaffold 创建完整的目录结构。"""
        # 临时修改 AGENTS_DIR
        agents_dir = tmp_path / "source" / "agents"
        agents_dir.mkdir(parents=True)

        import scaffold
        old_dir = scaffold.AGENTS_DIR
        scaffold.AGENTS_DIR = str(agents_dir)
        try:
            scaffold.scaffold("new-agent", "Test description", ["read", "write"])
        finally:
            scaffold.AGENTS_DIR = old_dir

        agent_dir = agents_dir / "new-agent"
        assert agent_dir.is_dir()

        # Subdirs
        for subdir in ["tmp", "bak", "skills", "references"]:
            assert (agent_dir / subdir).is_dir()

        # Files
        assert (agent_dir / "changelog.md").exists()
        assert (agent_dir / ".mcp.json").exists()
        assert (agent_dir / "learnings.jsonl").exists()
        assert (agent_dir / "status.json").exists()
        assert (agent_dir / "agent.json").exists()

    def test_agent_json_has_benefits_from(self, tmp_path):
        agents_dir = tmp_path / "source" / "agents"
        agents_dir.mkdir(parents=True)

        import scaffold
        old_dir = scaffold.AGENTS_DIR
        scaffold.AGENTS_DIR = str(agents_dir)
        try:
            scaffold.scaffold("new-agent", "desc", ["read"])
        finally:
            scaffold.AGENTS_DIR = old_dir

        agent_json = json.loads((agents_dir / "new-agent" / "agent.json").read_text())
        assert "benefits_from" in agent_json
        assert agent_json["benefits_from"] == []

    def test_status_json_defaults(self, tmp_path):
        agents_dir = tmp_path / "source" / "agents"
        agents_dir.mkdir(parents=True)

        import scaffold
        old_dir = scaffold.AGENTS_DIR
        scaffold.AGENTS_DIR = str(agents_dir)
        try:
            scaffold.scaffold("new-agent")
        finally:
            scaffold.AGENTS_DIR = old_dir

        status = json.loads((agents_dir / "new-agent" / "status.json").read_text())
        assert status["name"] == "new-agent"
        assert status["type"] == "agent"
        assert status["phase"] == "created"
        assert status["last_test_score"] is None
        assert status["iterations_completed"] == 0
        assert status["total_learnings"] == 0

    def test_learnings_jsonl_is_empty(self, tmp_path):
        agents_dir = tmp_path / "source" / "agents"
        agents_dir.mkdir(parents=True)

        import scaffold
        old_dir = scaffold.AGENTS_DIR
        scaffold.AGENTS_DIR = str(agents_dir)
        try:
            scaffold.scaffold("new-agent")
        finally:
            scaffold.AGENTS_DIR = old_dir

        learnings = agents_dir / "new-agent" / "learnings.jsonl"
        assert learnings.exists()
        assert learnings.stat().st_size == 0

    def test_idempotent_on_existing_dir(self, tmp_path):
        """对已有目录运行只补充缺失文件。"""
        agents_dir = tmp_path / "source" / "agents"
        agent_dir = agents_dir / "existing-agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "tmp").mkdir()
        (agent_dir / "bak").mkdir()
        (agent_dir / "skills").mkdir()
        (agent_dir / "references").mkdir()
        (agent_dir / "changelog.md").write_text("# existing\n")
        (agent_dir / ".mcp.json").write_text("{}\n")
        (agent_dir / "agent.json").write_text('{"description":"old"}\n')

        import scaffold
        old_dir = scaffold.AGENTS_DIR
        scaffold.AGENTS_DIR = str(agents_dir)
        try:
            scaffold.scaffold("existing-agent")
        finally:
            scaffold.AGENTS_DIR = old_dir

        # Existing files not overwritten
        assert (agent_dir / "changelog.md").read_text() == "# existing\n"
        assert json.loads((agent_dir / "agent.json").read_text())["description"] == "old"
        # New files created
        assert (agent_dir / "learnings.jsonl").exists()
        assert (agent_dir / "status.json").exists()


# ── install.py _SKIP_INSTALL ───────────────────────────────────────


class TestInstallSkipList:
    def test_skip_list_includes_learnings_and_status(self):
        """确保 learnings.jsonl 和 status.json 在排除列表中。"""
        from install import _SKIP_INSTALL
        assert "learnings.jsonl" in _SKIP_INSTALL
        assert "status.json" in _SKIP_INSTALL
        assert "testcases.yaml" in _SKIP_INSTALL
        assert "changelog.md" in _SKIP_INSTALL
        assert "bak" in _SKIP_INSTALL
        assert "tmp" in _SKIP_INSTALL

    def test_skip_list_does_not_exclude_skill_md(self):
        """SKILL.md 和 skill.json 不应在排除列表中。"""
        from install import _SKIP_INSTALL
        assert "SKILL.md" not in _SKIP_INSTALL
        assert "skill.json" not in _SKIP_INSTALL
        assert "scripts" not in _SKIP_INSTALL


class TestInstallNoRules:
    def test_no_rules_source_dir_constant(self):
        """RULES_SOURCE_DIR 常量已移除。"""
        import install
        assert not hasattr(install, "RULES_SOURCE_DIR")

    def test_no_install_rules_function(self):
        """install_rules() 函数已移除。"""
        import install
        assert not hasattr(install, "install_rules")

    def test_no_convert_frontmatter_function(self):
        """convert_frontmatter_for_cli() 函数已移除。"""
        import install
        assert not hasattr(install, "convert_frontmatter_for_cli")

    def test_no_rules_in_non_agent_dirs(self):
        """NON_AGENT_DIRS 不再包含 'rules'。"""
        from install import NON_AGENT_DIRS
        assert "rules" not in NON_AGENT_DIRS


class TestWorkflowIntegrationDocs:
    def test_meta_plan_mentions_recover_and_sync(self):
        content = (PROJECT_ROOT / "source" / "skills" / "meta-plan" / "SKILL.md").read_text(encoding="utf-8")
        assert "scripts/context_tool.py recover [target_dir] --json" in content
        assert "scripts/status_tool.py sync [target_dir]" in content

    def test_meta_iterate_mentions_recover_summary_learning_and_sync(self):
        content = (PROJECT_ROOT / "source" / "skills" / "meta-iterate" / "SKILL.md").read_text(encoding="utf-8")
        assert "scripts/context_tool.py recover [target_dir] --json" in content
        assert "scripts/context_tool.py summary [target_dir]" in content
        assert "scripts/learnings_tool.py log [target_dir]" in content
        assert "scripts/status_tool.py sync [target_dir]" in content

    def test_meta_retrospective_mentions_learning_writeback_and_sync(self):
        content = (PROJECT_ROOT / "source" / "skills" / "meta-retrospective" / "SKILL.md").read_text(encoding="utf-8")
        assert "scripts/learnings_tool.py log [target_dir]" in content
        assert "scripts/status_tool.py sync [target_dir]" in content
        assert "learnings.jsonl" in content

    def test_readme_mentions_integrated_workflow(self):
        content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        assert "这三个脚本已经接入主流程" in content
        assert "恢复上下文 → 执行 → 沉淀经验 → 刷新状态" in content
