"""LLM出力からコードブロックフェンスを除去するサニタイザ。"""

import re


def clean_output(text: str) -> str:
    """LLM が返した ```code``` ブロックを外して中身だけ返す。

    対応パターン:
      - ```python\\n...\\n```
      - ```\\n...\\n```

    Args:
        text: LLMの生の出力テキスト。

    Returns:
        フェンス除去済みの文字列。フェンスがない場合はstripのみ適用。
    """
    if not text:
        return ""
    match = re.search(r"```(?:python\n)?(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()
