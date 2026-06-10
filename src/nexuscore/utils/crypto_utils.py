from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

__all__ = ["encrypt_string", "decrypt_string", "generate_encryption_key"]


def _get_key() -> bytes:
    """NEXUS_ENCRYPTION_KEY 環境変数からAES-256キーを取得"""
    key_b64 = os.environ.get("NEXUS_ENCRYPTION_KEY")
    if not key_b64:
        raise ValueError("NEXUS_ENCRYPTION_KEY is not set.")
    return base64.b64decode(key_b64)


def generate_encryption_key() -> str:
    """新しいAES-256キーを生成してbase64で返す（初回セットアップ用）"""
    key = AESGCM.generate_key(bit_length=256)
    return base64.b64encode(key).decode("utf-8")


def encrypt_string(plaintext: str) -> str:
    """平文をAES-256-GCMで暗号化してbase64文字列を返す"""
    key = _get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(16)
    ciphertext_bytes = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ciphertext_bytes).decode("utf-8")


def decrypt_string(ciphertext: str) -> str:
    """base64暗号文を復号して平文を返す"""
    key = _get_key()
    aesgcm = AESGCM(key)
    payload = base64.b64decode(ciphertext)
    if len(payload) < 16:
        raise ValueError("Invalid ciphertext: too short.")
    return aesgcm.decrypt(payload[:16], payload[16:], None).decode("utf-8")
