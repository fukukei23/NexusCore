# Self-Healing Badges

GitHub README などに Self-Healing のメトリクスを表示するためのバッジ API です。

## 使用方法

### 成功率バッジ

過去30回のRunの成功率を表示します。

```markdown
![Self-Healing Success Rate](https://img.shields.io/endpoint?url=https://your-nexuscore-host/api/projects/1/badge/success_rate)
```

### 最新Runステータスバッジ

最新のRunのステータスを表示します。

```markdown
![Last Run Status](https://img.shields.io/endpoint?url=https://your-nexuscore-host/api/projects/1/badge/last_run)
```

## API エンドポイント

### GET /api/projects/<project_id>/badge/success_rate

プロジェクトの成功率バッジ用 JSON を返します。

**レスポンス例:**
```json
{
  "schemaVersion": 1,
  "label": "self-healing",
  "message": "93.3% success",
  "color": "brightgreen"
}
```

**カラー:**
- `brightgreen`: 90%以上
- `green`: 70%以上
- `yellow`: 50%以上
- `red`: 50%未満

### GET /api/projects/<project_id>/badge/last_run

プロジェクトの最新Runステータスバッジ用 JSON を返します。

**レスポンス例:**
```json
{
  "schemaVersion": 1,
  "label": "self-healing",
  "message": "last: SUCCESS",
  "color": "brightgreen"
}
```

**ステータスとカラー:**
- `SUCCESS`: `brightgreen`
- `FAILED`: `red`
- `RUNNING`: `blue`
- その他: `lightgrey`

## README へのバッジ表示例

NexusCore SaaS の Self-Healing 成功率と最新 Run ステータスを、GitHub README 上にバッジとして表示することができます。

```markdown
<!-- NOTE: your-nexuscore-host / project_id は環境に応じて置き換えてください -->

[![Self-Healing Success Rate](https://your-nexuscore-host/api/projects/1/badge/success_rate)](https://your-nexuscore-host/dashboard/projects/1)
[![Self-Healing Last Run](https://your-nexuscore-host/api/projects/1/badge/last_run)](https://your-nexuscore-host/dashboard/projects/1)
```

shields.io の "endpoint" 方式と異なり、NexusCore が直接バッジ用 JSON を返します。
ホスト名・プロジェクトID は、運用環境に合わせて適宜変更してください。

---

## 認証

現在、これらのエンドポイントは認証不要で公開されています。
将来的には、プロジェクトの公開設定や認証トークンによる制御を追加する予定です。

