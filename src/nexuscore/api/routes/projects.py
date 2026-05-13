from fastapi import APIRouter

from ._projects_crud import router as crud_router
from ._projects_runs import router as runs_router

router = APIRouter(tags=["projects"])
router.include_router(crud_router)
router.include_router(runs_router)
