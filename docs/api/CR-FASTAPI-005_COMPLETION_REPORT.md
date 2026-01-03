# CR-FASTAPI-005: Pydantic モデルの分離と API 型安全化 - 完了レポート

## 実装日時

2025年12月3日

## 概要

### 目的
既存 Flask/混在コードから移行してくる API 仕様を FastAPI で「完全型安全化」する。
特に以下を達成すること：
1. API レスポンス仕様のゆらぎをすべて排除し、Pydantic BaseModel へ集約
2. Request と Response のスキーマを routes.py から切り離して schemas/ 以下へ集約
3. API・ドメイン・UI ロジックの責務分離（API 層にビジネスロジックを置かない）
4. OpenAPI の自動生成を正規化し、SaaS 外部公開に耐える構造へ移行
5. CR-FASTAPI-001〜004 のパターンに完全準拠する

### ゴール
- `/api/v1/projects` GET/POST の FastAPI 実装
- `/api/v1/projects/{id}` GET の FastAPI 実装
- `/api/v1/runs` GET の FastAPI 実装
- `/api/v1/runs/{id}` GET の FastAPI 実装
- `/api/v1/plans` GET の FastAPI 実装（将来的な拡張を考慮）
- すべての Request/Response を Pydantic BaseModel で型定義
- 統一されたエラーモデルの実装
- 既存の Flask 実装との互換性を保つ

### 原則
- すべての API Request/Response は Pydantic BaseModel を使用
- モデルは必ず `src/nexuscore/api/schemas/**` へ配置
- API ルータは `src/nexuscore/api/routes/**` に配置
- 認証は `Depends(get_current_user)` を必ず通す（health, webhook は例外）
- 既存の Flask 実装を壊さない

## 実装ステップ

### Step 1: 既存のFlask実装を確認して仕様を把握

**確認したファイル**:
- `src/nexuscore/webapp/api_external.py` - Flask実装の外部統合API
- `src/nexuscore/webapp/models.py` - データベースモデル定義
- `docs/api/api_inventory.md` - API棚卸し結果

**解析結果**:
- **Project モデル**:
  - `id`, `owner_id`, `name`, `repo_url`, `local_path`, `context_bundle_path`, `created_at`, `updated_at`
- **Run モデル**:
  - `id`, `project_id`, `run_id`, `triggered_by`, `status`, `started_at`, `finished_at`, `autonomy_level`, `llm_model_summary`, `requirement`, `created_at`
- **Plan モデル**:
  - データベースモデルとしては存在しない（将来的な拡張を考慮）

**既存のFlask実装**:
- GET `/api/v1/projects` - プロジェクト一覧取得（実装済み）
- POST `/api/v1/projects/<project_id>/run` - Run発火（要件とは異なる）
- GET `/api/v1/projects/<project_id>/runs/latest` - 最新Run取得（要件とは異なる）

**要件との差分**:
- 要件では `/api/v1/projects` POST（プロジェクト作成）が必要
- 要件では `/api/v1/projects/{id}` GET（プロジェクト取得）が必要
- 要件では `/api/v1/runs` GET（Run一覧）が必要
- 要件では `/api/v1/runs/{id}` GET（Run取得）が必要
- 要件では `/api/v1/plans` GET（Plan一覧）が必要

### Step 2: Pydanticスキーマの作成

**作成したファイル**:

1. **`src/nexuscore/api/schemas/error.py`**:
   - `ErrorDetail`: エラー詳細モデル（code, message）
   - `ErrorResponse`: 標準化されたエラーレスポンスモデル

2. **`src/nexuscore/api/schemas/project.py`**:
   - `ProjectBase`: Project の基本フィールド
   - `ProjectCreateRequest`: Project 作成リクエストモデル
   - `ProjectSummary`: Project サマリーモデル（一覧表示用）
   - `ProjectResponse`: Project 詳細レスポンスモデル
   - `ProjectListResponse`: Project 一覧レスポンスモデル

3. **`src/nexuscore/api/schemas/run.py`**:
   - `RunSummary`: Run サマリーモデル（一覧表示用）
   - `RunResponse`: Run 詳細レスポンスモデル
   - `RunListResponse`: Run 一覧レスポンスモデル

4. **`src/nexuscore/api/schemas/plan.py`**:
   - `PlanTask`: 計画タスクモデル
   - `PlanSummary`: Plan サマリーモデル（一覧表示用）
   - `PlanResponse`: Plan 詳細レスポンスモデル
   - `PlanListResponse`: Plan 一覧レスポンスモデル

**実装理由**:
- 既存のFlask実装の仕様に完全に準拠
- Pydantic の型安全性を活用
- OpenAPI スキーマに自動反映される
- 共通項目（id, created_at, updated_at）を含む

### Step 3: FastAPIルータの実装

**作成したファイル**:

1. **`src/nexuscore/api/routes/projects.py`**:
   - GET `/api/v1/projects`: プロジェクト一覧取得
   - POST `/api/v1/projects`: プロジェクト作成
   - GET `/api/v1/projects/{project_id}`: プロジェクト取得

2. **`src/nexuscore/api/routes/runs.py`**:
   - GET `/api/v1/runs`: Run一覧取得（project_id でフィルタ可能）
   - GET `/api/v1/runs/{run_id}`: Run取得

3. **`src/nexuscore/api/routes/plans.py`**:
   - GET `/api/v1/plans`: Plan一覧取得（現時点では空のリストを返す）

**実装内容**:
- 既存のFlask実装と同じロジックを使用（データベースクエリ、所有権確認など）
- 認証 DI (`Depends(get_current_user)`) を適用
- 統一されたエラーハンドリング（HTTPException）
- 既存のFlask実装との互換性を保つアダプター関数 (`_get_user_id_from_auth`)

**実装理由**:
- 既存のFlask実装と互換性を保つ
- FastAPI の標準 DI パターンに従う
- すべての Public API に一貫した認証方式を適用

### Step 4: 認証依存の改善

**変更ファイル**: `src/nexuscore/api/dependencies/auth.py`

**変更内容**:
- `get_current_user()` を改善し、データベースからAPI Keyを検証してユーザーを取得
- 既存のFlask実装 (`api_key_required`) と互換性を保つ
- `AuthenticatedUser.user_id` に実際のユーザーIDを含める

**実装理由**:
- 既存のFlask実装では `g.current_api_user.id` を使用しているため、FastAPI版でも同じユーザーIDを取得する必要がある
- データベースベースのAPI Key認証を実装

### Step 5: FastAPIアプリへのルータ登録

**変更ファイル**: `src/nexuscore/api/fastapi_app.py`

**変更内容**:
- `projects.router`, `runs.router`, `plans.router` をインポート
- `/api/v1` プレフィックスでマウント

**確認事項**:
- OpenAPI スキーマに `/api/v1/projects`, `/api/v1/runs`, `/api/v1/plans` が自動反映される

### Step 6: テストの作成

**作成したファイル**:

1. **`tests/api/test_fastapi_projects.py`**:
   - `test_list_projects_success` - プロジェクト一覧取得の正常系
   - `test_list_projects_requires_authentication` - 認証必須の確認
   - `test_create_project_success` - プロジェクト作成の正常系
   - `test_create_project_validation_error` - バリデーションエラー
   - `test_get_project_success` - プロジェクト取得の正常系
   - `test_get_project_not_found` - プロジェクトが見つからない場合
   - `test_projects_endpoints_are_documented_in_openapi` - OpenAPI スキーマの確認
   - `test_projects_response_structure` - レスポンス構造の詳細確認

2. **`tests/api/test_fastapi_runs.py`**:
   - `test_list_runs_success` - Run一覧取得の正常系
   - `test_list_runs_with_project_filter` - プロジェクトIDでフィルタ
   - `test_list_runs_requires_authentication` - 認証必須の確認
   - `test_get_run_success` - Run取得の正常系
   - `test_get_run_not_found` - Runが見つからない場合
   - `test_runs_endpoints_are_documented_in_openapi` - OpenAPI スキーマの確認
   - `test_runs_response_structure` - レスポンス構造の詳細確認

**実装理由**:
- 既存のFlaskテストの期待値に準拠
- FastAPI版の動作を保証
- OpenAPI スキーマの整合性を確認
- ステータスコード、レスポンス構造、エラーハンドリングを確認

## 変更ファイル一覧

### 新規作成ファイル
- `src/nexuscore/api/schemas/error.py` - 標準化されたエラーレスポンススキーマ
- `src/nexuscore/api/schemas/project.py` - Project API 用のPydanticスキーマ
- `src/nexuscore/api/schemas/run.py` - Run API 用のPydanticスキーマ
- `src/nexuscore/api/schemas/plan.py` - Plan API 用のPydanticスキーマ
- `src/nexuscore/api/routes/projects.py` - Projects ルータの実装
- `src/nexuscore/api/routes/runs.py` - Runs ルータの実装
- `src/nexuscore/api/routes/plans.py` - Plans ルータの実装
- `tests/api/test_fastapi_projects.py` - FastAPI Projects エンドポイントのテスト
- `tests/api/test_fastapi_runs.py` - FastAPI Runs エンドポイントのテスト

### 変更ファイル
- `src/nexuscore/api/dependencies/auth.py` - API Key認証の改善（データベースベースの認証）
- `src/nexuscore/api/fastapi_app.py` - Projects, Runs, Plans ルータの登録

### 変更なし（既存実装を再利用）
- `src/nexuscore/webapp/models.py` - データベースモデル（変更なし）
- `src/nexuscore/webapp/api_external.py` - 既存のFlask実装（変更なし）

## 動作確認結果

### 静的解析結果
- リンターエラー: なし
- 型チェック: 問題なし

### テスト結果

**実行コマンド**:
```bash
source myenv_linux/bin/activate
export PYTHONPATH=/home/yn441611/NexusCore/src:$PYTHONPATH
export NEXUSCORE_API_KEY=test-api-key-123
python -m pytest tests/api/test_fastapi_projects.py -v
python -m pytest tests/api/test_fastapi_runs.py -v
```

**結果**:
- Projects テスト: 8個のテストケースを実装
- Runs テスト: 7個のテストケースを実装
- すべてのテストが正常に通過（モックベースのテスト）

**確認項目**:
- ✅ `/api/v1/projects` GET が 200 を返す
- ✅ `/api/v1/projects` POST が 201 を返す
- ✅ `/api/v1/projects/{id}` GET が 200 を返す
- ✅ `/api/v1/runs` GET が 200 を返す
- ✅ `/api/v1/runs/{id}` GET が 200 を返す
- ✅ 認証ヘッダ未指定で 422 を返す
- ✅ 存在しないリソースで 404 を返す
- ✅ OpenAPI スキーマにすべてのエンドポイントが定義されている
- ✅ レスポンス構造が Pydantic モデルに準拠している

### コードレビュー結果
- ✅ `.cursorrules` のルールに準拠
- ✅ Pydantic BaseModel を使用したリクエスト/レスポンスモデル
- ✅ `/api/v1` プレフィックスの使用
- ✅ `Depends(get_current_user)` による認証
- ✅ 既存のFlask実装に影響なし
- ✅ 統一されたエラーモデル

## 設計上の改善点

### アーキテクチャの改善
1. **型安全性の向上**
   - すべての Request/Response を Pydantic BaseModel で型定義
   - OpenAPI スキーマへの自動反映
   - IDE での型補完とエラーチェックが可能に

2. **責務分離の明確化**
   - API 層（routes）とスキーマ層（schemas）の分離
   - ビジネスロジックは core 層に委譲
   - 既存のFlask実装との互換性を保つアダプター関数

3. **統一されたエラーモデル**
   - すべてのエンドポイントで統一されたエラー構造
   - `ErrorResponse` モデルによる一貫性の確保
   - FastAPI の HTTPException に統一

### 将来の拡張性への配慮
1. **Plan モデルの実装**
   - 現時点では Plan モデルがデータベースに存在しないため、空のリストを返す
   - 将来的に Plan モデルが実装されたら、実際のデータを返すように更新可能

2. **認証方式の拡張**
   - データベースベースのAPI Key認証を実装
   - 将来的に JWT 認証を追加可能な構造

3. **フィルタリング機能の拡張**
   - Run一覧で project_id によるフィルタリングを実装
   - 将来的に status, date_range などのフィルタリングを追加可能

### コード品質の向上
1. **明確な型定義**
   - Pydantic BaseModel による明示的なリクエスト/レスポンスモデル
   - OpenAPI スキーマへの自動反映
   - ドキュメント生成の自動化

2. **テストカバレッジ**
   - 既存のFlaskテストの期待値に準拠したテスト実装
   - FastAPI版の動作を保証
   - OpenAPI スキーマの整合性を確認

3. **エラーハンドリングの統一**
   - 統一されたエラーモデル
   - FastAPI の HTTPException に統一
   - 適切なステータスコードの使用

## 既知の制約・注意事項

### 既存コードとの互換性
- ✅ 既存の Flask アプリケーション (`src/nexuscore/webapp/api_external.py`) には影響なし
- ✅ 既存のデータベースモデルを再利用
- ✅ 既存のFlask実装と同じロジックを使用

### 制限事項やトレードオフ
1. **認証の実装**
   - データベースベースのAPI Key認証を実装
   - 既存のFlask実装 (`api_key_required`) と互換性を保つ
   - 環境変数ベースの認証はフォールバックとして実装

2. **Plan モデル**
   - 現時点では Plan モデルがデータベースに存在しないため、空のリストを返す
   - 将来的に Plan モデルが実装されたら、実際のデータを返すように更新が必要

3. **実行環境**
   - WSL Ubuntu 環境での動作確認済み
   - `myenv_linux` 仮想環境での動作確認済み
   - データベース接続が必要（本番環境）

### 移行時の注意点
- FastAPI アプリは既存の Flask アプリとは別ポートで実行可能
- 既存の API クライアントは X-API-Key ヘッダーを使用する必要がある
- データベースベースのAPI Key認証を使用する場合、データベース接続が必要

## 次のステップ

### 推奨されるフォローアップアクション

1. **他のエンドポイントの移行**
   - CR-FASTAPI-000 で棚卸しした Public endpoints の移行を継続
   - `/api/v1/projects/<project_id>/run` の移行
   - `/api/v1/projects/<project_id>/runs/latest` の移行

2. **Plan モデルの実装**
   - Plan データベースモデルの実装
   - Plan エンドポイントの完全実装

3. **フィルタリング機能の拡張**
   - Run一覧で status, date_range などのフィルタリングを追加
   - Project一覧で name, repo_url などのフィルタリングを追加

4. **ドキュメント整備**
   - OpenAPI スキーマの詳細化
   - エンドポイントごとの説明文追加
   - 使用例の追加

5. **パフォーマンス最適化**
   - ページネーションの実装
   - キャッシュの追加
   - クエリ最適化

## 関連ドキュメント

- [API Inventory (CR-FASTAPI-000)](./api_inventory.md)
- [FastAPI Migration Prompts](./README.md)
- [CR-FASTAPI-001 Completion Report](./CR-FASTAPI-001_COMPLETION_REPORT.md)
- [CR-FASTAPI-002 Completion Report](./CR-FASTAPI-002_COMPLETION_REPORT.md)
- [CR-FASTAPI-003 Completion Report](./CR-FASTAPI-003_COMPLETION_REPORT.md)
- [CR-FASTAPI-004 Completion Report](./CR-FASTAPI-004_COMPLETION_REPORT.md)
- [.cursorrules](../../.cursorrules)

## まとめ

CR-FASTAPI-005 の実装により、Pydantic モデルの分離と API 型安全化が完成しました。既存の Flask 実装と互換性を保ちながら、すべての Request/Response を Pydantic BaseModel で型定義し、OpenAPI スキーマへの自動反映を実現しました。統一されたエラーモデルと FastAPI の標準 DI パターンに従った実装により、SaaS 外部公開に耐える構造へ移行しました。

すべてのテストが成功し、`.cursorrules` のルールに準拠した実装が完了しています。

