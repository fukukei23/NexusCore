/**
 * E2E テスト用 API Key ヘルパー
 *
 * CR-FASTAPI-022 で作成された TypeScript SDK E2E テスト用の API Key 自動発行ヘルパー。
 *
 * 使用方法:
 *   const apiKey = await getE2EApiKey();
 *   if (!apiKey) {
 *     // API Key が取得できない場合はテストをスキップ
 *     return;
 *   }
 */

import axios, { AxiosError } from 'axios';

/**
 * E2E テスト用の API Key を取得する
 *
 * 優先順位:
 * 1. NEXUSCORE_API_KEY 環境変数（既に設定されている場合）
 * 2. NEXUSCORE_BOOTSTRAP_API_KEY 環境変数から /api/v1/api-keys 経由で発行
 * 3. どちらもない場合は null を返す（テストをスキップ）
 *
 * @returns API Key 文字列、または null（取得できない場合）
 */
export async function getE2EApiKey(): Promise<string | null> {
    // 1. NEXUSCORE_API_KEY が既に設定されている場合はそれを使用
    const existingApiKey = process.env.NEXUSCORE_API_KEY;
    if (existingApiKey && existingApiKey !== 'your-api-key-here') {
        return existingApiKey;
    }

    // 2. NEXUSCORE_BOOTSTRAP_API_KEY を確認
    const bootstrapApiKey = process.env.NEXUSCORE_BOOTSTRAP_API_KEY;
    if (!bootstrapApiKey || bootstrapApiKey === 'your-api-key-here') {
        // どちらもない場合は null を返す（テストをスキップ）
        return null;
    }

    // 3. Bootstrap API Key を使用して新しい API Key を発行
    const baseUrl = process.env.FASTAPI_BASE_URL || 'http://localhost:8000';
    const apiKeysUrl = `${baseUrl}/api/v1/api-keys`;

    try {
        const response = await axios.post(
            apiKeysUrl,
            {
                name: 'TS E2E Key',
            },
            {
                headers: {
                    'X-API-Key': bootstrapApiKey,
                    'Content-Type': 'application/json',
                },
                timeout: 10000, // 10秒のタイムアウト
            }
        );

        // レスポンスから token を取得
        if (response.status === 201 && response.data && response.data.token) {
            const newApiKey = response.data.token as string;

            // プロセス内で再利用できるように環境変数にも設定
            process.env.NEXUSCORE_API_KEY = newApiKey;

            return newApiKey;
        } else {
            console.warn('⚠️  Failed to get API key from response:', response.data);
            return null;
        }
    } catch (error) {
        if (axios.isAxiosError(error)) {
            const axiosError = error as AxiosError;
            // サーバーが起動していない場合や接続エラーの場合
            if (axiosError.code === 'ECONNREFUSED' || axiosError.message?.includes('connect')) {
                console.warn('⚠️  FastAPI server is not running. Cannot issue API key.');
                return null;
            }
            // 認証エラー（401）の場合
            if (axiosError.response?.status === 401) {
                console.warn('⚠️  Bootstrap API Key is invalid. Cannot issue API key.');
                return null;
            }
            // その他のエラー
            console.warn(`⚠️  Failed to issue API key: ${axiosError.message}`);
            if (axiosError.response?.data) {
                console.warn('   Response:', JSON.stringify(axiosError.response.data, null, 2));
            }
        } else {
            console.warn(`⚠️  Unexpected error while issuing API key: ${error}`);
        }
        return null;
    }
}

