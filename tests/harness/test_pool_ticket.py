"""pool枯渇恒久改善（D案′・2026-11-01）の単体テスト

設計正典: obsidian-ssot 60_MLR_LOGS/2026-11-01_harness枯渇STOP恒久改善D案レビュー/revised_proposal.md
- 連続STOPカウンタ（エピソード単位）・3晩連続でバックログ自動起票（冪等）
- 予防線（pool_low時のP2起票）・成功runでリセット+補充日記録
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts import run_harness_task as w  # noqa: E402


def _git_obsidian(tmp_path: Path) -> Path:
    """起票先のモックobsidian-ssot（git init済・バックログ.mdあり）"""
    repo = tmp_path / "obsidian-ssot"
    (repo / "00_SYSTEM").mkdir(parents=True)
    (repo / "00_SYSTEM/バックログ.md").write_text(
        "# バックログ\n\n- [ ]（P2・既存タスク）**別タスク** — 既存行\n")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def _pool_exhausted(tmp_path: Path) -> None:
    (tmp_path / ".venv/bin").mkdir(parents=True)
    (tmp_path / ".venv/bin/python").write_text("")
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs/harness_題庫.md").write_text(
        "# 題庫\n\n## 無人用（読む系）\n- [x] A: x\n")


# --- 連続STOPカウンタ（エピソード単位） ---

def test_bump_stop_count_increments(tmp_path: Path) -> None:
    assert w.read_stop_count(tmp_path) == 0  # 不在=0
    c1, ep1 = w.bump_stop_count(tmp_path)
    c2, ep2 = w.bump_stop_count(tmp_path)
    assert c1 == 1 and c2 == 2
    assert ep1 == ep2  # 同一エピソード（連続STOP開始日を維持）


def test_read_stop_count_tolerates_corrupt_file(tmp_path: Path) -> None:
    f = tmp_path / "artifacts/harness/pool_stop_count.txt"
    f.parent.mkdir(parents=True)
    f.write_text("not-a-number")
    assert w.read_stop_count(tmp_path) == 0


def test_record_success_reset_closes_streak_and_records_replenish(
        tmp_path: Path) -> None:
    w.bump_stop_count(tmp_path)
    w.bump_stop_count(tmp_path)
    closed = w.record_success_reset(tmp_path)
    assert closed is True
    assert w.read_stop_count(tmp_path) == 0
    f = tmp_path / "artifacts/harness/pool_last_replenish.txt"
    assert f.exists() and re.match(r"\d{4}-\d{2}-\d{2}", f.read_text().strip())
    assert w.ticket_flag_episode(tmp_path) is None  # フラグも消える


def test_record_success_reset_returns_false_when_no_streak(
        tmp_path: Path) -> None:
    assert w.record_success_reset(tmp_path) is False
    assert not (tmp_path / "artifacts/harness/pool_last_replenish.txt").exists()


# --- バックログ自動起票（冪等・repo identity確認） ---

def test_ensure_ticket_creates_p1_row(tmp_path: Path) -> None:
    backlog = _git_obsidian(tmp_path) / "00_SYSTEM/バックログ.md"
    result = w.ensure_backlog_ticket(tmp_path, 3, backlog_path=backlog)
    assert result == "created"
    body = backlog.read_text()
    assert "- [ ]（P1・[AUTO-HARNESS-POOL]" in body
    assert "harness題庫補充が必要" in body
    assert "3晩連続STOP" in body


def test_ensure_ticket_is_idempotent_when_open_row_exists(
        tmp_path: Path) -> None:
    backlog = _git_obsidian(tmp_path) / "00_SYSTEM/バックログ.md"
    assert w.ensure_backlog_ticket(tmp_path, 3, backlog_path=backlog) == "created"
    before = backlog.read_text()
    assert w.ensure_backlog_ticket(tmp_path, 5, backlog_path=backlog) == "exists"
    assert backlog.read_text() == before  # 重複行を作らない


def test_ensure_ticket_done_row_does_not_block(tmp_path: Path) -> None:
    """完了[x]行は冪等判定の邪魔をしない（前エピソードの完了行が残っていても起票可）"""
    backlog = _git_obsidian(tmp_path) / "00_SYSTEM/バックログ.md"
    backlog.write_text(
        "# バックログ\n\n- [x]（P1・[AUTO-HARNESS-POOL]・2026-10-06起票）"
        "harness題庫補充が必要（前回分）— 完了\n")
    assert w.ensure_backlog_ticket(tmp_path, 3, backlog_path=backlog) == "created"
    assert backlog.read_text().count("harness題庫補充が必要") == 2


def test_ensure_ticket_fails_on_foreign_repo_identity(tmp_path: Path) -> None:
    """repo identity不一致（obsidian-ssotでないgit repo）→起票しない"""
    other = tmp_path / "not-obsidian"
    (other / "00_SYSTEM").mkdir(parents=True)
    backlog = other / "00_SYSTEM/バックログ.md"
    backlog.write_text("# バックログ\n")
    subprocess.run(["git", "init", "-q", str(other)], check=True)
    assert w.ensure_backlog_ticket(tmp_path, 3, backlog_path=backlog) == "failed"
    assert "harness題庫補充が必要" not in backlog.read_text()


def test_ensure_ticket_fails_when_backlog_missing(tmp_path: Path) -> None:
    backlog = tmp_path / "nope/00_SYSTEM/バックログ.md"
    assert w.ensure_backlog_ticket(tmp_path, 3, backlog_path=backlog) == "failed"


# --- 予防線（pool_low時のP2起票） ---

def test_prep_ticket_creates_p2_row_and_p1_closes_it(tmp_path: Path) -> None:
    backlog = _git_obsidian(tmp_path) / "00_SYSTEM/バックログ.md"
    assert w.ensure_prep_ticket(tmp_path, 2, backlog_path=backlog) == "created"
    body = backlog.read_text()
    assert "- [ ]（P2・[AUTO-HARNESS-POOL]" in body
    assert "harness題庫補充準備" in body
    # P1起票時にP2行が自動クローズ（P1起票に統合）
    assert w.ensure_backlog_ticket(tmp_path, 3, backlog_path=backlog) == "created"
    body2 = backlog.read_text()
    assert "- [x]（P2・[AUTO-HARNESS-POOL]" in body2
    assert body2.count("harness題庫補充が必要") == 1


def test_prep_ticket_is_idempotent(tmp_path: Path) -> None:
    backlog = _git_obsidian(tmp_path) / "00_SYSTEM/バックログ.md"
    assert w.ensure_prep_ticket(tmp_path, 3, backlog_path=backlog) == "created"
    before = backlog.read_text()
    assert w.ensure_prep_ticket(tmp_path, 2, backlog_path=backlog) == "exists"
    assert backlog.read_text() == before


# --- main()統合: STOP経路・成功リセット経路 ---

def test_main_stop_includes_streak_and_ticket_in_notify(
        tmp_path: Path, monkeypatch) -> None:
    """3晩目: 通知に「3晩連続」と「バックログ起票済み」を含みP1行が実在する"""
    _pool_exhausted(tmp_path)
    w.bump_stop_count(tmp_path)
    w.bump_stop_count(tmp_path)  # 2晩目まで済み
    backlog = _git_obsidian(tmp_path) / "00_SYSTEM/バックログ.md"
    monkeypatch.setattr(w, "OBSIDIAN_BACKLOG", backlog)

    calls: list[str] = []
    monkeypatch.setattr(w, "notify_failure", lambda r, m: calls.append(m))
    old_argv = sys.argv
    sys.argv = ["run_harness_task.py", "--repo", str(tmp_path)]
    try:
        assert w.main() == 4
    finally:
        sys.argv = old_argv
    assert "3晩連続" in calls[0]
    assert "バックログ起票済み" in calls[0]
    assert "harness題庫補充が必要" in backlog.read_text()
    assert w.ticket_flag_episode(tmp_path) is not None  # 起票フラグ=エピソードID


def test_main_first_stop_no_ticket_yet(tmp_path: Path, monkeypatch) -> None:
    """1晩目: 起票はまだ・通知に「1晩連続」のみ"""
    _pool_exhausted(tmp_path)
    backlog = _git_obsidian(tmp_path) / "00_SYSTEM/バックログ.md"
    monkeypatch.setattr(w, "OBSIDIAN_BACKLOG", backlog)
    calls: list[str] = []
    monkeypatch.setattr(w, "notify_failure", lambda r, m: calls.append(m))
    old_argv = sys.argv
    sys.argv = ["run_harness_task.py", "--repo", str(tmp_path)]
    try:
        assert w.main() == 4
    finally:
        sys.argv = old_argv
    assert "1晩連続" in calls[0]
    assert "バックログ起票済み" not in calls[0]
    assert "harness題庫補充が必要" not in backlog.read_text()


def test_main_success_run_resets_streak(tmp_path: Path, monkeypatch) -> None:
    """正常runでストリークが閉じ補充日が記録される"""
    import json as _json
    (tmp_path / ".venv/bin").mkdir(parents=True)
    (tmp_path / ".venv/bin/python").write_text("")
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs/harness_題庫.md").write_text(
        "# 題庫\n\n## 無人用（読む系）\n- [ ] A: 正常お題\n")
    hdir = tmp_path / "artifacts/harness"
    hdir.mkdir(parents=True)
    w.bump_stop_count(tmp_path)
    w.bump_stop_count(tmp_path)

    def fake_run(repo, task, state_path, timeout, ask=False):
        return 0, _json.dumps({"abort_reason": None, "tokens_used": 10}), ""

    monkeypatch.setattr(w, "run_harness", fake_run)
    old_argv = sys.argv
    sys.argv = ["run_harness_task.py", "--repo", str(tmp_path)]
    try:
        assert w.main() == 0
    finally:
        sys.argv = old_argv
    assert w.read_stop_count(tmp_path) == 0
    assert (hdir / "pool_last_replenish.txt").exists()


def test_main_dry_run_does_not_bump_or_ticket(tmp_path: Path, monkeypatch) -> None:
    """dry-runは状態を一切変えない（カウンタ・起票とも）"""
    _pool_exhausted(tmp_path)
    backlog = _git_obsidian(tmp_path) / "00_SYSTEM/バックログ.md"
    monkeypatch.setattr(w, "OBSIDIAN_BACKLOG", backlog)
    monkeypatch.setattr(w, "notify_failure", lambda r, m: None)
    old_argv = sys.argv
    sys.argv = ["run_harness_task.py", "--repo", str(tmp_path), "--dry-run"]
    try:
        assert w.main() == 4
    finally:
        sys.argv = old_argv
    assert w.read_stop_count(tmp_path) == 0
    assert "harness題庫補充が必要" not in backlog.read_text()


def test_main_pool_low_creates_prep_ticket(tmp_path: Path, monkeypatch) -> None:
    """残≤POOL_LOW_WARNで予防起票（P2）が走る（dry-run以外）"""
    import json as _json
    (tmp_path / ".venv/bin").mkdir(parents=True)
    (tmp_path / ".venv/bin/python").write_text("")
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "docs/harness_題庫.md").write_text(
        "# 題庫\n\n## 無人用（読む系）\n- [ ] A: x\n- [ ] B: y\n")
    (tmp_path / "artifacts/harness").mkdir(parents=True)
    backlog = _git_obsidian(tmp_path) / "00_SYSTEM/バックログ.md"
    monkeypatch.setattr(w, "OBSIDIAN_BACKLOG", backlog)

    def fake_run(repo, task, state_path, timeout, ask=False):
        return 0, _json.dumps({"abort_reason": None, "tokens_used": 10}), ""

    monkeypatch.setattr(w, "run_harness", fake_run)
    old_argv = sys.argv
    sys.argv = ["run_harness_task.py", "--repo", str(tmp_path)]
    try:
        assert w.main() == 0
    finally:
        sys.argv = old_argv
    assert "harness題庫補充準備" in backlog.read_text()
