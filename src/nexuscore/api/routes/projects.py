"""
Projects エンドポイント

プロジェクト管理用の FastAPI エンドポイント。
既存の Flask 実装 (`src/nexuscore/webapp/api_external.py`) と互換性を保つ。

split: CRUD + Runs（_projects_crud / _projects_runs）
"""

from fastapi import APIRouter

from ._projects_crud import router as crud_router
from ._projects_runs import router as runs_router

router = APIRouter(tags=["projects"])
router.include_router(crud_router)
router.include_router(runs_router)
