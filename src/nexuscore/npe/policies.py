# ==============================================================================
# File: src/nexuscore/npe/policies.py
# Purpose:
#   - 機密情報（シークレット、PII）のスキャンとマスキング
#   - LLMへの情報送信前の「自動セキュリティゲート」
# ==============================================================================
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List


@dataclass
class SecretMatch:
    """
    機密情報の検出結果を表すデータクラス。

    Attributes:
        type: 検出された機密情報の種類（"aws_access_key", "pem_private_key", "email", "phone", "api_key" など）
        value: マッチした文字列（マスク済みの場合もある）
        span: マッチした位置（start, end）のタプル
    """
    type: str
    value: str
    span: tuple[int, int]


# 機密情報パターンの定義（種類ごとに分類）
_AWS_ACCESS_KEY_PATTERNS = [
    r'AKIA[0-9A-Z]{16}',
    r'ASIA[0-9A-Z]{16}',
]

_PEM_PRIVATE_KEY_PATTERN = r'-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----'

_EMAIL_PATTERN = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'

_PHONE_PATTERN = r'\b\d{2,4}[-\s]?\d{2,4}[-\s]?\d{3,4}\b'

_API_KEY_PATTERNS = [
    r'^\s*(?:[A-Z0-9_]+_)?(?:API|SECRET|ACCESS|REFRESH)?_?KEY\s*=\s*["\']?[^"\']+["\']?\s*$',
    r'^\s*(?:TOKEN|PASSWORD|PASS|AUTH)_?[A-Z0-9_]*\s*=\s*["\']?[^"\']+["\']?\s*$',
]


def _scan_aws_keys(text: str) -> List[SecretMatch]:
    """AWS アクセスキーをスキャンする。"""
    matches: List[SecretMatch] = []
    for pattern in _AWS_ACCESS_KEY_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            matches.append(SecretMatch(
                type="aws_access_key",
                value=match.group(0),
                span=(match.start(), match.end())
            ))
    return matches


def _scan_pem_keys(text: str) -> List[SecretMatch]:
    """PEM 秘密鍵をスキャンする。"""
    matches: List[SecretMatch] = []
    for match in re.finditer(_PEM_PRIVATE_KEY_PATTERN, text, flags=re.IGNORECASE):
        # PEM鍵の開始位置を記録（終了位置は後で検出する必要があるが、簡易的に開始位置のみ）
        matches.append(SecretMatch(
            type="pem_private_key",
            value=match.group(0),
            span=(match.start(), match.end())
        ))
    return matches


def _scan_emails(text: str) -> List[SecretMatch]:
    """メールアドレスをスキャンする。"""
    matches: List[SecretMatch] = []
    for match in re.finditer(_EMAIL_PATTERN, text):
        matches.append(SecretMatch(
            type="email",
            value=match.group(0),
            span=(match.start(), match.end())
        ))
    return matches


def _scan_phones(text: str) -> List[SecretMatch]:
    """電話番号をスキャンする。"""
    matches: List[SecretMatch] = []
    for match in re.finditer(_PHONE_PATTERN, text):
        matches.append(SecretMatch(
            type="phone",
            value=match.group(0),
            span=(match.start(), match.end())
        ))
    return matches


def _scan_api_keys(text: str) -> List[SecretMatch]:
    """API キー形式の文字列をスキャンする。"""
    matches: List[SecretMatch] = []
    for pattern in _API_KEY_PATTERNS:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            matches.append(SecretMatch(
                type="api_key",
                value=match.group(0),
                span=(match.start(), match.end())
            ))
    return matches


def scan_text_for_secrets(text: str) -> List[SecretMatch]:
    """
    テキスト内の機密情報をスキャンし、検出結果のリストを返す。

    Args:
        text: スキャン対象のテキスト

    Returns:
        検出された機密情報のリスト（SecretMatch オブジェクト）。検出されない場合は空リスト。
    """
    all_matches: List[SecretMatch] = []

    # 各種類の機密情報をスキャン
    all_matches.extend(_scan_aws_keys(text))
    all_matches.extend(_scan_pem_keys(text))
    all_matches.extend(_scan_emails(text))
    all_matches.extend(_scan_phones(text))
    all_matches.extend(_scan_api_keys(text))

    # 重複を除去（同じ位置で複数のパターンにマッチする場合）
    # span が同じで type が異なる場合は、最初に見つかったものを優先
    seen_spans: set[tuple[int, int]] = set()
    unique_matches: List[SecretMatch] = []
    for match in all_matches:
        if match.span not in seen_spans:
            seen_spans.add(match.span)
            unique_matches.append(match)

    return unique_matches


def context_scanner(code: str) -> str:
    """
    コンテキストをスキャンし、機密情報の有無を判定する ('safe' or 'sensitive')。

    後方互換性のため、新しい scan_text_for_secrets() API を使用する。
    """
    matches = scan_text_for_secrets(code)
    if matches:
        return "sensitive"
    return "safe"


def secure_context_builder(code: str) -> str:
    """
    機密情報をマスキング（匿名化）処理する。

    後方互換性のため、既存のマスキングロジックを維持。
    """
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
    masked = re.sub(r'(-----BEGIN (?:RSA|EC|OPENSSH|PRIVATE) KEY-----)[\s\S]+?(-----END .*? KEY-----)', r'\1\n[REDACTED_PEM_BY_NPE]\n\2', masked, flags=re.IGNORECASE)
    # 連絡先のゆるマスク
    masked = re.sub(r'([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', r'[\1]@[REDACTED_DOMAIN]', masked)
    masked = re.sub(r'\b(\d{2,4})[-\s]?(\d{2,4})[-\s]?(\d{3,4})\b', r'\1-[REDACTED]-\3', masked)
    return masked
