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


class TestUpdateBaselineRejectsMissingSkill:
    """W45💡1: --skill に実在しないパスで --update-baseline を渡すと
    baseline書込前に reject する（空hash書込の事故防止・同型3回実証済み）。

    fail条件（事前固定）: 実在しない --skill + --update-baseline で baseline
    ファイルが作成された時＝reject 不成立。
    """

    def test_update_baseline_with_missing_skill_rejects(self, tmp_path, capsys):
        from nexuscore.scripts.check_skill_drift import main

        baseline_path = tmp_path / "baseline.sha256"
        rc = main(
            ["--skill", str(tmp_path / "nope.md"),
             "--baseline", str(baseline_path),
             "--update-baseline"]
        )
        assert rc == 2
        assert "reject" in capsys.readouterr().err
        assert not baseline_path.exists()  # baseline 未書込＝fail条件の核

    def test_update_baseline_with_existing_skill_writes(self, tmp_path):
        from nexuscore.scripts.check_skill_drift import main

        skill = tmp_path / "SKILL.md"
        skill.write_text("content", encoding="utf-8")
        baseline_path = tmp_path / "baseline.sha256"
        rc = main(
            ["--skill", str(skill),
             "--baseline", str(baseline_path),
             "--update-baseline"]
        )
        assert rc == 0
        assert baseline_path.exists()

    def test_missing_skill_without_update_still_reports_missing(self, tmp_path, capsys):
        """update 無しの drift チェックは既存どおり missing 報告（exit 0）。"""
        from nexuscore.scripts.check_skill_drift import main

        rc = main(
            ["--skill", str(tmp_path / "nope.md"),
             "--baseline", str(tmp_path / "b.sha256")]
        )
        assert rc == 0
        assert '"missing"' in capsys.readouterr().out
