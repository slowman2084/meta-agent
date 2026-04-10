"""status_tool.py 测试"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from status_tool import (
    _read_status,
    _write_status,
    _detect_type,
    _parse_value,
    _sync_from_artifacts,
    STATUS_FILE,
)
from learnings_tool import LEARNINGS_FILE


# ── helpers ──────────────────────────────────────────────────────────


def _make_dir(tmp_path, name="test-agent", parent="agents"):
    d = tmp_path / "source" / parent / name
    d.mkdir(parents=True)
    (d / "tmp").mkdir()
    return d


# ── _read_status / _write_status ────────────────────────────────────


class TestReadWriteStatus:
    def test_read_nonexistent_returns_defaults(self, tmp_path):
        d = _make_dir(tmp_path)
        status = _read_status(d)
        assert status["name"] == "test-agent"
        assert status["phase"] == "created"
        assert status["last_test_score"] is None
        assert status["iterations_completed"] == 0

    def test_write_then_read(self, tmp_path):
        d = _make_dir(tmp_path)
        _write_status(d, {"name": "test-agent", "phase": "iterate", "total_learnings": 5})
        status = _read_status(d)
        assert status["phase"] == "iterate"
        assert status["total_learnings"] == 5

    def test_read_malformed_json_returns_defaults(self, tmp_path):
        d = _make_dir(tmp_path)
        (d / STATUS_FILE).write_text("not json")
        status = _read_status(d)
        assert status["name"] == "test-agent"
        assert status["phase"] == "created"


# ── _detect_type ────────────────────────────────────────────────────


class TestDetectType:
    def test_agent_path(self, tmp_path):
        d = _make_dir(tmp_path, parent="agents")
        assert _detect_type(d) == "agent"

    def test_skill_path(self, tmp_path):
        d = _make_dir(tmp_path, name="test-skill", parent="skills")
        assert _detect_type(d) == "skill"

    def test_ambiguous_defaults_to_agent(self, tmp_path):
        d = tmp_path / "random-dir"
        d.mkdir()
        assert _detect_type(d) == "agent"

    def test_skills_in_name_not_misdetected(self, tmp_path):
        """Agent named 'my-skills-helper' under agents/ should be 'agent', not 'skill'."""
        d = _make_dir(tmp_path, name="my-skills-helper", parent="agents")
        assert _detect_type(d) == "agent"


# ── _parse_value ────────────────────────────────────────────────────


class TestParseValue:
    def test_int(self):
        assert _parse_value("42") == 42

    def test_float(self):
        assert _parse_value("3.14") == 3.14

    def test_null(self):
        assert _parse_value("null") is None
        assert _parse_value("None") is None

    def test_string(self):
        assert _parse_value("iterate") == "iterate"


# ── _sync_from_artifacts ────────────────────────────────────────────


class TestSyncFromArtifacts:
    def test_empty_dir(self, tmp_path):
        d = _make_dir(tmp_path)
        status = _sync_from_artifacts(d)
        assert status["name"] == "test-agent"
        assert status["active_plan"] is None
        assert status["total_learnings"] == 0

    def test_with_plan(self, tmp_path):
        d = _make_dir(tmp_path)
        fm = "---\nstatus: running\ncurrent_phase: phase2\ncurrent_iteration: 3\n---\n"
        (d / "tmp" / "plan_20260401.md").write_text(fm)
        status = _sync_from_artifacts(d)
        assert status["phase"] == "phase2"
        assert status["iterations_completed"] == 3
        assert "plan_20260401.md" in status["active_plan"]

    def test_with_baseline(self, tmp_path):
        d = _make_dir(tmp_path)
        baseline = {"avg": 72.5, "cases": {"c0": 70, "c1": 75}}
        (d / "tmp" / "baseline_scores.json").write_text(json.dumps(baseline))
        status = _sync_from_artifacts(d)
        assert status["baseline_score"] == 72.5

    def test_with_test_results(self, tmp_path):
        d = _make_dir(tmp_path)
        test_dir = d / "tmp" / "test_20260401"
        test_dir.mkdir()
        (test_dir / "评估报告.md").write_text("# Report\n\n平均分: 88.5\n")
        status = _sync_from_artifacts(d)
        assert status["last_test_score"] == 88.5

    def test_with_learnings(self, tmp_path):
        d = _make_dir(tmp_path)
        entries = [
            {"ts": "2026-04-01T00:00:00Z", "agent": "a", "type": "pitfall",
             "key": f"k{i}", "insight": "i", "confidence": 5, "source": "observed"}
            for i in range(4)
        ]
        jsonl = d / LEARNINGS_FILE
        jsonl.write_text("\n".join(json.dumps(e) for e in entries) + "\n")
        status = _sync_from_artifacts(d)
        assert status["total_learnings"] == 4

    def test_combined(self, tmp_path):
        """All artifacts present."""
        d = _make_dir(tmp_path)
        # Plan
        (d / "tmp" / "plan_20260501.md").write_text(
            "---\nstatus: running\ncurrent_phase: phase3\ncurrent_iteration: 7\n---\n"
        )
        # Baseline
        (d / "tmp" / "baseline_scores.json").write_text(
            json.dumps({"avg": 60.0, "cases": {}})
        )
        # Test results
        test_dir = d / "tmp" / "evalooper_iter_7"
        test_dir.mkdir()
        (test_dir / "评估报告.md").write_text("平均分：92.1")
        # Learnings
        (d / LEARNINGS_FILE).write_text(
            json.dumps({"ts": "2026-05-01T00:00:00Z", "agent": "a", "type": "pitfall",
                        "key": "k1", "insight": "i", "confidence": 5, "source": "observed"}) + "\n"
        )

        status = _sync_from_artifacts(d)
        assert status["phase"] == "phase3"
        assert status["iterations_completed"] == 7
        assert status["baseline_score"] == 60.0
        assert status["last_test_score"] == 92.1
        assert status["total_learnings"] == 1
        assert status["last_activity"] is not None


# ── CLI integration ─────────────────────────────────────────────────


class TestCLI:
    def _run(self, *args):
        import subprocess
        cmd = [
            sys.executable,
            str(Path(__file__).parent.parent / "scripts" / "status_tool.py"),
            *args,
        ]
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_get_defaults(self, tmp_path):
        d = _make_dir(tmp_path)
        r = self._run("get", str(d))
        assert r.returncode == 0
        assert "test-agent" in r.stdout
        assert "created" in r.stdout

    def test_get_field(self, tmp_path):
        d = _make_dir(tmp_path)
        _write_status(d, {"name": "a", "phase": "iterate"})
        r = self._run("get", str(d), "--field", "phase")
        assert r.returncode == 0
        assert r.stdout.strip() == "iterate"

    def test_get_json(self, tmp_path):
        d = _make_dir(tmp_path)
        _write_status(d, {"name": "a", "phase": "test"})
        r = self._run("get", str(d), "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["phase"] == "test"

    def test_set(self, tmp_path):
        d = _make_dir(tmp_path)
        _write_status(d, {"name": "a", "phase": "created"})
        r = self._run("set", str(d), "phase", "iterate")
        assert r.returncode == 0
        assert "created → iterate" in r.stdout
        status = json.loads((d / STATUS_FILE).read_text())
        assert status["phase"] == "iterate"

    def test_set_numeric(self, tmp_path):
        d = _make_dir(tmp_path)
        _write_status(d, {"name": "a", "last_test_score": None})
        r = self._run("set", str(d), "last_test_score", "92.5")
        assert r.returncode == 0
        status = json.loads((d / STATUS_FILE).read_text())
        assert status["last_test_score"] == 92.5

    def test_sync(self, tmp_path):
        d = _make_dir(tmp_path)
        (d / "tmp" / "baseline_scores.json").write_text(json.dumps({"avg": 70.0, "cases": {}}))
        r = self._run("sync", str(d))
        assert r.returncode == 0
        assert "baseline=70.0" in r.stdout

    def test_nonexistent_dir(self, tmp_path):
        r = self._run("get", str(tmp_path / "no-such"))
        assert r.returncode == 1
