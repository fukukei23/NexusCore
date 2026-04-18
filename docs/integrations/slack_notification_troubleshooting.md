# Slack 通知が来ない場合のトラブルシューティング

## クイックチェックリスト

- [ ] 環境変数 `NEXUS_SLACK_WEBHOOK_URL` が設定されている
- [ ] `requests` ライブラリがインストールされている
- [ ] Webhook URL が有効である
- [ ] テスト通知が送信できる
- [ ] Flask アプリケーション / Celery Worker を再起動した

## ステップバイステップ診断

### ステップ1: テスト通知を送信

```bash
cd /home/yn441611/NexusCore
source myenv_linux/bin/activate
python tools/test_slack_notification.py
```

**期待される結果:**
```
✅ SlackNotifier が有効です
✅ テスト通知を送信しました
```

**問題がある場合:**
- 環境変数が設定されていない → ステップ2へ
- 通知送信に失敗 → ステップ3へ

### ステップ2: 環境変数の設定

#### 2-1. 環境変数の確認

```bash
echo $NEXUS_SLACK_WEBHOOK_URL
```

#### 2-2. .env ファイルに追加

```bash
# .env ファイルを編集
nano .env

# 以下を追加
NEXUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

#### 2-3. 環境変数の読み込み確認

```bash
# .env ファイルを読み込む（source コマンドで読み込む場合）
source .env

# または直接設定
export NEXUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### ステップ3: Webhook URL の確認

#### 3-1. Webhook URL の形式確認

正しい形式:
```
https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX
```

#### 3-2. Webhook の有効性確認

1. [Slack API](https://api.slack.com/apps) にアクセス
2. アプリを選択
3. 「Incoming Webhooks」を確認
4. Webhook が有効になっているか確認

#### 3-3. 新しい Webhook URL を生成

Webhook URL が無効な場合：
1. Slack API で Webhook を無効化
2. 新しい Webhook を追加
3. 新しい URL をコピー
4. `.env` ファイルを更新

### ステップ4: 依存関係の確認

```bash
# requests ライブラリがインストールされているか確認
pip list | grep requests

# インストールされていない場合
pip install requests
```

### ステップ5: ログの確認

#### 5-1. 実行時のログを確認

```bash
# ログファイルを確認
tail -f logs/nexuscore.log | grep -i slack

# または実行時の標準出力を確認
# "Failed to send Slack notification" が表示されていないか
# "Slack通知を送信しました" が表示されているか
```

#### 5-2. エラーメッセージの確認

よくあるエラーメッセージ：

- `NEXUS_SLACK_WEBHOOK_URLが設定されていません`
  → 環境変数を設定してください

- `requestsライブラリがインストールされていません`
  → `pip install requests` を実行してください

- `Failed to send Slack notification: ...`
  → Webhook URL が無効か、ネットワークエラーの可能性があります

### ステップ6: 手動で通知を送信

```bash
# 簡単なテスト通知を送信
python tools/notify_slack.py \
  --project "NexusCore" \
  --task "テスト通知" \
  --status "info"
```

**期待される結果:**
```
✅ Slack通知を送信しました: NexusCore - テスト通知
```

### ステップ7: アプリケーションの再起動

環境変数を設定した後は、アプリケーションを再起動してください：

```bash
# Flask アプリケーションを再起動
# （実行中のプロセスを停止して再起動）

# Celery Worker を再起動
# systemd の場合
sudo systemctl restart nexuscore-celery

# supervisor の場合
supervisorctl restart nexuscore-celery

# 手動起動の場合
# プロセスを停止して再起動
```

## よくある問題と解決方法

### 問題1: 環境変数が設定されているのに通知が来ない

**原因:**
- アプリケーションが環境変数を読み込む前に起動している
- 環境変数が正しく読み込まれていない

**解決方法:**
1. アプリケーションを再起動
2. `.env` ファイルが正しい場所にあるか確認
3. 環境変数の読み込み方法を確認

### 問題2: 通知は送信されているが Slack で表示されない

**原因:**
- Slack の通知設定が無効
- チャンネルに Webhook が正しく設定されていない
- Slack アプリの通知権限が不足

**解決方法:**
1. Slack の通知設定を確認
2. チャンネルに Webhook が正しく設定されているか確認
3. Slack アプリの通知権限を確認

### 問題3: Android スマホで通知が来ない

**原因:**
- Slack アプリがインストールされていない
- プッシュ通知が無効
- チャンネルをフォローしていない

**解決方法:**
1. [Slack アプリ](https://play.google.com/store/apps/details?id=com.Slack)をインストール
2. ワークスペースにログイン
3. 通知設定で「プッシュ通知」を有効化
4. 通知を受け取りたいチャンネルをフォロー

### 問題4: テスト通知は成功するが、実際の実行では通知が来ない

**原因:**
- Orchestrator や Celery タスクの実行時に通知が送信されていない
- エラーが発生して通知が送信されていない

**解決方法:**
1. ログを確認して、通知送信のエラーがないか確認
2. `orchestrator_inline.py` や `celery_app.py` の通知送信コードを確認
3. 実行時のログを確認

## デバッグ用コマンド

### 環境変数の確認

```bash
# 現在の環境変数を確認
env | grep SLACK

# Python から確認
python3 -c "import os; print(os.getenv('NEXUS_SLACK_WEBHOOK_URL'))"
```

### 通知機能のテスト

```bash
# テスト通知スクリプトを実行
python tools/test_slack_notification.py

# 簡単な通知を送信
python tools/notify_slack.py --project "Test" --task "Test" --status "info"
```

### ログの確認

```bash
# ログファイルを確認
tail -f logs/nexuscore.log | grep -i slack

# エラーログを確認
grep -i "failed.*slack" logs/*.log
```

## サポート

問題が解決しない場合：

1. ログファイルを確認
2. エラーメッセージを記録
3. `docs/slack_notification_setup.md` を参照
4. GitHub Issues で報告（必要に応じて）
