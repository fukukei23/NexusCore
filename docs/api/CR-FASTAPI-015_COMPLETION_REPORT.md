# CR-FASTAPI-015: Error Code Catalog 作成（エラーコード一覧の単一ソース化） - 完了レポート

## 実装日時

2025年12月7日

## 概要

### 目的

各ルータ・Dependency で ErrorResponse は使っているが、error.code と HTTP ステータスの対応表がコード散在している。また、「このエラーコードはどのエンドポイントでどういう条件で返るか」が一覧で分からない。

SDK / 外部クライアント視点で見ると、「どんなエラーが返り得るか」を 1 か所で確認できない。

### ゴール

1. Error Code Catalog（エラーコードカタログ）を 1 ファイルにまとめる
2. 「ErrorResponse.error.code」「HTTP ステータス」「意味」「代表的な発生箇所」を一覧化
3. FastAPI 実装・OpenAPI・テストと矛盾がない状態にそろえる
4. 将来、SDK・外部ドキュメント・ダッシュボードでこのカタログを唯一の仕様として参照できる状態にする

### 原則

- Error Code Catalog がエラーコードの単一のソース（Single Source of Truth）である
- すべてのエラーコードはカタログに記載されている必要がある
- カタログに載っていないエラーコードは使用しない
- 新しいエラーコードを追加する場合は、必ずカタログにも追記する

## 実装ステップ

### Step 1: Spec の作成

**実施内容**:
- `docs/spec/CR-FASTAPI-015_Error_Code_Catalog.md` を作成
- Error Code Catalog の設計と実装方針を明確化

**結果**:
- ✅ Spec を作成しました

### Step 2: Error Code Catalog の作成

**作成ファイル**: `docs/api/ERROR_CODE_CATALOG.md`

**実装内容**:
- エラーコード一覧表（error.code, HTTP ステータス, カテゴリ, 説明, 発生箇所）を作成
- エラーコードの命名規則を定義
- エラーコードのカテゴリ（Auth, NotFound, Validation, Conflict, Internal）を定義
- エラーコードの使用例を追加
- エラーコードの追加手順を記載

**定義されたエラーコード**:
- `UNAUTHORIZED` (401, Auth) - API Key が無効または欠如
- `FORBIDDEN` (403, Auth) - 権限なし
- `NOT_FOUND` (404, NotFound) - リソースが見つからない
- `INVALID_REQUEST` (400, Validation) - パラメータ不正
- `VALIDATION_ERROR` (422, Validation) - バリデーション不正
- `CONFLICT` (409, Conflict) - 既存・重複エラー
- `INTERNAL_ERROR` (500, Internal) - サーバー内部エラー

**結果**:
- ✅ Error Code Catalog を作成しました

### Step 3: コード側コメントの追加

**変更ファイル**: `src/nexuscore/api/schemas/error.py`

**変更内容**:
- ErrorResponse の docstring に「ERROR_CODE_CATALOG.md に定義されたコードのみを使う」旨を追記
- ErrorDetail の docstring にカタログへの参照を追加

**変更ファイル**: `src/nexuscore/api/utils/errors.py`

**変更内容**:
- モジュールの docstring にカタログへの参照を追加
- `make_error()` 関数の docstring にカタログへの参照を追加
- 各ショートカット関数（`make_not_found_error()`, `make_unauthorized_error()`, `make_validation_error()`, `make_internal_error()`, `make_bad_request_error()`, `make_forbidden_error()`, `make_conflict_error()`）の docstring にカタログへの参照を追加

**結果**:
- ✅ コード側のコメントを追加しました

### Step 4: テストの作成

**作成ファイル**: `tests/api/test_error_code_catalog.py`

**実装内容**:
- ERROR_CODE_CATALOG.md からエラーコードと HTTP ステータスの対応をパースする関数を実装
- OpenAPI スキーマから ErrorResponse を返すレスポンス定義を抽出する関数を実装
- カタログと OpenAPI の整合性をチェックするテストを実装

**テストケース**:
- `test_error_code_catalog_exists`: ERROR_CODE_CATALOG.md が存在することを確認
- `test_error_code_catalog_parsable`: ERROR_CODE_CATALOG.md が正しくパースできることを確認
- `test_error_code_catalog_has_required_fields`: 各エラーコードに必要な情報が含まれていることを確認
- `test_openapi_error_responses_match_catalog`: OpenAPI スキーマのエラーレスポンスがカタログに定義されたエラーコードと一致することを確認
- `test_error_code_catalog_completeness`: カタログに最低限必要なエラーコードが含まれていることを確認
- `test_error_code_catalog_no_duplicates`: カタログに重複するエラーコードがないことを確認
- `test_error_code_catalog_status_code_consistency`: カタログのエラーコードと HTTP ステータスの対応が一貫していることを確認

**結果**:
- ✅ テストを作成しました

### Step 5: ドキュメント更新

**変更ファイル**: `docs/api/README.md`

**変更内容**:
- 「Error Code Catalog（エラーコードカタログ）」セクションを追加
- ERROR_CODE_CATALOG.md へのリンクを追加
- 「エラー仕様の単一ソースは ERROR_CODE_CATALOG.md」という一文を明記
- エラーコード一覧のセクションにカタログへの参照を追加

**変更ファイル**: `README.md`

**変更内容**:
- API 構成セクションに「エラーコード: すべてのエラーコードは `docs/api/ERROR_CODE_CATALOG.md` に定義されています（単一のソース）」を追加

**結果**:
- ✅ ドキュメントを更新しました

### Step 6: .cursorrules の更新

**変更ファイル**: `.cursorrules`

**変更内容**:
- Error Code Catalog ルールを追加
- 新しいエラーコードを追加する際の手順を明記
- カタログに載っていないエラーコードを使用しないことを明記

**結果**:
- ✅ .cursorrules を更新しました

## 変更ファイル一覧

### 新規作成ファイル

- `docs/spec/CR-FASTAPI-015_Error_Code_Catalog.md` - Spec ドキュメント
- `docs/api/ERROR_CODE_CATALOG.md` - Error Code Catalog（エラーコードの単一のソース）
- `tests/api/test_error_code_catalog.py` - カタログと OpenAPI の整合性チェックテスト
- `docs/api/CR-FASTAPI-015_COMPLETION_REPORT.md` - 完了レポート（本ファイル）

### 変更ファイル

- `src/nexuscore/api/schemas/error.py` - ErrorResponse と ErrorDetail の docstring にカタログへの参照を追加
- `src/nexuscore/api/utils/errors.py` - make_error() 系関数の docstring にカタログへの参照を追加
- `docs/api/README.md` - Error Code Catalog セクションを追加
- `README.md` - API 構成セクションにエラーコードカタログへの参照を追加
- `.cursorrules` - Error Code Catalog ルールを追加

## 動作確認結果

### テスト実行

**実行コマンド**:
```bash
python -m pytest tests/api/test_error_code_catalog.py -v --tb=short
```

**結果**:
- ✅ すべてのテストが成功しました

**テストケース**:
- ✅ `test_error_code_catalog_exists`: ERROR_CODE_CATALOG.md が存在することを確認
- ✅ `test_error_code_catalog_parsable`: ERROR_CODE_CATALOG.md が正しくパースできることを確認
- ✅ `test_error_code_catalog_has_required_fields`: 各エラーコードに必要な情報が含まれていることを確認
- ✅ `test_openapi_error_responses_match_catalog`: OpenAPI スキーマのエラーレスポンスがカタログに定義されたエラーコードと一致することを確認
- ✅ `test_error_code_catalog_completeness`: カタログに最低限必要なエラーコードが含まれていることを確認
- ✅ `test_error_code_catalog_no_duplicates`: カタログに重複するエラーコードがないことを確認
- ✅ `test_error_code_catalog_status_code_consistency`: カタログのエラーコードと HTTP ステータスの対応が一貫していることを確認

### 静的解析

**実行コマンド**:
```bash
python -m pylint src/nexuscore/api/schemas/error.py src/nexuscore/api/utils/errors.py
```

**結果**:
- ✅ 静的解析エラーなし

### OpenAPI スキーマ確認

**確認内容**:
- OpenAPI スキーマ（`/api/openapi.json`）に ErrorResponse が正しく定義されていることを確認
- エラーレスポンスがカタログに定義されたエラーコードと一致することを確認

**結果**:
- ✅ OpenAPI スキーマとカタログの整合性が確認されました

## 設計上の改善点

### アーキテクチャ

- **単一のソース（Single Source of Truth）**: Error Code Catalog がエラーコードの唯一の仕様として機能するようになりました
- **整合性チェック**: テストにより、カタログと OpenAPI スキーマの整合性が自動的にチェックされます
- **拡張性**: 新しいエラーコードを追加する際の手順が明確になりました

### 将来の拡張性への配慮

- **カテゴリ分類**: エラーコードをカテゴリ（Auth, NotFound, Validation, Conflict, Internal）に分類することで、将来の拡張が容易になりました
- **テスト自動化**: カタログと OpenAPI の整合性チェックが自動化されているため、将来の変更でも整合性が保たれます

### コード品質の向上

- **ドキュメント化**: すべてのエラーコードがカタログに記載され、説明と使用例が提供されています
- **一貫性**: エラーコードの命名規則と HTTP ステータスコードの対応が明確になりました

## 既知の制約・注意事項

### 既存コードとの互換性

- 既存のエラーコードはすべてカタログに含まれています
- 既存のコードは変更不要です（コメント追加のみ）

### 制限事項やトレードオフ

- **422 ステータスコード**: FastAPI の自動バリデーションエラーは 422 を返しますが、これはカタログに含まれています
- **カタログのパース**: ERROR_CODE_CATALOG.md のパースは Markdown テーブルの形式に依存しています。テーブル形式を変更する場合は、テストも更新する必要があります

### 移行時の注意点

- 新しいエラーコードを追加する場合は、必ず ERROR_CODE_CATALOG.md にも追記してください
- カタログとコードの整合性を保つため、テストを実行して確認してください

## 次のステップ

### 推奨されるフォローアップアクション

1. **SDK ドキュメント更新**: SDK のドキュメントに Error Code Catalog への参照を追加する
2. **外部ドキュメント更新**: 外部向けの API ドキュメントに Error Code Catalog への参照を追加する
3. **ダッシュボード統合**: 将来的に、ダッシュボードで Error Code Catalog を参照できるようにする

### 関連 CR

- **CR-FASTAPI-006**: Error Handling Unification（エラー標準化）
- **CR-FASTAPI-014**: Auth Error Normalization（認証エラー正規化）

## 関連ドキュメント

- [CR-FASTAPI-015 Spec](../spec/CR-FASTAPI-015_Error_Code_Catalog.md) - Error Code Catalog の Spec
- [ERROR_CODE_CATALOG.md](./ERROR_CODE_CATALOG.md) - Error Code Catalog（エラーコードの単一のソース）
- [CR-FASTAPI-006 Completion Report](./CR-FASTAPI-006_COMPLETION_REPORT.md) - エラー標準化
- [CR-FASTAPI-014 Completion Report](./CR-FASTAPI-014_COMPLETION_REPORT.md) - 認証エラー正規化
- [API README](./README.md) - FastAPI Migration Prompts & Documentation

