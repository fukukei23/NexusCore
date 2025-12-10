# NexusCore TypeScript SDK

**Version**: 0.1.0
**License**: MIT

NexusCore API の公式 TypeScript SDK です。型安全な API クライアントを提供し、API key 認証を内部で処理します。

## インストール

### npm からインストール（公開後）

```bash
npm install @nexuscore/sdk
```

### ローカルパスからインストール（開発中）

```bash
npm install /path/to/NexusCore/sdk/typescript
```

## クイックスタート

### 基本的な使用例

```typescript
import { NexusCoreClient } from '@nexuscore/sdk';

// クライアントを作成
const client = new NexusCoreClient({
  baseUrl: 'https://api.nexuscore.example.com',
  apiKey: 'nexus_xxx...' // 必須
});

// プロジェクト一覧を取得
const projects = await client.listProjects();
console.log(`Found ${projects.length} projects`);

// プロジェクトの詳細を取得
const project = await client.getProject(1);
console.log(`Project: ${project.name}`);

// Self-Healing ジョブを実行
const response = await client.execute({
  requirement: 'Fix failing tests',
  autonomy_level: 2,
  fast_lane: true
});
console.log(`Task ID: ${response.task_id}`);
```

## 認証設定

### API Key の取得

API Key は以下の方法で取得できます：

1. **初回発行（ブートストラップ CLI）**:
   ```bash
   python -m nexuscore.cli.bootstrap_apikey \
     --user-login dev \
     --key-name "Local Dev Key"
   ```

2. **API 経由で発行**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/api-keys \
     -H "X-API-Key: existing-api-key" \
     -H "Content-Type: application/json" \
     -d '{"name": "New Key"}'
   ```

詳細は [CR-FASTAPI-021 完了レポート](../../docs/api/CR-FASTAPI-021_COMPLETION_REPORT.md) を参照してください。

### クライアント設定

```typescript
const client = new NexusCoreClient({
  baseUrl: 'https://api.nexuscore.example.com', // デフォルト: http://localhost:8000
  apiKey: 'nexus_xxx...',                        // 必須
  timeout: 30000,                                // デフォルト: 30000ms (30秒)
  fetch: customFetch                             // オプション: カスタム fetch 実装
});
```

## API メソッド

### プロジェクト関連

```typescript
// プロジェクト一覧を取得
const projects: ProjectSummary[] = await client.listProjects();

// プロジェクトを取得
const project: ProjectSummary = await client.getProject(projectId);

// プロジェクトの最新 Run を取得
const run: RunSummary = await client.getLatestRun(projectId);

// プロジェクトの Run を実行
const response: ExecuteResponse = await client.triggerProjectRun(projectId, {
  requirement: 'Fix bugs',
  autonomy_level: 2,
  fast_lane: true
});
```

### Run 関連

```typescript
// Run 一覧を取得
const runs: RunSummary[] = await client.listRuns(limit, offset);

// Run を取得
const run: RunSummary = await client.getRun(runId);
```

### Self-Healing 実行

```typescript
// Self-Healing ジョブを実行
const response: ExecuteResponse = await client.execute({
  requirement: 'Fix failing tests',
  autonomy_level: 2,
  fast_lane: true
});

// タスクステータスを取得
const status: ExecuteStatusResponse = await client.getTaskStatus(response.task_id);
```

### ヘルスチェック

```typescript
// ヘルスチェック
const health = await client.healthCheck();
console.log(`Status: ${health.status}`);
```

## エラーハンドリング

SDK は Error Code Catalog に準拠したエラーハンドリングを提供します。

### エラーの種類

```typescript
import { NexusCoreApiError } from '@nexuscore/sdk';

try {
  await client.listProjects();
} catch (error) {
  if (error instanceof NexusCoreApiError) {
    // HTTP ステータスコード
    console.log(`Status: ${error.status}`);

    // エラーコード（Error Code Catalog の ID）
    console.log(`Code: ${error.code}`);

    // エラーメッセージ
    console.log(`Message: ${error.message}`);

    // エラー詳細
    console.log(`Details:`, error.details);

    // 便利な判定メソッド
    if (error.isUnauthorized()) {
      console.log('認証エラー: API Key が無効です');
    } else if (error.isNotFound()) {
      console.log('リソースが見つかりません');
    } else if (error.isValidationError()) {
      console.log('バリデーションエラー: リクエストパラメータを確認してください');
    } else if (error.isServerError()) {
      console.log('サーバーエラー: しばらく待ってから再試行してください');
    }
  } else {
    // その他のエラー（ネットワークエラーなど）
    console.error('Unexpected error:', error);
  }
}
```

### Error Code Catalog

すべてのエラーコードは [Error Code Catalog](../../docs/api/ERROR_CODE_CATALOG.md) に定義されています。

主なエラーコード：

- `UNAUTHORIZED` (401): API Key が無効または欠如
- `FORBIDDEN` (403): 権限なし
- `NOT_FOUND` (404): リソースが見つからない
- `VALIDATION_ERROR` (422): バリデーションエラー
- `INTERNAL_ERROR` (500): サーバー内部エラー

## 型定義

SDK は完全に型安全です。すべての API メソッドは TypeScript の型定義を提供します。

```typescript
import type {
  ProjectSummary,
  RunSummary,
  ExecuteRequest,
  ExecuteResponse,
  ExecuteStatusResponse,
} from '@nexuscore/sdk';
```

## 環境変数

E2E テスト実行時は、以下の環境変数を設定してください：

- `FASTAPI_BASE_URL`: FastAPI サーバーのベース URL（デフォルト: `http://localhost:8000`）
- `NEXUSCORE_API_KEY`: API Key（既に設定されている場合）
- `NEXUSCORE_BOOTSTRAP_API_KEY`: ブートストラップ API Key（自動発行用）

詳細は [CR-FASTAPI-022 完了レポート](../../docs/api/CR-FASTAPI-022_COMPLETION_REPORT.md) を参照してください。

## CI での使用

GitHub Actions では、`.github/workflows/ts-e2e.yml` が自動的に bootstrap API Key を生成し、E2E テストを実行します。

詳細は [CR-FASTAPI-023 完了レポート](../../docs/api/CR-FASTAPI-023_COMPLETION_REPORT.md) を参照してください。

## 開発

### ビルド

```bash
npm install
npm run build
```

### テスト

```bash
# すべてのテストを実行
npm test

# インポートテストのみ
npm test -- tests/test_imports.test.ts

# E2E テストのみ（FastAPI サーバー起動が必要）
npm test -- tests/test_projects_e2e.test.ts
```

### 型チェック

```bash
npx tsc --noEmit
```

## ライセンス

MIT License - 詳細は [LICENSE](./LICENSE) を参照してください。

## 関連ドキュメント

- [FastAPI API ドキュメント](../../docs/api/README.md)
- [Error Code Catalog](../../docs/api/ERROR_CODE_CATALOG.md)
- [CR-FASTAPI-019 完了レポート](../../docs/api/CR-FASTAPI-019_COMPLETION_REPORT.md)
