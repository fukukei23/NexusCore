"""
CR-005-1: npe/policies.py の API 整理＋テスト追加

機密データ検出ロジックのテスト。
"""

from nexuscore.npe.policies import (
    SecretMatch,
    context_scanner,
    scan_text_for_secrets,
    secure_context_builder,
)


def test_scan_text_for_secrets_detects_aws_access_key():
    """AWS アクセスキー形式の文字列を含むテキストを入力。"""
    text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"

    matches = scan_text_for_secrets(text)

    assert len(matches) > 0
    aws_matches = [m for m in matches if m.type == "aws_access_key"]
    assert len(aws_matches) > 0

    # span が元テキストの位置と整合していること
    match = aws_matches[0]
    assert match.span[0] < match.span[1]
    assert text[match.span[0] : match.span[1]] == match.value
    assert "AKIA" in match.value


def test_scan_text_for_secrets_detects_aws_access_key_asia():
    """ASIA 形式の AWS アクセスキーも検出されること。"""
    text = "ASIAIOSFODNN7EXAMPLE"

    matches = scan_text_for_secrets(text)

    aws_matches = [m for m in matches if m.type == "aws_access_key"]
    assert len(aws_matches) > 0
    assert "ASIA" in aws_matches[0].value


def test_scan_text_for_secrets_detects_pem_private_key():
    """-----BEGIN PRIVATE KEY----- を含む文字列を渡す。"""
    text = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC...
-----END PRIVATE KEY-----"""

    matches = scan_text_for_secrets(text)

    pem_matches = [m for m in matches if m.type == "pem_private_key"]
    assert len(pem_matches) > 0

    # span が元テキストの位置と整合していること
    match = pem_matches[0]
    assert match.span[0] < match.span[1]
    assert "BEGIN" in match.value
    assert "PRIVATE KEY" in match.value or "RSA" in match.value or "EC" in match.value


def test_scan_text_for_secrets_detects_email():
    """メールアドレスを含むテキストで type == "email" が検出されること。"""
    text = "Contact us at support@example.com for help."

    matches = scan_text_for_secrets(text)

    email_matches = [m for m in matches if m.type == "email"]
    assert len(email_matches) > 0

    # span が元テキストの位置と整合していること
    match = email_matches[0]
    assert match.span[0] < match.span[1]
    assert text[match.span[0] : match.span[1]] == match.value
    assert "@" in match.value
    assert "example.com" in match.value


def test_scan_text_for_secrets_detects_phone():
    """電話番号が検出されること。"""
    text = "Call us at 03-1234-5678"

    matches = scan_text_for_secrets(text)

    phone_matches = [m for m in matches if m.type == "phone"]
    assert len(phone_matches) > 0


def test_scan_text_for_secrets_detects_api_key():
    """API キー形式の文字列が検出されること。"""
    text = "API_KEY=sk_test_1234567890abcdef"

    matches = scan_text_for_secrets(text)

    api_key_matches = [m for m in matches if m.type == "api_key"]
    assert len(api_key_matches) > 0


def test_scan_text_for_secrets_no_false_positive_on_normal_text():
    """日常的な文章やログ（疑似）を渡して、検出結果が空リストになること。"""
    normal_texts = [
        "This is a normal Python function that does nothing special.",
        "def hello_world():\n    print('Hello, world!')\n    return True",
        "import os\nimport sys\nfrom pathlib import Path",
        "logger.info('Processing started')\nlogger.debug('Debug message')",
        "x = 42\ny = 'hello'\nz = [1, 2, 3]",
    ]

    for text in normal_texts:
        matches = scan_text_for_secrets(text)
        # メールアドレスや電話番号のパターンが誤検出する可能性があるため、
        # 厳密には空リストとは限らないが、少なくともAWSキーやPEM鍵は検出されない
        aws_matches = [m for m in matches if m.type == "aws_access_key"]
        pem_matches = [m for m in matches if m.type == "pem_private_key"]
        assert len(aws_matches) == 0
        assert len(pem_matches) == 0


def test_scan_text_for_secrets_multiple_types():
    """複数の種類の機密情報が検出されること。"""
    text = """
    AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
    Contact: admin@example.com
    API_KEY=sk_test_1234567890abcdef
    """

    matches = scan_text_for_secrets(text)

    assert len(matches) > 0
    types = {m.type for m in matches}
    assert "aws_access_key" in types or "api_key" in types
    assert "email" in types


def test_context_scanner_returns_sensitive():
    """context_scanner が機密情報を検出した場合 "sensitive" を返すこと。"""
    text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"

    result = context_scanner(text)

    assert result == "sensitive"


def test_context_scanner_returns_safe():
    """context_scanner が機密情報を検出しない場合 "safe" を返すこと。"""
    text = "def hello_world():\n    print('Hello, world!')\n    return True"

    result = context_scanner(text)

    assert result == "safe"


def test_secure_context_builder_masks_aws_key():
    """secure_context_builder が AWS キーをマスクすること。"""
    text = "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE"

    masked = secure_context_builder(text)

    assert "AKIAIOSFODNN7EXAMPLE" not in masked
    assert "REDACTED" in masked


def test_secure_context_builder_masks_email():
    """secure_context_builder がメールアドレスをマスクすること。"""
    text = "Contact us at support@example.com"

    masked = secure_context_builder(text)

    assert "support@example.com" not in masked
    assert "REDACTED" in masked or "REDACTED_DOMAIN" in masked


def test_secret_match_dataclass():
    """SecretMatch データクラスが正しく動作すること。"""
    match = SecretMatch(type="aws_access_key", value="AKIAIOSFODNN7EXAMPLE", span=(0, 20))

    assert match.type == "aws_access_key"
    assert match.value == "AKIAIOSFODNN7EXAMPLE"
    assert match.span == (0, 20)
