"""
GitHub PR 修正要約生成モジュール

Run に紐づくパッチとログを元に、「何を直したか／なぜ壊れていたか／リスク」を自然言語で要約する。
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Webapp モデルはオプショナルインポート
try:
    from nexuscore.webapp import db
    from nexuscore.webapp.models import ExecutionLog, PatchRecord, Run

    HAS_WEBAPP = True
except ImportError:
    HAS_WEBAPP = False
    Run = None
    PatchRecord = None
    ExecutionLog = None
    db = None

# LLM 呼び出し用
try:
    from nexuscore.llm.llm_router import LLMRouter
    from nexuscore.npe.engine import guarded_llm_call

    HAS_LLM = True
except ImportError:
    HAS_LLM = False
    guarded_llm_call = None
    LLMRouter = None


def generate_pr_change_summary(
    run: object,
    guardian_review_markdown: str,
    max_tokens: int = 512,
    llm_router: object | None = None,
) -> str | None:
    """
    Run に紐づくパッチとログを元に、「何を直したか／なぜ壊れていたか／リスク」を自然言語で要約する。

    Args:
        run: Run モデル
        guardian_review_markdown: Guardian レビューの Markdown 本文
        max_tokens: 最大トークン数
        llm_router: LLMRouter インスタンス（省略時は新規作成）

    Returns:
        要約テキスト（失敗時は None）
    """
    if not HAS_WEBAPP or not HAS_LLM:
        logger.warning("Webapp or LLM modules not available. Skipping summary generation.")
        return None

    try:
        # パッチ情報を収集
        patches = []
        if hasattr(run, "id") and PatchRecord:
            patches = PatchRecord.query.filter_by(run_id=run.id).all()

        diff_snippets = []
        for p in patches[:10]:  # 最大10ファイル
            file_path = p.file_path if hasattr(p, "file_path") else "unknown"
            diff_text = p.diff_text if hasattr(p, "diff_text") else ""

            # 1ファイルあたり80行まで
            lines = diff_text.splitlines()[:80] if diff_text else []
            if lines:
                diff_snippets.append(f"File: {file_path}\n" + "\n".join(lines))

        diff_block = "\n\n".join(diff_snippets) if diff_snippets else "(no diff available)"

        # ログ情報を収集（ERROR/WARNING のみ）
        log_entries = []
        if hasattr(run, "id") and ExecutionLog:
            log_entries = (
                ExecutionLog.query.filter(ExecutionLog.run_id == run.id)
                .order_by(ExecutionLog.created_at.asc())
                .all()
            )

        log_text_lines: list[str] = []
        for lg in log_entries[:100]:  # 最大100エントリ
            source = lg.source if hasattr(lg, "source") else "unknown"
            level = lg.level if hasattr(lg, "level") else "INFO"
            message = lg.message if hasattr(lg, "message") else ""

            if level in ("ERROR", "WARNING"):
                log_text_lines.append(f"[{source}][{level}] {message}")

        log_text = "\n".join(log_text_lines) if log_text_lines else "(no important logs)"

        # プロンプトを構築
        prompt = f"""
You are an AI code review assistant.

The following codebase was automatically self-healed by an AI orchestrator.
We have:

- Guardian review comments (high level)
- Patch diffs
- Structured logs (errors/warnings)

Please summarize the essence of the change for a pull request comment, in concise bullet points.

Focus on:

1. What was broken or risky before.
2. What was changed (at a high level; avoid too much detail).
3. Why this change reduces risk or improves quality.
4. Any remaining risks or recommendations.

Guardian review:

{guardian_review_markdown[:2000]}

Patch diff snippets:

{diff_block[:3000]}

Important logs:

{log_text[:2000]}

Write the summary in Japanese, 5 bullets or fewer.
"""

        # LLM を呼び出す
        if llm_router is None:
            if LLMRouter is None:
                logger.warning("LLMRouter not available. Skipping summary generation.")
                return None
            llm_router = LLMRouter()

        # guarded_llm_call 経由で LLM を呼び出す
        if guarded_llm_call is None:
            logger.warning("guarded_llm_call not available. Skipping summary generation.")
            return None

        # LLMRouter の complete メソッドをラップ
        def llm_complete_fn(model: str, system_prompt: str, user_prompt: str) -> dict:
            if hasattr(llm_router, "complete"):
                return llm_router.complete(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    task="code_review",
                )
            else:
                return {"ok": False, "reason": "LLMRouter.complete not available", "content": ""}

        result = guarded_llm_call(
            model="gpt-5.1-mini",  # 軽量モデルを使用
            task="code_review",
            system_prompt="You summarize code changes for pull requests. Return concise bullet points in Japanese.",
            user_prompt=prompt,
            llm_complete_fn=llm_complete_fn,
        )

        if isinstance(result, dict) and result.get("ok"):
            summary_text = result.get("content", "").strip()
            return summary_text if summary_text else None
        else:
            logger.warning(f"LLM call failed: {result.get('reason', 'unknown')}")
            return None

    except Exception as e:
        logger.error(f"Failed to generate PR change summary: {e}", exc_info=True)
        return None
