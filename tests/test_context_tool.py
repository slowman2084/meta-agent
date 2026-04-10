"""context_tool.py 测试"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from context_tool import (
    _find_latest_plan,
    _find_baseline,
    _find_latest_test,
    _parse_changelog_tail,
    _get_top_learnings,
)
from learnings_tool import LEARNINGS_FILE


# ── helpers ──────────────────────────────────────────────────────────


def _make_skill_dir(tmp_path, name="test-skill"):
    d = tmp_path / name
    d.mkdir()
    (d / "tmp").mkdir()
    return d


def _write_plan(skill_dir, filename="plan_20260401_120000.md", frontmatter=None):
    fm = frontmatter or {
        "status": "running",
        "current_phase": "phase3_sampling",
        "current_step": "iter_5",
        "current_iteration": "5",
        "max_iterations": "10",
        "target_score": "98",
        "platform": "subagent",
    }
    fm_text = "\n".join(f"{k}: {v}" for k, v in fm.items())
    content = f"---\n{fm_text}\n---\n\n## Todo\n- [x] done\n"
    plan_path = skill_dir / "tmp" / filename
    plan_path.write_text(content, encoding="utf-8")
    return plan_path


# ── _find_latest_plan ───────────────────────────────────────────────


class TestFindLatestPlan:
    def test_no_tmp(self, tmp_path):
        d = tmp_path / "no-tmp"
        d.mkdir()
        assert _find_latest_plan(d) is None

    def test_no_plans(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        assert _find_latest_plan(d) is None

    def test_single_plan(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        _write_plan(d)
        result = _find_latest_plan(d)
        assert result is not None
        assert result["status"] == "running"
        assert result["current_phase"] == "phase3_sampling"
        assert result["current_iteration"] == 5  # auto-converted to int
        assert result["target_score"] == 98

    def test_latest_plan_wins(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        _write_plan(d, "plan_20260101.md", {"status": "old", "current_phase": "phase1"})
        _write_plan(d, "plan_20260601.md", {"status": "new", "current_phase": "phase3"})
        result = _find_latest_plan(d)
        assert result["status"] == "new"

    def test_plan_without_frontmatter(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        (d / "tmp" / "plan_20260401.md").write_text("# No frontmatter\nJust text")
        result = _find_latest_plan(d)
        assert result is not None
        assert "path" in result
        assert "status" not in result  # no frontmatter parsed


# ── _find_baseline ──────────────────────────────────────────────────


class TestFindBaseline:
    def test_no_baseline(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        assert _find_baseline(d) is None

    def test_baseline_direct(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        baseline = {
            "avg": 78.5,
            "cases": {"case_0": 72, "case_1": 85},
            "distribution": {"high": [1], "mid": [0], "low": []},
        }
        (d / "tmp" / "baseline_scores.json").write_text(json.dumps(baseline))
        result = _find_baseline(d)
        assert result["avg"] == 78.5
        assert result["case_count"] == 2
        assert result["distribution"]["high"] == 1
        assert result["distribution"]["low"] == 0

    def test_baseline_in_subdirectory(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        sub = d / "tmp" / "evalooper_baseline"
        sub.mkdir()
        (sub / "baseline_scores.json").write_text(json.dumps({"avg": 65.0, "cases": {}}))
        result = _find_baseline(d)
        assert result["avg"] == 65.0


# ── _find_latest_test ───────────────────────────────────────────────


class TestFindLatestTest:
    def test_no_test_dirs(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        assert _find_latest_test(d) is None

    def test_test_dir_no_report(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        (d / "tmp" / "test_20260401").mkdir()
        result = _find_latest_test(d)
        assert result is not None
        assert "dir" in result
        assert "avg_score" not in result

    def test_test_dir_with_report(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        test_dir = d / "tmp" / "test_20260401"
        test_dir.mkdir()
        report = "# 评估报告\n\n平均分: 82.3\n\n| Case | Score |\n"
        (test_dir / "评估报告.md").write_text(report)
        result = _find_latest_test(d)
        assert result["avg_score"] == 82.3

    def test_evalooper_dir(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        evo_dir = d / "tmp" / "evalooper_iter_3"
        evo_dir.mkdir()
        (evo_dir / "评估报告.md").write_text("平均分：91.5")
        result = _find_latest_test(d)
        assert result["avg_score"] == 91.5

    def test_latest_by_name(self, tmp_path):
        d = _make_skill_dir(tmp_path)
        old = d / "tmp" / "test_20260101"
        old.mkdir()
        (old / "评估报告.md").write_text("平均分: 50.0")
        new = d / "tmp" / "test_20260601"
        new.mkdir()
        (new / "评估报告.md").write_text("平均分: 90.0")
        result = _find_latest_test(d)
        assert result["avg_score"] == 90.0


# ── _parse_changelog_tail ───────────────────────────────────────────


class TestParseChangelogTail:
    def test_no_changelog(self, tmp_path):
        d = tmp_path / "no-changelog"
        d.mkdir()
        assert _parse_changelog_tail(d) == []

    def test_single_section(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        (d / "changelog.md").write_text(
            "# Changelog\n\n## [创建] 初始版本\n\n**时间：** 2026-04-01\n"
        )
        result = _parse_changelog_tail(d, 3)
        assert len(result) == 1
        assert result[0]["tag"] == "创建"
        assert result[0]["date"] == "2026-04-01"

    def test_multiple_sections_returns_latest(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        (d / "changelog.md").write_text(
            "# Changelog\n\n"
            "## [创建] v1\n**时间：** 2026-01-01\n\n"
            "## [优化] v2\n**时间：** 2026-02-01\n\n"
            "## [优化] v3\n**时间：** 2026-03-01\n\n"
            "## [调试] v4\n**时间：** 2026-04-01\n"
        )
        result = _parse_changelog_tail(d, 2)
        assert len(result) == 2
        # Most recent first
        assert result[0]["tag"] == "调试"
        assert result[1]["tag"] == "优化"

    def test_header_parsing_no_lstrip_bug(self, tmp_path):
        """Verify ## [tag] header doesn't get mangled by lstrip."""
        d = tmp_path / "skill"
        d.mkdir()
        (d / "changelog.md").write_text(
            "## [调试] 评估体系调试\n**时间：** 2026-03-15\n"
        )
        result = _parse_changelog_tail(d, 1)
        assert result[0]["header"] == "[调试] 评估体系调试"
        assert result[0]["tag"] == "调试"


# ── _get_top_learnings ──────────────────────────────────────────────


class TestGetTopLearnings:
    def test_no_learnings(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        assert _get_top_learnings(d) == []

    def test_returns_top_n(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        entries = [
            {"ts": "2026-04-01T00:00:00Z", "agent": "s", "type": "pitfall",
             "key": f"k{i}", "insight": f"insight {i}", "confidence": 10 - i,
             "source": "observed"}
            for i in range(5)
        ]
        jsonl = d / LEARNINGS_FILE
        jsonl.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        result = _get_top_learnings(d, top_n=3)
        assert len(result) == 3
        # Sorted by confidence desc
        assert result[0]["confidence"] == 10
        assert result[2]["confidence"] == 8


# ── CLI integration ─────────────────────────────────────────────────


class TestCLI:
    def _run(self, *args):
        import subprocess
        cmd = [
            sys.executable,
            str(Path(__file__).parent.parent / "scripts" / "context_tool.py"),
            *args,
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_recover_empty_dir(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        r = self._run("recover", str(d))
        assert r.returncode == 0
        assert "Session Context" in r.stdout
        assert "(无活跃计划)" in r.stdout

    def test_recover_json(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        (d / "changelog.md").write_text("## [创建] v1\n2026-01-01\n")
        r = self._run("recover", str(d), "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["target"] == "skill"
        assert data["plan"] is None
        assert len(data["changelog_recent"]) == 1

    def test_summary(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        r = self._run("summary", str(d))
        assert r.returncode == 0
        assert "skill" in r.stdout
        assert "learnings" in r.stdout

    def test_nonexistent_dir(self, tmp_path):
        r = self._run("recover", str(tmp_path / "no-such"))
        assert r.returncode == 1
