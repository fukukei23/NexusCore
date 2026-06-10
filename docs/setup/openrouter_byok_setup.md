# OpenRouter BYOK (Bring Your Own Key) 初期設定手順

## 概要

- **OpenRouter BYOKとは**: ユーザーが自身のAPIキーをNexusCoreに持ち込み（Bring Your Own Key）、1つのAPIキーで100以上のLLMモデル（OpenAI, Anthropic, Googleなど）にアクセスできるようにする機能です。
- **NEXUS_ENCRYPTION_KEYの役割**: ユーザーのAPIキーをデータベースに平文で保存することを防ぐため、NexusCoreはこのキーを使用してAPIキーをAES-256-GCMで暗号化して保存します。

## 前提条件

- openrouter.ai のアカウントが作成済みであること
- NexusCoreアプリケーションが実行可能な環境であること

---

## 手順1: NEXUS_ENCRYPTION_KEY の生成

**Pythonでの生成コマンド:**

```bash
cd /path/to/NexusCore
source .venv/bin/activate
PYTHONPATH=src python -c "from nexuscore.utils.crypto_utils import generate_encryption_key; print(generate_encryption_key())"
```

**出力例（プレースホルダー）:**
```
BASE64_ENCODED_32_BYTES_HERE
```

**`.secrets.env` への追記:**

```bash
NEXUS_ENCRYPTION_KEY=<上記で生成した値>
```

> **⚠️ 警告:** `NEXUS_ENCRYPTION_KEY` を紛失すると、DBに保存済みのすべてのAPIキーが復号不能になります。必ずバックアップを取ってください。

---

## 手順2: OpenRouterのAPIキー取得

1. openrouter.ai にログイン
2. ダッシュボード左メニューの「Keys」を選択
3. 「Create Key」をクリックし、`sk-or-` から始まるキーをコピー

---

## 手順3: APIでキーを登録

```bash
curl -X POST http://localhost:8000/api/v1/user/openrouter-key \
  -H "X-API-Key: <NexusCoreのAPIキー>" \
  -H "Content-Type: application/json" \
  -d '{"api_key": "sk-or-xxxx"}'
```

**成功レスポンス:**
```json
{"message": "OpenRouter key saved"}
```

---

## 手順4: 登録確認

```bash
curl http://localhost:8000/api/v1/user/openrouter-key/status \
  -H "X-API-Key: <NexusCoreのAPIキー>"
```

**レスポンス例:**
```json
{"configured": true}
```

---

## キーの削除

```bash
curl -X DELETE http://localhost:8000/api/v1/user/openrouter-key \
  -H "X-API-Key: <NexusCoreのAPIキー>"
```

---

## トラブルシューティング

| エラー | 原因 | 解決策 |
|--------|------|--------|
| `500: NEXUS_ENCRYPTION_KEY is not configured` | 環境変数が未設定 | 手順1を再実行してアプリを再起動 |
| `{"configured": false}` | キー未登録または登録失敗 | 手順3を再実行 |
| `401 Unauthorized` | NexusCoreのAPIキーが無効 | `/api/v1/api-keys` で有効なキーを発行 |
