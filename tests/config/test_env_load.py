# 目的:
#  1) .env の読み込み結果を確認
#  2) LLMRouter が生成され、OpenAI(=gpt-5) も初期化できるかを確認
#
# 使い方:
#   (.venv) PS C:\Users\USER\tools\NexusCore> python tests/test_env_load.py

from __future__ import annotations

import os
import sys
from pathlib import Path

# --- プロジェクトルートを sys.path に追加（tests/ からでも src/ が import 可能に）---
ROOT = Path(__file__).resolve().parents[1]  # <- C:\Users\USER\tools\NexusCore
sys.path.insert(0, str(ROOT))

# --- .env を明示読み込み（REPL/単体実行でも確実に）---
from dotenv import load_dotenv

env_path = ROOT / ".env"
load_dotenv(dotenv_path=str(env_path), override=True)

print("=== ENV LOAD TEST ===")
print("OPENAI_API_KEY head:", os.getenv("OPENAI_API_KEY", "")[:10])
print("OPENAI_PROJECT:", os.getenv("OPENAI_PROJECT"))
print("=====================")

# --- ルーター import とクライアント初期化テスト ---
from src.nexuscore.llm import llm_router

router = llm_router.LLMRouter()

# 1) OpenAI（gpt-5）での初期化テスト
try:
    c1 = router._make_client("gpt-5")
    print("[OK] OpenAI client:", type(c1).__name__, getattr(c1, "model_name", ""))
except Exception as e:
    print("[NG] OpenAI init failed:", repr(e))

# 2) 代替: Gemini での初期化（OpenAIが失敗する場合の疎通確認用）
try:
    c2 = router._make_client("gemini-1.5-flash-latest")
    print("[OK] Gemini client:", type(c2).__name__, getattr(c2, "model_name", ""))
except Exception as e:
    print("[NG] Gemini init failed:", repr(e))
