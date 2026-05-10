"""後方互換モジュール。実装は orchestrator_helper.py に統合済み。"""

from nexuscore.webapp.orchestrator_helper import run_orchestrator_inline  # noqa: F401

__all__ = ["run_orchestrator_inline"]
