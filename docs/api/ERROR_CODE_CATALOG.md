# Error Code Catalog（エラーコードカタログ）

**最終更新**: 2025年12月7日
**バージョン**: 1.0.0

## 概要

このカタログは、NexusCore FastAPI API で使用されるすべてのエラーコードの単一のソース（Single Source of Truth）です。

すべてのエンドポイントは、このカタログに定義されたエラーコードのみを使用する必要があります。新しいエラーコードを追加する場合は、必ずこのカタログにも追記してください。

## エラーコード一覧

| error.code | HTTP Status | カテゴリ | 説明 | 主な発生箇所 |
|------------|-------------|----------|------|-------------|
| `UNAUTHORIZED` | 401 | Auth | API Key が無効または欠如。認証が必要なエンドポイントで、API Key が提供されていない、または無効な場合に返される。 | `get_current_user()`, 認証付きエンドポイント（Projects, Runs, Execute など） |
| `FORBIDDEN` | 403 | Auth | 権限なし。認証は成功したが、リソースへのアクセス権限がない場合に返される。 | 認証付きエンドポイント（将来の拡張） |
| `NOT_FOUND` | 404 | NotFound | リソースが見つからない。指定された ID のリソースが存在しない場合に返される。 | Projects (`/api/v1/projects/{project_id}`), Runs (`/api/v1/runs/{run_id}`), Execute (`/api/v1/status/{task_id}`), Badges (`/api/v1/projects/{project_id}/badge/*`) |
| `INVALID_REQUEST` | 400 | Validation | パラメータ不正。リクエストパラメータが不正な場合に返される。 | GitHub Webhook (`/api/v1/github/webhook`), Projects (`/api/v1/projects/{project_id}/run`) |
| `VALIDATION_ERROR` | 422 | Validation | バリデーション不正。リクエストボディのバリデーションに失敗した場合に返される。 | すべてのエンドポイント（FastAPI の自動バリデーション） |
| `CONFLICT` | 409 | Conflict | 既存・重複エラー。リソースが既に存在する、または競合状態が発生した場合に返される。 | Projects エンドポイント（将来の拡張） |
| `INTERNAL_ERROR` | 500 | Internal | サーバー内部エラー。予期しないエラーが発生した場合に返される。認証フェイルでは使用しない（認証フェイルは必ず 401 を返す）。 | すべてのエンドポイント（DB アクセスエラー、予期しない例外など） |

## エラーコードの命名規則

- エラーコードは **大文字のスネークケース**（例: `UNAUTHORIZED`, `NOT_FOUND`）を使用する
- エラーコードは **動詞ではなく名詞** を使用する（例: `NOT_FOUND` ではなく `NOT_FOUND`）
- エラーコードは **簡潔で明確** である必要がある
- エラーコードは **HTTP ステータスコードと対応** している必要がある

## エラーコードのカテゴリ

### Auth（認証・認可）
- `UNAUTHORIZED` (401): 認証が必要、または認証に失敗した
- `FORBIDDEN` (403): 認証は成功したが、権限がない

### NotFound（リソース未検出）
- `NOT_FOUND` (404): 指定されたリソースが見つからない

### Validation（バリデーション）
- `INVALID_REQUEST` (400): リクエストパラメータが不正
- `VALIDATION_ERROR` (422): リクエストボディのバリデーションに失敗

### Conflict（競合）
- `CONFLICT` (409): リソースが既に存在する、または競合状態が発生

### Internal（サーバー内部エラー）
- `INTERNAL_ERROR` (500): サーバー内部で予期しないエラーが発生

## エラーコードの使用例

### 認証エラー（401）
```python
from nexuscore.api.utils.errors import make_unauthorized_error

raise make_unauthorized_error("Invalid or missing API key")
```

### リソース未検出（404）
```python
from nexuscore.api.utils.errors import make_not_found_error

raise make_not_found_error("Project", str(project_id))
```

### バリデーションエラー（422）
```python
from nexuscore.api.utils.errors import make_validation_error

raise make_validation_error("requirement is required")
```

### サーバー内部エラー（500）
```python
from nexuscore.api.utils.errors import make_internal_error

raise make_internal_error("Database connection error")
```

## エラーコードの追加手順

新しいエラーコードを追加する場合は、以下の手順に従ってください：

1. **ERROR_CODE_CATALOG.md に追加**
   - エラーコード一覧表に新しいエラーコードを追加
   - HTTP ステータス、カテゴリ、説明、発生箇所を記載

2. **コード側の実装**
   - `src/nexuscore/api/utils/errors.py` にショートカット関数を追加（必要に応じて）
   - または `make_error()` を直接使用

3. **テストの追加**
   - 新しいエラーコードのテストを追加
   - `tests/api/test_error_code_catalog.py` でカタログとの整合性を確認

4. **ドキュメント更新**
   - 必要に応じて `docs/api/README.md` を更新

## エラーコードと HTTP ステータスの対応

| HTTP Status | エラーコード | 説明 |
|-------------|-------------|------|
| 400 | `INVALID_REQUEST` | リクエストパラメータが不正 |
| 401 | `UNAUTHORIZED` | 認証が必要、または認証に失敗 |
| 403 | `FORBIDDEN` | 認証は成功したが、権限がない |
| 404 | `NOT_FOUND` | リソースが見つからない |
| 409 | `CONFLICT` | リソースが既に存在する、または競合状態 |
| 422 | `VALIDATION_ERROR` | リクエストボディのバリデーションに失敗 |
| 500 | `INTERNAL_ERROR` | サーバー内部で予期しないエラー |

## 重要な原則

1. **認証フェイルは必ず 401 を返す**
   - 認証フェイル（API Key 不正・欠如）は決して 500 を返さない
   - DB アクセスエラーは 500 を返すが、認証フェイルと明確に区別する

2. **エラーコードの一貫性**
   - 同じエラー条件では同じエラーコードを使用する
   - エラーコードは HTTP ステータスコードと対応している必要がある

3. **エラーコードの拡張性**
   - 新しいエラーコードを追加する場合は、既存のカテゴリに分類する
   - 必要に応じて新しいカテゴリを追加可能

## 関連ドキュメント

- [CR-FASTAPI-006: Error Handling Unification](./CR-FASTAPI-006_COMPLETION_REPORT.md) - エラー標準化
- [CR-FASTAPI-014: Auth Error Normalization](./CR-FASTAPI-014_COMPLETION_REPORT.md) - 認証エラー正規化
- [API README](./README.md) - FastAPI Migration Prompts & Documentation

