# External Run API Examples

NexusCore SaaS の Self-Healing を、VSCode 拡張や Chrome 拡張などの外部ツールから呼び出すための例です。

## 1. エンドポイント概要

- **Base URL**: `https://your-nexuscore-host`
- **認証**: `X-Api-Key` ヘッダ（APIキーは `tools/generate_api_key.py` スクリプトで発行）
- **主なエンドポイント**:
  - `GET /api/v1/projects` - プロジェクト一覧を取得
  - `POST /api/v1/projects/<project_id>/run` - Self-Healing Run を発火
  - `GET /api/v1/projects/<project_id>/runs/latest` - 最新の Run ステータスを取得

### クイックスタート: API キーの発行

```bash
# 1. 仮想環境を有効化
source myenv_linux/bin/activate  # または .venv/bin/activate

# 2. API キーを発行（GitHub ログイン名を指定）
python tools/generate_api_key.py --user <your-github-login> --name "My API Key"

# 例:
python tools/generate_api_key.py --user testuser --name "VSCode Extension Key"
```

出力された API キー（`nexus_...` で始まる文字列）をコピーして使用してください。

### リクエスト例 (curl)

```bash
curl -X POST "https://your-nexuscore-host/api/v1/projects/1/run" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: YOUR_API_KEY_HERE" \
  -d '{
    "requirement": "Run self-healing for current repository",
    "autonomy_level": 2,
    "fast_lane": true
  }'
```

**レスポンス例**:
```json
{
  "run_id": "abc123def456...",
  "project_id": 1,
  "status": "PENDING",
  "queue_mode": "async"
}
```

---

## 2. VSCode Extension からの呼び出し例 (TypeScript)

VSCode 拡張機能のコマンド内などから、`fetch` を使って NexusCore の Run API を叩きます。

```typescript
import * as vscode from "vscode";
import fetch from "node-fetch"; // Webpack バンドル or node 18+ ならグローバル fetch でも可

async function triggerNexusCoreRun() {
  const apiBase = "https://your-nexuscore-host";
  const projectId = 1; // TODO: 設定またはユーザー入力で差し替え
  const apiKey = process.env.NEXUSCORE_API_KEY || "<YOUR_API_KEY>";

  const requirement = "Run self-healing for the current repository";

  const res = await fetch(`${apiBase}/api/v1/projects/${projectId}/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Api-Key": apiKey,
    },
    body: JSON.stringify({
      requirement,
      autonomy_level: 2,
      fast_lane: true,
    }),
  });

  if (!res.ok) {
    const body = await res.text();
    vscode.window.showErrorMessage(
      `NexusCore Run failed: HTTP ${res.status} - ${body}`
    );
    return;
  }

  const data = (await res.json()) as {
    run_id: string;
    status: string;
    queue_mode: "sync" | "async";
  };

  vscode.window.showInformationMessage(
    `NexusCore Run started: ${data.run_id} (mode: ${data.queue_mode}, status: ${data.status})`
  );
}
```

`projectId` と `apiKey` は VSCode の設定項目 (configuration) にしておくと運用しやすくなります。

`queue_mode` が `async` の場合、ステータス確認用に `GET /api/v1/projects/<id>/runs/latest` を叩くようなコマンドを追加すると便利です。

### VSCode 設定例 (package.json)

```json
{
  "contributes": {
    "configuration": {
      "properties": {
        "nexuscore.apiBase": {
          "type": "string",
          "default": "https://your-nexuscore-host",
          "description": "NexusCore API base URL"
        },
        "nexuscore.apiKey": {
          "type": "string",
          "description": "NexusCore API key (X-Api-Key)"
        },
        "nexuscore.projectId": {
          "type": "number",
          "default": 1,
          "description": "NexusCore project ID"
        }
      }
    },
    "commands": [
      {
        "command": "nexuscore.triggerRun",
        "title": "Trigger NexusCore Self-Healing Run"
      }
    ]
  }
}
```

---

## 3. Chrome Extension からの呼び出し例 (Manifest V3)

```javascript
// service_worker.js (background script)
async function triggerNexusCoreRunFromChrome() {
  const apiBase = "https://your-nexuscore-host";
  const projectId = 1;
  const apiKey = "<YOUR_API_KEY>";

  const res = await fetch(`${apiBase}/api/v1/projects/${projectId}/run`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Api-Key": apiKey,
    },
    body: JSON.stringify({
      requirement: "Run self-healing from Chrome extension",
      autonomy_level: 2,
      fast_lane: true,
    }),
  });

  const data = await res.json();
  console.log("NexusCore run response:", data);

  // 通知を表示
  chrome.notifications.create({
    type: "basic",
    iconUrl: "icon.png",
    title: "NexusCore Run Started",
    message: `Run ID: ${data.run_id} (${data.queue_mode})`,
  });
}
```

### manifest.json 例

```json
{
  "name": "NexusCore Self-Healing Trigger",
  "version": "0.1.0",
  "manifest_version": 3,
  "permissions": ["scripting", "storage", "notifications"],
  "host_permissions": ["https://your-nexuscore-host/*"],
  "background": {
    "service_worker": "service_worker.js"
  },
  "action": {
    "default_popup": "popup.html",
    "default_icon": {
      "16": "icon16.png",
      "48": "icon48.png",
      "128": "icon128.png"
    }
  }
}
```

CORS 対応として、NexusCore 側では `/api/v1/*` に対して `Access-Control-Allow-Origin` を許可するよう設定しておいてください（開発中は `"*"`、本番では使用ドメインに限定することを推奨します）。

---

## 4. Python クライアント例

```python
import requests

def trigger_nexuscore_run(api_base: str, api_key: str, project_id: int, requirement: str):
    """
    NexusCore の Self-Healing Run を発火する

    Args:
        api_base: NexusCore API のベース URL
        api_key: API キー
        project_id: プロジェクト ID
        requirement: 実行要件

    Returns:
        Run 情報の辞書
    """
    url = f"{api_base}/api/v1/projects/{project_id}/run"
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": api_key,
    }
    data = {
        "requirement": requirement,
        "autonomy_level": 2,
        "fast_lane": True,
    }

    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()

    return response.json()


# 使用例
if __name__ == "__main__":
    result = trigger_nexuscore_run(
        api_base="https://your-nexuscore-host",
        api_key="YOUR_API_KEY",
        project_id=1,
        requirement="Run self-healing for current repository",
    )
    print(f"Run started: {result['run_id']} (status: {result['status']}, mode: {result['queue_mode']})")
```

---

## 5. API キーの発行方法

### 方法1: スクリプトを使用（推奨）

`tools/generate_api_key.py` スクリプトを使用して API キーを発行できます：

```bash
# 仮想環境を有効化
source myenv_linux/bin/activate  # または .venv/bin/activate

# API キーを発行
python tools/generate_api_key.py --user <github_login> --name "VSCode Extension Key"

# 既存の API キーを確認
python tools/generate_api_key.py --user <github_login> --name "Check" --show-existing
```

**例**:
```bash
python tools/generate_api_key.py --user testuser --name "VSCode Extension Key"
```

出力例:
```
✅ API key generated successfully!

User: testuser (id: 1)
Key Name: VSCode Extension Key
Key ID: 1

⚠️  IMPORTANT: Save this API key now. It will not be shown again!

API Key: nexus_abc123def456...

Usage example:
  curl -H "X-Api-Key: nexus_abc123def456..." https://your-nexuscore-host/api/v1/projects
```

### 方法2: Python スクリプトで直接発行

管理者が直接データベースに API キーを登録することも可能です：

```python
from nexuscore.webapp import create_app, db
from nexuscore.webapp.models import ApiKey, User

app = create_app()
with app.app_context():
    # ユーザーを取得
    user = User.query.filter_by(github_login="your-username").first()

    # API キーを生成
    raw_token = ApiKey.generate_token()
    token_hash = ApiKey.hash_token(raw_token)

    # API キーを保存
    api_key = ApiKey(
        user_id=user.id,
        token_hash=token_hash,
        name="VSCode Extension Key",
    )
    db.session.add(api_key)
    db.session.commit()

    # 生成されたキーを表示（この時だけ表示可能）
    print(f"API Key: {raw_token}")
```

### 方法3: Webapp UI から発行（将来実装予定）

将来的には Webapp UI から API キーを発行・管理できる機能を追加予定です。

**重要**:
- 生成された API キーは一度だけ表示されます。紛失した場合は新しいキーを発行してください。
- API キーは SHA-256 でハッシュ化して保存されるため、平文での復元は不可能です。

---

## 6. エラーハンドリング

### 401 Unauthorized

API キーが無効または欠落している場合：

```json
{
  "error": "Invalid or missing API key"
}
```

### 400 Bad Request

必須パラメータが欠落している場合：

```json
{
  "error": "requirement is required"
}
```

### 404 Not Found

プロジェクトが見つからない場合：

```json
{
  "error": "Project not found"
}
```

### 500 Internal Server Error

実行中にエラーが発生した場合（同期実行時）：

```json
{
  "run_id": "abc123...",
  "project_id": 1,
  "status": "FAILED",
  "queue_mode": "sync",
  "error": "Error message"
}
```

---

## 7. ステータス確認

非同期実行（`queue_mode: "async"`）の場合、Run のステータスを確認するには：

```bash
curl -X GET "https://your-nexuscore-host/api/v1/projects/1/runs/latest" \
  -H "X-Api-Key: YOUR_API_KEY_HERE"
```

**レスポンス例**:
```json
{
  "run": {
    "id": 123,
    "run_id": "abc123def456...",
    "status": "SUCCESS",
    "started_at": "2025-01-01T00:00:00",
    "finished_at": "2025-01-01T00:05:00"
  }
}
```

Run が存在しない場合:
```json
{
  "run": null
}
```

---

## 関連ドキュメント

- `docs/saas_architecture.md` - SaaS アーキテクチャの詳細
- `docs/saas_badges.md` - README バッジ API の使用方法

