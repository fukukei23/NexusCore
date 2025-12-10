/**
 * NexusCoreClient の E2E テスト
 *
 * 商品レベルの SDK クライアントを使用した E2E テストです。
 *
 * 前提条件:
 *   - FASTAPI_BASE_URL 環境変数が設定されている（デフォルト: http://localhost:8000）
 *   - NEXUSCORE_API_KEY または NEXUSCORE_BOOTSTRAP_API_KEY 環境変数が設定されている
 *   - FastAPI サーバーが起動している
 */

import { NexusCoreClient, NexusCoreApiError } from '../index';
import { getE2EApiKey } from './utils/apikey_helper';

describe('NexusCoreClient E2E', () => {
    const baseUrl = process.env.FASTAPI_BASE_URL || 'http://localhost:8000';

    test('NexusCoreClient でプロジェクト一覧を取得できること', async () => {
        const apiKey = await getE2EApiKey();
        if (!apiKey) {
            console.warn('⚠️  NEXUSCORE_API_KEY or NEXUSCORE_BOOTSTRAP_API_KEY is not set. Skipping E2E test.');
            return;
        }

        const client = new NexusCoreClient({
            baseUrl,
            apiKey,
        });

        try {
            const projects = await client.listProjects();

            expect(Array.isArray(projects)).toBe(true);
            expect(projects.length).toBeGreaterThanOrEqual(0);
        } catch (error: unknown) {
            if (error instanceof Error && (error as { code?: string }).code === 'ECONNREFUSED') {
                console.warn('⚠️  FastAPI server is not running. Skipping E2E test.');
                return;
            }
            throw error;
        }
    }, 30000);

    test('無効な API Key でエラーが発生すること（401 Unauthorized）', async () => {
        const client = new NexusCoreClient({
            baseUrl,
            apiKey: 'invalid-api-key-12345',
        });

        try {
            await client.listProjects();
            // エラーが発生しない場合は失敗
            fail('Expected NexusCoreApiError to be thrown');
        } catch (error: unknown) {
            // ネットワークエラーの場合はスキップ
            if (error instanceof NexusCoreApiError) {
                // status 0 はネットワークエラーを示す
                if (error.status === 0) {
                    // details から code を取得
                    const details = error.details as { code?: string } | undefined;
                    if (details?.code === 'ECONNREFUSED' || error.code === 'ECONNREFUSED') {
                        console.warn('⚠️  FastAPI server is not running. Skipping E2E test.');
                        return;
                    }
                }
            }

            // その他のネットワークエラーもスキップ（NexusCoreApiError に変換される前）
            if (error instanceof Error && (error as { code?: string }).code === 'ECONNREFUSED') {
                console.warn('⚠️  FastAPI server is not running. Skipping E2E test.');
                return;
            }

            expect(error).toBeInstanceOf(NexusCoreApiError);
            const apiError = error as NexusCoreApiError;

            // デバッグ用: エラー情報を出力（ネットワークエラーでない場合のみ）
            if (apiError.status !== 0 && !apiError.isUnauthorized()) {
                console.error('Error details:', {
                    status: apiError.status,
                    code: apiError.code,
                    message: apiError.message,
                    details: apiError.details,
                });
            }

            expect(apiError.isUnauthorized()).toBe(true);
            expect(apiError.status).toBe(401);
            expect(apiError.code).toBe('UNAUTHORIZED');
        }
    }, 30000);

    test('存在しないプロジェクト ID でエラーが発生すること（404 Not Found）', async () => {
        const apiKey = await getE2EApiKey();
        if (!apiKey) {
            console.warn('⚠️  NEXUSCORE_API_KEY or NEXUSCORE_BOOTSTRAP_API_KEY is not set. Skipping E2E test.');
            return;
        }

        const client = new NexusCoreClient({
            baseUrl,
            apiKey,
        });

        try {
            await client.getProject(999999); // 存在しない ID
            fail('Expected NexusCoreApiError to be thrown');
        } catch (error: unknown) {
            if (error instanceof Error && (error as { code?: string }).code === 'ECONNREFUSED') {
                console.warn('⚠️  FastAPI server is not running. Skipping E2E test.');
                return;
            }

            expect(error).toBeInstanceOf(NexusCoreApiError);
            const apiError = error as NexusCoreApiError;
            expect(apiError.isNotFound()).toBe(true);
            expect(apiError.status).toBe(404);
            expect(apiError.code).toBe('NOT_FOUND');
        }
    }, 30000);
});

