from __future__ import annotations

import base64

import pytest

from nexuscore.utils.crypto_utils import (
    decrypt_string,
    encrypt_string,
    generate_encryption_key,
)


def test_generate_key_returns_base64_string() -> None:
    key = generate_encryption_key()
    assert isinstance(key, str)
    assert len(base64.b64decode(key)) == 32


def test_encrypt_decrypt_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_ENCRYPTION_KEY", generate_encryption_key())
    plaintext = "sk-or-test-openrouter-key"
    assert decrypt_string(encrypt_string(plaintext)) == plaintext


def test_encrypt_produces_different_ciphertext_each_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_ENCRYPTION_KEY", generate_encryption_key())
    ct1 = encrypt_string("same text")
    ct2 = encrypt_string("same text")
    assert ct1 != ct2
    assert decrypt_string(ct1) == decrypt_string(ct2) == "same text"


def test_decrypt_raises_on_invalid_ciphertext(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NEXUS_ENCRYPTION_KEY", generate_encryption_key())
    with pytest.raises(Exception):
        decrypt_string("not-valid-base64-ciphertext!!")


def test_missing_key_raises_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NEXUS_ENCRYPTION_KEY", raising=False)
    with pytest.raises(ValueError):
        encrypt_string("any text")
