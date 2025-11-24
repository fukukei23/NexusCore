"""
LLM ランタイムの共有シングルトンと診断ユーティリティ。

各モジュールが import したタイミングで ENV 連携と HTTP クライアントの
有無を確定し、ログ出力も一元管理できるようにする。
"""

from __future__ import annotations

import logging
import os
from dataclasses import asdict, dataclass
from typing import Dict, Optional

from nexuscore.llm.config import LLMRouterConfig
from nexuscore.llm.http_client import HttpClientFactory

LOGGER = logging.getLogger("LLMRuntime")

CONFIG = LLMRouterConfig.from_env()
REQUEST_TIMEOUT = CONFIG.request_timeout
HTTP_CLIENT_FACTORY = HttpClientFactory()
HTTP_AVAILABLE = HTTP_CLIENT_FACTORY.available


@dataclass(frozen=True)
class LLMRuntimeDiagnostics:
    """ランタイム状態を可視化するためのデータコンテナ。"""

    env_file: Optional[str]
    request_timeout: float
    http_available: bool
    dry_run: bool
    real_calls_enabled: bool

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def log(self, logger: Optional[logging.Logger] = None) -> None:
        target = logger or LOGGER
        summary = ", ".join(f"{k}={v}" for k, v in self.to_dict().items())
        target.info("[Runtime] %s", summary)
        if not self.http_available:
            target.warning("[Runtime] HTTP client unavailable; providers will use stub mode.")
        if self.dry_run or not self.real_calls_enabled:
            target.info(
                "[Runtime] Real LLM calls disabled (dry_run=%s, real_calls_enabled=%s).",
                self.dry_run,
                self.real_calls_enabled,
            )


def current_diagnostics() -> LLMRuntimeDiagnostics:
    """
    現在のランタイム状態を取得する。テストからも直接参照しやすいように
    追加の副作用は発生させない。
    """
    env_file = os.getenv("NEXUSCORE_ENV_LOADED")
    return LLMRuntimeDiagnostics(
        env_file=env_file,
        request_timeout=REQUEST_TIMEOUT,
        http_available=HTTP_AVAILABLE,
        dry_run=CONFIG.dry_run,
        real_calls_enabled=CONFIG.real_calls_enabled,
    )


def log_runtime_status(logger: Optional[logging.Logger] = None) -> LLMRuntimeDiagnostics:
    """
    ランタイム状況をログ出力しつつ Diagnostics を返す。
    Router 初期化時などに呼び出す想定。
    """
    diag = current_diagnostics()
    diag.log(logger)
    return diag


__all__ = [
    "CONFIG",
    "REQUEST_TIMEOUT",
    "HTTP_CLIENT_FACTORY",
    "HTTP_AVAILABLE",
    "LLMRuntimeDiagnostics",
    "current_diagnostics",
    "log_runtime_status",
]
