"""
エラーハンドリングユーティリティ

FastAPI 全 API で統一されたエラー形式を提供する。

エラーコードの仕様:
- すべてのエラーコードは `docs/api/ERROR_CODE_CATALOG.md` に定義されている必要があります
- 新しいエラーコードを追加する場合は、必ず ERROR_CODE_CATALOG.md にも追記してください
- ERROR_CODE_CATALOG.md がエラーコードの単一のソース（Single Source of Truth）です

詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
"""
from fastapi import HTTPException, status

from ..schemas.error import ErrorResponse, ErrorDetail


def make_error(status_code: int, code: str, message: str) -> HTTPException:
    """
    統一されたエラーレスポンスを生成する

    すべての FastAPI エンドポイントで使用する標準的なエラーレスポンスを生成する。
    ErrorResponse モデルに準拠した構造でエラーを返す。

    Args:
        status_code: HTTP ステータスコード（400, 401, 404, 500 など）
        code: エラーコード（例: "NOT_FOUND", "VALIDATION_ERROR", "UNAUTHORIZED"）
            - すべてのエラーコードは `docs/api/ERROR_CODE_CATALOG.md` に定義されている必要があります
            - 詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください
        message: ユーザー向けのエラーメッセージ

    Returns:
        HTTPException: FastAPI の HTTPException（detail に ErrorResponse を含む）

    Example:
        ```python
        raise make_error(404, "NOT_FOUND", "Project not found")
        ```

    Note:
        詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
    """
    error_response = ErrorResponse(
        error=ErrorDetail(code=code, message=message)
    )
    return HTTPException(
        status_code=status_code,
        detail=error_response.model_dump(),
    )


# よく使用されるエラーのショートカット関数
# 詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。

def make_not_found_error(resource: str, resource_id: str) -> HTTPException:
    """
    リソースが見つからない場合のエラーを生成

    Args:
        resource: リソース名（例: "Project", "Run"）
        resource_id: リソースID

    Returns:
        HTTPException: 404 エラー（error.code: "NOT_FOUND"）

    Note:
        詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
    """
    return make_error(
        status_code=status.HTTP_404_NOT_FOUND,
        code="NOT_FOUND",
        message=f"{resource} with id {resource_id} not found",
    )


def make_unauthorized_error(message: str = "Invalid or missing API key") -> HTTPException:
    """
    認証エラーを生成

    Args:
        message: エラーメッセージ（デフォルト: "Invalid or missing API key"）

    Returns:
        HTTPException: 401 エラー（error.code: "UNAUTHORIZED"）

    Note:
        詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
    """
    return make_error(
        status_code=status.HTTP_401_UNAUTHORIZED,
        code="UNAUTHORIZED",
        message=message,
    )


def make_validation_error(message: str) -> HTTPException:
    """
    バリデーションエラーを生成

    Args:
        message: エラーメッセージ

    Returns:
        HTTPException: 422 エラー（error.code: "VALIDATION_ERROR"）

    Note:
        詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
    """
    return make_error(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="VALIDATION_ERROR",
        message=message,
    )


def make_internal_error(message: str = "Internal server error") -> HTTPException:
    """
    内部サーバーエラーを生成

    Args:
        message: エラーメッセージ（デフォルト: "Internal server error"）

    Returns:
        HTTPException: 500 エラー（error.code: "INTERNAL_ERROR"）

    Note:
        - 認証フェイルでは使用しない（認証フェイルは必ず 401 を返す）
        - 詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
    """
    return make_error(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_ERROR",
        message=message,
    )


def make_bad_request_error(message: str) -> HTTPException:
    """
    不正リクエストエラーを生成

    Args:
        message: エラーメッセージ

    Returns:
        HTTPException: 400 エラー（error.code: "INVALID_REQUEST"）

    Note:
        詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
    """
    return make_error(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="INVALID_REQUEST",
        message=message,
    )


def make_forbidden_error(message: str = "Forbidden") -> HTTPException:
    """
    権限エラーを生成

    Args:
        message: エラーメッセージ（デフォルト: "Forbidden"）

    Returns:
        HTTPException: 403 エラー（error.code: "FORBIDDEN"）

    Note:
        詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
    """
    return make_error(
        status_code=status.HTTP_403_FORBIDDEN,
        code="FORBIDDEN",
        message=message,
    )


def make_conflict_error(message: str) -> HTTPException:
    """
    競合エラーを生成

    Args:
        message: エラーメッセージ

    Returns:
        HTTPException: 409 エラー（error.code: "CONFLICT"）

    Note:
        詳細なエラーコード仕様は `docs/api/ERROR_CODE_CATALOG.md` を参照してください。
    """
    return make_error(
        status_code=status.HTTP_409_CONFLICT,
        code="CONFLICT",
        message=message,
    )

