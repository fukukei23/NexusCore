"""
LLM プロバイダ向け HTTP クライアント補助モジュール。

更新履歴:
- 2025-11-22 00:51 JST / Version 2.3.5-hotfix
  - Retry 付き Session を集中管理し、requests 未導入時はスタブで降格する仕様を明確化。
"""

from __future__ import annotations

import logging

try:  # pragma: no cover - exercised indirectly via providers
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:  # pragma: no cover - fallback when requests isn't installed
    requests = None
    HTTPAdapter = None
    Retry = None  # type: ignore[assignment, misc]

logger = logging.getLogger("LLMHttpClient")


class HttpClientFactory:
    """
    プロバイダごとに使い捨て Session を払い出す遅延初期化ファクトリ。
    Retry 設定や TLS アダプタ差し替えを中央集約する。
    """

    def __init__(self) -> None:
        self.available = requests is not None
        if not self.available:
            logger.warning(
                "[Init] 'requests' or 'urllib3' is not available. Providers will "
                "operate in stub mode."
            )

    def create_session(self) -> requests.Session | None:
        if not self.available or not requests:
            return None

        session = requests.Session()
        if Retry is not None and HTTPAdapter is not None:
            # 429/5xx を 3 回まで指数バックオフするデフォルト戦略
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=frozenset({"POST"}),
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("https://", adapter)
            session.mount("http://", adapter)
        return session


if requests:
    RequestsHTTPError = requests.exceptions.HTTPError
else:  # pragma: no cover - requests absent

    class RequestsHTTPError(Exception):  # type: ignore[no-redef]
        """Fallback HTTPError used when requests is unavailable."""

        pass
