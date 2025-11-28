# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# レジストリ/フォルダ: C:\Users\USER\tools\NexusCore\src\nexuscore\config\
# ファイル名: config.py
# 日付: 2025/09/02
#
# 使用方法:
#   この内容で既存のファイルを上書きしてください。
#   あなたの最新のAppConfigクラス設計を完全に維持しつつ、ImportErrorを解決します。
#
# 改修内容:
#   - ファイルの末尾で `config = AppConfig()` というインスタンスを生成。
#     これにより、他のモジュールは `from .config import config` で安全に設定を
#     インポートできるようになり、循環参照の問題が解消されます。
# ==============================================================================

from __future__ import annotations
from typing import Dict, Any, List
import os

class AppConfig:
    """
    アプリ全体の静的な構成（秘密鍵除く）＋ 自動運転ガバナンスの基準値
    既存の定義を後⽅互換で拡張
    """

    # ---- 既存（デフォルトは従来値。環境変数で上書き可能） -------------------
    FLASK_SECRET_KEY: str = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-dev")
    DATABASE_URI: str = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")

    # Celery 設定（開発/本番で切り替え可能）
    # 開発環境: redis://localhost:6379/0
    # 本番環境: redis://redis:6379/0 (Docker) または redis://redis.example.com:6379/0
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL",
        os.getenv("REDIS_URL", "redis://localhost:6379/0")  # REDIS_URL もサポート
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND",
        os.getenv("REDIS_URL", "redis://localhost:6379/1")  # REDIS_URL もサポート（別DB番号）
    )

    # Webapp ベースURL（PRコメントのリンク生成用）
    WEBAPP_BASE_URL: str = os.getenv("WEBAPP_BASE_URL", "http://localhost:5000")

    # ---- ロール別 自律度のサーバ上限（L0..L3） -------------------------------
    # 例) user<=1, admin<=2, system<=3
    ROLE_MAX_AUTONOMY: Dict[str, int] = {
        "user":   int(os.getenv("NEXUS_ROLE_MAX_AUTONOMY_USER",   "1")),
        "admin":  int(os.getenv("NEXUS_ROLE_MAX_AUTONOMY_ADMIN",  "2")),
        "system": int(os.getenv("NEXUS_ROLE_MAX_AUTONOMY_SYSTEM", "3")),
    }

    # ---- サーバ上限（来訪ポリシーのクランプ対象） -----------------------------
    SERVER_MAX_LIMITS: Dict[str, int] = {
        "max_llm_calls_per_task": int(os.getenv("NEXUS_MAX_LLM_CALLS", "12")),
        "max_diff_lines":         int(os.getenv("NEXUS_MAX_DIFF_LINES", "200")),
    }

    # ---- ベースライン（入口で丸める前の既定ポリシー） ------------------------
    #      include/exclude/protected はカンマ区切り文字列を配列化
    @staticmethod
    def _split_csv(env: str, default_csv: str) -> List[str]:
        val = os.getenv(env, default_csv).strip()
        return [s.strip() for s in val.split(",") if s.strip()]

    BASELINE_AUTOMATION_POLICY: Dict[str, Any] = {
        "autonomy_level": int(os.getenv("NEXUS_DEFAULT_AUTONOMY_LEVEL", "0")),  # 初期はドライラン
        "budget": {
            "max_llm_calls_per_task": int(os.getenv("NEXUS_MAX_LLM_CALLS", "12")),
            "hard_stop_on_exceed": True,  # False への緩和は不可
        },
        "scope": {
            "include_globs": _split_csv.__func__("NEXUS_SCOPE_INCLUDE",  "src/**,tools/**,tests/**"),
            "exclude_globs": _split_csv.__func__("NEXUS_SCOPE_EXCLUDE",  "**/.venv/**,**/openenv/**,exports/**,archive/**,sandbox_repo/**"),
            "protected_paths": _split_csv.__func__("NEXUS_SCOPE_PROTECTED","src/nexuscore/core/**,src/nexuscore/llm/**"),
            "max_diff_lines": int(os.getenv("NEXUS_MAX_DIFF_LINES", "200")),
        },
        # Orchestrator が参照する機密検出パターン（クライアントは追加のみ許容）
        "secret_detection_patterns": [
            r"(?:AKIA|ASIA)[0-9A-Z]{16}",        # AWS
            r"sk-[A-Za-z0-9]{20,}",              # OpenAI
            r"ghp_[A-Za-z0-9]{36}",              # GitHub PAT
            r"-----BEGIN (?:RSA|EC) PRIVATE KEY-----",
        ],
    }

# --- シングルトンインスタンスのエクスポート ---
# 他のファイルは `from nexuscore.config.config import config` でこのインスタンスをインポートする
config = AppConfig()

