# CR-FASTAPI-015: Error Code Catalog 作成（エラーコード一覧の単一ソース化）

- **CR-ID**: CR-FASTAPI-015
- **Status**: In-Progress
- **Author**: AI Codex
- **Date**: 2025-12-07
- **Related CR**: CR-FASTAPI-006, CR-FASTAPI-014

## 1. 概要（Overview）

### 1.1 目的

各ルータ・Dependency で ErrorResponse は使っているが、error.code と HTTP ステータスの対応表がコード散在している。また、「このエラーコードはどのエンドポイントでどういう条件で返るか」が一覧で分からない。

SDK / 外部クライアント視点で見ると、「どんなエラーが返り得るか」を 1 か所で確認できない。

### 1.2 ゴール

1. Error Code Catalog（エラーコードカタログ）を 1 ファイルにまとめる
2. 「ErrorResponse.error.code」「HTTP ステータス」「意味」「代表的な発生箇所」を一覧化
3. FastAPI 実装・OpenAPI・テストと矛盾がない状態にそろえる
4. 将来、SDK・外部ドキュメント・ダッシュボードでこのカタログを唯一の仕様として参照できる状態にする

### 1.3 原則

- Error Code Catalog がエラーコードの単一のソース（Single Source of Truth）である
- すべてのエラーコードはカタログに記載されている必要がある
- カタログに載っていないエラーコードは使用しない
- 新しいエラーコードを追加する場合は、必ずカタログにも追記する

## 2. コンテキストと前提

### 2.1 既存実装の確認

CR-FASTAPI-006 でエラーハンドリングが統一され、CR-FASTAPI-014 で認証エラーの正規化が完了している。

**現状のエラーコード**:
- `NOT_FOUND` (404) - リソース未検出
- `UNAUTHORIZED` (401) - API Key 不正
- `VALIDATION_ERROR` (422) - バリデーション不正
- `INTERNAL_ERROR` (500) - サーバー内部エラー
- `INVALID_REQUEST` (400) - パラメータ不正
- `FORBIDDEN` (403) - 権限なし
- `CONFLICT` (409) - 既存・重複エラー

### 2.2 関連ドキュメント

- `docs/api/CR-FASTAPI-006_COMPLETION_REPORT.md` - エラー標準化
- `docs/api/CR-FASTAPI-014_COMPLETION_REPORT.md` - 認証エラー正規化
- `src/nexuscore/api/schemas/error.py` - ErrorResponse モデル
- `src/nexuscore/api/utils/errors.py` - エラーハンドリングユーティリティ

## 3. スコープ（Scope）

### 3.1 実装・変更対象

**Error Code Catalog の新規作成**:
- `docs/api/ERROR_CODE_CATALOG.md` - エラーコードカタログ（新規作成）

**コード側コメント・ドキュメント更新**:
- `src/nexuscore/api/schemas/error.py` - ErrorResponse の docstring にカタログへの参照を追加
- `src/nexuscore/api/utils/errors.py` - make_error() 系関数の docstring にカタログへの参照を追加

**テスト**:
- `tests/api/test_error_code_catalog.py` - カタログと OpenAPI の整合性チェックテスト（新規作成）

**ドキュメント更新**:
- `docs/api/README.md` - Error Code Catalog セクションを追加
- `README.md` - エラーコードカタログへの参照を追加
- `.cursorrules` - エラーコード使用ルールを追加

### 3.2 スコープ外

- ビジネスロジックやルータの大幅な挙動変更
- HTTP ステータス体系の全面変更
- SDK 側の例外ラップ・エラーハンドリングの詳細実装

## 4. 実装計画

### 4.1 Step 1: Error Code Catalog の作成

**ファイル**: `docs/api/ERROR_CODE_CATALOG.md`

**内容**:
- エラーコード一覧表（error.code, HTTP ステータス, カテゴリ, 説明, 発生箇所）
- エラーコードの命名規則
- カタログの使用方法

**エラーコード一覧**:
| error.code | HTTP Status | カテゴリ | 説明 | 主な発生箇所 |
|------------|-------------|----------|------|-------------|
| UNAUTHORIZED | 401 | Auth | API Key が無効または欠如 | `get_current_user()`, 認証付きエンドポイント |
| FORBIDDEN | 403 | Auth | 権限なし | 認証付きエンドポイント（将来の拡張） |
| NOT_FOUND | 404 | NotFound | リソースが見つからない | Projects, Runs, Execute エンドポイント |
| INVALID_REQUEST | 400 | Validation | パラメータ不正 | GitHub Webhook, Projects エンドポイント |
| VALIDATION_ERROR | 422 | Validation | バリデーション不正 | すべてのエンドポイント |
| CONFLICT | 409 | Conflict | 既存・重複エラー | Projects エンドポイント（将来の拡張） |
| INTERNAL_ERROR | 500 | Internal | サーバー内部エラー | すべてのエンドポイント |

### 4.2 Step 2: コード側コメントの追加

**変更ファイル**: `src/nexuscore/api/schemas/error.py`

**変更内容**:
- ErrorResponse の docstring に「ERROR_CODE_CATALOG.md に定義されたコードのみを使う」旨を追記

**変更ファイル**: `src/nexuscore/api/utils/errors.py`

**変更内容**:
- make_error() / ショートカット関数の docstring に「詳細なエラーコード仕様は docs/api/ERROR_CODE_CATALOG.md を参照」と明示

### 4.3 Step 3: テストの作成

**ファイル**: `tests/api/test_error_code_catalog.py`

**実装内容**:
- ERROR_CODE_CATALOG.md から error.code と HTTP ステータスの対応をパース
- /api/openapi.json を読み込み、ErrorResponse を返すレスポンス定義が、カタログに存在する error.code / ステータスの組み合わせだけになっていることを確認
- 「カタログに載っていない error.code」または「カタログと異なるステータス」があればテスト失敗にする

### 4.4 Step 4: ドキュメント更新

**変更ファイル**: `docs/api/README.md`

**追加内容**:
- 「Error Code Catalog」セクションを追加
- ERROR_CODE_CATALOG.md へのリンクを張る
- 「エラー仕様の単一ソースは ERROR_CODE_CATALOG.md」という一文を明記

**変更ファイル**: `README.md`

**追加内容**:
- API / SDK 概要の中に、「エラーコードは ERROR_CODE_CATALOG に従う」ことを簡潔に追記

**変更ファイル**: `.cursorrules`

**追加内容**:
- Error code usage rules のような節を追加
- 新規の error.code を増やす場合は、必ず ERROR_CODE_CATALOG.md にも追記する
- コードとカタログがズレている状態でマージしない

## 5. テスト戦略

### 5.1 カタログと OpenAPI の整合性チェック

**テスト内容**:
- ERROR_CODE_CATALOG.md からエラーコード一覧を読み込む
- OpenAPI スキーマ（/api/openapi.json）から ErrorResponse を返すレスポンス定義を抽出
- カタログに載っていない error.code が OpenAPI に含まれていないことを確認
- カタログと異なるステータスコードが OpenAPI に含まれていないことを確認

### 5.2 実行コマンド

```bash
python -m pytest tests/api/test_error_code_catalog.py -v
```

## 6. 完了条件（Definition of Done）

- [ ] `docs/spec/CR-FASTAPI-015_Error_Code_Catalog.md` を作成（本 Spec）
- [ ] `docs/api/ERROR_CODE_CATALOG.md` を作成
- [ ] `src/nexuscore/api/schemas/error.py` にカタログへの参照を追加
- [ ] `src/nexuscore/api/utils/errors.py` にカタログへの参照を追加
- [ ] `tests/api/test_error_code_catalog.py` を作成
- [ ] `docs/api/README.md` を更新
- [ ] `README.md` を更新
- [ ] `.cursorrules` を更新
- [ ] テスト実行（`python -m pytest tests/api/test_error_code_catalog.py -v`）
- [ ] 完了レポート作成（`docs/api/CR-FASTAPI-015_COMPLETION_REPORT.md`）

## 7. 関連ドキュメント

- [CR-FASTAPI-006 Completion Report](../api/CR-FASTAPI-006_COMPLETION_REPORT.md) - エラー標準化
- [CR-FASTAPI-014 Completion Report](../api/CR-FASTAPI-014_COMPLETION_REPORT.md) - 認証エラー正規化
- [API README](../api/README.md) - FastAPI Migration Prompts & Documentation

