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
    picked, how = pick_topic(topics, [], "test-seed", False)
    assert how == "category_balanced"
    # 全カテゴリ消化数0のうち最小→最初の未消化カテゴリ群から選ばれる
    assert picked is not None
    assert picked["done"] is False


def test_pick_topic_budget_mode_prefers_shortest() -> None:
    topics = parse_pool(_pool(Path("/tmp")))["auto"]
    picked, how = pick_topic(topics, [], "s", True)
    assert how == "budget_mode_shortest"
    assert "サンプルA" in picked["text"]  # 一番短い題文


def test_pick_topic_exhausted() -> None:
    topics = [{"done": True, "category": "X", "text": "t", "line_no": 1}]
    picked, how = pick_topic(topics, [], "s", False)
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
