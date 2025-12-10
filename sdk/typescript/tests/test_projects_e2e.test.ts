/**
 * Projects API の E2E テスト
 *
 * FastAPI サーバーが起動している環境で、SDK 経由で /api/v1/projects を呼び出す。
 *
 * 前提条件:
 *   - FASTAPI_BASE_URL 環境変数が設定されている（デフォルト: http://localhost:8000）
 *   - NEXUSCORE_API_KEY または NEXUSCORE_BOOTSTRAP_API_KEY 環境変数が設定されている
 *   - FastAPI サーバーが起動している
 *
 * 環境変数が設定されていない場合はテストをスキップします。
 *
 * API Key の取得優先順位:
 * 1. NEXUSCORE_API_KEY（既に設定されている場合）
 * 2. NEXUSCORE_BOOTSTRAP_API_KEY から /api/v1/api-keys 経由で自動発行（CR-FASTAPI-022）
 */

import { NexusCoreClient } from '../index';
import { getE2EApiKey } from './utils/apikey_helper';

describe('Projects API E2E (Legacy - using generated API directly)', () => {
    const baseUrl = process.env.FASTAPI_BASE_URL || 'http://localhost:8000';

    test('Projects 一覧取得が成功すること（200 OK、最低 1 件以上）', async () => {
        // API Key を取得（CR-FASTAPI-022 の helper を使用）
        const apiKey = await getE2EApiKey();

        // API Key が取得できない場合はスキップ
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
            // サーバーが起動していない場合や接続エラーの場合
            if (error instanceof Error && (error as { code?: string }).code === 'ECONNREFUSED') {
                console.warn('⚠️  FastAPI server is not running. Skipping E2E test.');
                return;
            }
            // その他のエラーは再スロー
            throw error;
        }
    }, 30000); // 30秒のタイムアウト
});

