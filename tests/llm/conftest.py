"""tests/llm 共通 fixture。

C5（silent stub-fallback 解消・spec E+α改）の後方互換:
NEXUSCORE_ALLOW_STUB_FALLBACK は本番では未設定(=例外送出)。
tests/llm の既存テストは従来の stub-fallback 挙動を前提とするため、
デフォルトでフラグON（従来挙動）に設定する。

フラグOFF（本番＝例外送出）を検証する新規テストは、各テスト関数内で
monkeypatch.delenv("NEXUSCORE_ALLOW_STUB_FALLBACK", raising=False) で上書きする
（pytest は autouse fixture → テスト関数の順に実行されるため、delenv が勝つ）。
"""
import pytest


@pytest.fixture(autouse=True)
def _allow_stub_fallback_by_default(monkeypatch):
    """tests/llm は従来の stub-fallback 挙動をデフォルトで許可（C5 後方互換）。"""
    monkeypatch.setenv("NEXUSCORE_ALLOW_STUB_FALLBACK", "1")
