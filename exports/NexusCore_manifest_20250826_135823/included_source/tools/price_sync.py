# ==============================================================================
# ファイル: tools/price_sync.py
# 目的  : 主要ベンダの料金表を取得し、統一スキーマJSONを出力。
# 使い方:
#   python tools/price_sync.py --out data/cost_table.json
#   （.env に NEXUS_COST_TABLE_JSON=data/cost_table.json を設定）
# 依存  : pip install requests beautifulsoup4 python-dotenv
# 注意  : 各社のページ構造は変化しやすい。失敗時は fallback 値を使用。
# スキーマ:
# {
#   "<model_name>": {"in": <USD_per_1M>, "out": <USD_per_1M>},
#   ...
# }
# ==============================================================================

from __future__ import annotations
import os
import re
import json
import argparse
import logging
from typing import Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(override=False)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("price_sync")

# ----------------------- Fallback（最低限の初期値） ----------------------- #
FALLBACK = {
    "gpt-4o": {"in": 2.50, "out": 10.00},
    "gemini-1.5-flash-latest": {"in": 0.0375, "out": 0.15},
    "gemini-1.5-pro-latest": {"in": 3.50, "out": 10.50},
    "claude-3-sonnet": {"in": 3.00, "out": 15.00},  # Console無料枠は別扱い
    "claude-3-haiku": {"in": 0.80, "out": 4.00},
    "deepseek-r1": {"in": 0.55, "out": 2.19},
    "command-r-plus": {"in": 2.50, "out": 10.00},
    "mistral-small": {"in": 0.25, "out": 0.60},
    "mistral-medium": {"in": 2.70, "out": 8.10},
    "kimi-k2": {"in": 0.15, "out": 2.50},
    "qwen-1_5-7b": {"in": 0.10, "out": 0.20},
    "yi-1_5-9b": {"in": 0.20, "out": 0.40},
}

# ----------------------- ユーティリティ ----------------------- #
def _usd_per_m_from_text(text: str) -> Optional[float]:
    """
    ' $0.15 / 1M tokens ' のような文字列から数値を抽出。
    小数 or 整数を許容。カンマは削除。
    """
    if not text:
        return None
    t = text.replace(",", "")
    m = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*1\s*M", t, re.I)
    if not m:
        m = re.search(r"\$?\s*([0-9]+(?:\.[0-9]+)?)\s*(?:per|/)\s*M", t, re.I)
    return float(m.group(1)) if m else None

def _get(url: str) -> Optional[str]:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return r.text
    except Exception as e:
        log.warning(f"fetch failed: {url} ({e})")
        return None

# ----------------------- 各社アダプタ（簡易スクレイプ） ----------------------- #
def sync_openai() -> Dict[str, Any]:
    # 参考: OpenAI pricing ページ（構造変動に注意）
    url = os.getenv("PRICE_URL_OPENAI", "https://openai.com/api/pricing/")
    html = _get(url)
    data = {}
    if html:
        soup = BeautifulSoup(html, "html.parser")
        # 例: gpt-4o in/out をそれぞれ拾う（簡易；構造変更時は正規表現で保険）
        text = soup.get_text(" ", strip=True)
        # ざっくり検索
        gpt4o_in = _usd_per_m_from_text(re.search(r"GPT-4o.*?Input.*?\$?\s*([0-9\.\,]+)\s*/\s*1M", text, re.I|re.S).group(0)) if re.search(r"GPT-4o.*?Input", text, re.I|re.S) else None
        gpt4o_out = _usd_per_m_from_text(re.search(r"GPT-4o.*?(Output|Completion).*?\$?\s*([0-9\.\,]+)\s*/\s*1M", text, re.I|re.S).group(0)) if re.search(r"GPT-4o.*?(Output|Completion)", text, re.I|re.S) else None
        if gpt4o_in and gpt4o_out:
            data["gpt-4o"] = {"in": gpt4o_in, "out": gpt4o_out}
    return data

def sync_gemini() -> Dict[str, Any]:
    url = os.getenv("PRICE_URL_GEMINI", "https://ai.google.dev/pricing")
    html = _get(url)
    data = {}
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        # Flash の単価を粗く抽出（価格体系は階層的なため、最低水準の例を拾う）
        flash_in = _usd_per_m_from_text(re.search(r"Gemini 1\.5 Flash.*?Input.*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Gemini 1\.5 Flash.*?Input", text, re.I|re.S) else None
        flash_out = _usd_per_m_from_text(re.search(r"Gemini 1\.5 Flash.*?(Output|Generate).*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Gemini 1\.5 Flash.*?(Output|Generate)", text, re.I|re.S) else None
        if flash_in and flash_out:
            data["gemini-1.5-flash-latest"] = {"in": flash_in, "out": flash_out}
        # Pro も同様に（必要に応じて）
        pro_in = _usd_per_m_from_text(re.search(r"Gemini 1\.5 Pro.*?Input.*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Gemini 1\.5 Pro.*?Input", text, re.I|re.S) else None
        pro_out = _usd_per_m_from_text(re.search(r"Gemini 1\.5 Pro.*?(Output|Generate).*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Gemini 1\.5 Pro.*?(Output|Generate)", text, re.I|re.S) else None
        if pro_in and pro_out:
            data["gemini-1.5-pro-latest"] = {"in": pro_in, "out": pro_out}
    return data

def sync_anthropic() -> Dict[str, Any]:
    url = os.getenv("PRICE_URL_ANTHROPIC", "https://www.anthropic.com/pricing")
    html = _get(url)
    data = {}
    if html:
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True)
        # Sonnet/Haiku 抽出（3.x/3.5 等の表記差あり→名称で広めに拾う）
        sonnet_in = _usd_per_m_from_text(re.search(r"Sonnet.*?Input.*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Sonnet.*?Input", text, re.I|re.S) else None
        sonnet_out = _usd_per_m_from_text(re.search(r"Sonnet.*?(Output|Generate).*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Sonnet.*?(Output|Generate)", text, re.I|re.S) else None
        haiku_in = _usd_per_m_from_text(re.search(r"Haiku.*?Input.*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Haiku.*?Input", text, re.I|re.S) else None
        haiku_out = _usd_per_m_from_text(re.search(r"Haiku.*?(Output|Generate).*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Haiku.*?(Output|Generate)", text, re.I|re.S) else None
        if sonnet_in and sonnet_out:
            data["claude-3-sonnet"] = {"in": sonnet_in, "out": sonnet_out}
        if haiku_in and haiku_out:
            data["claude-3-haiku"] = {"in": haiku_in, "out": haiku_out}
    return data

def sync_deepseek() -> Dict[str, Any]:
    url = os.getenv("PRICE_URL_DEEPSEEK", "https://api-docs.deepseek.com/")  # 公式ドキュメントTOP等
    html = _get(url)
    data = {}
    if html:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        r1_in = _usd_per_m_from_text(re.search(r"(Reasoner|R1).*?Input.*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"(Reasoner|R1).*?Input", text, re.I|re.S) else None
        r1_out = _usd_per_m_from_text(re.search(r"(Reasoner|R1).*?(Output|Generate).*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"(Reasoner|R1).*?(Output|Generate)", text, re.I|re.S) else None
        if r1_in and r1_out:
            data["deepseek-r1"] = {"in": r1_in, "out": r1_out}
    return data

def sync_cohere() -> Dict[str, Any]:
    url = os.getenv("PRICE_URL_COHERE", "https://cohere.com/pricing")
    html = _get(url)
    data = {}
    if html:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        cmdr_in = _usd_per_m_from_text(re.search(r"Command R\+.*?Input.*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Command R\+.*?Input", text, re.I|re.S) else None
        cmdr_out = _usd_per_m_from_text(re.search(r"Command R\+.*?(Output|Generate).*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Command R\+.*?(Output|Generate)", text, re.I|re.S) else None
        if cmdr_in and cmdr_out:
            data["command-r-plus"] = {"in": cmdr_in, "out": cmdr_out}
    return data

def sync_mistral() -> Dict[str, Any]:
    url = os.getenv("PRICE_URL_MISTRAL", "https://mistral.ai/technology/#pricing")
    html = _get(url)
    data = {}
    if html:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        small_in = _usd_per_m_from_text(re.search(r"Mistral (Small|sm).*?Input.*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Mistral (Small|sm).*?Input", text, re.I|re.S) else None
        small_out = _usd_per_m_from_text(re.search(r"Mistral (Small|sm).*?(Output|Generate).*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Mistral (Small|sm).*?(Output|Generate)", text, re.I|re.S) else None
        if small_in and small_out:
            data["mistral-small"] = {"in": small_in, "out": small_out}
    return data

def sync_moonshot() -> Dict[str, Any]:
    # Kimi K2（Moonshot）公式は変動・審査制が多いため、公開ページが取れない場合はFALLBACK維持
    url = os.getenv("PRICE_URL_MOONSHOT", "https://platform.moonshot.cn/")  # 参考パス
    html = _get(url)
    data = {}
    if html:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
        k2_in = _usd_per_m_from_text(re.search(r"Kimi.*?K2.*?Input.*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Kimi.*?K2.*?Input", text, re.I|re.S) else None
        k2_out = _usd_per_m_from_text(re.search(r"Kimi.*?K2.*?(Output|Generate).*?\$?[0-9\.\,]+/?\s*1M", text, re.I|re.S).group(0)) if re.search(r"Kimi.*?K2.*?(Output|Generate)", text, re.I|re.S) else None
        if k2_in and k2_out:
            data["kimi-k2"] = {"in": k2_in, "out": k2_out}
    return data

# ----------------------- メイン ----------------------- #
PROVIDERS = [
    ("openai", sync_openai),
    ("gemini", sync_gemini),
    ("anthropic", sync_anthropic),
    ("deepseek", sync_deepseek),
    ("cohere", sync_cohere),
    ("mistral", sync_mistral),
    ("moonshot", sync_moonshot),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="出力JSONパス（例: data/cost_table.json）")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    merged = dict(FALLBACK)  # まずはFallbackで初期化
    for name, fn in PROVIDERS:
        try:
            data = fn() or {}
            # Fallbackよりも“取得できた値”を優先
            for k, v in data.items():
                if isinstance(v, dict) and "in" in v and "out" in v:
                    merged[k] = {"in": float(v["in"]), "out": float(v["out"])}
            logging.info(f"[{name}] captured: {list(data.keys())}")
        except Exception as e:
            logging.warning(f"[{name}] sync failed: {e}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    print(f"[OK] wrote: {args.out}")
    print("環境変数に以下を追加すると、起動時にこの表が使われます：")
    print(f"NEXUS_COST_TABLE_JSON={args.out}")

if __name__ == "__main__":
    main()
