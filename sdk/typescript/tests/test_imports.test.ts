/**
 * SDK インポートと基本構造のテスト
 *
 * SDK が正しく生成され、インポート可能であることを確認する smoke test。
 * ネットワーク依存のテストは含まれません（E2E テストは別ファイル）。
 */

import { Configuration, ExecuteApi, HealthApi, ProjectsApi, RunsApi } from '../index';

describe('SDK Imports', () => {
    test('SDK パッケージが import できること', () => {
        // index.ts からエクスポートされていることを確認
        expect(Configuration).toBeDefined();
        expect(ProjectsApi).toBeDefined();
    });

    test('Configuration クラスが存在すること', () => {
        expect(Configuration).toBeDefined();
        expect(typeof Configuration).toBe('function');
    });

    test('ProjectsApi クラスが存在すること', () => {
        expect(ProjectsApi).toBeDefined();
        expect(typeof ProjectsApi).toBe('function');
    });

    test('RunsApi クラスが存在すること', () => {
        expect(RunsApi).toBeDefined();
        expect(typeof RunsApi).toBe('function');
    });

    test('ExecuteApi クラスが存在すること', () => {
        expect(ExecuteApi).toBeDefined();
        expect(typeof ExecuteApi).toBe('function');
    });

    test('HealthApi クラスが存在すること', () => {
        expect(HealthApi).toBeDefined();
        expect(typeof HealthApi).toBe('function');
    });

    test('Configuration をインスタンス化できること', () => {
        const config = new Configuration({
            basePath: 'http://localhost:8000',
        });
        expect(config).toBeDefined();
        expect(config.basePath).toBe('http://localhost:8000');
    });

    test('ProjectsApi をインスタンス化できること', () => {
        const config = new Configuration({
            basePath: 'http://localhost:8000',
        });
        const api = new ProjectsApi(config);
        expect(api).toBeDefined();
        expect(api).toBeInstanceOf(ProjectsApi);
    });

    test('RunsApi をインスタンス化できること', () => {
        const config = new Configuration({
            basePath: 'http://localhost:8000',
        });
        const api = new RunsApi(config);
        expect(api).toBeDefined();
        expect(api).toBeInstanceOf(RunsApi);
    });

    test('ExecuteApi をインスタンス化できること', () => {
        const config = new Configuration({
            basePath: 'http://localhost:8000',
        });
        const api = new ExecuteApi(config);
        expect(api).toBeDefined();
        expect(api).toBeInstanceOf(ExecuteApi);
    });
});

