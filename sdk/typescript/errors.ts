/**
 * NexusCore API エラーハンドリング
 *
 * Error Code Catalog に準拠したエラー型を提供します。
 * @see https://github.com/nexuscore/docs/api/ERROR_CODE_CATALOG.md
 */

/**
 * NexusCore API エラー
 *
 * 非 2xx レスポンスをマッピングしたエラー型です。
 */
export class NexusCoreApiError extends Error {
    /**
     * HTTP ステータスコード
     */
    public readonly status: number;

    /**
     * エラーコード（Error Code Catalog の ID）
     * 例: "UNAUTHORIZED", "NOT_FOUND", "INTERNAL_ERROR"
     */
    public readonly code?: string;

    /**
     * エラーメッセージ
     */
    public readonly message: string;

    /**
     * エラー詳細（オプション）
     */
    public readonly details?: unknown;

    constructor(
        status: number,
        message: string,
        code?: string,
        details?: unknown
    ) {
        super(message);
        this.name = 'NexusCoreApiError';
        this.status = status;
        this.code = code;
        this.message = message;
        this.details = details;

        // TypeScript の Error クラスのプロトタイプチェーンを維持
        Object.setPrototypeOf(this, NexusCoreApiError.prototype);
    }

    /**
     * エラーが認証エラー（401）かどうかを判定
     */
    public isUnauthorized(): boolean {
        return this.status === 401;
    }

    /**
     * エラーが権限エラー（403）かどうかを判定
     */
    public isForbidden(): boolean {
        return this.status === 403;
    }

    /**
     * エラーがリソース未検出（404）かどうかを判定
     */
    public isNotFound(): boolean {
        return this.status === 404;
    }

    /**
     * エラーがバリデーションエラー（422）かどうかを判定
     */
    public isValidationError(): boolean {
        return this.status === 422;
    }

    /**
     * エラーがサーバーエラー（500以上）かどうかを判定
     */
    public isServerError(): boolean {
        return this.status >= 500;
    }
}

/**
 * API レスポンスからエラーを抽出
 *
 * @param status HTTP ステータスコード
 * @param data レスポンスボディ（ErrorResponse 形式を想定）
 * @returns NexusCoreApiError インスタンス
 */
export function extractErrorFromResponse(
    status: number,
    data: unknown
): NexusCoreApiError {
    // FastAPI の ErrorResponse 形式を想定: { detail: { error: { code: string, message: string } } }
    if (
        typeof data === 'object' &&
        data !== null &&
        'detail' in data &&
        typeof (data as { detail: unknown }).detail === 'object' &&
        (data as { detail: unknown }).detail !== null
    ) {
        const detail = (data as { detail: unknown }).detail;

        // detail が ErrorResponse 形式の場合: { error: { code, message } }
        if (
            typeof detail === 'object' &&
            detail !== null &&
            'error' in detail &&
            typeof (detail as { error: unknown }).error === 'object' &&
            (detail as { error: unknown }).error !== null
        ) {
            const errorObj = (detail as { error: Record<string, unknown> }).error;
            const code = typeof errorObj.code === 'string' ? errorObj.code : undefined;
            const message =
                typeof errorObj.message === 'string'
                    ? errorObj.message
                    : `HTTP ${status} Error`;
            return new NexusCoreApiError(status, message, code, errorObj);
        }

        // detail が文字列の場合（FastAPI のシンプルなエラー形式）
        if (typeof detail === 'string') {
            return new NexusCoreApiError(status, detail, undefined, { detail });
        }
    }

    // 直接 error キーがある場合（下位互換性）
    if (
        typeof data === 'object' &&
        data !== null &&
        'error' in data &&
        typeof (data as { error: unknown }).error === 'object' &&
        (data as { error: unknown }).error !== null
    ) {
        const errorObj = (data as { error: Record<string, unknown> }).error;
        const code = typeof errorObj.code === 'string' ? errorObj.code : undefined;
        const message =
            typeof errorObj.message === 'string'
                ? errorObj.message
                : `HTTP ${status} Error`;
        return new NexusCoreApiError(status, message, code, errorObj);
    }

    // フォールバック: エラー形式が不明な場合
    const message =
        typeof data === 'object' && data !== null && 'message' in data
            ? String((data as { message: unknown }).message)
            : `HTTP ${status} Error`;
    return new NexusCoreApiError(status, message, undefined, data);
}

