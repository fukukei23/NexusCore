"""
Error Code Catalog の整合性チェックテスト

CR-FASTAPI-015 で作成された Error Code Catalog と OpenAPI スキーマの整合性を確認する。
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nexuscore.api.fastapi_app import app

# プロジェクトルートを取得
PROJECT_ROOT = Path(__file__).parent.parent.parent
ERROR_CODE_CATALOG_PATH = PROJECT_ROOT / "docs" / "api" / "ERROR_CODE_CATALOG.md"


def parse_error_code_catalog() -> dict[str, tuple[int, str]]:
    """
    ERROR_CODE_CATALOG.md からエラーコードと HTTP ステータスの対応をパースする

    Returns:
        Dict[str, Tuple[int, str]]: {error_code: (http_status, category)} の辞書
    """
    if not ERROR_CODE_CATALOG_PATH.exists():
        pytest.skip(f"ERROR_CODE_CATALOG.md not found at {ERROR_CODE_CATALOG_PATH}")

    catalog_content = ERROR_CODE_CATALOG_PATH.read_text(encoding="utf-8")

    # エラーコード一覧表をパース
    # 表の形式: | error.code | HTTP Status | カテゴリ | 説明 | 主な発生箇所 |
    error_codes = {}
    in_table = False
    table_started = False

    for line in catalog_content.split("\n"):
        # テーブルの開始を検出
        if "| error.code" in line.lower() and "| http status" in line.lower():
            in_table = True
            table_started = True
            continue

        if not in_table:
            continue

        # テーブルの終了を検出（空行または別のセクション）
        if line.strip() == "" or line.startswith("##"):
            if table_started:
                break

        # テーブルの行をパース
        if table_started and line.strip().startswith("|") and "`" in line:
            # | `UNAUTHORIZED` | 401 | Auth | ... | の形式をパース
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 4:
                error_code = parts[1].strip("`").strip()
                http_status_str = parts[2].strip()
                category = parts[3].strip()

                # HTTP ステータスを数値に変換
                try:
                    http_status = int(http_status_str)
                    error_codes[error_code] = (http_status, category)
                except ValueError:
                    # ヘッダー行や無効な行はスキップ
                    continue

    return error_codes


def get_openapi_error_responses(openapi_schema: dict) -> dict[str, set[int]]:
    """
    OpenAPI スキーマから ErrorResponse を返すレスポンス定義を抽出する

    Args:
        openapi_schema: OpenAPI スキーマの辞書

    Returns:
        Dict[str, Set[int]]: {path: {status_codes}} の辞書
    """
    error_responses = {}
    paths = openapi_schema.get("paths", {})

    for path, path_item in paths.items():
        status_codes = set()
        for method, operation in path_item.items():
            if method.lower() in ["get", "post", "put", "delete", "patch"]:
                responses = operation.get("responses", {})
                for status_str, response_spec in responses.items():
                    # ステータスコードを数値に変換
                    try:
                        status_code = int(status_str)
                    except ValueError:
                        continue

                    # ErrorResponse が含まれているか確認
                    content = response_spec.get("content", {})
                    for _content_type, media_type_spec in content.items():
                        schema_ref = media_type_spec.get("schema", {}).get("$ref", "")
                        if "ErrorResponse" in schema_ref or "ErrorResponse" in str(response_spec):
                            status_codes.add(status_code)

        if status_codes:
            error_responses[path] = status_codes

    return error_responses


@pytest.fixture
def client():
    """FastAPI TestClient のフィクスチャ"""
    return TestClient(app)


@pytest.fixture
def error_code_catalog():
    """Error Code Catalog をパースするフィクスチャ"""
    return parse_error_code_catalog()


@pytest.fixture
def openapi_schema(client: TestClient):
    """OpenAPI スキーマを取得するフィクスチャ"""
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    return response.json()


def test_error_code_catalog_exists():
    """
    ERROR_CODE_CATALOG.md が存在することを確認
    """
    assert (
        ERROR_CODE_CATALOG_PATH.exists()
    ), f"ERROR_CODE_CATALOG.md not found at {ERROR_CODE_CATALOG_PATH}"


def test_error_code_catalog_parsable(error_code_catalog: dict[str, tuple[int, str]]):
    """
    ERROR_CODE_CATALOG.md が正しくパースできることを確認
    """
    assert len(error_code_catalog) > 0, "Error Code Catalog is empty"

    # 最低限のエラーコードが含まれていることを確認
    expected_codes = {"UNAUTHORIZED", "NOT_FOUND", "VALIDATION_ERROR", "INTERNAL_ERROR"}
    catalog_codes = set(error_code_catalog.keys())
    assert expected_codes.issubset(
        catalog_codes
    ), f"Expected error codes not found in catalog. Found: {catalog_codes}"


def test_error_code_catalog_has_required_fields(error_code_catalog: dict[str, tuple[int, str]]):
    """
    ERROR_CODE_CATALOG.md の各エラーコードに必要な情報が含まれていることを確認
    """
    for error_code, (http_status, category) in error_code_catalog.items():
        assert error_code, "Error code is empty"
        assert isinstance(http_status, int), f"HTTP status for {error_code} is not an integer"
        assert (
            400 <= http_status <= 599
        ), f"HTTP status {http_status} for {error_code} is out of range"
        assert category, f"Category for {error_code} is empty"


def test_openapi_error_responses_match_catalog(
    client: TestClient,
    error_code_catalog: dict[str, tuple[int, str]],
    openapi_schema: dict,
):
    """
    OpenAPI スキーマのエラーレスポンスがカタログに定義されたエラーコードと一致することを確認
    """
    error_responses = get_openapi_error_responses(openapi_schema)

    # カタログに定義された HTTP ステータスのセット
    catalog_statuses = {status for status, _ in error_code_catalog.values()}

    # OpenAPI に含まれるエラーレスポンスのステータスコードを収集
    openapi_statuses = set()
    for status_codes in error_responses.values():
        openapi_statuses.update(status_codes)

    # OpenAPI のエラーレスポンスがカタログに定義されていることを確認
    # （カタログにないステータスコードが OpenAPI に含まれていないことを確認）
    unknown_statuses = openapi_statuses - catalog_statuses
    # 422 は FastAPI の自動バリデーションエラーなので許容
    unknown_statuses.discard(422)
    assert not unknown_statuses, (
        f"OpenAPI schema contains error responses with status codes not in catalog: {unknown_statuses}. "
        f"Catalog statuses: {catalog_statuses}, OpenAPI statuses: {openapi_statuses}"
    )


def test_error_code_catalog_completeness(error_code_catalog: dict[str, tuple[int, str]]):
    """
    カタログに最低限必要なエラーコードが含まれていることを確認
    """
    required_codes = {
        "UNAUTHORIZED": (401, "Auth"),
        "NOT_FOUND": (404, "NotFound"),
        "VALIDATION_ERROR": (422, "Validation"),
        "INTERNAL_ERROR": (500, "Internal"),
    }

    for code, (expected_status, expected_category) in required_codes.items():
        assert code in error_code_catalog, f"Required error code {code} not found in catalog"
        actual_status, actual_category = error_code_catalog[code]
        assert (
            actual_status == expected_status
        ), f"Error code {code} has wrong HTTP status: expected {expected_status}, got {actual_status}"
        assert (
            actual_category == expected_category
        ), f"Error code {code} has wrong category: expected {expected_category}, got {actual_category}"


def test_error_code_catalog_no_duplicates(error_code_catalog: dict[str, tuple[int, str]]):
    """
    カタログに重複するエラーコードがないことを確認
    """
    error_codes = list(error_code_catalog.keys())
    unique_codes = set(error_codes)
    assert len(error_codes) == len(unique_codes), f"Duplicate error codes found: {error_codes}"


def test_error_code_catalog_status_code_consistency(error_code_catalog: dict[str, tuple[int, str]]):
    """
    カタログのエラーコードと HTTP ステータスの対応が一貫していることを確認
    """
    # 同じ HTTP ステータスコードを持つエラーコードが複数ある場合でも、
    # それぞれが適切なカテゴリに分類されていることを確認
    status_to_codes = {}
    for code, (status, category) in error_code_catalog.items():
        if status not in status_to_codes:
            status_to_codes[status] = []
        status_to_codes[status].append((code, category))

    # 各ステータスコードに対して、カテゴリが適切であることを確認
    for status, codes in status_to_codes.items():
        if status == 401:
            # 401 は認証エラーなので、Auth カテゴリである必要がある
            assert all(
                category == "Auth" for _, category in codes
            ), f"Status 401 error codes should be in Auth category: {codes}"
        elif status == 404:
            # 404 は NotFound カテゴリである必要がある
            assert all(
                category == "NotFound" for _, category in codes
            ), f"Status 404 error codes should be in NotFound category: {codes}"
        elif status == 422:
            # 422 は Validation カテゴリである必要がある
            assert all(
                category == "Validation" for _, category in codes
            ), f"Status 422 error codes should be in Validation category: {codes}"
        elif status == 500:
            # 500 は Internal カテゴリである必要がある
            assert all(
                category == "Internal" for _, category in codes
            ), f"Status 500 error codes should be in Internal category: {codes}"
