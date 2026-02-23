# nexuscore/utils/clean_output.py
import re


def clean_output(text: str) -> str:
    """
    LLM が返した ```code``` ブロックを外して中身だけ返す簡易サニタイザ
    """
    if not text:
        return ""
    # ```python ... ``` や ``` ... ``` 形式を探す
    match = re.search(r"```(?:python\n)?(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()
