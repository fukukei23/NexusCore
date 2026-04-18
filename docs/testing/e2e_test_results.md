# Self-Healing E2E テスト結果

## テスト実行日時
2025-01-XX

## テスト環境
- プロジェクトルート: `/home/yn441611/NexusCore`
- Python 環境: `myenv_linux`
- 設定ファイル: `.nexus/self_healing.config.json`

## 実装完了項目

### ✅ 1. モック Webhook ツール
- **ファイル**: `tools/mock_github_pr_webhook.py`
- **機能**:
  - `--label` オプションでラベル名を指定可能
  - `--base-branch` オプションでベースブランチを指定可能
  - GitHub Webhook ペイロードを生成して送信

### ✅ 2. Webhook ログ強化
- **ファイル**: `src/nexuscore/api/github_self_healing_webhook.py`
- **機能**:
  - `github_webhook()` 関数に `event` と `delivery` パラメータを追加
  - デバッグログを追加: `"GitHub webhook received: event=%s delivery=%s"`

### ✅ 3. Flask エンドポイント
- **ファイル**: `src/nexuscore/api/server.py`
- **機能**:
  - `/api/github/webhook` エンドポイントを追加
  - `handle_github_webhook()` を呼び出し

### ✅ 4. PR コメント投稿機能
- **ファイル**: `src/nexuscore/api/github_webhook_handler.py`
- **機能**:
  - `GITHUB_SELF_HEALING_TOKEN` が設定されている場合、PR にコメントを投稿
  - `format_pr_comment()` で Markdown 形式のコメントを生成

### ✅ 5. 設定ファイル統合
- **ファイル**: `src/nexuscore/config/self_healing_config.py`
- **機能**:
  - `.nexus/self_healing.config.json` から設定を読み込み
  - ラベル、ブランチ、テストコマンドなどを設定可能

## テスト実行手順

### 1. サーバ起動
```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
export NEXUS_PROJECT_ROOT=$(pwd)
python src/nexuscore/api/server.py
```

### 2. モック Webhook 送信
```bash
python tools/mock_github_pr_webhook.py \
  --url http://127.0.0.1:5001/api/github/webhook \
  --repo-full-name test/repo \
  --pr-number 1 \
  --head-sha abc123def456 \
  --label self-healing \
  --base-branch main
```

### 3. 確認ポイント

#### ✅ Webhook 受信
- サーバログに `"GitHub webhook received: event=pull_request delivery=xxx"` が表示される

#### ✅ PR イベントパース
- `parse_pull_request_event()` が正しくラベルとブランチをチェック
- 設定ファイルの `label` と `allowed_target_branches` が適用される

#### ✅ Self-Healing 実行
- `SelfHealingService.run_for_pull_request()` が呼び出される
- テストコマンドが `config.test_command` から読み込まれる

#### ✅ Guardian レビュー
- `GuardianAgent` がレビューを実行（利用可能な場合）
- 結果が `details.guardian_status` と `details.guardian_comment` に追加される

#### ✅ PR コメント投稿
- `GITHUB_SELF_HEALING_TOKEN` が設定されている場合、PR にコメントが投稿される
- コメントには Status、Guardian Review、Patch Preview が含まれる

#### ✅ 実行履歴
- `.nexus/history/self_healing.log.jsonl` に実行履歴が記録される
- ダッシュボードで履歴を確認可能

## 注意事項

### 実際の E2E テストに必要なもの
1. **実際の GitHub リポジトリ**: テスト用の PR が必要
2. **GitHub トークン**: PR コメント投稿には `GITHUB_SELF_HEALING_TOKEN` が必要
3. **テストが失敗する状態**: Self-Healing を実行するには、テストが失敗している必要がある

### モックテストの限界
- 実際のリポジトリのクローンは行われない
- 実際のテスト実行は行われない
- PR コメント投稿はトークンが必要

## 次のステップ

1. 実際の GitHub リポジトリで Webhook を設定
2. テストが失敗する PR を作成
3. `self-healing` ラベルを付ける
4. Webhook を送信して E2E フローを確認

