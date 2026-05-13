from __future__ import annotations

from typing import Any


def generate_diff_summary(
    execute_llm_fn: Any,
    before_code: str | None = None,
    after_code: str | None = None,
    file_diffs: dict[str, dict[str, str]] | None = None,
    semantic_diffs: dict[str, dict[str, Any]] | None = None,
    model: str = "gpt-4.1",
    logger: Any = None,
) -> str | dict[str, str]:
    """
    パッチ適用前後のコードを LLM に渡し、改善点を要約する。

    Args:
        execute_llm_fn: LLM呼び出し用callable (prompt, as_json) -> str
        before_code: 変更前のコード（単一ファイル用）
        after_code: 変更後のコード（単一ファイル用）
        file_diffs: 複数ファイルの差分
        semantic_diffs: 意味的差分情報
        model: 使用する LLM モデル
        logger: ロガー

    Returns:
        単一ファイル: 5行以内の改善点要約（Markdown）
        複数ファイル: {"a.py": "要約...", ...} の辞書
    """
    if file_diffs:
        return _generate_multi_file_diff_summary(
            execute_llm_fn, file_diffs, semantic_diffs, model, logger=logger,
        )

    if before_code is None or after_code is None:
        return "差分サマリーの生成に失敗しました: before_code または after_code が指定されていません"

    prompt = f"""
以下のコード変更をレビューし、改善点を5行以内で要約してください。

## 変更前のコード
```python
{before_code}
```

## 変更後のコード
```python
{after_code}
```

## 出力要件
- 改善点を5行以内で要約してください
- 各項目は箇条書き（- で始まる）で記述してください
- 技術的な改善点（簡潔化、複雑度低減、バグ修正など）を明確に示してください
- Markdown 形式で出力してください

出力例:
- XXX が簡潔化され、可読性が向上
- 複雑度が低減され、保守性が改善
- エラーハンドリングが追加され、堅牢性が向上
"""

    try:
        summary = execute_llm_fn(prompt, as_json=False)

        lines = summary.strip().split("\n")
        if len(lines) > 5:
            summary = "\n".join(lines[:5])
            summary += "\n_(要約が長いため、最初の5行のみ表示)_"

        return summary.strip()

    except Exception as e:
        if logger:
            logger.error(f"Failed to generate diff summary: {e}", exc_info=True)
        return f"差分サマリーの生成に失敗しました: {e}"


def _generate_multi_file_diff_summary(
    execute_llm_fn: Any,
    file_diffs: dict[str, dict[str, str]],
    semantic_diffs: dict[str, dict[str, Any]] | None = None,
    model: str = "gpt-4.1",
    logger: Any = None,
) -> dict[str, str]:
    """
    複数ファイルの差分サマリーを生成する。

    Args:
        execute_llm_fn: LLM呼び出し用callable
        file_diffs: ファイル名→{"before": "...", "after": "..."} の辞書
        semantic_diffs: 意味的差分情報
        model: 使用する LLM モデル
        logger: ロガー

    Returns:
        {"a.py": "要約...", ...} の辞書
    """
    result: dict[str, str] = {}

    for file_path, diff_pair in file_diffs.items():
        before_code = diff_pair.get("before", "")
        after_code = diff_pair.get("after", "")

        if not before_code or not after_code:
            result[file_path] = "差分サマリーの生成に失敗しました: before/after が空です"
            continue

        try:
            semantic_info = None
            if semantic_diffs and file_path in semantic_diffs:
                semantic_info = semantic_diffs[file_path]

            summary = generate_diff_summary(
                execute_llm_fn=execute_llm_fn,
                before_code=before_code,
                after_code=after_code,
                semantic_diffs={file_path: semantic_info} if semantic_info else None,
                model=model,
                logger=logger,
            )
            result[file_path] = (
                summary if isinstance(summary, str) else "要約生成に失敗しました"
            )
        except Exception as e:
            if logger:
                logger.warning(
                    f"Failed to generate diff summary for {file_path}: {e}", exc_info=True,
                )
            result[file_path] = f"差分サマリーの生成に失敗しました: {e}"

    return result
