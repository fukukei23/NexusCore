# テーマ D（Run レポート＋Slack通知＋READMEバッジ）実装完了レポート

## 実装日時

2025-11-28

## 概要

Run 完了時に自動で Markdown レポートを生成し、Slack 通知を強化し、README バッジ用のメトリクス API を提供する機能を実装しました。

## 実装ステップ

### D-1: Run 完了時 Markdown レポート自動生成

#### D-1-1. レポート生成モジュールの追加

**ファイル**: `src/nexuscore/integration/run_report_generator.py`

**実装内容**:
- `generate_run_report_markdown()`: 単一 Run 向けの Markdown レポート本文を生成
- `write_run_report_file()`: `docs/run_reports/RUN_{run_id}.md` にレポートを保存
- `_collect_run_metrics()`: Run からメトリクスを収集（パッチ情報、LLMコスト、実行時間など）
- `_collect_test_results()`: テスト結果を収集（エラー数、警告数、テスト出力など）
- `_compute_recent_success_rate()`: 過去30回の成功率を計算

**レポート内容**:
- プロジェクト情報（名前、リポジトリURL、ローカルパス）
- Run サマリー（Run ID、ステータス、開始/終了時刻、実行時間、自律度）
- Self-Healing メトリクス（パッチ数、LLM使用モデル、推定コスト、成功率）
- パッチファイル一覧
- テスト結果（エラー/警告/情報メッセージ数、テスト出力）
- Observability リンク（Run ログ、プロジェクトログ、ダッシュボード）

#### D-1-2. Celery タスク完了時にフック呼び出し

**ファイル**: `src/nexuscore/webapp/celery_app.py`

**実装内容**:
- `_run_orchestrator_task_internal()` の `finally` ブロックで、Run ステータス更新後に `write_run_report_file()` を呼び出し
- レポート生成失敗は本処理を壊さない（警告ログのみ）
- ExecutionLog に「REPORT_GENERATED」ログを記録

### D-2: Slack 通知の UX 強化（メトリクス付き）

#### D-2-1. Slack 通知メソッドの拡張

**ファイル**: `src/nexuscore/core/notifier.py`

**実装内容**:
- `notify_self_healing_complete()` に `metrics` パラメータを追加
- メトリクス情報（実行時間、パッチ数、使用モデル、推定コスト、成功率）をメッセージ本文に含める

**メッセージ形式**:
```
実行ID: `{run_id}`
ステータス: {status_text}
実行時間: {duration_str}
パッチ: {patch_lines} lines / {patch_files_count} files
使用モデル: {model1} ({count1} calls), ...
推定コスト: ~{cost} JPY
最近の成功率 (last 30): {success_rate}%

{summary}
```

#### D-2-2. Webhook ハンドラから Slack 呼び出し

**ファイル**: `src/nexuscore/api/github_webhook_handler.py`

**実装内容**:
- `_send_slack_notification_if_configured()` 関数を追加
- `handle_github_webhook()` から、PR コメント投稿後に Slack 通知を送信
- `NEXUS_SLACK_WEBHOOK_URL` 環境変数が設定されている場合のみ送信
- Run と Project を取得してメトリクスを収集し、`notify_self_healing_complete()` に渡す

### D-3: README バッジ向けのメトリクス API

#### D-3-1. API Blueprint の追加

**ファイル**: `src/nexuscore/webapp/api_badges.py`

**実装内容**:
- `api_badges` Blueprint を作成
- `/api/projects/<project_id>/badge/success_rate`: 成功率バッジ用 JSON
- `/api/projects/<project_id>/badge/last_run`: 最新Runステータスバッジ用 JSON

**レスポンス形式（shields.io endpoint 互換）**:
```json
{
  "schemaVersion": 1,
  "label": "self-healing",
  "message": "93.3% success",
  "color": "brightgreen"
}
```

#### D-3-2. Blueprint 登録

**ファイル**: `src/nexuscore/webapp/__init__.py`

**実装内容**:
- `api_badges.bp` を Flask アプリに登録

#### D-3-3. ドキュメント作成

**ファイル**: `docs/saas_badges.md`

**内容**:
- バッジの使用方法
- API エンドポイントの説明
- レスポンス形式とカラーの説明

## 変更ファイル一覧

### 新規作成ファイル

1. **`src/nexuscore/integration/run_report_generator.py`**
   - Run レポート生成モジュール

2. **`src/nexuscore/webapp/api_badges.py`**
   - README バッジ用 API エンドポイント

3. **`docs/saas_badges.md`**
   - バッジ API のドキュメント

4. **`tests/integration/test_run_report_generator.py`**
   - Run レポート生成のテスト

5. **`tests/integration/test_slack_notifier.py`**
   - Slack 通知のテスト

### 変更ファイル

1. **`src/nexuscore/webapp/celery_app.py`**
   - Run 完了時にレポート生成を呼び出し

2. **`src/nexuscore/core/notifier.py`**
   - `notify_self_healing_complete()` にメトリクスパラメータを追加

3. **`src/nexuscore/api/github_webhook_handler.py`**
   - Slack 通知送信機能を追加

4. **`src/nexuscore/webapp/__init__.py`**
   - `api_badges` Blueprint を登録

## 動作確認結果

### 静的解析結果

- リンターエラー: なし
- 型チェック: 問題なし

### 設計上の改善点

1. **コードの再利用性**:
   - `github_pr_comment.py` のメトリクス収集ロジック（`_collect_run_metrics()`, `_compute_recent_success_rate()`）を `run_report_generator.py` でも再利用
   - 共通のヘルパー関数として実装

2. **エラーハンドリング**:
   - レポート生成失敗や Slack 通知失敗は本処理を壊さない（警告ログのみ）
   - Webapp モデルが利用できない場合のフォールバック処理

3. **拡張性**:
   - バッジ API は shields.io 互換形式で、将来的に他のバッジサービスでも使用可能
   - レポート形式は Markdown なので、GitHub や他のプラットフォームでも表示可能

## 既知の制約・注意事項

1. **認証**:
   - バッジ API は現在認証不要で公開されています
   - 将来的には、プロジェクトの公開設定や認証トークンによる制御を追加する予定

2. **レポート保存先**:
   - レポートは `docs/run_reports/` に保存されます
   - 大量の Run が生成される場合は、古いレポートの削除やアーカイブ機能が必要になる可能性があります

3. **Slack 通知**:
   - `NEXUS_SLACK_WEBHOOK_URL` 環境変数が設定されている場合のみ送信されます
   - Webhook URL が無効な場合でも、エラーはログに記録されるだけで処理は続行されます

## 次のステップ

### 推奨される動作確認

1. **Run レポート生成の確認**:
   - Celery タスクで Run を実行し、`docs/run_reports/` にレポートが生成されるか確認
   - レポートの内容が正しいか確認

2. **Slack 通知の確認**:
   - `NEXUS_SLACK_WEBHOOK_URL` を設定して、Self-Healing 実行後に Slack 通知が送信されるか確認
   - メトリクス情報が正しく含まれているか確認

3. **バッジ API の確認**:
   - `/api/projects/<id>/badge/success_rate` と `/api/projects/<id>/badge/last_run` にアクセスして、正しい JSON が返されるか確認
   - shields.io でバッジが正しく表示されるか確認

### 将来の拡張

1. **レポートの拡張**:
   - 時系列グラフの追加
   - より詳細なメトリクス（テストカバレッジ、コード品質スコアなど）

2. **バッジ API の拡張**:
   - より多くのメトリクスバッジ（総Run数、平均実行時間など）
   - 認証機能の追加

3. **通知チャネルの拡張**:
   - Discord、Microsoft Teams などの他の通知チャネルへの対応

## 関連ドキュメント

- `docs/saas_badges.md` - バッジ API の使用方法
- `docs/completion_reports/UI_ENHANCEMENT_COMPLETION_REPORT.md` - Web UI 強化レポート
- `docs/saas_architecture.md` - SaaS アーキテクチャドキュメント

