# Slack通知設定ガイド

NexusCoreの実行完了通知をSlackに送信するための設定方法です。

## 概要

NexusCoreは、以下のタイミングでSlack通知を送信できます：

- **Self-Healing Service**: PR単位の自己修復実行が完了したとき
- **Orchestrator**: フルプロジェクト実行が完了したとき

AndroidスマホでもSlackアプリをインストールしていれば、同じ通知を受信できます。

## セットアップ手順

### 1. Slack Incoming Webhookの作成

1. [Slack API](https://api.slack.com/apps) にアクセス
2. 「Create New App」をクリック
3. 「From scratch」を選択
4. App名とワークスペースを選択
5. 「Incoming Webhooks」を有効化
6. 「Add New Webhook to Workspace」をクリック
7. 通知を送信したいチャンネルを選択
8. Webhook URLをコピー（例: `https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX`）

### 2. 環境変数の設定

プロジェクトルートの `.env` ファイルに以下を追加：

```bash
NEXUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

または、環境変数として直接設定：

```bash
export NEXUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 3. 依存関係のインストール

```bash
pip install requests
```

または、`requirements.txt`に含まれているので：

```bash
pip install -r requirements.txt
```

## 通知の種類

### Self-Healing通知

Self-Healing ServiceがPRの自己修復を完了したときに送信されます。

**通知内容:**
- ✅ 成功（fixed）: パッチ適用後、テストが通過
- ⚠️ 警告（not_fixed）: パッチ適用したがテストが失敗、またはパッチ生成失敗
- ℹ️ 情報（no_issues）: テストが既に通過していた
- ❌ エラー（error）: 実行中にエラーが発生

**通知に含まれる情報:**
- リポジトリ名
- PR番号
- 実行ID
- サマリー
- 詳細情報（オプション）

### Orchestrator通知

Orchestratorがフルプロジェクト実行を完了したときに送信されます。

**通知内容:**
- ✅ 成功（success）: 正常に完了
- ❌ エラー（error）: 実行中にエラーが発生
- ⏸️ 停止（stopped）: ユーザーによって中断された

**通知に含まれる情報:**
- プロジェクトパス
- セッションID
- 要件
- 詳細情報（オプション）

## カスタマイズ

### 通知を無効化する

環境変数を削除または空に設定：

```bash
unset NEXUS_SLACK_WEBHOOK_URL
```

### プログラムから通知を送信

```python
from nexuscore.core.notifier import SlackNotifier

# Notifierを初期化
notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/YOUR/WEBHOOK/URL")

# カスタム通知を送信
notifier.send(
    title="カスタム通知",
    message="これはカスタムメッセージです",
    status="info",
    details={"key": "value"},
)
```

### atelier-kyo-manager など他のプロジェクトから通知を送信

`tools/notify_slack.py` スクリプトを使用して、任意のプロジェクトから通知を送信できます：

```bash
# 成功通知
python tools/notify_slack.py \
  --project "atelier-kyo-manager" \
  --task "実装完了: Stage 3A-3" \
  --status "success"

# エラー通知（詳細情報付き）
python tools/notify_slack.py \
  --project "atelier-kyo-manager" \
  --task "テスト失敗" \
  --status "error" \
  --detail "エラー内容: TypeError" \
  --detail "ファイル: navigation_driver.py"

# 警告通知
python tools/notify_slack.py \
  --project "atelier-kyo-manager" \
  --task "リファクタリング完了" \
  --status "warning" \
  --detail "変更ファイル数: 5"
```

または、Pythonコードから直接呼び出し：

```python
import sys
from pathlib import Path

# NexusCoreのパスを追加
nexuscore_path = Path("/home/yn441611/NexusCore/src")
sys.path.insert(0, str(nexuscore_path))

from nexuscore.core.notifier import get_notifier

notifier = get_notifier()
if notifier:
    notifier.notify_project_complete(
        project_name="atelier-kyo-manager",
        task_description="実装完了: Stage 3A-3",
        status="success",
        details={"変更ファイル": "navigation_driver.py"},
    )
```

## トラブルシューティング

### 通知が送信されない

1. **環境変数の確認**
   ```bash
   echo $NEXUS_SLACK_WEBHOOK_URL
   ```

2. **Webhook URLの確認**
   - URLが正しいか確認
   - Webhookが有効になっているか確認

3. **依存関係の確認**
   ```bash
   pip list | grep requests
   ```

4. **ログの確認**
   - NexusCoreのログに「Failed to send Slack notification」が表示されていないか確認

### Androidスマホで通知を受信する

1. [Slackアプリ](https://play.google.com/store/apps/details?id=com.Slack)をインストール
2. ワークスペースにログイン
3. 通知設定で「プッシュ通知」を有効化
4. 通知チャンネルをフォロー（必要に応じて）

## セキュリティ

- Webhook URLは機密情報です。`.env`ファイルに保存し、Gitにコミットしないでください
- `.gitignore`に`.env`が含まれていることを確認してください
- Webhook URLが漏洩した場合は、SlackでWebhookを無効化し、新しいURLを生成してください


