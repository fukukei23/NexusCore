"""
SDK クライアントヘルパー

生成された Python SDK を使用してクライアントを作成するヘルパー関数。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# プロジェクトルートを取得
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
SDK_PYTHON_DIR = PROJECT_ROOT / "sdk" / "python"

# SDK を import できるようにパスを追加
if SDK_PYTHON_DIR.exists():
    sys.path.insert(0, str(SDK_PYTHON_DIR))

# SDK の import を試みる
SDK_AVAILABLE = False
SDK_IMPORT_ERROR: str | None = None
ApiClient: Any | None = None
Configuration: Any | None = None
DefaultApi: Any | None = None

if SDK_PYTHON_DIR.exists() and (SDK_PYTHON_DIR / "nexuscore_sdk").exists():
    try:
        from nexuscore_sdk import ApiClient, Configuration

        # DefaultApi またはタグごとの API クラスを試みる
        try:
            from nexuscore_sdk.api import DefaultApi
        except ImportError:
            # タグごとの API クラスを試みる
            try:
                from nexuscore_sdk.api import ExecuteApi, HealthApi, ProjectsApi

                DefaultApi = None  # DefaultApi が存在しない場合は None
            except ImportError:
                DefaultApi = None
        SDK_AVAILABLE = True
    except ImportError as e:
        SDK_AVAILABLE = False
        SDK_IMPORT_ERROR = str(e)
else:
    SDK_IMPORT_ERROR = f"SDK not found at {SDK_PYTHON_DIR}"


def create_sdk_client(base_url: str, api_key: str | None = None) -> Any:
    """
    生成された Python SDK を使用してクライアントを作成する。

    Args:
        base_url: API のベース URL（例: "http://127.0.0.1:8000"）
        api_key: API Key（認証が必要な場合）

    Returns:
        SDK の API クライアントインスタンス（DefaultApi またはタグごとの API クラス）

    Raises:
        ImportError: SDK が import できない場合
        RuntimeError: SDK が利用できない場合
    """
    if not SDK_AVAILABLE:
        raise RuntimeError(
            f"Python SDK not available: {SDK_IMPORT_ERROR}. "
            "Please run 'make sdk-python' to generate the SDK."
        )

    # SDK の設定
    configuration = Configuration(host=base_url)
    if api_key:
        # openapi-generator の Python SDK では、通常 api_key_prefix または api_key を使用
        # 実際の SDK の構造に合わせて調整が必要な場合がある
        if hasattr(configuration, "api_key"):
            configuration.api_key["X-API-Key"] = api_key
        elif hasattr(configuration, "api_key_prefix"):
            configuration.api_key_prefix["X-API-Key"] = api_key

    # API クライアントを作成
    api_client = ApiClient(configuration)

    # DefaultApi が存在する場合はそれを使用、そうでなければ api_client を返す
    if DefaultApi is not None:
        return DefaultApi(api_client)
    else:
        # タグごとの API クラスを使用する場合は、ここで適切なクラスを返す
        # または、api_client を直接返して、テスト側で適切な API クラスを使用する
        return api_client
