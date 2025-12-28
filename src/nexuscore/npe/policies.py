# ==============================================================================
# File: src/nexuscore/npe/policies.py
# Purpose:
#   - 機密情報（シークレット、PII）のスキャンとマスキング
#   - LLMへの情報送信前の「自動セキュリティゲート」
# ==============================================================================
from __future__ import annotations
import re
from nexuscore.logging_standard import get_logger

logger = get_logger(__name__)

_SENSITIVE_PATTERNS = [
    # .env形式のキー=値
    r'^\s*(?:[A-Z0-9_]+_)?(?:API|SECRET|ACCESS|REFRESH)?_?KEY\s*=\s*["\']?[^"\']+["\']?\s*$',
    r'^\s*(?:TOKEN|PASSWORD|PASS|AUTH)_?[A-Z0-9_]*\s*=\s*["\']?[^"\']+["\']?\s*$',
    # AWS
    r'AKIA[0-9A-Z]{16}',
    r'ASIA[0-9A-Z]{16}',
    # PEM鍵
    r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
    # メール/電話（誤送出防止のゆるめヒット）
    r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
    r'\b\d{2,4}[-\s]?\d{2,4}[-\s]?\d{3,4}\b',
]

def context_scanner(code: str) -> str:
    """
    コンテキストをスキャンし、機密情報の有無を判定する ('safe' or 'sensitive')。
    """
    logger.info("Context scan initiated...")
    for pat in _SENSITIVE_PATTERNS:
        if re.search(pat, code, flags=re.IGNORECASE | re.MULTILINE):
            m = re.search(pat, code, flags=re.IGNORECASE | re.MULTILINE)
            logger.warning(f"RESULT: Sensitive pattern found. Match: '{m.group(0)[:64]}...'")
            return "sensitive"
    logger.info("RESULT: No sensitive patterns found.")
    return "safe"


def secure_context_builder(code: str) -> str:
    """
    機密情報をマスキング（匿名化）処理する。
    """
    logger.info("Masking sensitive data in context...")
    masked = code
    # キー=値の一般マスク
    masked = re.sub(
        r'^(\s*(?:[A-Z0-9_]+_)?(?:API|SECRET|ACCESS|REFRESH)?_?KEY\s*=\s*)["\']?[^"\']+["\']?\s*$',
        r'\1"[REDACTED_BY_NPE]"',
        masked,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    masked = re.sub(
        r'^(\s*(?:TOKEN|PASSWORD|PASS|AUTH)_?[A-Z0-9_]*\s*=\s*)["\']?[^"\']+["\']?\s*$',
        r'\1"[REDACTED_BY_NPE]"',
        masked,
        flags=re.IGNORECASE | re.MULTILINE,
    )
    masked = re.sub(r'AKIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY_BY_NPE]', masked, flags=re.IGNORECASE)
    masked = re.sub(r'ASIA[0-9A-Z]{16}', '[REDACTED_AWS_KEY_BY_NPE]', masked, flags=re.IGNORECASE)
    masked = re.sub(r'(-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)[\s\S]+?(-----END .*? KEY-----)', r'\1\n[REDACTED_PEM_BY_NPE]\n\2', masked, flags=re.IGNORECASE)
    # 連絡先のゆるマスク
    masked = re.sub(r'([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', r'[\1]@[REDACTED_DOMAIN]', masked)
    masked = re.sub(r'\b(\d{2,4})[-\s]?(\d{2,4})[-\s]?(\d{3,4})\b', r'\1-[REDACTED]-\3', masked)
    return masked
