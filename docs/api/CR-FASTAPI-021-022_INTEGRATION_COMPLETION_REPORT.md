# CR-FASTAPI-021 & CR-FASTAPI-022 ― 統合完了レポート（最終版）

## 1. 全体サマリー

今回の 2 CR（021: ブートストラップ CLI、022: TS SDK E2E helper）はどちらも、
API Key 運用基盤を NexusCore 全体に正式導入するためのクリティカルパスであり、
次の 2 点を実現しました：

- **初回 API Key を安全に発行する公式ツール（CLI）を確立**
- **TypeScript SDK の E2E テストが API Key を「自動発行」できる仕組みを確立**

これにより、
「CI/CD・ローカル開発・SDK テスト」すべてで API Key が安定的に扱える統合運用モデルが完成しました。

## 2. テスト結果（全件成功）

### 2.1 CLI テスト（5テスト）

すべて成功。

- 初回発行で User + ApiKey が作成
- 2 回目実行で User を再利用し、Key のみ増加
- デフォルト key_name が設定される
- CLI メインが exit code 0 を返す
- stdout に `export NEXUSCORE_API_KEY="..."` が出力される

### 2.2 API Key API テスト（9テスト）

すべて成功。

- 発行成功
- 認証なしは 401 / 422
- 上限超過（403）
- 一覧成功・空リスト成功
- 無効化成功 / NotFound / Forbidden
- デフォルト名テスト

## 3. CR-FASTAPI-021（ブートストラップ CLI）実装内容

### 3.1 ロジック構造の再設計（重要）

**純粋ロジック関数を新設**：

```python
bootstrap_apikey_for_app(app, user_login, user_name, key_name)
```

- User と ApiKey を DB に作成するロジックを「アプリに依存しない形」で分離
- テストはこの関数を直接呼び出すだけで完結
- DB がどこを向いているかを自由に制御可能
- → テストの独立性と信頼性が大きく向上

**CLI ラッパー関数**：

```python
bootstrap_apikey_main()
```

- `create_app() → db.create_all() → 純粋ロジック → export 出力`
- CLI の責務は「入出力と app 生成」のみ
- ビジネスロジックから完全分離された

**品質的効果**：

- FastAPI API（CR-FASTAPI-020）と CLI の責務境界が明確化
- future maintenance（API 側刷新・app context 変更）に強い構造
- CLI のテストの「副作用ゼロ化」を達成

### 3.2 動作確認結果

実 CLI 実行にて：

```
[INFO] Using user: dev (id=1)
[INFO] Created API key: "Local Dev Key" (id=2)
export NEXUSCORE_API_KEY="nexus_xxxxx..."
```

exit code 0。

### 3.3 設計改善点（完了レポート要素）

- ✔ ロジック分離
- ✔ detached object 問題の排除
- ✔ DB 初期化の扱いの整理
- ✔ github_id 自動生成（GitHub OAuth 未導入の暫定仕様）

## 4. CR-FASTAPI-022（TS SDK E2E helper）実装内容

### 4.1 API Key 自動発行フローを実現

`apikey_helper.ts` の挙動：

1. `NEXUSCORE_API_KEY` があればそれを使う
2. なければ `NEXUSCORE_BOOTSTRAP_API_KEY` を使って `/api/v1/api-keys` を叩いて自動発行
3. それもなければ E2E を skip

→ CI でもローカルでも「API Key 不足で落ちる」問題を完全解消

### 4.2 E2E テスト修正内容

`test_projects_e2e.test.ts` が helper を使用：

- `basePath = FASTAPI_BASE_URL`
- 取得した `apiKey` を `Configuration` に渡す
- skip 条件を明確化（環境依存の暴走防止）

## 5. 運用フローの確立（README / .cursorrules 反映済み）

以下が正式な API Key 運用ルートとなった：

### 5.1 初回（必ずこれ）

```bash
python -m nexuscore.cli.bootstrap_apikey \
    --user-login dev \
    --key-name "Local Dev Key"
```

### 5.2 2 本目以降（API 経由）

```
POST /api/v1/api-keys
```

### 5.3 TS E2E 用

```bash
export NEXUSCORE_BOOTSTRAP_API_KEY="nexus_..."
npm test -- tests/test_projects_e2e.test.ts
```

### 5.4 禁止事項（cursorrules に記載）

- DB を直接更新して API Key を作ること
- SDK コードを手書き修正すること
- CLI のロジックを API 側に混在させること

## 6. 完了レポート（CR-FASTAPI-021 / 022）

- **CR-FASTAPI-021 完了レポート（CLI 完全実装・テスト完了）**
  → `docs/api/CR-FASTAPI-021_COMPLETION_REPORT.md`

- **CR-FASTAPI-022 完了レポート（TS helper + E2E 運用確立）**
  → `docs/api/CR-FASTAPI-022_COMPLETION_REPORT.md`（内容一致確認済み）

## 7. 最終評価（厳密）

| 状態 | 内容 |
|------|------|
| **実装** | 完了（CLI + helper + API 依存部門） |
| **テスト** | CLI 5/5、API Key API 9/9 全て成功（完全グリーン） |
| **ドキュメント** | README / docs / .cursorrules 全て反映済み |
| **アーキテクチャ適合** | API 層と CLI 層の分離が適切、責務境界クリア |
| **将来拡張性** | OAuth 連携・外部 UI 統合にも耐える構成 |

→ **CR-FASTAPI-021 / 022 は品質基準を満たし、完全完了として確定できます。**

