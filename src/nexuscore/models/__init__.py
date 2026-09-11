"""DB モデル層。

`db` とエンティティをここから import する:

    from nexuscore.models import db, Project, Run

2026-09-12 に `webapp/models.py` から抽出した。
それまでは api / integration がモデルを使うためだけに webapp を import しており、
`api → webapp` 28 エッジのうち 24 件、`integration ↔ webapp` の循環 6 エッジが
この 1 点に集中していた。

後方互換のため `nexuscore.webapp.models` と `nexuscore.webapp.db` も当面動作する
（それぞれ本パッケージへの薄い再エクスポート）。新規コードは本パッケージを使うこと。
"""

from __future__ import annotations

from nexuscore.models.base import db
from nexuscore.models.entities import (
    ApiKey,
    ExecutionLog,
    NotificationLog,
    PatchRecord,
    Project,
    Run,
    User,
)

__all__ = [
    "ApiKey",
    "ExecutionLog",
    "NotificationLog",
    "PatchRecord",
    "Project",
    "Run",
    "User",
    "db",
]
