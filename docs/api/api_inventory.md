# API Inventory (Flask baseline)

このドキュメントは、NexusCore リポジトリ内の既存 HTTP API（主に Flask ベース）の棚卸し結果です。
FastAPI 移行の優先順位を決定するためのベースラインとして使用します。

## Public endpoints

外部公開を想定した API エンドポイント（SaaS API、Webhook など）。

| HTTP Method | Path | Module / File | Handler Function | 認証方式 | 備考 |
|------------|------|---------------|------------------|---------|------|
| POST | `/api/v1/execute` | `src/nexuscore/api/server.py` | `execute_task` | Bearer Token (NEXUSCORE_API_TOKEN) | Orchestrator タスク実行。LEGACY コメントあり。FastAPI 移行優先度高 |
| GET | `/api/v1/status/<task_id>` | `src/nexuscore/api/server.py` | `get_task_status` | no auth | タスクステータス取得。LEGACY コメントあり。FastAPI 移行優先度高 |
| POST | `/api/github/webhook` | `src/nexuscore/api/server.py` | `github_webhook_endpoint` | no auth | GitHub Webhook エンドポイント。外部公開想定 |
| GET | `/api/v1/projects` | `src/nexuscore/webapp/api_external.py` | `list_projects` | API Key (X-Api-Key) | プロジェクト一覧取得。外部統合 API |
| POST | `/api/v1/projects/<project_id>/run` | `src/nexuscore/webapp/api_external.py` | `external_trigger_run` | API Key (X-Api-Key) | Self-Healing Run 発火。外部統合 API |
| GET | `/api/v1/projects/<project_id>/runs/latest` | `src/nexuscore/webapp/api_external.py` | `get_latest_run` | API Key (X-Api-Key) | 最新Run取得。外部統合 API |
| GET | `/api/projects/<project_id>/badge/success_rate` | `src/nexuscore/webapp/api_badges.py` | `project_success_rate_badge` | no auth | shields.io 互換バッジ API。公開想定 **→ FastAPI移行済み (CR-FASTAPI-009): `/api/v1/projects/{id}/badge/success_rate`** |
| GET | `/api/projects/<project_id>/badge/last_run` | `src/nexuscore/webapp/api_badges.py` | `project_last_run_badge` | no auth | shields.io 互換バッジ API。公開想定 **→ FastAPI移行済み (CR-FASTAPI-009): `/api/v1/projects/{id}/badge/last_run`** |

## Internal endpoints

UI や内部マイクロサービスからのみ利用されるエンドポイント。

| HTTP Method | Path | Module / File | Handler Function | 認証方式 | 備考 |
|------------|------|---------------|------------------|---------|------|
| GET | `/` | `src/nexuscore/webapp/__init__.py` | `index` | no auth | ルートページ（プロジェクト一覧へリダイレクト） |
| GET | `/projects/` | `src/nexuscore/webapp/views_projects.py` | `list_projects` | Session (require_auth) | プロジェクト一覧（カード形式）。Web UI |
| GET | `/projects/<project_id>` | `src/nexuscore/webapp/views_projects.py` | `project_detail` | Session (require_auth) | プロジェクト詳細＋Run一覧。Web UI |
| GET, POST | `/projects/new` | `src/nexuscore/webapp/views_projects.py` | `create_project` | Session (require_auth) | 新規プロジェクト作成。Web UI |
| POST | `/projects/<project_id>/run` | `src/nexuscore/webapp/views_projects.py` | `trigger_run` | Session (require_auth) | Run発火（Web UI経由）。Web UI |
| GET | `/logs/projects/<project_id>` | `src/nexuscore/webapp/views_logs.py` | `project_logs` | Session (require_auth) | プロジェクト単位ログ一覧。Web UI |
| GET | `/logs/runs/<run_id>` | `src/nexuscore/webapp/views_logs.py` | `run_logs` | Session (require_auth) | Run単位ログ一覧。Web UI |
| GET | `/dashboard/` | `src/nexuscore/webapp/views_dashboard.py` | `dashboard` | Session (require_auth) | ダッシュボード（全プロジェクト）。Web UI |
| GET | `/dashboard/projects/<project_id>` | `src/nexuscore/webapp/views_dashboard.py` | `project_dashboard` | Session (require_auth) | プロジェクトダッシュボード。Web UI |
| GET | `/dashboard/gradio/<project_id>` | `src/nexuscore/webapp/views_dashboard.py` | `gradio_dashboard` | Session (require_auth) | Gradio UI iframe統合。Web UI |
| GET, POST | `/api-test/` | `src/nexuscore/webapp/views_api_test.py` | `api_test` | Session (require_auth) | API テスト UI。Web UI |
| GET | `/auth/login/github` | `src/nexuscore/webapp/auth.py` | `login_github` | no auth | GitHub OAuth ログイン開始。Web UI |
| GET | `/auth/github/callback` | `src/nexuscore/webapp/auth.py` | `github_callback` | no auth | GitHub OAuth コールバック。Web UI |
| GET | `/auth/logout` | `src/nexuscore/webapp/auth.py` | `logout` | Session (require_auth) | ログアウト。Web UI |

## Deprecated / removal candidates

現在ほぼ使われていない、または今後廃止してよいエンドポイント。

| HTTP Method | Path | Module / File | Handler Function | 認証方式 | 備考 |
|------------|------|---------------|------------------|---------|------|
| GET | `/` | `src/nexuscore/agents/constitutional_council_agent.py` | `index` | no auth | Constitutional Council Agent の内部Web UI。エージェント固有のため、FastAPI 移行対象外の可能性 |
| GET | `/approve/<filename>` | `src/nexuscore/agents/constitutional_council_agent.py` | `approve` | no auth | Constitutional Council Agent の内部Web UI。エージェント固有のため、FastAPI 移行対象外の可能性 |
| GET | `/reject/<filename>` | `src/nexuscore/agents/constitutional_council_agent.py` | `reject` | no auth | Constitutional Council Agent の内部Web UI。エージェント固有のため、FastAPI 移行対象外の可能性 |

## サマリー

- **Public endpoints**: 9件
- **Internal endpoints**: 14件
- **Deprecated / removal candidates**: 3件
- **合計**: 26件

## FastAPI 移行優先順位

### 優先度: 高（Phase 1）
1. `/api/v1/execute` - 外部公開 API、LEGACY コメントあり
2. `/api/v1/status/<task_id>` - 外部公開 API、LEGACY コメントあり
3. `/api/v1/projects` - 外部統合 API
4. `/api/v1/projects/<project_id>/run` - 外部統合 API
5. `/api/v1/projects/<project_id>/runs/latest` - 外部統合 API

### 優先度: 中（Phase 2）
6. `/api/github/webhook` - Webhook エンドポイント
7. `/api/projects/<project_id>/badge/success_rate` - バッジ API **→ FastAPI移行済み (CR-FASTAPI-009): `/api/v1/projects/{id}/badge/success_rate`**
8. `/api/projects/<project_id>/badge/last_run` - バッジ API **→ FastAPI移行済み (CR-FASTAPI-009): `/api/v1/projects/{id}/badge/last_run`**

### 優先度: 低（Phase 3）
9. Internal endpoints（Web UI） - 既存の Flask アプリと共存可能なため、段階的に移行

### 移行対象外
- Constitutional Council Agent の内部Web UI - エージェント固有のため、別途検討

## 注意事項

- `src/nexuscore/api/server.py` のエンドポイントには `# LEGACY: will be removed after FastAPI migration is completed` コメントが付いている
- 外部統合 API (`api_external.py`) は既に `/api/v1` プレフィックスを使用しているため、FastAPI 移行が容易
- Web UI エンドポイントは既存の Flask アプリと共存可能なため、段階的な移行が可能
- 認証方式の統一が必要（Bearer Token / API Key / Session）

