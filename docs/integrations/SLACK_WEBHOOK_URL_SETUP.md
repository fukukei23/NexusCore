# Slack Webhook URL の取得方法

## 概要

`YOUR/WEBHOOK/URL` は、Slack の **Incoming Webhook URL** のことです。
この URL を使って、NexusCore から Slack に通知を送信します。

形式は以下のようになります：
```
https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

## 取得手順（詳細版）

### ステップ1: Slack API にアクセス

1. ブラウザで [https://api.slack.com/apps](https://api.slack.com/apps) を開く
2. ログイン（必要に応じて）

### ステップ2: 新しいアプリを作成（または既存のアプリを選択）

#### 新規作成する場合：

1. 「**Create New App**」ボタンをクリック
2. 「**From scratch**」を選択
3. アプリ名を入力（例: `NexusCore Notifications`）
4. ワークスペースを選択（例: `NexusCore`）
5. 「**Create App**」をクリック

#### 既存のアプリを使用する場合：

1. アプリ一覧から既存のアプリを選択

### ステップ3: Incoming Webhooks を有効化

1. 左側のメニューから「**Incoming Webhooks**」をクリック
2. 「**Activate Incoming Webhooks**」を **ON** にする（トグルスイッチ）

### ステップ4: Webhook をワークスペースに追加

1. ページを下にスクロール
2. 「**Add New Webhook to Workspace**」ボタンをクリック
3. 通知を送信したいチャンネルを選択
   - 例: `#general`、`#notifications`、`#nexuscore` など
   - または、DM に送信したい場合は自分の名前を選択
4. 「**Allow**」をクリック

### ステップ5: Webhook URL をコピー

1. 「**Webhook URLs for Your Workspace**」セクションに表示される URL をコピー
2. URL の形式は以下のようになります：
   ```
   https://hooks.slack.com/services/T099F91V6HL/B0A12QVBD2L/XXXXXXXXXXXXXXXXXXXXXXXX
   ```
3. **この URL は機密情報です。他人に共有しないでください。**

### ステップ6: NexusCore に設定

#### 方法1: .env ファイルに追加（推奨）

```bash
cd /home/yn441611/NexusCore
nano .env
```

以下の行を追加（`YOUR/WEBHOOK/URL` を実際の URL に置き換え）：

```bash
NEXUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T099F91V6HL/B0A12QVBD2L/XXXXXXXXXXXXXXXXXXXXXXXX
```

保存して終了（`Ctrl+X` → `Y` → `Enter`）

#### 方法2: 環境変数として直接設定

```bash
export NEXUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T099F91V6HL/B0A12QVBD2L/XXXXXXXXXXXXXXXXXXXXXXXX
```

### ステップ7: 動作確認

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
python tools/test_slack_notification.py
```

Slack のチャンネルにテスト通知が届けば成功です！

## よくある質問

### Q: どのチャンネルに通知を送信すればいいですか？

A: お好みのチャンネルを選択できます。推奨：
- `#notifications` - 通知専用チャンネル
- `#nexuscore` - NexusCore 専用チャンネル
- DM（自分の名前） - 個人の通知

### Q: 複数のチャンネルに通知を送信できますか？

A: はい。複数の Webhook URL を作成して、それぞれ異なるチャンネルに設定できます。
ただし、NexusCore は現在、1つの Webhook URL のみをサポートしています。
複数のチャンネルに送信したい場合は、各チャンネル用の Webhook URL を作成し、
必要に応じてコードを修正してください。

### Q: Webhook URL が期限切れになったらどうすればいいですか？

A: 新しい Webhook URL を生成してください：
1. Slack API でアプリを開く
2. 「Incoming Webhooks」を開く
3. 既存の Webhook を削除（必要に応じて）
4. 新しい Webhook を追加
5. 新しい URL を `.env` ファイルに更新

### Q: Webhook URL を他人に知られてしまったら？

A: すぐに無効化してください：
1. Slack API でアプリを開く
2. 「Incoming Webhooks」を開く
3. 該当の Webhook を削除または無効化
4. 新しい Webhook URL を生成
5. `.env` ファイルを更新

### Q: テスト通知は送信できるが、実際の実行では通知が来ない

A: 以下を確認してください：
1. アプリケーションを再起動したか（環境変数は起動時に読み込まれる）
2. ログにエラーがないか確認
3. `orchestrator_inline.py` や `celery_app.py` の通知送信コードを確認

## セキュリティの注意事項

⚠️ **重要:**
- Webhook URL は機密情報です
- `.env` ファイルを Git にコミットしないでください
- `.gitignore` に `.env` が含まれていることを確認してください
- Webhook URL を他人に共有しないでください

## 参考リンク

- [Slack API - Incoming Webhooks](https://api.slack.com/messaging/webhooks)
- [Slack API - Apps](https://api.slack.com/apps)
- [NexusCore Slack 通知設定ガイド](./slack_notification_setup.md)

