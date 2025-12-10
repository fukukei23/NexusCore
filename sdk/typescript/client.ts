/**
 * NexusCore API クライアント
 *
 * 商品レベルの TypeScript SDK のメインエントリーポイントです。
 * API key 認証を内部で処理し、型安全な API メソッドを提供します。
 */

import {
    ExecuteApi,
    HealthApi,
    ProjectsApi,
    RunsApi,
    type ExecuteRequest,
    type ExecuteResponse,
    type ExecuteStatusResponse,
    type LatestRunDetail,
    type ProjectResponse,
    type ProjectSummary,
    type RunSummary,
} from './api';
import { Configuration } from './configuration';
import { NexusCoreApiError, extractErrorFromResponse } from './errors';

/**
 * NexusCore クライアント設定
 */
export interface NexusCoreClientConfig {
    /**
     * API のベース URL
     * デフォルト: "http://localhost:8000"
     */
    baseUrl?: string;

    /**
     * API Key（必須）
     * X-API-Key ヘッダーとして自動的に設定されます。
     */
    apiKey: string;

    /**
     * リクエストタイムアウト（ミリ秒）
     * デフォルト: 30000 (30秒)
     */
    timeout?: number;
}

/**
 * NexusCore API クライアント
 *
 * 使用例:
 * ```typescript
 * const client = new NexusCoreClient({
 *   baseUrl: 'https://api.nexuscore.example.com',
 *   apiKey: 'nexus_xxx...'
 * });
 *
 * const projects = await client.listProjects();
 * ```
 */
export class NexusCoreClient {
    private readonly config: Required<Pick<NexusCoreClientConfig, 'baseUrl' | 'timeout'>> &
        Pick<NexusCoreClientConfig, 'apiKey'>;
    private readonly configuration: Configuration;
    private readonly projectsApi: ProjectsApi;
    private readonly runsApi: RunsApi;
    private readonly executeApi: ExecuteApi;
    private readonly healthApi: HealthApi;

    constructor(config: NexusCoreClientConfig) {
        if (!config.apiKey) {
            throw new Error('apiKey is required');
        }

        this.config = {
            baseUrl: config.baseUrl || 'http://localhost:8000',
            apiKey: config.apiKey,
            timeout: config.timeout || 30000,
        };

        // Configuration を作成（API key を設定）
        this.configuration = new Configuration({
            basePath: this.config.baseUrl,
            apiKey: this.config.apiKey,
            baseOptions: {
                timeout: this.config.timeout,
            },
        });

        // API インスタンスを作成
        this.projectsApi = new ProjectsApi(this.configuration);
        this.runsApi = new RunsApi(this.configuration);
        this.executeApi = new ExecuteApi(this.configuration);
        this.healthApi = new HealthApi(this.configuration);
    }

    /**
     * ヘルスチェック
     *
     * @returns ヘルスチェック結果
     * @throws {NexusCoreApiError} API エラー時
     */
    async healthCheck(): Promise<{ status: string }> {
        try {
            const response = await this.healthApi.healthCheckApiV1HealthGet();
            return { status: response.data.status || 'ok' };
        } catch (error: unknown) {
            throw this.handleError(error);
        }
    }

    /**
     * プロジェクト一覧を取得
     *
     * @returns プロジェクト一覧
     * @throws {NexusCoreApiError} API エラー時
     */
    async listProjects(): Promise<ProjectSummary[]> {
        try {
            const response = await this.projectsApi.listProjectsApiV1ProjectsGet(
                this.config.apiKey,
                {}
            );
            return response.data.projects || [];
        } catch (error: unknown) {
            throw this.handleError(error);
        }
    }

    /**
     * プロジェクトを取得
     *
     * @param projectId プロジェクト ID
     * @returns プロジェクト詳細
     * @throws {NexusCoreApiError} API エラー時
     */
    async getProject(projectId: number): Promise<ProjectResponse> {
        try {
            const response = await this.projectsApi.getProjectApiV1ProjectsProjectIdGet(
                projectId,
                this.config.apiKey,
                {}
            );
            return response.data;
        } catch (error: unknown) {
            throw this.handleError(error);
        }
    }

    /**
     * プロジェクトの最新 Run を取得
     *
     * @param projectId プロジェクト ID
     * @returns 最新 Run の詳細（存在しない場合は null）
     * @throws {NexusCoreApiError} API エラー時
     */
    async getLatestRun(projectId: number): Promise<LatestRunDetail | null> {
        try {
            const response =
                await this.projectsApi.getLatestRunApiV1ProjectsProjectIdRunsLatestGet(
                    projectId,
                    this.config.apiKey,
                    {}
                );
            return response.data.run ?? null;
        } catch (error: unknown) {
            throw this.handleError(error);
        }
    }

    /**
     * プロジェクトの Run を実行
     *
     * @param projectId プロジェクト ID
     * @param request 実行リクエスト
     * @returns 実行レスポンス
     * @throws {NexusCoreApiError} API エラー時
     */
    async triggerProjectRun(
        projectId: number,
        request: {
            requirement: string;
            autonomy_level?: number;
            fast_lane?: boolean;
        }
    ): Promise<{
        run_id: string;
        project_id: number;
        status: string;
        queue_mode: string;
    }> {
        try {
            const response = await this.projectsApi.triggerProjectRunApiV1ProjectsProjectIdRunPost(
                projectId,
                this.config.apiKey,
                request,
                {}
            );
            return response.data;
        } catch (error: unknown) {
            throw this.handleError(error);
        }
    }

    /**
     * Run 一覧を取得
     *
     * @param projectId プロジェクト ID でフィルタ（オプション）
     * @returns Run 一覧
     * @throws {NexusCoreApiError} API エラー時
     */
    async listRuns(projectId?: number | null): Promise<RunSummary[]> {
        try {
            const response = await this.runsApi.listRunsApiV1RunsGet(
                this.config.apiKey,
                projectId,
                {}
            );
            return response.data.runs || [];
        } catch (error: unknown) {
            throw this.handleError(error);
        }
    }

    /**
     * Run を取得
     *
     * @param runId Run ID
     * @returns Run 詳細
     * @throws {NexusCoreApiError} API エラー時
     */
    async getRun(runId: string): Promise<RunSummary> {
        try {
            const response = await this.runsApi.getRunApiV1RunsRunIdGet(
                runId,
                this.config.apiKey,
                {}
            );
            return response.data;
        } catch (error: unknown) {
            throw this.handleError(error);
        }
    }

    /**
     * Self-Healing ジョブを実行
     *
     * @param request 実行リクエスト
     * @returns 実行レスポンス
     * @throws {NexusCoreApiError} API エラー時
     */
    async execute(request: ExecuteRequest): Promise<ExecuteResponse> {
        try {
            const response = await this.executeApi.executeEndpointApiV1ExecutePost(
                this.config.apiKey,
                request,
                {}
            );
            return response.data;
        } catch (error: unknown) {
            throw this.handleError(error);
        }
    }

    /**
     * タスクステータスを取得
     *
     * @param taskId タスク ID
     * @returns ステータスレスポンス
     * @throws {NexusCoreApiError} API エラー時
     */
    async getTaskStatus(taskId: string): Promise<ExecuteStatusResponse> {
        try {
            const response = await this.executeApi.getTaskStatusApiV1StatusTaskIdGet(
                taskId,
                this.config.apiKey,
                {}
            );
            return response.data;
        } catch (error: unknown) {
            throw this.handleError(error);
        }
    }

    /**
     * エラーを処理して NexusCoreApiError に変換
     *
     * @param error 元のエラー
     * @returns NexusCoreApiError インスタンス
     */
    private handleError(error: unknown): NexusCoreApiError {
        // Axios エラーで response がある場合（HTTP エラー）
        if (
            typeof error === 'object' &&
            error !== null &&
            'response' in error &&
            typeof (error as { response: unknown }).response === 'object' &&
            (error as { response: unknown }).response !== null
        ) {
            const axiosError = error as {
                response: {
                    status: number;
                    data: unknown;
                };
            };
            return extractErrorFromResponse(
                axiosError.response.status,
                axiosError.response.data
            );
        }

        // Axios エラーで request があるが response がない場合（ネットワークエラー）
        if (
            typeof error === 'object' &&
            error !== null &&
            'request' in error &&
            'code' in error &&
            typeof (error as { code: unknown }).code === 'string'
        ) {
            const networkError = error as {
                code: string;
                message?: string;
            };
            // ネットワークエラーはそのまま再スロー（テストで早期リターンできるように）
            // ただし、NexusCoreApiError として統一するため、status 0 で返す
            const errorMessage = networkError.message || `Network error: ${networkError.code}`;
            return new NexusCoreApiError(
                0,
                errorMessage,
                networkError.code,
                error
            );
        }

        // その他のエラー
        if (error instanceof Error) {
            return new NexusCoreApiError(0, error.message, undefined, error);
        }

        return new NexusCoreApiError(0, 'Unknown error', undefined, error);
    }
}
