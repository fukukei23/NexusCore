import importlib
import os


def test_default_retry_limits(monkeypatch):
    monkeypatch.delenv("NEXUS_DEBUG_MAX_RETRIES", raising=False)
    monkeypatch.delenv("NEXUS_REVIEW_MAX_RETRIES", raising=False)
    import nexuscore.core.phase_runner_mixin as mod
    importlib.reload(mod)
    try:
        assert mod.DEBUG_MAX_RETRIES == 3
        assert mod.REVIEW_MAX_RETRIES == 2
    finally:
        # モジュールグローバルへの reload は他テストと共有されるため、
        # 元の状態(デフォルト値)に戻してからテストを終える(テスト間汚染防止)
        monkeypatch.undo()
        importlib.reload(mod)


def test_env_override_retry_limits(monkeypatch):
    monkeypatch.setenv("NEXUS_DEBUG_MAX_RETRIES", "7")
    monkeypatch.setenv("NEXUS_REVIEW_MAX_RETRIES", "1")
    import nexuscore.core.phase_runner_mixin as mod
    importlib.reload(mod)
    try:
        assert mod.DEBUG_MAX_RETRIES == 7
        assert mod.REVIEW_MAX_RETRIES == 1
    finally:
        # importlib.reload はモジュールグローバル(DEBUG_MAX_RETRIES等)を書き換えるため、
        # env varを戻すだけでなく再reloadしてデフォルト値に復元する必要がある
        # (これを怠ると後続テストが DEBUG_MAX_RETRIES=7 のまま実行され、フルスイートでのみ失敗する)
        monkeypatch.undo()
        importlib.reload(mod)
