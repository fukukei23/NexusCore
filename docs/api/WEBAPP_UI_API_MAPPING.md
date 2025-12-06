# WebApp HTML UI と FastAPI API の対応関係

## 責務分離の原則

- **WebApp HTML UI**: 人間向け画面（HTML レンダリング、フォーム受け付け）
- **FastAPI API**: 外部/機械向け JSON API（`/api/v1/*`）

WebApp HTML UI は FastAPI を経由せず、直接データベースアクセスまたは services 層を使用します。
これは責務分離のため、FastAPI API migration の対象外です。

## 各画面のデータアクセス方法

### Projects 一覧 (`/projects/`)

- **View 関数**: `views_projects.list_projects()`
- **データアクセス**: Direct DB access (no API call)
- **FastAPI 相当エンドポイント**: `GET /api/v1/projects` (for external clients)
- **主要なリンク/ボタン**:
  - プロジェクト詳細: `/projects/{id}`
  - 新規プロジェクト作成: `/projects/new`
  - API Test UI: `/api-test/`

### プロジェクト詳細 (`/projects/{id}`)

- **View 関数**: `views_projects.project_detail()`
- **データアクセス**: Direct DB access (no API call)
- **FastAPI 相当エンドポイント**: `GET /api/v1/projects/{id}` (for external clients)
- **主要なリンク/ボタン**:
  - Run 一覧: `/projects/{id}` (同一ページ内)
  - Run 実行: `POST /projects/{id}/run`
  - ログ一覧: `/logs/projects/{id}`
  - ダッシュボード: `/dashboard/projects/{id}`

### 新規プロジェクト作成 (`/projects/new`)

- **View 関数**: `views_projects.create_project()`
- **データアクセス**: Direct DB access (no API call)
- **FastAPI 相当エンドポイント**: `POST /api/v1/projects` (for external clients)
- **主要なリンク/ボタン**:
  - プロジェクト一覧へ戻る: `/projects/`

### Run 実行 (`POST /projects/{id}/run`)

- **View 関数**: `views_projects.trigger_run()`
- **データアクセス**: Direct DB access + Orchestrator service call (no API call)
- **FastAPI 相当エンドポイント**: `POST /api/v1/projects/{id}/run` (for external clients)
- **主要なリンク/ボタン**:
  - プロジェクト詳細へ戻る: `/projects/{id}`

### プロジェクト単位ログ一覧 (`/logs/projects/{id}`)

- **View 関数**: `views_logs.project_logs()`
- **データアクセス**: Direct DB access (no API call)
- **FastAPI 相当エンドポイント**: N/A (internal UI only)
- **主要なリンク/ボタン**:
  - Run 単位ログ: `/logs/runs/{run_id}`
  - プロジェクト詳細へ戻る: `/projects/{id}`

### Run 単位ログ一覧 (`/logs/runs/{run_id}`)

- **View 関数**: `views_logs.run_logs()`
- **データアクセス**: Direct DB access (no API call)
- **FastAPI 相当エンドポイント**: `GET /api/v1/runs/{id}` (for external clients, but different data structure)
- **主要なリンク/ボタン**:
  - プロジェクト単位ログ: `/logs/projects/{project_id}`
  - プロジェクト詳細へ戻る: `/projects/{project_id}`

### ダッシュボード (`/dashboard/`)

- **View 関数**: `views_dashboard.dashboard()`
- **データアクセス**: Direct DB access (no API call)
- **FastAPI 相当エンドポイント**: N/A (internal UI only)
- **主要なリンク/ボタン**:
  - プロジェクトダッシュボード: `/dashboard/projects/{id}`

### プロジェクトダッシュボード (`/dashboard/projects/{id}`)

- **View 関数**: `views_dashboard.project_dashboard()`
- **データアクセス**: Direct DB access (no API call)
- **FastAPI 相当エンドポイント**: N/A (internal UI only)
- **主要なリンク/ボタン**:
  - Gradio UI: `/dashboard/gradio/{id}`
  - プロジェクト詳細: `/projects/{id}`

### Gradio UI 統合 (`/dashboard/gradio/{id}`)

- **View 関数**: `views_dashboard.gradio_dashboard()`
- **データアクセス**: Direct DB access (no API call)
- **FastAPI 相当エンドポイント**: N/A (internal UI only)
- **主要なリンク/ボタン**:
  - プロジェクトダッシュボードへ戻る: `/dashboard/projects/{id}`

### API Test UI (`/api-test/`)

- **View 関数**: `views_api_test.api_test()`
- **データアクセス**: N/A (UI only, no actual API call)
- **FastAPI 相当エンドポイント**:
  - `GET /api/v1/projects` (for reference)
  - `POST /api/v1/projects/{id}/run` (for reference)
- **主要なリンク/ボタン**:
  - プロジェクト一覧へ戻る: `/projects/`

## FastAPI エンドポイントとの対応表

| HTML UI 画面 | FastAPI エンドポイント | 備考 |
|-------------|---------------------|------|
| `/projects/` | `GET /api/v1/projects` | データ構造は異なる（HTML 用 vs JSON 用） |
| `/projects/{id}` | `GET /api/v1/projects/{id}` | データ構造は異なる（HTML 用 vs JSON 用） |
| `/projects/new` | `POST /api/v1/projects` | データ構造は異なる（HTML フォーム vs JSON） |
| `POST /projects/{id}/run` | `POST /api/v1/projects/{id}/run` | データ構造は異なる（HTML フォーム vs JSON） |
| `/logs/projects/{id}` | N/A | HTML UI 専用 |
| `/logs/runs/{run_id}` | `GET /api/v1/runs/{id}` | データ構造は異なる（HTML 用 vs JSON 用） |
| `/dashboard/` | N/A | HTML UI 専用 |
| `/dashboard/projects/{id}` | N/A | HTML UI 専用 |
| `/dashboard/gradio/{id}` | N/A | HTML UI 専用 |
| `/api-test/` | N/A | UI のみ（実際の API 呼び出しは行わない） |

## 重要な注意事項

1. **HTML UI は API を使わない**: WebApp HTML UI は FastAPI を経由せず、直接データベースアクセスまたは services 層を使用します。

2. **責務分離**: HTML UI = 人間向け画面、FastAPI = 外部/機械向け API という責務分離を維持します。

3. **URL 統一**: HTML UI 内で言及される API URL はすべて `/api/v1/*` 形式に統一されています（CR-NEXUS-011 で確認済み）。

4. **将来の拡張**: 新規 HTML UI 画面を作成する場合も、FastAPI を経由せず直接 DB アクセスまたは services 層を使用することを推奨します。

## 関連ドキュメント

- [FastAPI Migration Status](./FASTAPI_MIGRATION_STATUS.md)
- [API README](./README.md)
- [CR-NEXUS-011 Completion Report](./CR-NEXUS-011_COMPLETION_REPORT.md)

