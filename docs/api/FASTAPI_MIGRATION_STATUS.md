# FastAPI Migration Status

このドキュメントは、NexusCore の Flask REST API から FastAPI への移行状況を追跡します。

## 概要

NexusCore では、外部向けの正式な API レイヤーを FastAPI（`/api/v1/`）に完全統一することを目指しています。
Flask ベースの REST API は段階的に非推奨化され、最終的に削除される予定です。

**重要**: Flask Web UI（HTMLテンプレート・ビュー）や Flask-SQLAlchemy による DB 層は当面残します。
この移行は「REST API の互換レイヤー（Flask）」のみを対象とします。

## 移行状況一覧

| Category   | Flask Endpoint                    | FastAPI Endpoint                    | Status        | Notes                                    |
|------------|-----------------------------------|-------------------------------------|---------------|------------------------------------------|
| Execute    | `/api/v1/execute` (POST)          | `/api/v1/execute` (POST)           | Removed (Flask)| Removed in CR-FASTAPI-008; use FastAPI /api/v1/execute only. |
| Status     | `/api/v1/status/<task_id>` (GET) | `/api/v1/status/{task_id}` (GET)   | Removed (Flask)| Removed in CR-FASTAPI-008; use FastAPI /api/v1/status/{task_id} only. |
| Projects   | `/api/v1/projects` (GET)         | `/api/v1/projects` (GET)           | Removed (Flask)| Removed in CR-FASTAPI-010; use FastAPI /api/v1/projects only. |
| Projects   | `/api/v1/projects` (POST)        | `/api/v1/projects` (POST)          | Removed (Flask)| Removed in CR-FASTAPI-010; use FastAPI /api/v1/projects only. |
| Projects   | `/api/v1/projects/<id>` (GET)    | `/api/v1/projects/{id}` (GET)      | Removed (Flask)| Removed in CR-FASTAPI-010; use FastAPI /api/v1/projects/{id} only. |
| Runs       | `/api/v1/runs` (GET)             | `/api/v1/runs` (GET)               | Removed (Flask)| Removed in CR-FASTAPI-010; use FastAPI /api/v1/runs only. |
| Runs       | `/api/v1/runs/<id>` (GET)         | `/api/v1/runs/{id}` (GET)          | Removed (Flask)| Removed in CR-FASTAPI-010; use FastAPI /api/v1/runs/{id} only. |
| Plans      | N/A                               | `/api/v1/plans` (GET)              | New           | FastAPI のみ実装                          |
| GitHub     | `/api/github/webhook` (POST)      | `/api/v1/github/webhook` (POST)    | Migrated      | FastAPI 側が正式版。Flask は廃止候補     |
| Health     | N/A                               | `/api/v1/health` (GET)              | New           | FastAPI のみ実装                          |
| Projects   | `/api/v1/projects/<id>/run` (POST)| `/api/v1/projects/{id}/run` (POST) | Removed (Flask)| Removed in CR-FASTAPI-010; use FastAPI /api/v1/projects/{id}/run only. |
| Runs       | `/api/v1/projects/<id>/runs/latest` (GET) | `/api/v1/projects/{id}/runs/latest` (GET) | Removed (Flask)| Removed in CR-FASTAPI-010; use FastAPI /api/v1/projects/{id}/runs/latest only. |
| Badges     | `/api/projects/<id>/badge/success_rate` (GET) | `/api/v1/projects/{id}/badge/success_rate` (GET) | Removed (Flask)| Removed in CR-FASTAPI-010; use FastAPI /api/v1/projects/{id}/badge/success_rate only. Path unified to /api/v1/ in CR-FASTAPI-010A. |
| Badges     | `/api/projects/<id>/badge/last_run` (GET)    | `/api/v1/projects/{id}/badge/last_run` (GET) | Removed (Flask)| Removed in CR-FASTAPI-010; use FastAPI /api/v1/projects/{id}/badge/last_run only. Path unified to /api/v1/ in CR-FASTAPI-010A. |

## ステータス説明

- **Migrated**: FastAPI に完全移行済み。Flask 側は互換レイヤーとして非推奨（Deprecated）扱い。
- **Removed (Flask)**: Flask 側のエンドポイントが物理削除済み。FastAPI 側のみ使用可能。
- **New**: FastAPI のみ実装。Flask 側には対応するエンドポイントが存在しない。
- **To-Be-Migrated**: まだ FastAPI に移行していない。次 CR で移行予定。
- **Legacy-UI-Only**: Flask Web UI 専用。今回の CR の削除対象外。
- **To-Be-Removed**: 機能としても廃止予定。

## Flask REST API の非推奨化状況

### `src/nexuscore/api/server.py`

以下のエンドポイントは CR-FASTAPI-008 で物理削除されました：

- `/api/v1/execute` (POST) - **削除済み** (CR-FASTAPI-008)。FastAPI `/api/v1/execute` を使用してください。
- `/api/v1/status/<task_id>` (GET) - **削除済み** (CR-FASTAPI-008)。FastAPI `/api/v1/status/{task_id}` を使用してください。

以下のエンドポイントはまだ Flask 側に残っています（別 CR で削除予定）：

- `/api/github/webhook` (POST) - FastAPI `/api/v1/github/webhook` に移行済み。別 CR で削除予定

**注意**: 現時点では外部クライアントから利用されていないため、利用状況ログ無しで削除しています。

### `src/nexuscore/webapp/api_external.py`

**削除済み** (CR-FASTAPI-010)

以下のエンドポイントは CR-FASTAPI-010 で物理削除されました：

- `/api/v1/projects` (GET) - **削除済み** (CR-FASTAPI-010)。FastAPI `/api/v1/projects` を使用してください。
- `/api/v1/projects/<project_id>/run` (POST) - **削除済み** (CR-FASTAPI-010)。FastAPI `/api/v1/projects/{id}/run` を使用してください。
- `/api/v1/projects/<project_id>/runs/latest` (GET) - **削除済み** (CR-FASTAPI-010)。FastAPI `/api/v1/projects/{id}/runs/latest` を使用してください。

### `src/nexuscore/webapp/api_badges.py`

**削除済み** (CR-FASTAPI-010)

以下のエンドポイントは CR-FASTAPI-010 で物理削除されました：

- `/api/projects/<project_id>/badge/success_rate` (GET) - **削除済み** (CR-FASTAPI-010)。FastAPI `/api/projects/{id}/badge/success_rate` を使用してください。
- `/api/projects/<project_id>/badge/last_run` (GET) - **削除済み** (CR-FASTAPI-010)。FastAPI `/api/projects/{id}/badge/last_run` を使用してください。

## Flask REST API 削除計画（Draft）

### Phase 1: CR-FASTAPI-008（完了）

**削除対象**:
- `src/nexuscore/api/server.py` の以下のエンドポイント:
  - `/api/v1/execute` (POST) - **削除済み**
  - `/api/v1/status/<task_id>` (GET) - **削除済み**
  - `/api/github/webhook` (POST) - 別 CR で削除予定（残存）

**削除バージョン**: v0.9.0
**削除日**: 2025-12-03 (CR-FASTAPI-008)

**実施内容**:
- Flask REST API エンドポイント `/api/v1/execute` と `/api/v1/status/<task_id>` を物理削除
- `run_orchestrator_task()` 関数を削除（FastAPI 側に実装あり）
- `tests/test_api_server.py` を削除
- `tests/api/test_server.py` を skip メッセージ更新（歴史ドキュメントとして保持）

**前提条件**:
- FastAPI 側の実装が完全に動作していることを確認済み
- 外部依存なし（現時点では外部クライアントから利用されていないため、利用状況ログ無しで削除）

**影響範囲**:
- `tests/test_api_server.py` - 削除済み
- `tests/api/test_server.py` - skip メッセージ更新済み（歴史ドキュメントとして保持）

### Phase 2: CR-FASTAPI-009（完了）

**移行対象**:
- `src/nexuscore/webapp/api_external.py` の以下のエンドポイントを FastAPI に移行:
  - `/api/v1/projects/<project_id>/run` (POST) - **移行済み**
  - `/api/v1/projects/<project_id>/runs/latest` (GET) - **移行済み**
- `src/nexuscore/webapp/api_badges.py` の以下のエンドポイントを FastAPI に移行:
  - `/api/projects/<project_id>/badge/success_rate` (GET) - **移行済み**
  - `/api/projects/<project_id>/badge/last_run` (GET) - **移行済み**

**移行日**: 2025-01-28 (CR-FASTAPI-009)

**実施内容**:
- FastAPI ルータの実装（`projects.py` に追加、`badges.py` 新規作成）
- Pydantic スキーマの作成（`project_run.py`, `badge.py`）
- テストの作成（`test_fastapi_project_runs.py`, `test_fastapi_badges.py`）
- Flask エンドポイントに DEPRECATED コメントと警告ログを追加

**削除予定バージョン**: v0.9.0
**削除予定日**: 2026-01

**前提条件**:
- FastAPI 側の実装が完全に動作していることを確認
- 外部依存が FastAPI エンドポイントを使用していることを確認
- **Warning ログを確認し、これらのエンドポイントが使用されていないことを確認**

**影響範囲**:
- 外部統合 API を使用しているクライアントが FastAPI エンドポイントを使用していることを確認
- shields.io などの外部サービスが FastAPI エンドポイントを使用していることを確認

### Phase 3: CR-FASTAPI-010（完了）

**削除対象**:
- `src/nexuscore/webapp/api_external.py` - **削除済み**
  - `/api/v1/projects` (GET) - **削除済み**
  - `/api/v1/projects/<project_id>/run` (POST) - **削除済み**
  - `/api/v1/projects/<project_id>/runs/latest` (GET) - **削除済み**
- `src/nexuscore/webapp/api_badges.py` - **削除済み**
  - `/api/projects/<project_id>/badge/success_rate` (GET) - **削除済み**
  - `/api/projects/<project_id>/badge/last_run` (GET) - **削除済み**

**削除バージョン**: v0.9.0
**削除日**: 2025-12-04 (CR-FASTAPI-010)

**実施内容**:
- Flask Blueprint (`api_external.py`, `api_badges.py`) を物理削除
- `src/nexuscore/webapp/__init__.py` から Blueprint 登録を削除
- `src/nexuscore/webapp/views_api_test.py` から `api_external` の参照を削除
- `tests/webapp/test_external_api.py` を skip（FastAPI テストを使用）

**前提条件**:
- FastAPI 側の実装が完全に動作していることを確認済み（CR-FASTAPI-001〜009）
- 外部依存が FastAPI エンドポイントを使用していることを確認済み
- Warning ログを確認し、これらのエンドポイントが使用されていないことを確認済み

## 外部依存の確認事項

削除前に確認すべき外部依存：

1. **GitHub Actions**
   - GitHub Actions ワークフローが Flask エンドポイントを使用していないか確認
   - FastAPI エンドポイントへの移行が必要な場合は、ワークフローを更新

2. **外部クライアント**
   - VSCode 拡張、Chrome 拡張などの外部クライアントが Flask エンドポイントを使用していないか確認
   - FastAPI エンドポイントへの移行が必要な場合は、クライアントを更新

3. **社内ツール**
   - 社内で使用しているツールが Flask エンドポイントを使用していないか確認
   - FastAPI エンドポイントへの移行が必要な場合は、ツールを更新

4. **shields.io などの外部サービス**
   - バッジ API を使用している外部サービスが Flask エンドポイントを使用していないか確認
   - FastAPI エンドポイントへの移行が必要な場合は、サービスを更新

## テストの整理状況

### Flask REST API テスト

以下のテストファイルは Flask REST API を前提としています：

- `tests/test_api_server.py` - Flask `/api/v1/execute` と `/api/v1/status/<task_id>` のテスト
- `tests/api/test_server.py` - Flask API サーバーのテスト

**ポリシー**:
- FastAPI での同等テストが存在する場合、Flask 側テストは skip または削除方向で整理
- FastAPI 側にまだテストがない Flask API は、この CR では「削除対象候補」とだけマーク

### FastAPI テスト

以下のテストファイルは FastAPI を前提としています：

- `tests/api/test_fastapi_execute.py` - FastAPI `/api/v1/execute` と `/api/v1/status/{task_id}` のテスト
- `tests/api/test_fastapi_projects.py` - FastAPI `/api/v1/projects` のテスト
- `tests/api/test_fastapi_runs.py` - FastAPI `/api/v1/runs` のテスト
- `tests/api/test_fastapi_github_webhook.py` - FastAPI `/api/v1/github/webhook` のテスト
- `tests/api/test_fastapi_health.py` - FastAPI `/api/v1/health` のテスト
- `tests/api/test_fastapi_auth.py` - FastAPI 認証のテスト
- `tests/api/test_fastapi_errors.py` - FastAPI エラーハンドリングのテスト

**ポリシー**:
- 「正式 API」は FastAPI ベースのテストを通す
- Flask REST API テストは「非推奨／削除予定」であることが読み取れる状態にする

## 関連ドキュメント

- [API Inventory (CR-FASTAPI-000)](./api_inventory.md)
- [FastAPI Migration Prompts](./README.md)
- [CR-FASTAPI-001 Completion Report](./CR-FASTAPI-001_COMPLETION_REPORT.md)
- [CR-FASTAPI-002 Completion Report](./CR-FASTAPI-002_COMPLETION_REPORT.md)
- [CR-FASTAPI-003 Completion Report](./CR-FASTAPI-003_COMPLETION_REPORT.md)
- [CR-FASTAPI-004 Completion Report](./CR-FASTAPI-004_COMPLETION_REPORT.md)
- [CR-FASTAPI-005 Completion Report](./CR-FASTAPI-005_COMPLETION_REPORT.md)
- [CR-FASTAPI-006 Completion Report](./CR-FASTAPI-006_COMPLETION_REPORT.md)
- [CR-FASTAPI-007 Completion Report](./CR-FASTAPI-007_COMPLETION_REPORT.md)
- [CR-FASTAPI-008 Completion Report](./CR-FASTAPI-008_COMPLETION_REPORT.md)
- [CR-FASTAPI-009 Completion Report](./CR-FASTAPI-009_COMPLETION_REPORT.md)
- [.cursorrules](../../.cursorrules)

