"""Tests for the local BYOK key store (utils/key_store.py)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from nexuscore.utils.crypto_utils import generate_encryption_key
from nexuscore.utils.key_store import (
    delete_key,
    has_key,
    list_providers,
    load_key,
    save_key,
)


@pytest.fixture()
def tmp_key_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ``_KEY_DIR`` to a temp directory."""
    key_dir = tmp_path / "byok"
    monkeypatch.setattr("nexuscore.utils.key_store._KEY_DIR", key_dir)
    monkeypatch.setattr("nexuscore.utils.key_store._KEY_FILE", key_dir / "keys.json")
    return key_dir


@pytest.fixture()
def encryption_key(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set NEXUS_ENCRYPTION_KEY so crypto_utils works."""
    key = generate_encryption_key()
    monkeypatch.setenv("NEXUS_ENCRYPTION_KEY", key)
    return key


class TestKeyStore:
    """key_store round-trip tests."""

    def test_save_and_load_encrypted(self, tmp_key_dir: Path, encryption_key: str) -> None:
        save_key("openrouter", "sk-or-test-key-123")
        assert load_key("openrouter") == "sk-or-test-key-123"

    def test_save_and_load_plaintext_fallback(self, tmp_key_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NEXUS_ENCRYPTION_KEY", raising=False)
        save_key("openrouter", "sk-or-plain-key")
        assert load_key("openrouter") == "sk-or-plain-key"

    def test_load_missing_returns_none(self, tmp_key_dir: Path) -> None:
        assert load_key("nonexistent") is None

    def test_has_key(self, tmp_key_dir: Path, encryption_key: str) -> None:
        assert has_key("openrouter") is False
        save_key("openrouter", "sk-or-test")
        assert has_key("openrouter") is True

    def test_delete_key(self, tmp_key_dir: Path, encryption_key: str) -> None:
        save_key("openrouter", "sk-or-test")
        assert delete_key("openrouter") is True
        assert load_key("openrouter") is None
        assert delete_key("openrouter") is False  # already gone

    def test_list_providers(self, tmp_key_dir: Path, encryption_key: str) -> None:
        save_key("openrouter", "key1")
        save_key("openai", "key2")
        providers = list_providers()
        assert set(providers) == {"openrouter", "openai"}

    def test_overwrite_existing_key(self, tmp_key_dir: Path, encryption_key: str) -> None:
        save_key("openrouter", "old-key")
        save_key("openrouter", "new-key")
        assert load_key("openrouter") == "new-key"

    def test_file_permissions(self, tmp_key_dir: Path, encryption_key: str) -> None:
        save_key("openrouter", "sk-or-test")
        key_file = tmp_key_dir / "keys.json"
        # File should be readable only by owner (0o600)
        mode = key_file.stat().st_mode & 0o777
        assert mode == 0o600
