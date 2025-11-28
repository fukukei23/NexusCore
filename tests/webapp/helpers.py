"""
UI スモークテスト共通ヘルパー

HTML の 200 チェック＋キーワード検証を共通化。
"""

from __future__ import annotations

from typing import List


def assert_page_keywords(response, keywords: List[str]) -> None:
    """
    レスポンスが 200 を返し、指定されたキーワードがすべて含まれていることを確認する。

    Args:
        response: Flask test client のレスポンス
        keywords: 検証するキーワードのリスト

    Raises:
        AssertionError: status_code が 200 でない場合、またはキーワードが含まれていない場合
    """
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}"

    html = response.data.decode("utf-8")

    for kw in keywords:
        assert kw in html, f"Missing keyword: {kw}"


def login_user(client, user) -> None:
    """
    テスト用ユーザーでログイン（セッションにユーザー情報を設定）

    Args:
        client: Flask test client
        user: User モデルインスタンス
    """
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["github_login"] = user.github_login

