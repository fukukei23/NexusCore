# CR-FASTAPI-014: Auth Error Normalization（認証エラーの正規化）

- **CR-ID**: CR-FASTAPI-014
- **Status**: In-Progress
- **Author**: AI Codex
- **Date**: 2025-12-07
- **Related CR**: CR-FASTAPI-004, CR-FASTAPI-006, CR-FASTAPI-013, CR-FASTAPI-013A

## 1. 概要（Overview）

### 1.1 目的

Projects 系の E2E テスト（`test_projects_list_e2e`）実行時に、認証不備や DB アクセス失敗が 500 Internal Server Error になっている問題を解決する。

認証エラーとしては、本来は 401 Unauthorized または 403 Forbidden で返すべきであり、500 は「サーバ側のバグ」を意味するステータスコードである。

### 1.2 ゴール

1. 認証フェイル（API Key 不正・欠如・DB ロード失敗）は **決して 500 を返さない** ように正規化する
2. 401/403 のポリシーを決めて ErrorResponse モデルで統一的に表現する
3. Projects / Runs / Execute など、認証付きエンドポイントの実装とテストを正しいステータスコードとメッセージに揃える
4. SDK E2E テスト（特に `test_projects_list_e2e`）を「正しい期待値（200 / 401 / 403）」で通す

### 1.3 原則

- 認証フェイルは必ず 401 Unauthorized を返す（500 は返さない）
- DB アクセスエラーなど、サーバー側の致命的な障害は 500 にするが、認証フェイルと明確に区別する
- すべてのエラーは `make_error()` 関数を経由して ErrorResponse モデルで統一する
- 既存の Flask 実装には影響を与えない

## 2. コンテキストと前提

### 2.1 既存実装の確認

CR-FASTAPI-004 で認証 DI が統一され、CR-FASTAPI-006 でエラーハンドリングが統一されている。

**現状の問題点**:
- `get_current_user()` の例外ハンドリングで、予期しない例外が 500 エラーになっている
- DB アクセスエラーと認証フェイルが区別されていない
- E2E テストで 500 エラーが返されている

### 2.2 関連ドキュメント

- `docs/api/CR-FASTAPI-004_COMPLETION_REPORT.md` - 認証 DI 統一
- `docs/api/CR-FASTAPI-006_COMPLETION_REPORT.md` - エラー標準化
- `docs/api/CR-FASTAPI-013_COMPLETION_REPORT.md` - SDK E2E テスト基盤
- `src/nexuscore/api/dependencies/auth.py` - 認証 Dependency
- `src/nexuscore/api/utils/errors.py` - エラーハンドリングユーティリティ

## 3. スコープ（Scope）

### 3.1 実装・変更対象

**認証依存・エラー共通部**:
- `src/nexuscore/api/dependencies/auth.py` - `get_current_user()` のエラー正規化
- `src/nexuscore/api/utils/errors.py` - エラービルダー関数（必要に応じて追加）

**対象 FastAPI ルータ**:
- `src/nexuscore/api/routes/projects.py` - responses 定義の確認・更新
- `src/nexuscore/api/routes/runs.py` - responses 定義の確認・更新
- `src/nexuscore/api/routes/execute.py` - responses 定義の確認・更新

**テスト**:
- `tests/api/test_fastapi_auth.py` - 認証エラーのテスト追加・強化
- `tests/api/test_fastapi_projects.py` - 401 エラーの確認テスト
- `tests/api/test_fastapi_runs.py` - 401 エラーの確認テスト
- `tests/e2e/test_sdk_e2e.py` - `test_projects_list_e2e` の期待値修正

**ドキュメント**:
- `docs/api/README.md` - 認証エラー時のステータスコードポリシーを追記
- `README.md` - 外部クライアント向けの簡易説明を追加
- `docs/api/CR-FASTAPI-014_COMPLETION_REPORT.md` - 完了レポート（新規作成）

### 3.2 スコープ外

- 認証方式自体の変更（API Key → JWT など）
- RBAC（ロールベースの権限設計）の詳細設計
- DB スキーマの変更やマイグレーション
- SDK 自体のテンプレート変更

## 4. ステータスコードポリシー

### 4.1 認証エラー（API Key 不正・欠如）

**原則**: 401 Unauthorized

以下のケースで 401 を返す:
- API Key ヘッダーが欠如している場合
- API Key が無効な場合
- API Key が DB に存在しない場合
- API Key が期限切れの場合（将来の拡張）

**エラーコード**: `UNAUTHORIZED`
**エラーメッセージ**: "Invalid or missing API key" または具体的な理由

### 4.2 認可エラー（ロール不足など）

**原則**: 403 Forbidden（必要に応じて）

現時点では最小限の実装でよいが、将来的にロールベースのアクセス制御を実装する場合に備える。

**エラーコード**: `FORBIDDEN`
**エラーメッセージ**: "Forbidden" または具体的な理由

### 4.3 サーバー内部のバグ・予期しない例外

**原則**: 500 Internal Server Error

ただし、認証フェイルでは使わない。以下のケースで 500 を返す:
- DB 接続エラー（ただし認証フェイルと区別できるように）
- 予期しない例外（ただし認証フェイルと区別できるように）

**エラーコード**: `INTERNAL_ERROR`
**エラーメッセージ**: サーバー側の問題であることを示すメッセージ

## 5. 実装計画

### 5.1 Step 1: `get_current_user()` のエラー正規化

**ファイル**: `src/nexuscore/api/dependencies/auth.py`

**変更内容**:
1. API Key 未設定 / 無効 / DB に存在しない / 期限切れ 等のケースを明示的に判定
2. 認証フェイルは `make_unauthorized_error()` を経由して 401 にマッピング
3. DB アクセスエラーなど、ユーザー起因でない障害は 500 にするが、認証フェイルと区別できるようにエラーメッセージ・コードを整理

**実装方針**:
- `ImportError` の場合（webapp モジュールが利用できない場合）:
  - 環境変数ベースの認証にフォールバック
  - API Key 不一致は 401 を返す
- DB アクセスエラーの場合:
  - SQLAlchemy の例外をキャッチ
  - 認証フェイルと区別できるようにエラーメッセージを設定
  - 500 を返す（ただし認証フェイルではないことを明示）
- その他の予期しない例外:
  - ログに記録
  - 500 を返す（ただし認証フェイルではないことを明示）

### 5.2 Step 2: 各ルータでの responses 定義の整合

**変更ファイル**:
- `src/nexuscore/api/routes/projects.py`
- `src/nexuscore/api/routes/runs.py`
- `src/nexuscore/api/routes/execute.py`

**変更内容**:
- `responses` に 401（必要に応じて 403）を追加し、ErrorResponse を割り当てる
- 既に 401/403 がある場合は、今回のロジックとメッセージに合わせて説明を調整

### 5.3 Step 3: `test_projects_list_e2e` の期待値修正

**ファイル**: `tests/e2e/test_sdk_e2e.py`

**変更内容**:
- 正常系: 正しい API Key を渡して 200 OK / プロジェクト一覧を取得できること
- 異常系（オプション）: 不正な API Key で 401（または 403）が返ること
- 現状 500 になっている部分を、上記ポリシーに従ってテストを「通る状態」に修正

### 5.4 Step 4: Unit テストの追加・強化

**ファイル**: `tests/api/test_fastapi_auth.py`

**追加テスト**:
- API Key が無い場合に 401 が返ること
- 無効な API Key の場合に 401 が返ること
- 有効な API Key の場合に、AuthenticatedUser が期待どおり設定されること
- DB アクセスエラーの場合に 500 が返ること（ただし認証フェイルと区別できること）

**ファイル**: `tests/api/test_fastapi_projects.py`, `tests/api/test_fastapi_runs.py`

**追加テスト**:
- 認証なしリクエストが 401 を返すことを確認するテストを追加 / 修正

### 5.5 Step 5: ドキュメント更新

**変更ファイル**: `docs/api/README.md`

**追加内容**:
- 「認証エラー時のステータスコードポリシー」セクションを追加
- どのケースで 401 / 403 / 500 を返すかを簡潔に表にする

**変更ファイル**: `README.md`

**追加内容**:
- 外部クライアント向けの簡易説明を追加（SaaS 公開時に外部クライアントが参照できるレベル）

## 6. テスト戦略

### 6.1 Unit テスト

**実行コマンド**:
```bash
python -m pytest \
  tests/api/test_fastapi_auth.py \
  tests/api/test_fastapi_projects.py \
  tests/api/test_fastapi_runs.py \
  tests/api/test_fastapi_execute.py \
  tests/api/test_fastapi_errors.py \
  -v
```

**確認項目**:
- ✅ API Key が無い場合に 401 が返ること
- ✅ 無効な API Key の場合に 401 が返ること
- ✅ 有効な API Key の場合に認証が成功すること
- ✅ DB アクセスエラーの場合に 500 が返ること（ただし認証フェイルと区別できること）
- ✅ 認証なしリクエストが 401 を返すこと

### 6.2 E2E テスト

**実行コマンド**:
```bash
make test-e2e
# または
python -m pytest tests/e2e/test_sdk_e2e.py -v --tb=short
```

**確認項目**:
- ✅ `test_health_e2e` が 200 を返すこと
- ✅ `test_projects_list_e2e` が 401 を返すこと（認証なしの場合）または 200 を返すこと（認証ありの場合）
- ✅ `test_execute_e2e` が 401 を返すこと（認証なしの場合）または 200 を返すこと（認証ありの場合）

## 7. 既知の制約・注意事項

### 7.1 既存コードとの互換性

- ✅ 既存の Flask アプリケーションには影響なし
- ✅ 既存のデータベースモデルを再利用
- ✅ 既存の認証ロジックを維持（エラーハンドリングのみ改善）

### 7.2 制限事項やトレードオフ

1. **DB アクセスエラーと認証フェイルの区別**
   - DB アクセスエラーは 500 を返すが、認証フェイルと区別できるようにエラーメッセージを設定
   - 将来的には、より詳細なエラーコードで区別可能にする

2. **テスト環境での認証**
   - テスト環境では webapp モジュールが利用できない場合がある
   - 環境変数ベースの認証にフォールバックする実装を維持

## 8. 関連ドキュメント

- [CR-FASTAPI-004 Completion Report](../api/CR-FASTAPI-004_COMPLETION_REPORT.md) - 認証 DI 統一
- [CR-FASTAPI-006 Completion Report](../api/CR-FASTAPI-006_COMPLETION_REPORT.md) - エラー標準化
- [CR-FASTAPI-013 Completion Report](../api/CR-FASTAPI-013_COMPLETION_REPORT.md) - SDK E2E テスト基盤
- [API README](../api/README.md) - FastAPI Migration Prompts & Documentation


