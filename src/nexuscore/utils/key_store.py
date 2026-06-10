"""Local BYOK key storage for Gradio UI (standalone mode).

Stores encrypted API keys in ``~/.nexuscore/byok/keys.json``.
Always requires ``NEXUS_ENCRYPTION_KEY`` — **fail-closed**: refuses to
save if the encryption key is not configured.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

__all__ = ["save_key", "load_key", "delete_key", "has_key", "list_providers"]

logger = logging.getLogger(__name__)

_KEY_DIR = Path.home() / ".nexuscore" / "byok"
_KEY_FILE = _KEY_DIR / "keys.json"


def _ensure_dir() -> None:
    _KEY_DIR.mkdir(parents=True, exist_ok=True)
    _KEY_DIR.chmod(0o700)


def _load_all() -> dict:
    if not _KEY_FILE.exists():
        return {}
    try:
        return json.loads(_KEY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _flush(keys: dict) -> None:
    _ensure_dir()
    _KEY_FILE.write_text(json.dumps(keys, indent=2), encoding="utf-8")
    _KEY_FILE.chmod(0o600)


# ---- public API ----


def save_key(provider: str, api_key: str) -> None:
    """Save an encrypted API key for *provider*.

    Raises ``ValueError`` if ``NEXUS_ENCRYPTION_KEY`` is not set
    (fail-closed: never stores keys in plaintext).
    """
    from nexuscore.utils.crypto_utils import encrypt_string  # noqa: F811

    keys = _load_all()
    keys[provider] = {"encrypted": encrypt_string(api_key)}
    _flush(keys)


def load_key(provider: str) -> str | None:
    """Load and decrypt the API key for *provider*.  Returns ``None`` if missing."""
    entry = _load_all().get(provider)
    if not entry or "encrypted" not in entry:
        return None
    try:
        from nexuscore.utils.crypto_utils import decrypt_string

        return decrypt_string(entry["encrypted"])
    except Exception:
        logger.exception("Failed to decrypt %s key", provider)
        return None


def delete_key(provider: str) -> bool:
    """Delete stored key for *provider*.  Returns ``True`` if it existed."""
    keys = _load_all()
    existed = provider in keys
    keys.pop(provider, None)
    _flush(keys)
    return existed


def has_key(provider: str) -> bool:
    """Check whether a key is stored for *provider*."""
    return load_key(provider) is not None


def list_providers() -> list[str]:
    """Return the list of providers that have stored keys."""
    return list(_load_all().keys())
