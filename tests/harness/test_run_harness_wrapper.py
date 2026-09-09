"""run_harness_task ラッパーの単体テスト（v4仕様・実LLM呼出なし・tmp_path完結）"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.run_harness_task import (  # noqa: E402
    load_history,
    mark_done,
    monthly_tokens,
    normalize,
    parse_pool,
    pick_topic,
    task_hash,
    watchdog_check,
)

POOL = """# harness 題庫

## 無人用（読む系）
- [ ] コード読解: サンプルAのお題本文です
- [ ] エラー診断: サンプルBのお題本文です
- [ ] 設定・docs生成: サンプルCのお題本文です
- [ ] コード読解: サンプルDのお題本文です

## 手動用（書く系）
- [ ] テスト作成: サンプルEのお題本文です
- [ ] docs修正: サンプルFのお題本文です
"""


def _pool(tmp_path: Path, content: str = POOL) -> Path:
    p = tmp_path / "harness_題庫.md"
    p.write_text(content)
    return p


def test_parse_pool_sections() -> None:
    topics = parse_pool(_pool(Path("/tmp")))["auto"]
    assert len(topics) == 4
    assert topics[0]["done"] is False
    assert topics[0]["category"] == "コード読解"


def test_pick_topic_category_balanced() -> None:
    topics = parse_pool(_pool(Path("/tmp")))["auto"]
    picked, how = pick_topic(topics, "test-seed", False)
    assert how == "category_balanced"
    # 全カテゴリ消化数0のうち最小→最初の未消化カテゴリ群から選ばれる
    assert picked is not None
    assert picked["done"] is False


def test_pick_topic_budget_mode_prefers_shortest() -> None:
    topics = parse_pool(_pool(Path("/tmp")))["auto"]
    picked, how = pick_topic(topics, "s", True)
    assert how == "budget_mode_shortest"
    assert "サンプルA" in picked["text"]  # 一番短い題文


def test_pick_topic_exhausted() -> None:
    topics = [{"done": True, "category": "X", "text": "t", "line_no": 1}]
    picked, how = pick_topic(topics, "s", False)
    assert picked is None and how == "pool_exhausted"


def test_normalize_and_hash_stable() -> None:
    assert normalize("Hello  World！ テスト") == normalize("hello world! テスト")
    assert task_hash("A B") == task_hash("a  b")


def test_watchdog_two_stage() -> None:
    def hist(uniq: int) -> list[dict]:
        return [{"task_hash": f"h{i}", "tokens_used": 1} for i in range(uniq)]

    few = hist(4)
    few += [{"task_hash": "h0", "tokens_used": 1} for _ in range(10)]
    assert watchdog_check(few).startswith("stop")
    medium = hist(6)
    medium += [{"task_hash": "h0", "tokens_used": 1} for _ in range(10)]
    assert watchdog_check(medium).startswith("warn")
    assert watchdog_check(hist(12)) == "ok"
    assert watchdog_check(hist(5)) == "ok"  # 10run未満は判定しない


def test_monthly_tokens_filters_by_month() -> None:
    h = [{"ts": "2026-09-01T00:00:00+00:00", "tokens_used": 100},
         {"ts": "2026-08-01T00:00:00+00:00", "tokens_used": 999}]
    assert monthly_tokens(h) == 100


def test_mark_done_atomic_update(tmp_path: Path) -> None:
    p = _pool(tmp_path)
    assert mark_done(p, 4) is True  # 4行目=無人用1行目
    assert "- [x] コード読解: サンプルA" in p.read_text()
    assert p.with_suffix(".md.lock").exists() or Path(str(p) + ".lock").exists()


def test_load_history_skips_blank() -> None:
    p = Path("/tmp") / "hist_test.jsonl"
    p.write_text('{"tokens_used": 5}\n\n{"tokens_used": 7}\n')
    h = load_history(p)
    assert len(h) == 2
    p.unlink()


# --- 網羅性点検で追加した回帰テスト（2026-09-09実装レビュー） ---

def test_watchdog_boundary_exact_5_and_8() -> None:
    """境界: uniq=5はstopでなくwarn（<5がstop）・uniq=8はok（<8がwarn）"""
    def hist(u: int) -> list[dict]:
        return [{"task_hash": f"h{i}", "tokens_used": 1} for i in range(u)] * 2
    assert watchdog_check(hist(5)).startswith("warn")
    assert watchdog_check(hist(8)) == "ok"


def test_load_history_skips_malformed_line() -> None:
    """破損行が1行あっても全run停止しない（クラッシュ経路・skip+警告）"""
    p = Path("/tmp") / "hist_bad.jsonl"
    p.write_text('{"tokens_used": 5}\n{broken json\n{"tokens_used": 7}\n')
    h = load_history(p)
    assert len(h) == 2
    p.unlink()


def test_mark_done_noop_on_already_done() -> None:
    """既に[x]の行を指定しても壊さない（no-op・True返却の挙動を固定）"""
    p = _pool(Path("/tmp"))
    mark_done(p, 4)
    before = p.read_text()
    assert mark_done(p, 4) is True
    assert p.read_text() == before


def test_mark_done_falls_back_to_text_search(tmp_path: Path) -> None:
    """line_noがズレていても題文照合で正しい行を[x]化（r2 Gemini#1/OR#2）"""
    p = _pool(tmp_path)
    lines = p.read_text().splitlines()
    lines.insert(4, "")  # 行を1つ挿入してline_noを1行ズラす
    p.write_text("\n".join(lines) + "\n")
    assert mark_done(p, 4, "サンプルBのお題本文") is True
    out = p.read_text()
    assert "- [x] エラー診断" in out  # 題文照合で正しい行が当たる
    assert "- [ ] コード読解: サンプルA" in out  # ズレた行は触られていない


def test_mark_done_skip_when_topic_missing(tmp_path: Path) -> None:
    """題文が題庫に存在しない場合はFalse（誤[x]化しない）"""
    p = _pool(tmp_path)
    assert mark_done(p, 4, "存在しないお題") is False


def test_acquire_wrapper_lock_blocks_second(tmp_path: Path) -> None:
    """二重起動: 1つ目が保持中なら2つ目はFalse（MiniMax r3-critical）"""
    sys.path.insert(0, "/home/yn4416/projects/NexusCore/scripts")
    from scripts.run_harness_task import acquire_wrapper_lock
    repo = tmp_path
    assert acquire_wrapper_lock(repo) is True
    assert acquire_wrapper_lock(repo) is False  # 同プロセス内2回目は競合


# --- Phase B: stamp/heartbeat/selfcheck（cron-setup規定路線） ---

def test_daily_stamp_skip_and_force(tmp_path: Path) -> None:
    """当日スタンプ: 同日ならskip(False)・forceなら再実行可"""
    from scripts.run_harness_task import check_daily_stamp, stamp_path, write_stamp
    repo = tmp_path
    assert check_daily_stamp(repo, force=False) is True  # 初回=実行可
    write_stamp(repo)
    assert check_daily_stamp(repo, force=False) is False  # 同日=skip
    assert check_daily_stamp(repo, force=True) is True  # force=再実行可
    assert stamp_path(repo).read_text().strip()  # 日付が書かれている


def test_heartbeat_touches_file(tmp_path: Path) -> None:
    from scripts.run_harness_task import heartbeat
    heartbeat(tmp_path)
    assert (tmp_path / "artifacts/harness/heartbeat").exists()


def test_selfcheck_ng_on_missing_venv(tmp_path: Path) -> None:
    """selfcheck: venv不在でNG理由を返す（exit 78の根拠）"""
    from scripts.run_harness_task import selfcheck
    ng = selfcheck(tmp_path)
    assert ng is not None and "venv" in ng


def test_notify_failure_dead_letter_without_webhook(tmp_path: Path) -> None:
    """webhook未設定時も.notify.failへ退避（デッドレター対策・r1 MiniMax#3）"""
    import os

    from scripts.run_harness_task import notify_failure
    old = os.environ.pop("DISCORD_CLAUDE_WEBHOOK", None)
    try:
        notify_failure(tmp_path, "test message")
        assert (tmp_path / "artifacts/harness/.notify.fail").exists()
        assert "test message" in (tmp_path / "artifacts/harness/.notify.fail").read_text()
    finally:
        if old is not None:
            os.environ["DISCORD_CLAUDE_WEBHOOK"] = old
