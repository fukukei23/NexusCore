# Projects API Contract

CR-NEXUS-040: Projects API のレスポンス shape とエラー応答の契約仕様。

## 概要

本ドキュメントは `/api/v1/projects` 配下のエンドポイントの成功レスポンスとエラーレスポンスの契約を定義します。

## 成功レスポンス

### GET /api/v1/projects

プロジェクト一覧を取得する。

**認証**: X-API-Key ヘッダー必須

**成功レスポンス（200）**:

```json
{
  "projects": [
    {
      "id": 1,
      "name": "My Project",
      "repo_url": "https://github.com/owner/repo",
      "local_path": "/path/to/project",
      "created_at": "2025-01-01T00:00:00",
      "updated_at": "2025-01-01T00:00:00"
    }
  ]
}
```

**レスポンス shape の契約**:
- トップレベルに `projects` キーを持つ
- `projects` は配列（list）である
- 各要素は `ProjectSummary` スキーマに準拠
- 最小限の必須キー: `id`, `name`

### GET /api/v1/projects/{project_id}/runs/latest

最新の Run を取得する。

**認証**: X-API-Key ヘッダー必須

**成功レスポンス（200） - Run ありの場合**:

```json
{
  "run": {
    "id": 1,
    "run_id": "abc123def456",
    "status": "SUCCESS",
    "started_at": "2025-01-01T00:00:00",
    "finished_at": "2025-01-01T00:05:00"
  }
}
```

**成功レスポンス（200） - Run なしの場合**:

```json
{
  "run": null
}
```

**レスポンス shape の契約**:
- トップレベルに `run` キーを持つ
- `run` は `null` または `dict` のいずれかである
- `run` が `dict` の場合、最小限の必須キー: `id`, `run_id`, `status`
- `started_at` と `finished_at` は `Optional[datetime]` である

## エラーレスポンス

すべての projects 系エンドポイントで、エラーレスポンスは以下の統一形式で返されます。

**エラーレスポンス形式（CR-NEXUS-034 Option A）**:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### エラーステータスコード

#### 401 Unauthorized

認証失敗（API Key が無効または欠如）

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or missing API key"
  }
}
```

#### 404 Not Found

リソースが見つからない（プロジェクトが存在しない等）

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Project with id 999 not found"
  }
}
```

#### 422 Unprocessable Entity

バリデーションエラー（FastAPI の自動バリデーション）

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation error (field: body -> requirement)"
  }
}
```

#### 500 Internal Server Error

内部サーバーエラー

```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Internal server error"
  }
}
```

### エラーレスポンス shape の契約

- トップレベルに `error` キーを持つ
- `error` は `dict` であり、`code` と `message` を含む
- **`detail` がトップレベルにないこと**（FastAPI 標準の `{"detail": ...}` 形式ではない）
- すべてのエラーコードは `docs/api/エラーコードカタログ.md` に定義されている

## 互換性ルール

### 追加キーの許容

レスポンスに追加のキーを追加することは許容されます（後方互換性を維持するため）。

例：
- `ProjectSummary` に新しいフィールド（`description`, `tags` など）を追加することは可能

### 破壊的変更の禁止

以下の変更は破壊的変更として扱われます：

1. **既存キーの削除**
   - `projects` キーの削除
   - `run` キーの削除
   - `ProjectSummary` の `id`, `name` の削除

2. **型の変更**
   - `projects` が `list` から他の型に変更されること
   - `run` が `Optional[dict]` から他の型に変更されること

3. **エラーレスポンス形式の変更**
   - トップレベル `error` キーが `detail` に変更されること
   - `error.code` や `error.message` が削除されること

## スキーマ定義

レスポンススキーマは以下の Pydantic モデルで定義されています：

- `ProjectListResponse`: GET /api/v1/projects のレスポンス
- `ProjectSummary`: プロジェクト一覧の各要素
- `LatestRunResponse`: GET /api/v1/projects/{project_id}/runs/latest のレスポンス
- `LatestRunDetail`: Run 詳細情報

詳細は `src/nexuscore/api/schemas/project.py` および `src/nexuscore/api/schemas/project_run.py` を参照してください。

## テスト

契約は `tests/api/test_projects_contract.py` で固定されています。

- レスポンス shape の検証
- エラーレスポンス envelope の検証
- OpenAPI schema の検証

契約に違反する変更が行われた場合、これらのテストが失敗します。

