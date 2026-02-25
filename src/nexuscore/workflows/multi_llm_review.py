# ==============================================================================
# ファイル: src/nexuscore/workflows/multi_llm_review.py
# 目的  : マルチLLM相互添削（並列→統合→自信度→追加検証/打切り）
# 仕様  : --models で与えたモデルを「厳密に」使用（ルーターの自動選択は使わない）
# 実行例:
#   python -m src.nexuscore.workflows.multi_llm_review --task "pytest失敗の共通原因レビュー" \
#     --models "gemini-1.5-flash-latest,claude-3-sonnet,gpt-4o,deepseek-r1" \
#     --threshold 0.9 --max_extra 1 --tokens 400
# ==============================================================================

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any

# 既存基盤
from ..agents.base_agent import BaseAgent
from ..llm.llm_router import LLMRouter  # 直接クライアントを生成するために使用

# 任意（未導入でも動作可）
try:
    from tools.prompt_batcher import build_batch_prompt
except Exception:

    def build_batch_prompt(task_title, code_snippets, **_):
        blocks = []
        for i, it in enumerate(code_snippets or [], 1):
            blocks.append(
                f"[{i}] {it.get('path','')}\n{it.get('content','')}\n{it.get('error','')}"
            )
        return f"# {task_title}\n" + "\n---\n".join(blocks)


# ---------------------------- 設定 ---------------------------- #
DEFAULT_CONFIDENCE_THRESHOLD = float(os.getenv("NEXUS_CONFIDENCE_SKIP_THRESHOLD", "0.90"))
DEFAULT_MAX_EXTRA_VALIDATIONS = int(os.getenv("NEXUS_MAX_EXTRA_VALIDATIONS", "1"))
DEFAULT_MAX_OUTPUT_TOKENS = int(os.getenv("NEXUS_DEFAULT_MAX_OUT_TOKENS", "512"))  # 短め推奨
DEFAULT_TEMP = float(os.getenv("NEXUS_ROUTER_TEMPERATURE", "0.2"))
COST_CAP = float(os.getenv("NEXUS_REVIEW_COST_CAP_USD", "0.02"))  # ここは使わず、明示モデル優先


# ---------------------------- データ構造 ---------------------------- #
@dataclass
class ReviewItem:
    path: str
    content: str
    error: str = ""


@dataclass
class ModelReview:
    model: str
    summary: dict[str, Any]  # {"issues":[...],"severity":"low|medium|high","confidence":0.0-1.0}
    raw: str = ""
    ok: bool = True
    error: str = ""


@dataclass
class ConsensusResult:
    issues: list[str] = field(default_factory=list)
    file_fixes: dict[str, str] = field(default_factory=dict)
    confidence: float = 0.0
    contributing_models: list[str] = field(default_factory=list)


# ---------------------------- プロンプト ---------------------------- #
SUMMARY_SYSTEM = (
    "You are a concise, rigorous code reviewer.\n"
    "Return ONLY JSON with schema:\n"
    "{"
    '"issues":[{"title":string,"evidence":string}],'
    '"severity":"low|medium|high",'
    '"confidence": 0.0-1.0'
    "}\n"
    "No preface. No code fences. Keep output minimal."
)


def make_summary_prompt(task: str, batch_text: str) -> str:
    return (
        f"【レビュー要件】\n{task}\n\n"
        f"【対象】\n{batch_text}\n\n"
        "出力条件:\n"
        "- 300文字以内で要点のみ（issues は最大3件）\n"
        "- JSONスキーマ厳守\n"
    )


# ---------------------------- ロジック ---------------------------- #
class ReviewAgent(BaseAgent):
    SYSTEM_PROMPT = SUMMARY_SYSTEM


def _make_client_forced(model_name: str):
    """
    ルーターのモデル自動選択をバイパスし、明示モデルのクライアントを生成。
    （内部メソッド _make_client を使用）
    """
    r = LLMRouter()
    # 明示モデルが不明でもルーターが最終的に LocalLLM にフォールバック
    return r._make_client(model_name)  # 公開APIが無いので内部を利用


async def _run_one_model(
    model_name: str,
    prompt: str,
    max_tokens: int,
) -> ModelReview:
    agent = ReviewAgent()
    try:
        client = _make_client_forced(model_name)
        # BaseAgent 経由の execute_llm_task を使わず、直接クライアントを叩く
        out = client.execute(
            prompt=prompt,
            system_prompt=agent.SYSTEM_PROMPT,
            as_json=True,
            temperature=DEFAULT_TEMP,
            max_output_tokens=max_tokens,
        )
        try:
            data = json.loads(out or "{}")
        except Exception:
            data = {}
        summary = {
            "issues": data.get("issues", []),
            "severity": data.get("severity", "low"),
            "confidence": float(data.get("confidence", 0.0)),
        }
        return ModelReview(model=model_name, summary=summary, raw=out, ok=True)
    except Exception as e:
        # 認証エラーや429などはここに来る。低自信度で継続させる。
        return ModelReview(
            model=model_name,
            summary={"issues": [], "severity": "low", "confidence": 0.0},
            raw="",
            ok=False,
            error=str(e),
        )


def _merge_consensus(reviews: list[ModelReview]) -> ConsensusResult:
    seen = set()
    merged: list[str] = []
    for r in reviews:
        for it in r.summary.get("issues", []):
            title = (it.get("title") or "").strip()
            if title and title not in seen:
                seen.add(title)
                merged.append(title)
    confs = [r.summary.get("confidence", 0.0) for r in reviews if isinstance(r.summary, dict)]
    conf = sum(confs) / len(confs) if confs else 0.0
    return ConsensusResult(
        issues=merged[:5],
        file_fixes={},
        confidence=conf,
        contributing_models=[f"{r.model}{'' if r.ok else ' (fail)'}" for r in reviews],
    )


async def run_consensus_review(
    task: str,
    items: list[ReviewItem],
    models: list[str],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    max_extra_validations: int = DEFAULT_MAX_EXTRA_VALIDATIONS,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> ConsensusResult:
    batch_text = build_batch_prompt(
        task_title=task,
        code_snippets=[{"path": it.path, "content": it.content, "error": it.error} for it in items],
        max_items=10,
        ask_style="consensus_ready",  # 後段統合に最適化
    )
    prompt = make_summary_prompt(task, batch_text)

    # 1st 波：先頭2件を並列（軽量を先に並べること）
    first_wave = models[:2] if len(models) >= 2 else models
    second_wave = models[2:] if len(models) > 2 else []

    results: list[ModelReview] = []
    first_tasks = [
        asyncio.create_task(_run_one_model(m, prompt, max_output_tokens)) for m in first_wave
    ]
    first_done = await asyncio.gather(*first_tasks)
    results.extend(first_done)

    consensus = _merge_consensus(results)
    if consensus.confidence >= confidence_threshold:
        return consensus

    # 2nd 波：必要時のみ、順次追加（max_extra_validations で打切り）
    extra_budget = max_extra_validations
    for m in second_wave:
        if extra_budget <= 0:
            break
        res = await _run_one_model(m, prompt, max_output_tokens)
        results.append(res)
        consensus = _merge_consensus(results)
        extra_budget -= 1
        if consensus.confidence >= confidence_threshold:
            break

    return consensus


# ---------------------------- CLI ---------------------------- #
def _parse_models(s: str) -> list[str]:
    return [x.strip() for x in s.split(",") if x.strip()]


def main():
    logging.basicConfig(level=logging.INFO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True, help="レビュー要件文（簡潔に）")
    ap.add_argument("--models", required=True, help="使用モデルのカンマ区切り（軽量→高精度の順）")
    ap.add_argument("--threshold", type=float, default=DEFAULT_CONFIDENCE_THRESHOLD)
    ap.add_argument("--max_extra", type=int, default=DEFAULT_MAX_EXTRA_VALIDATIONS)
    ap.add_argument("--tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    ap.add_argument("--inputs_json", help="レビュー対象のJSON（[{path,content,error}]）")
    args = ap.parse_args()

    items = [
        ReviewItem(path="src/app.py", content="def add(a,b):\n    return a+b", error=""),
        ReviewItem(path="tests/test_app.py", content="assert add(2,2)==5", error="AssertionError"),
    ]
    if args.inputs_json and os.path.exists(args.inputs_json):
        with open(args.inputs_json, encoding="utf-8") as f:
            raw = json.load(f)
        items = [ReviewItem(**x) for x in raw]

    models = _parse_models(args.models)

    loop = asyncio.get_event_loop()
    result: ConsensusResult = loop.run_until_complete(
        run_consensus_review(
            task=args.task,
            items=items,
            models=models,
            confidence_threshold=args.threshold,
            max_extra_validations=args.max_extra,
            max_output_tokens=args.tokens,
        )
    )
    print(
        json.dumps(
            {
                "issues": result.issues,
                "confidence": round(result.confidence, 3),
                "models": result.contributing_models,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
