# TypeScript SDK テスト実行ガイド

## 概要

TypeScript SDK のテストを実行する方法を説明します。

## 前提条件

1. **Node.js がインストールされていること**
   ```bash
   node --version  # v18 以上推奨
   npm --version   # v9 以上推奨
   ```

2. **TypeScript SDK が生成されていること**
   ```bash
   make sdk-ts
   ```

3. **FastAPI サーバーが起動していること（E2E テストの場合）**
   ```bash
   make server
   # または
   bash scripts/start_fastapi_server.sh
   ```

## テストの種類

### 1. インポートテスト（Import Tests）

SDK が正しく生成され、インポート可能であることを確認する smoke test。

**実行方法**:
```bash
cd sdk/typescript
npm install
npm test -- test_imports.test.ts
```

**内容**:
- SDK パッケージのインポート確認
- API クライアントクラスの存在確認
- 型定義のインポート確認
- インスタンス化の確認

### 2. E2E テスト（End-to-End Tests）

実際の FastAPI サーバーに対して SDK 経由で API を呼び出すテスト。

**実行方法**:
```bash
cd sdk/typescript

# 環境変数を設定
export FASTAPI_BASE_URL="http://localhost:8000"
export NEXUSCORE_API_KEY="your-api-key-here"

# E2E テストを実行
npm test -- test_projects_e2e.test.ts
```

**注意**: 環境変数が設定されていない場合は、テストは自動的にスキップされます。

## セットアップ手順

### Step 1: SDK を生成

```bash
# プロジェクトルートから
make sdk-ts
```

### Step 2: 依存関係をインストール

```bash
cd sdk/typescript
npm install
```

### Step 3: テストを実行

```bash
# すべてのテストを実行
npm test

# 特定のテストファイルだけ実行
npm test -- test_imports.test.ts
npm test -- test_projects_e2e.test.ts

# ウォッチモード（ファイル変更時に自動再実行）
npm run test:watch

# カバレッジ付きで実行
npm run test:coverage
```

## Makefile を使用した実行

プロジェクトルートから直接実行できます：

```bash
# TypeScript SDK のテストを実行
make sdk-ts-test
```

このコマンドは以下を自動的に実行します：
1. `cd sdk/typescript`
2. `npm install`（必要に応じて）
3. `npm test`

## E2E テストの環境変数

E2E テストを実行するには、以下の環境変数を設定してください：

| 環境変数 | 説明 | デフォルト値 | 必須 |
|---------|------|------------|------|
| `FASTAPI_BASE_URL` | FastAPI サーバーのベース URL | `http://localhost:8000` | 任意 |
| `NEXUSCORE_API_KEY` | API Key（認証用） | - | **必須** |

**設定例**:
```bash
export FASTAPI_BASE_URL="http://localhost:8000"
export NEXUSCORE_API_KEY="your-actual-api-key"
```

## テストファイルの構造

```
sdk/typescript/
├── tests/
│   ├── test_imports.test.ts      # インポートテスト
│   └── test_projects_e2e.test.ts  # E2E テスト
├── examples/
│   └── basic_usage.ts            # 使用例（テストではない）
├── package.json                  # 依存関係とスクリプト
├── jest.config.js                # Jest 設定
└── tsconfig.json                 # TypeScript 設定
```

## トラブルシューティング

### エラー: "Cannot find module"

SDK が生成されていない可能性があります：

```bash
# SDK を再生成
make sdk-ts

# 依存関係を再インストール
cd sdk/typescript
rm -rf node_modules package-lock.json
npm install
```

### エラー: "ECONNREFUSED"（E2E テスト）

FastAPI サーバーが起動していない可能性があります：

```bash
# 別のターミナルでサーバーを起動
make server

# または
bash scripts/start_fastapi_server.sh
```

### エラー: "401 Unauthorized"（E2E テスト）

API Key が設定されていないか、無効です：

```bash
# 環境変数を確認
echo $NEXUSCORE_API_KEY

# 設定されていない場合は設定
export NEXUSCORE_API_KEY="your-api-key"
```

### テストがスキップされる

環境変数が設定されていない場合、E2E テストは自動的にスキップされます。これは正常な動作です。

## CI/CD での実行

CI/CD 環境では、環境変数が設定されていない場合でもテストが失敗しないよう、E2E テストは条件付きで実行されます：

```yaml
# GitHub Actions の例
- name: Run TypeScript SDK tests
  run: |
    cd sdk/typescript
    npm install
    npm test
  env:
    FASTAPI_BASE_URL: ${{ secrets.FASTAPI_BASE_URL }}
    NEXUSCORE_API_KEY: ${{ secrets.NEXUSCORE_API_KEY }}
```

## 関連ドキュメント

- [CR-FASTAPI-019 完了レポート](../api/CR-FASTAPI-019_COMPLETION_REPORT.md)
- [TypeScript SDK README](../sdk/typescript/README.md)
- [API ドキュメント](../api/README.md)

