# ==============================================================================
# ファイル: tools/prompt_batcher.py
# 目的  : 類似エラーや複数ファイルの指摘を "1プロンプト" に安全圧縮。
# 改良点:
#   - 重複除去（path+内容ハッシュ）
#   - シークレット簡易マスキング
#   - 全体サイズ上限（max_total_chars）
#   - 出力言語制御 (locale)
#   - 追加ask_style: "consensus_ready"（後段集約向けJSON）
# ==============================================================================

from __future__ import annotations
from typing import List, Dict
import hashlib
import re

_SECRET_PATTERNS = [
    r"sk-[A-Za-z0-9]{20,}",            # OpenAI風
    r"(?i)api[_-]?key\s*[:=]\s*[A-Za-z0-9\-\._]{16,}",
    r"(?i)secret\s*[:=]\s*[A-Za-z0-9\-\._]{16,}",
    r"(?i)token\s*[:=]\s*[A-Za-z0-9\-\._]{16,}",
]

def _shorten(s: str, lim: int) -> str:
    if len(s) <= lim:
        return s
    return s[: max(0, lim - 100)] + "\n...<truncated>..."

def _mask_secrets(s: str) -> str:
    out = s
    for pat in _SECRET_PATTERNS:
        out = re.sub(pat, "[REDACTED]", out)
    return out

def _dedup(snippets: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    uniq = []
    for it in snippets:
        key_src = f"{it.get('path','')}::{it.get('content','')[:500]}"
        h = hashlib.sha1(key_src.encode("utf-8")).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        uniq.append(it)
    return uniq

def build_batch_prompt(
    task_title: str,
    code_snippets: List[Dict[str, str]],
    max_items: int = 10,
    max_chars_per_snippet: int = 1200,
    ask_style: str = "bullet_critical",  # "bullet_critical" | "yes_no" | "patch_suggestion" | "consensus_ready"
    max_total_chars: int = 18000,
    locale: str = "ja",  # "ja" or "en"
) -> str:
    """
    Args:
      task_title: 例) "pytest失敗の共通原因レビュー"
      code_snippets: [{"path": "src/x.py", "content": "...", "error": "Traceback..."}]
      max_items: バッチ化する最大件数
      max_chars_per_snippet: 各スニペットの最大文字数（超過時は省略）
      ask_style: 出力フォーマットの誘導
      max_total_chars: 生成プロンプト全体の最大文字数（超過時は末尾カット）
      locale: 出力言語のヒント（"ja" / "en"）
    """
    # 1) 事前整形：重複除去 & シークレットマスク
    items = _dedup(code_snippets)[:max_items]

    blocks = []
    for i, it in enumerate(items, 1):
        code = _mask_secrets(it.get("content", ""))
        err = _mask_secrets(it.get("error", ""))
        blocks.append(
            f"### [{i}] {it.get('path','')}\n"
            f"--- code ---\n{_shorten(code, max_chars_per_snippet)}\n"
            f"--- error ---\n{_shorten(err, 800)}\n"
        )

    if ask_style == "bullet_critical":
        ask = (
            "出力は以下のJSONのみ:\n"
            "{ \"global_root_cause\": string,\n"
            "  \"common_fixes\": [string],\n"
            "  \"file_specific\": [{\"path\": string, \"fix\": string}]\n"
            "}\n"
            "冗長説明、序文、コードフェンスは禁止。"
        )
    elif ask_style == "yes_no":
        ask = "各項目に対し Yes/No と1行根拠のみを出力せよ。"
    elif ask_style == "patch_suggestion":
        ask = "各ファイルの修正案を最小差分で提案せよ（Unified Diff禁止、要点のみ）。"
    elif ask_style == "consensus_ready":
        # 後段のコンセンサス統合用に、モデル間で整合しやすい最小JSONを指定
        ask = (
            "Return ONLY JSON with schema:\n"
            "{ \"issues\":[{\"title\":string,\"evidence\":string}],"
            "  \"severity\":\"low|medium|high\","
            "  \"confidence\":0.0-1.0 }\n"
            "No preface. No code fences. Keep output minimal (≤300 chars)."
        )
    else:
        ask = "Answer concisely."

    header_ja = (
        f"# タスク: {task_title}\n"
        f"以下の複数エラー/コード断片を一括レビューし、共通原因と修正方針を抽出してください。\n"
        f"**短く・論点のみ** で回答すること。\n\n"
    )
    header_en = (
        f"# Task: {task_title}\n"
        f"Review multiple error/code snippets together and extract common root causes and fixes.\n"
        f"Respond **briefly and to the point**.\n\n"
    )
    header = header_ja if locale.lower().startswith("ja") else header_en

    prompt = header + "\n".join(blocks) + "\n\n" + ask

    # 2) 全体サイズ上限
    if len(prompt) > max_total_chars:
        prompt = prompt[: max_total_chars - 40] + "\n...<prompt_truncated>"

    return prompt
