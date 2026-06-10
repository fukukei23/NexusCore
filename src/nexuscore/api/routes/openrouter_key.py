from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from nexuscore.utils.crypto_utils import encrypt_string
from nexuscore.webapp import db
from nexuscore.webapp.models import User

from ..dependencies.auth import AuthenticatedUser, get_current_user

router = APIRouter(prefix="/user", tags=["openrouter"])
logger = logging.getLogger(__name__)


class OpenRouterKeyRequest(BaseModel):
    api_key: str


@router.post("/openrouter-key", status_code=201)
async def save_openrouter_key(
    request: OpenRouterKeyRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str]:
    """OpenRouterキーを暗号化してDBに保存"""
    user = db.session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        user.openrouter_key_enc = encrypt_string(request.api_key)
    except ValueError as e:
        logger.error("Encryption failed: %s", e)
        raise HTTPException(status_code=500, detail="NEXUS_ENCRYPTION_KEY is not configured.")
    db.session.commit()
    return {"message": "OpenRouter key saved"}


@router.delete("/openrouter-key", status_code=200)
async def delete_openrouter_key(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, str]:
    """保存済みOpenRouterキーを削除"""
    user = db.session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.openrouter_key_enc = None
    db.session.commit()
    return {"message": "OpenRouter key deleted"}


@router.get("/openrouter-key/status", status_code=200)
async def get_openrouter_key_status(
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> dict[str, bool]:
    """OpenRouterキーが設定済みかを返す"""
    user = db.session.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"configured": user.openrouter_key_enc is not None}
