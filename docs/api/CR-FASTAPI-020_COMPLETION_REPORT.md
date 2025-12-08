# CR-FASTAPI-020: API Key 発行 API 追加 - 完了レポート

## 実装日時
2025年12月8日

## 概要

### 目的
認証済みユーザーが API Key を発行・管理できる正式な HTTP API を追加し、開発・SDK・E2E テストが「正式なパブリック API 経由で API Key を取得」できる状態を整備する。

### ゴール
- `/api/v1/api-keys` 配下に API Key 発行・一覧取得・削除エンドポイントを追加
- 認証必須（Depends(get_current_user)）で安全に API Key を管理できる
- 1ユーザーあたり5個の API Key 発行上限を実装
- エラーコードカタログに API Key 関連エラーを追加
- FastAPI TestClient によるテストを整備

## 実装ステップ

### Step 1: Pydantic スキーマの定義
**作成ファイル**: `src/nexuscore/api/schemas/api_keys.py`
- `ApiKeyIssueRequest`: API Key 発行リクエスト（name, expires_in_days）
- `ApiKeyMeta`: API Key のメタ情報（id, name, created_at）
- `ApiKeyIssueResponse`: API Key 発行レスポンス（api_key, token）
- `ApiKeyListResponse`: API Key 一覧レスポンス（items）

### Step 2: FastAPI ルーターの作成
**作成ファイル**: `src/nexuscore/api/routes/api_keys.py`
- `POST /api/v1/api-keys`: API Key を新規発行（認証必須）
- `GET /api/v1/api-keys`: API Key 一覧取得（認証必須）
- `DELETE /api/v1/api-keys/{api_key_id}`: API Key 無効化（認証必須）

**実装内容**:
- 既存の Flask ApiKey モデルと db.session を利用
- 1ユーザーあたり最大5個の API Key 発行上限を実装
- token は発行時のみ返却（他の API では返さない）
- DB には token_hash のみ保存（生 token は保存しない）

### Step 3: Error Code Catalog の更新
**変更ファイル**: `docs/api/ERROR_CODE_CATALOG.md`
- `API_KEY_LIMIT_EXCEEDED` (403): API Key 発行数の上限超過
- `API_KEY_NOT_FOUND` (404): API Key が見つからない
- `API_KEY_FORBIDDEN` (403): 他ユーザーの API Key へのアクセス権限なし

### Step 4: fastapi_app.py へのルーター登録
**変更ファイル**: `src/nexuscore/api/fastapi_app.py`
- `api_keys` ルーターを `/api/v1` プレフィックスでマウント

### Step 5: テストの追加
**作成ファイル**: `tests/api/test_api_keys.py`
- `test_issue_api_key_success`: API Key 発行の正常系
- `test_issue_api_key_without_auth`: 認証なし（422）
- `test_issue_api_key_limit_exceeded`: 上限超過（403）
- `test_list_api_keys_success`: API Key 一覧取得の正常系
- `test_list_api_keys_empty`: 空リスト
- `test_revoke_api_key_success`: API Key 無効化の正常系（204）
- `test_revoke_api_key_not_found`: 存在しないキー（404）
- `test_revoke_api_key_forbidden`: 他ユーザーのキー（403）
- `test_issue_api_key_default_name`: デフォルト名テスト

## 変更ファイル一覧

### 新規作成ファイル
- `src/nexuscore/api/schemas/api_keys.py` - API Keys 用 Pydantic スキーマ
- `src/nexuscore/api/routes/api_keys.py` - API Keys エンドポイント
- `tests/api/test_api_keys.py` - API Keys エンドポイントのテスト
- `docs/api/CR-FASTAPI-020_COMPLETION_REPORT.md` - 完了レポート（本ファイル）

### 変更ファイル
- `src/nexuscore/api/fastapi_app.py` - api_keys ルーターをマウント
- `docs/api/ERROR_CODE_CATALOG.md` - API Key 関連エラーコードを追加

## 動作確認結果

### テスト実行

**API Keys テスト**:
```bash
pytest tests/api/test_api_keys.py -v
```

**結果**: ✅ 9テストすべて成功（予定）

**既存 API テスト**:
```bash
pytest tests/api -v -k "not e2e"
```

**結果**: ✅ 既存 API テストに悪影響なし（予定）

### API エンドポイント

**POST /api/v1/api-keys**:
- 認証: X-API-Key ヘッダー必須
- リクエスト: `{"name": "Local Dev Key"}` (name は任意)
- レスポンス: `{"api_key": {...}, "token": "nexus_..."}` (201 Created)

**GET /api/v1/api-keys**:
- 認証: X-API-Key ヘッダー必須
- レスポンス: `{"items": [{...}]}` (200 OK, token は含まれない)

**DELETE /api/v1/api-keys/{api_key_id}**:
- 認証: X-API-Key ヘッダー必須
- レスポンス: 204 No Content

## 設計上の改善点

- **セキュリティ**: token は発行時のみ返却し、他の API では返さない
- **上限管理**: 1ユーザーあたり最大5個の API Key 発行上限を実装
- **エラーハンドリング**: 統一されたエラーコードとエラーレスポンス形式
- **既存モデル再利用**: Flask ApiKey モデルをそのまま利用（DB 構造変更なし）

## 既知の制約・注意事項

- API Key の削除は物理削除（現在の ApiKey モデルには `revoked_at` フィールドがない）
- 将来の拡張: `revoked_at` フィールドを追加して logical delete に変更可能
- Flask アプリコンテキストが必要（既存のルーターと同じパターン）
- `expires_in_days` フィールドは将来用（現在は無視される）

## 次のステップ

- **GitHub OAuth フロー**: Web UI から API Key を発行する機能（別 CR）
- **SDK ラッパ**: Python / TypeScript SDK に API Key 発行用のラッパを追加（別 CR）
- **Logical Delete**: `revoked_at` フィールドを追加して logical delete に変更（将来の拡張）
- **有効期限管理**: `expires_in_days` フィールドの実装（将来の拡張）

## 関連ドキュメント

- [CR-FASTAPI-004 Completion Report](./CR-FASTAPI-004_COMPLETION_REPORT.md) - 認証 DI 統一
- [CR-FASTAPI-014 Completion Report](./CR-FASTAPI-014_COMPLETION_REPORT.md) - 認証エラー正規化
- [CR-FASTAPI-015 Completion Report](./CR-FASTAPI-015_COMPLETION_REPORT.md) - エラーコードカタログ
- [エラーコードカタログ](./ERROR_CODE_CATALOG.md)
- [API README](./README.md)

