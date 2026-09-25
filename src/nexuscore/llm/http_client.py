from __future__ import annotations

import logging

try:  # pragma: no cover - exercised indirectly via providers
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:  # pragma: no cover - fallback when requests isn't installed
    requests = None  # type: ignore[assignment]
    HTTPAdapter = None  # type: ignore[assignment, misc]
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
            # 方向1v3.1 プラン①′（2026-09-26・Step 0計測 57run解析に基づく再設計）:
            # - read=1: ReadTimeoutは2試行でfail-fast（120s×2+backoff≈245s・旧設計は3試行
            #   =最悪360s超・bench実測で「答えは満点・時間だけ切られる」の主要因）
            # - 429はRetry-After尊重（urllib3既定）+ backoff 2-30s・5xxも同戻略
            # - 429以外の4xxは status_forcelist 外＝retryしない（即raise）
            retry_strategy = Retry(
                total=3,
                connect=1,
                read=1,
                status=3,
                backoff_factor=2,
                backoff_max=30,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=frozenset({"POST"}),
                respect_retry_after_header=True,
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
