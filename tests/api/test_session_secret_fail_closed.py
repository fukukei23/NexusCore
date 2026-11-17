"""SESSION_SECRET 未設定時の fail-closed 化テスト（2026-11-17・Strix診断A案⑤）

Strix診断（nexuscore_bfa5）で「`SESSION_SECRET` 未設定時に固定文字列
`nexuscore-dev-secret` でセッションCookieが署名され、攻撃者が任意の
セッションCookieを偽造できる」と指摘（medium）。

対応方針:
  - `SESSION_SECRET` 設定済み → その値を使用（従来どおり）
  - `ENV=production` かつ未設定 → RuntimeError（従来どおり）
  - それ以外（開発・検証環境）で未設定 → **ランダム生成した一時鍵**を使用
    （固定鍵は公開情報なので伪造が可能。一時鍵なら再起動で失効し偽造不能）
"""
from __future__ import annotations

import os

import pytest
from starlette.middleware.sessions import SessionMiddleware


def _session_secret(app) -> str | None:
    """SessionMiddleware に渡された secret_key を取得する

    app.user_middleware の要素は starlette.middleware.Middleware ラッパーで
    cls に実クラス、kwargs に渡した引数を持つ（2026-11-17 実測）。
    """
    for mw in app.user_middleware:
        if getattr(mw, "cls", None) is SessionMiddleware:
            return mw.kwargs.get("secret_key")
    return None


def test_no_hardcoded_dev_secret_in_source() -> None:
    """コード（コメントを除く）に固定フォールバック文字列が残っていないこと

    コメントは移行経緯として残すため、コメント行を除いて検査する。
    """
    src = open(
        os.path.join(os.path.dirname(__file__), "..", "..", "src", "nexuscore", "api", "fastapi_app.py"),
        encoding="utf-8",
    ).read()
    code_lines = [
        line for line in src.splitlines() if not line.lstrip().startswith("#")
    ]
    assert not any("nexuscore-dev-secret" in line for line in code_lines)


def test_session_secret_is_used_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """SESSION_SECRET 設定済みならその値を使う"""
    monkeypatch.setenv("SESSION_SECRET", "explicit-session-secret-value")
    monkeypatch.delenv("ENV", raising=False)

    from nexuscore.api.fastapi_app import create_app

    app = create_app()
    assert _session_secret(app) == "explicit-session-secret-value"


def test_random_secret_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    """未設定（本番以外）ではランダムな一時鍵を使う（固定鍵ではない）"""
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("ENV", raising=False)

    from nexuscore.api.fastapi_app import create_app

    app = create_app()
    secret = _session_secret(app)
    assert secret is not None
    assert secret != "nexuscore-dev-secret"
    assert len(secret) >= 32


def test_random_secret_differs_between_instances(monkeypatch: pytest.MonkeyPatch) -> None:
    """インスタンスごとに異なる（＝固定値ではないことの実証）"""
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.delenv("ENV", raising=False)

    from nexuscore.api.fastapi_app import create_app

    assert _session_secret(create_app()) != _session_secret(create_app())


def test_production_requires_session_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """本番（ENV=production）では未設定なら RuntimeError"""
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.setenv("ENV", "production")

    from nexuscore.api.fastapi_app import create_app

    with pytest.raises(RuntimeError):
        create_app()
