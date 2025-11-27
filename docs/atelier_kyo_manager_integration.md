# atelier-kyo-manager へのSlack通知統合ガイド

atelier-kyo-managerプロジェクトからSlack通知を送信する方法です。

## 概要

atelier-kyo-managerで実装やテストが完了した際に、Slackに通知を送信できます。
AndroidスマホでもSlackアプリをインストールしていれば、同じ通知を受信できます。

## セットアップ

### 1. 環境変数の設定

atelier-kyo-managerプロジェクトのルート、またはNexusCoreプロジェクトのルートで、`.env`ファイルに以下を追加：

```bash
NEXUS_SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
```

### 2. 通知スクリプトの使用

atelier-kyo-managerプロジェクトから、以下のように通知を送信できます：

```bash
# NexusCoreのパスを指定して実行
python /home/yn441611/NexusCore/tools/notify_slack.py \
  --project "atelier-kyo-manager" \
  --task "実装完了: Stage 3A-3" \
  --status "success"
```

### 3. Pythonコードからの直接呼び出し

atelier-kyo-managerのPythonコードから直接通知を送信する場合：

```python
import sys
from pathlib import Path

# NexusCoreのパスを追加
nexuscore_path = Path("/home/yn441611/NexusCore/src")
if str(nexuscore_path) not in sys.path:
    sys.path.insert(0, str(nexuscore_path))

from nexuscore.core.notifier import get_notifier

# 通知を送信
notifier = get_notifier()
if notifier:
    notifier.notify_project_complete(
        project_name="atelier-kyo-manager",
        task_description="実装完了: Stage 3A-3 (trap判定の観測フック追加)",
        status="success",
        details={
            "変更ファイル": "navigation_driver.py, browser_use_agent.py",
            "テスト結果": "すべて通過",
        },
    )
```

## 使用例

### 実装完了時

```bash
python /home/yn441611/NexusCore/tools/notify_slack.py \
  --project "atelier-kyo-manager" \
  --task "実装完了: Stage 3A-3" \
  --status "success" \
  --detail "変更ファイル: navigation_driver.py" \
  --detail "テスト: すべて通過"
```

### テスト失敗時

```bash
python /home/yn441611/NexusCore/tools/notify_slack.py \
  --project "atelier-kyo-manager" \
  --task "テスト失敗" \
  --status "error" \
  --detail "エラー: TypeError" \
  --detail "ファイル: navigation_driver.py:123"
```

### リファクタリング完了時

```bash
python /home/yn441611/NexusCore/tools/notify_slack.py \
  --project "atelier-kyo-manager" \
  --task "リファクタリング完了" \
  --status "info" \
  --detail "変更ファイル数: 5" \
  --detail "影響範囲: agents/browser/"
```

## ステータスの種類

- `success`: 成功（緑色）
- `error`: エラー（赤色）
- `warning`: 警告（オレンジ色）
- `info`: 情報（青色）

## 注意事項

- Webhook URLは機密情報です。`.env`ファイルに保存し、Gitにコミットしないでください
- 通知は日本語で送信されます
- Androidスマホで通知を受信するには、Slackアプリをインストールし、通知設定を有効化してください

