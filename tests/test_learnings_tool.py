"""learnings_tool.py 测试"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

# 添加 scripts/ 到 path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from learnings_tool import (
    _load_learnings,
    _dedup_learnings,
    _effective_confidence,
    _filter_learnings,
    LEARNINGS_FILE,
)


# ── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def skill_dir(tmp_path):
    """创建一个临时 skill 目录。"""
    d = tmp_path / "test-skill"
    d.mkdir()
    return d


def _write_entries(skill_dir, entries):
    """写入多条 JSONL 条目。"""
    jsonl = skill_dir / LEARNINGS_FILE
    with open(jsonl, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")


def _make_entry(key="k1", type_="pitfall", confidence=8, source="observed",
                ts=None, insight="test insight", tags=None):
    return {
        "ts": ts or datetime.now(timezone.utc).isoformat(),
        "agent": "test-skill",
        "type": type_,
        "key": key,
        "insight": insight,
        "confidence": confidence,
        "source": source,
        **({"tags": tags} if tags else {}),
    }


# ── _load_learnings ─────────────────────────────────────────────────


class TestLoadLearnings:
    def test_empty_dir(self, skill_dir):
        assert _load_learnings(skill_dir) == []

    def test_empty_file(self, skill_dir):
        (skill_dir / LEARNINGS_FILE).touch()
        assert _load_learnings(skill_dir) == []

    def test_load_entries(self, skill_dir):
        entries = [_make_entry(key="a"), _make_entry(key="b")]
        _write_entries(skill_dir, entries)
        loaded = _load_learnings(skill_dir)
        assert len(loaded) == 2
        assert loaded[0]["key"] == "a"
        assert loaded[1]["key"] == "b"

    def test_skip_malformed_lines(self, skill_dir, capsys):
        jsonl = skill_dir / LEARNINGS_FILE
        jsonl.write_text(
            json.dumps(_make_entry(key="good")) + "\n"
            + "this is not json\n"
            + json.dumps(_make_entry(key="also-good")) + "\n"
        )
        loaded = _load_learnings(skill_dir)
        assert len(loaded) == 2
        assert loaded[0]["key"] == "good"
        assert loaded[1]["key"] == "also-good"
        captured = capsys.readouterr()
        assert "第 2 行 JSON 解析失败" in captured.out

    def test_skip_blank_lines(self, skill_dir):
        jsonl = skill_dir / LEARNINGS_FILE
        jsonl.write_text(
            json.dumps(_make_entry(key="a")) + "\n"
            + "\n"
            + "   \n"
            + json.dumps(_make_entry(key="b")) + "\n"
        )
        assert len(_load_learnings(skill_dir)) == 2


# ── _dedup_learnings ────────────────────────────────────────────────


class TestDedupLearnings:
    def test_no_duplicates(self):
        entries = [_make_entry(key="a"), _make_entry(key="b")]
        assert len(_dedup_learnings(entries)) == 2

    def test_same_key_type_keeps_latest(self):
        old = _make_entry(key="x", ts="2026-01-01T00:00:00Z", insight="old")
        new = _make_entry(key="x", ts="2026-06-01T00:00:00Z", insight="new")
        result = _dedup_learnings([old, new])
        assert len(result) == 1
        assert result[0]["insight"] == "new"

    def test_same_key_different_type_kept(self):
        a = _make_entry(key="x", type_="pitfall")
        b = _make_entry(key="x", type_="pattern")
        assert len(_dedup_learnings([a, b])) == 2

    def test_empty_input(self):
        assert _dedup_learnings([]) == []


# ── _effective_confidence ───────────────────────────────────────────


class TestEffectiveConfidence:
    def test_no_decay_for_user_stated(self):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()
        entry = _make_entry(source="user-stated", confidence=8, ts=old_ts)
        assert _effective_confidence(entry) == 8.0

    def test_decay_for_observed(self):
        # 60 days ago → 2 decay intervals → confidence 8 - 2 = 6
        ts = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        entry = _make_entry(source="observed", confidence=8, ts=ts)
        assert _effective_confidence(entry) == 6.0

    def test_decay_for_inferred(self):
        ts = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
        entry = _make_entry(source="inferred", confidence=5, ts=ts)
        # 90 days → 3 intervals → 5 - 3 = 2
        assert _effective_confidence(entry) == 2.0

    def test_decay_floors_at_zero(self):
        ts = (datetime.now(timezone.utc) - timedelta(days=3650)).isoformat()
        entry = _make_entry(source="observed", confidence=3, ts=ts)
        assert _effective_confidence(entry) == 0.0

    def test_no_decay_within_30_days(self):
        ts = (datetime.now(timezone.utc) - timedelta(days=15)).isoformat()
        entry = _make_entry(source="observed", confidence=7, ts=ts)
        assert _effective_confidence(entry) == 7.0

    def test_missing_ts(self):
        entry = _make_entry(confidence=5)
        del entry["ts"]
        assert _effective_confidence(entry) == 5.0


# ── _filter_learnings ───────────────────────────────────────────────


class TestFilterLearnings:
    def _entries(self):
        return [
            _make_entry(key="a", type_="pitfall", confidence=9, tags=["api"]),
            _make_entry(key="b", type_="pattern", confidence=5, tags=["api", "format"]),
            _make_entry(key="c", type_="optimization", confidence=3),
        ]

    def test_no_filters(self):
        entries = self._entries()
        result = _filter_learnings(entries)
        assert len(result) == 3

    def test_filter_by_type(self):
        result = _filter_learnings(self._entries(), type_filter="pitfall")
        assert len(result) == 1
        assert result[0]["key"] == "a"

    def test_filter_by_query(self):
        entries = [
            _make_entry(key="a", insight="SearchLog requires epoch"),
            _make_entry(key="b", insight="Table output preferred"),
        ]
        result = _filter_learnings(entries, query="epoch")
        assert len(result) == 1
        assert result[0]["key"] == "a"

    def test_query_case_insensitive(self):
        entries = [_make_entry(key="a", insight="SearchLog API")]
        result = _filter_learnings(entries, query="searchlog")
        assert len(result) == 1

    def test_filter_by_tags_all_must_match(self):
        result = _filter_learnings(self._entries(), tags=["api", "format"])
        assert len(result) == 1
        assert result[0]["key"] == "b"

    def test_filter_by_min_confidence(self):
        result = _filter_learnings(self._entries(), min_conf=5.0)
        assert len(result) == 2  # a(9) and b(5), not c(3)

    def test_sorted_by_confidence_desc(self):
        result = _filter_learnings(self._entries())
        confs = [r["confidence"] for r in result]
        assert confs == sorted(confs, reverse=True)

    def test_empty_input(self):
        assert _filter_learnings([]) == []


# ── CLI 子命令（通过 subprocess 测试） ──────────────────────────────


class TestCLI:
    def _run(self, skill_dir, *args):
        """通过 subprocess 运行 learnings_tool.py。"""
        import subprocess
        cmd = [
            sys.executable,
            str(Path(__file__).parent.parent / "scripts" / "learnings_tool.py"),
            *args,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def test_log_and_count(self, skill_dir):
        r = self._run(skill_dir, "log", str(skill_dir),
                       "--type", "pitfall", "--key", "test-key",
                       "--insight", "test insight", "--confidence", "7",
                       "--source", "observed")
        assert r.returncode == 0
        assert "Logged learning" in r.stdout

        r = self._run(skill_dir, "count", str(skill_dir))
        assert r.returncode == 0
        assert "1 entries" in r.stdout
        assert "1 unique" in r.stdout

    def test_log_invalid_type(self, skill_dir):
        r = self._run(skill_dir, "log", str(skill_dir),
                       "--type", "invalid-type", "--key", "k",
                       "--insight", "i", "--confidence", "5",
                       "--source", "observed")
        assert r.returncode != 0

    def test_log_invalid_confidence(self, skill_dir):
        r = self._run(skill_dir, "log", str(skill_dir),
                       "--type", "pitfall", "--key", "k",
                       "--insight", "i", "--confidence", "99",
                       "--source", "observed")
        assert r.returncode == 1
        assert "1-10" in r.stdout

    def test_search_empty(self, skill_dir):
        r = self._run(skill_dir, "search", str(skill_dir))
        assert r.returncode == 0
        assert "无 learnings" in r.stdout

    def test_search_json(self, skill_dir):
        self._run(skill_dir, "log", str(skill_dir),
                  "--type", "pitfall", "--key", "k1",
                  "--insight", "insight1", "--confidence", "8",
                  "--source", "observed")
        r = self._run(skill_dir, "search", str(skill_dir), "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert len(data) == 1
        assert data[0]["key"] == "k1"
        assert "_effective_confidence" in data[0]

    def test_count_json(self, skill_dir):
        self._run(skill_dir, "log", str(skill_dir),
                  "--type", "pattern", "--key", "k1",
                  "--insight", "i1", "--confidence", "5",
                  "--source", "inferred")
        r = self._run(skill_dir, "count", str(skill_dir), "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["total_entries"] == 1
        assert data["unique_entries"] == 1
        assert data["by_type"]["pattern"] == 1

    def test_nonexistent_dir(self, skill_dir):
        r = self._run(skill_dir, "search", str(skill_dir / "no-such-dir"))
        assert r.returncode == 1
        assert "目录不存在" in r.stdout
