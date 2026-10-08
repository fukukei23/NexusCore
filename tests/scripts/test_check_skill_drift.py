"""check_skill_drift.py（L141=A・乖離検知のみ）のテスト。

SKILL.md（CLI版で運用で育つ正典）と NexusCore 組込み版の乖離を検知するだけの
チェッカー。同期はしない。baseline hash（取込時点の記録）と現行 SKILL.md の
hash 突合で ok / drift / missing を返す。
失敗条件（fail条件・バックログL141）: SKILL.md を1行変更して検知（drift 判定）
が変わらなければ不成立 — 1行変更 → drift を単体テストで担保。
"""

import hashlib

from nexuscore.scripts.check_skill_drift import (
    compute_sha256,
    detect_drift,
    load_baseline,
    write_baseline,
)


def _write(path, content: str) -> str:
    path.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class TestDetectDrift:
    def test_same_hash_is_ok(self, tmp_path):
        p = tmp_path / "SKILL.md"
        h = _write(p, "content")
        assert detect_drift(h, h) == "ok"

    def test_one_line_change_is_detected_as_drift(self, tmp_path):
        """fail条件: 1行変更で drift 判定が変わること"""
        p = tmp_path / "SKILL.md"
        h1 = _write(p, "content v1\n")
        h2 = _write(p, "content v2\n")  # 1行変更
        assert h1 != h2
        assert detect_drift(h1, h2) == "drift"

    def test_missing_baseline_is_missing(self, tmp_path):
        assert detect_drift(None, "abc") == "missing"

    def test_missing_skill_is_missing(self, tmp_path):
        assert detect_drift("abc", None) == "missing"


class TestBaselineIO:
    def test_write_and_load_baseline(self, tmp_path):
        p = tmp_path / "baseline.sha256"
        write_baseline(str(p), "deadbeef", note="adoption")
        data = load_baseline(str(p))
        assert data["sha256"] == "deadbeef"
        assert data["note"] == "adoption"

    def test_load_baseline_missing_returns_none(self, tmp_path):
        assert load_baseline(str(tmp_path / "nope.sha256")) is None


class TestComputeSha256:
    def test_compute_sha256_matches_hashlib(self, tmp_path):
        p = tmp_path / "f.md"
        expected = _write(p, "hello")
        assert compute_sha256(str(p)) == expected
