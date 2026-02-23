"""
API スモークテスト共通ヘルパー

JSON レスポンスの検証を共通化。
"""

from __future__ import annotations

from collections.abc import Iterable


def assert_json_keys(obj: dict, keys: Iterable[str]) -> None:
    """
    JSON オブジェクトに指定されたキーがすべて含まれていることを確認する。

    Args:
        obj: 検証する JSON オブジェクト（dict）
        keys: 検証するキーのリスト

    Raises:
        AssertionError: キーが含まれていない場合
    """
    for k in keys:
        assert k in obj, f"Missing key in JSON response: {k}"
