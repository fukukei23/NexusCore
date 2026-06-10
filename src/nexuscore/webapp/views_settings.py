from __future__ import annotations

import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for

from nexuscore.utils.crypto_utils import encrypt_string
from nexuscore.webapp import db
from nexuscore.webapp.auth import get_current_user, require_auth
from nexuscore.webapp.models import User

logger = logging.getLogger(__name__)

bp = Blueprint("views_settings", __name__, url_prefix="/settings")


@bp.route("/")
@require_auth
def settings_index() -> str:
    """設定ページを表示"""
    user: User = get_current_user()
    return render_template(
        "settings/index.html",
        user_login=user.github_login,
        key_configured=user.openrouter_key_enc is not None,
    )


@bp.route("/openrouter-key", methods=["POST"])
@require_auth
def save_openrouter_key():
    """OpenRouter APIキーを暗号化して保存"""
    user: User = get_current_user()
    try:
        user.openrouter_key_enc = encrypt_string(request.form["api_key"])
        db.session.commit()
        flash("OpenRouter APIキーを保存しました")
    except ValueError:
        flash("サーバー設定エラー: NEXUS_ENCRYPTION_KEY が未設定です", "error")
    return redirect(url_for("views_settings.settings_index"))


@bp.route("/openrouter-key/delete", methods=["POST"])
@require_auth
def delete_openrouter_key():
    """OpenRouter APIキーを削除"""
    user: User = get_current_user()
    user.openrouter_key_enc = None
    db.session.commit()
    flash("OpenRouter APIキーを削除しました")
    return redirect(url_for("views_settings.settings_index"))
