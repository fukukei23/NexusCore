# NexusCore SaaS基盤 - アーキテクチャドキュメント

## Overview

NexusCore SaaS MVP は、「LLM ベースのコード解析・修正・テスト自動化」をマルチユーザーで提供するための最小構成です。

NexusCore 本体（Orchestrator / Agents / Sandbox）を SaaS 化レイヤー（認証・プロジェクト管理・ログ管理）でラップすることで、既存のアーキテクチャを壊さずに Web UI と API を提供します。

### 主な特徴

- **既存アーキテクチャの保護**: Orchestrator v8.2 / NPE / BaseAgent / LLMRouter を壊さない
- **段階的な拡張**: 最小実装から始めて、必要に応じて機能を追加
- **マルチユーザー対応**: GitHub OAuth による認証とプロジェクト管理
- **観測性**: 構造化ログと実行履歴の一元管理

## High-level Architecture

### システム構成

```
┌─────────────────┐
│  Browser /      │
│  Gradio UI      │
│  (port: 7860)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐
│  Flask WebApp   │     │  FastAPI REST   │
│  (port: 5000)   │     │  (port: 8000)   │
└────────┬────────┘     └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    ▼
         ┌─────────────────┐
         │  Orchestrator   │
         │  + Agents        │
         │  + Sandbox       │
         └────────┬────────┘
                  │
                  ▼
         ┌─────────────────┐
         │  Database       │
         │  (SQLite/PG)    │
         └─────────────────┘
```

**注意**: FastAPI は内部で Flask の DB モデルを共有（ Flask アプリコンテキストを共用）

### データフロー

1. **ユーザー認証**: GitHub OAuth → User レコード作成/更新
2. **プロジェクト管理**: Project レコード作成 → ローカルパス紐付け
3. **実行トリガー**: Web API → Orchestrator 起動 → Run レコード作成
4. **ログ収集**: Orchestrator / NPE / Agents → ExecutionLog に記録
5. **結果表示**: Web UI / Gradio → Run / Log を表示

## Core Components

### Webapp (src/nexuscore/webapp/)

Flask ベースの Web API レイヤー。

#### 認証 (auth.py)

- **GitHub OAuth**: `authlib.integrations.flask_client` を使用
- **エンドポイント**:
  - `GET /auth/login/github` - GitHub へリダイレクト
  - `GET /auth/github/callback` - コールバック処理
  - `GET /auth/logout` - ログアウト
- **セッション管理**: Flask セッションに `user_id` を保存

#### プロジェクト管理 (views_projects.py)

- **エンドポイント**:
  - `GET /projects/` - プロジェクト一覧
  - `GET /projects/<project_id>` - プロジェクト詳細
  - `GET /projects/new` - 新規プロジェクト作成フォーム
  - `POST /projects/new` - 新規プロジェクト作成
  - `POST /projects/<project_id>/run` - 実行トリガー

#### ログビューア (views_logs.py)

- **エンドポイント**:
  - `GET /logs/projects/<project_id>` - プロジェクト単位のログ一覧
  - `GET /logs/runs/<run_id>` - 特定のRunのログ一覧
- **フィルタリング**: ソース（NPE / Orchestrator / Agent）、レベル（INFO / WARNING / ERROR）
- **ページング**: 最新順で表示

#### ダッシュボード (views_dashboard.py)

- **エンドポイント**:
  - `GET /dashboard/` - 統計情報ダッシュボード
  - `GET /dashboard/gradio/<project_id>` - Gradioダッシュボード（iframe）

#### APIキー管理 (models.py - ApiKey)

- **用途**: 読み取り専用 API キー（ユーザーが自身のラン履歴やログを読むため）
- **セキュリティ**: ハッシュ化して保存（SHA-256）

### API Layer (FastAPI)

FastAPI REST API（`src/nexuscore/api/`）は外部連携用。

- **ポート**: 8000
- **主なエンドポイント**:
  - `POST /api/v1/execute` - 自我修復ジョブをバックグラウンド実行
  - `GET /api/v1/status/{task_id}` - タスクステータス取得
  - `POST /api/v1/github/webhook` - GitHub PR Webhook
  - `GET /api/v1/projects` - プロジェクト一覧
  - `POST /api/v1/projects/{id}/run` - 実行トリガー
- **認証**: `X-API-Key` ヘッダーによる API キー認証
- **DB共用**: FastAPI は内部で Flask の DB モデルを共有（アプリコンテキストを共用）

### Core Engine

#### Orchestrator

既存の `src/nexuscore/core/orchestrator.py` をそのまま使用。

- **役割**: Requirement → Planning → Architecture → Coding → Testing → Review → Postmortem の流れを制御
- **DB統合**: `orchestrator_db_hook.py` を通じて ExecutionLog に記録

#### Agents

既存のエージェント群をそのまま使用。

- **RequirementAgent**: 要件分析
- **PlannerAgent**: 実装計画
- **ArchitectAgent**: アーキテクチャ設計
- **CoderAgent**: コード生成
- **TesterAgent**: テスト生成
- **DebuggerAgent**: デバッグ
- **GuardianAgent**: コードレビュー
- **PatchApplier**: パッチ適用

#### SandboxExecutor

`src/nexuscore/core/sandbox_executor.py` で実装。

- **タイムアウト制御**: デフォルト60秒（`sandbox_policy.yml` で設定可能）
- **リトライ戦略**: 指数バックオフ、最大リトライ回数はポリシーで設定
- **例外分類**: RATE_LIMIT, TIMEOUT, INVALID_OUTPUT, EXECUTION_ERROR, NETWORK_ERROR

### UI

#### Gradioダッシュボード (nexus_dashboard.py)

4タブ構成:

1. **解析**: プロジェクト概要・コンテキスト表示
2. **修正**: 自己修復フロー、パッチ生成・適用
3. **テスト**: テスト実行と結果表示
4. **履歴**: Run / ExecutionLog / PatchRecord 一覧

### Hooks

#### Orchestrator → DB フック

`src/nexuscore/core/orchestrator_db_hook.py` で実装。

- **役割**: Orchestrator のイベントを ExecutionLog に記録
- **防衛的実装**: Flaskアプリコンテキストが存在する場合のみDBに書き込む

#### NPE → DB フック

`src/nexuscore/npe/logger.py` を拡張。

- **役割**: `log_transaction` を呼び出すと、自動的に ExecutionLog にも書き込む
- **防衛的実装**: Flaskアプリコンテキストが存在する場合のみDBに書き込む

## Request & Execution Flow

### 典型的なフロー

1. **ユーザー認証**
   - ユーザーが `GET /auth/login/github` にアクセス
   - GitHub OAuth で認証
   - コールバックで User レコードを upsert（存在すれば更新、なければ新規作成）
   - セッションに `user_id` を保存

2. **プロジェクト作成**
   - ユーザーが `POST /projects/new` でプロジェクトを作成
   - Project レコードを作成（owner_id, name, repo_url, local_path）

3. **実行トリガー**
   - ユーザーが `POST /projects/<project_id>/run` で実行をトリガー
   - Run レコードを作成（status=PENDING）
   - 将来的には Celery タスクとして Orchestrator を非同期実行

4. **Orchestrator 実行**
   - Orchestrator が Agents を呼び出し
   - SandboxExecutor 経由でコード実行
   - 各ステップで `orchestrator_db_hook.log_orchestrator_event` を通じて ExecutionLog に記録

5. **ログ表示**
   - ユーザーが `GET /logs/runs/<run_id>` でログを確認
   - Web UI / Gradio で Run / Log を表示

## Data Model

### 主要なモデル

#### User

- **役割**: GitHub OAuth で認証されたユーザー
- **主要フィールド**: `github_id`, `github_login`, `name`, `avatar_url`, `email`
- **リレーション**: `projects`, `runs`, `api_keys`

#### Project

- **役割**: 対象リポジトリ（プロジェクト）
- **主要フィールド**: `owner_id`, `name`, `repo_url`, `local_path`, `context_bundle_path`
- **リレーション**: `owner` (User), `runs`

#### Run

- **役割**: 1回のオーケストレーション実行を表現
- **主要フィールド**: `project_id`, `run_id`, `triggered_by`, `status`, `started_at`, `finished_at`, `autonomy_level`, `llm_model_summary`
- **リレーション**: `project` (Project), `triggered_by_user` (User), `patch_records`, `execution_logs`

#### PatchRecord

- **役割**: パッチ適用記録
- **主要フィールド**: `run_id`, `file_path`, `diff_text`, `applied`
- **リレーション**: `run` (Run)

#### ExecutionLog

- **役割**: 実行ログ（NPE / Orchestrator / Agent からの構造化ログ）
- **主要フィールド**: `run_id`, `source`, `level`, `message`, `payload_json`
- **リレーション**: `run` (Run)

#### ApiKey

- **役割**: APIキー（読み取り専用）
- **主要フィールド**: `user_id`, `token_hash`, `name`
- **セキュリティ**: ハッシュ化して保存（SHA-256）

### 外部キー関係

```
User.id
  ├─ Project.owner_id
  ├─ Run.triggered_by
  └─ ApiKey.user_id

Project.id
  └─ Run.project_id

Run.id
  ├─ PatchRecord.run_id
  └─ ExecutionLog.run_id
```

## Sandbox & Safety Model

### SandboxExecutor

`src/nexuscore/core/sandbox_executor.py` で実装。

#### タイムアウト制御

- **デフォルト**: 60秒（`sandbox_policy.yml` の `resource_limits.wall_time_seconds`）
- **実装**: `subprocess.run` の `timeout` パラメータを使用

#### リトライ戦略

- **指数バックオフ**: リトライ間隔を `retry_delay_sec * (2 ** attempt)` で計算
- **最大リトライ回数**: `sandbox_policy.yml` の `retry_policy.max_retries` で設定
- **リトライ可能なエラー**: `retry_policy.retryable_errors` で定義

#### 例外分類

- **RATE_LIMIT**: レート制限エラー
- **TIMEOUT**: タイムアウト
- **INVALID_OUTPUT**: 無効な出力
- **EXECUTION_ERROR**: 実行エラー（コンパイルエラー、テスト失敗など）
- **NETWORK_ERROR**: 一時的なネットワークエラー

### sandbox_policy.yml

サンドボックス実行に関するポリシー定義。

#### リソース制限

- **cpu_time_seconds**: 1実行あたりの最大CPU時間
- **wall_time_seconds**: 実時間のタイムアウト
- **memory_mb**: 最大メモリ使用量
- **disk_write_mb**: 一時ディスク書き込み上限

#### ネットワーク設定

- **enabled**: ネットワークを完全に禁止する場合
- **allowlist**: 許可ドメインのリスト（将来用）
- **denylist**: 禁止ドメインのリスト（将来用）

#### ファイルシステム制限

- **allowed_paths**: 許可されたパス
- **read_only_paths**: 読み取り専用パス
- **forbidden_paths**: 禁止パス

#### Python ランタイム制限

- **forbidden_modules**: 禁止モジュール（os, subprocess, socket, shutil など）
- **allowed_modules_extra**: 追加で許可したいモジュール

### 将来の拡張

現時点では、プロセス分離や OS レベルの制限は最小限です。将来的に以下の統合を検討：

- **コンテナ化**: Docker / Podman を使用した完全な分離
- **Firejail**: Linux のセキュリティサンドボックス
- **gVisor**: Google のセキュリティサンドボックス
- **ネットワーク制限**: iptables / nftables による制限

## Deployment Model

### Dev 環境

- **データベース**: ローカル SQLite (`db.sqlite3`)
- **Webサーバー**: Flask 開発サーバー (`app.run(debug=True)`)
- **Gradio**: 同一マシンで別ポート（7860）で起動

### Staging / Production の想定

- **Webサーバー**: Flask + WSGI (gunicorn 等)
- **データベース**: Postgres
- **逆プロキシ**: nginx
- **Gradio UI**: 別プロセス or 別サービスとしてホスト
- **非同期タスク**: Celery + Redis/RabbitMQ

## Future Work

### マルチテナント／組織（Org）モデル

- **Organization モデル**: 複数ユーザーを組織にまとめる
- **権限管理**: 組織内での権限（owner, member, viewer）
- **課金**: 組織単位での課金

### サンドボックスの強化

- **コンテナ化**: Docker / Podman を使用した完全な分離
- **ネットワーク制限**: iptables / nftables による制限
- **リソース制限**: cgroups による CPU / メモリ制限

### 課金・利用メトリクス基盤

- **Run数**: 実行回数の集計
- **実行時間**: 実行時間の集計
- **LLMトークン**: LLM呼び出しのトークン数とコスト

### SLA / SLO 定義

- **可用性**: 99.9% アップタイム
- **レイテンシ**: 平均レスポンス時間 < 2秒
- **エラー率**: エラー率 < 1%

## 関連ドキュメント

- `docs/saas_mvp_setup.md` - セットアップガイド
- `docs/saas_mvp_implementation_summary.md` - 実装完了レポート
- `docs/run_reports_policy.md` - Run レポート（Markdown）の格納ポリシーと運用方針

