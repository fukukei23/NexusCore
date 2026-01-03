# CR-FASTAPI-023: CI で自動的に Bootstrap API Key を生成する導線

## 1. 人間向け仕様書（Implementation Task Overview）

### 1.1 目的

**現状**：

- ローカル・WSL では `bootstrap_apikey` CLI を手動実行して「最初の API Key」を発行できる状態になっている（CR-FASTAPI-021）。
- TypeScript SDK の E2E テストは `NEXUSCORE_BOOTSTRAP_API_KEY` から `/api/v1/api-keys` を叩いてテスト用 API Key を自動発行できる（CR-FASTAPI-022）。

**しかし CI 環境では**：

- 初回セットアップ時に **誰が・どこで・どのタイミングで bootstrap key を作るか** が曖昧。
- 手順ミスや環境差分により、E2E が 401 / 403 で落ちるリスクがある。

**本 CR の目的は**：

CI（GitHub Actions 想定）で、**自動的に bootstrap API Key を生成し、後続ジョブに受け渡す「公式フロー」**を確立すること。

### 1.2 想定ユースケース

**CI 上での TS SDK E2E テスト**

GitHub Actions で：

1. FastAPI サーバー（またはテスト用バックエンド）を立ち上げる
2. `bootstrap_apikey` CLI を使って `NEXUSCORE_BOOTSTRAP_API_KEY` を生成
3. その key を env / job output 経由で TS E2E テストジョブに渡す
4. テストジョブは、CR-FASTAPI-022 の helper によって必要に応じてテスト用 API Key を発行し、E2E を実行。

**CI 上での Python API テスト（オプション）**

必要あれば Python 側の E2E/API テストでも同じ bootstrap key を使い回す。

### 1.3 仕様概要

CI での標準フローは次のようにしたい：

**bootstrap key ジョブ**

- DB・サーバー起動前提 or 同一 DB を見る環境で `bootstrap_apikey` を実行。
- `export NEXUSCORE_BOOTSTRAP_API_KEY="...."` 形式の行をキャプチャ。
- その値を GitHub Actions の job output に格納。

**テストジョブ**

- 前ジョブの output から `NEXUSCORE_BOOTSTRAP_API_KEY` を env に渡す。
- TS E2E テストを実行。
- helper は既存仕様通り動作：
  - `NEXUSCORE_API_KEY` があればそれを使用
  - 無ければ `NEXUSCORE_BOOTSTRAP_API_KEY` から `/api/v1/api-keys` を叩いて自動発行

**セキュリティ**

- GitHub Actions の log には raw key を直接出さない（`::add-mask::` や secrets 経由）。
- 生成された bootstrap key を GitHub Secrets に永続保存するかどうかは本 CR のスコープ外。
  → 本 CR では「CI ジョブ内で ephemeral に発行して使う」前提。

### 1.4 スコープ（In-Scope）

- GitHub Actions ワークフロー（または既存 workflow）の追加・修正：
  - `bootstrap_apikey` CLI を呼び出して key を生成する job
  - job output として `NEXUSCORE_BOOTSTRAP_API_KEY` を後続に引き渡す処理
- Makefile などローカル統一インターフェース（任意）：
  - `make ci-bootstrap-apikey` のような簡易ターゲット
- README / docs/api/README / sdk/typescript/README / .cursorrules 更新：
  - 「CI での bootstrap key 生成はこのワークフローを使う」ことを明文化
- 完了レポート作成
  - `docs/api/CR-FASTAPI-023_COMPLETION_REPORT.md`

### 1.5 非スコープ（Out-of-Scope）

- 本番環境用の永続的な API Key 管理（Vault, KMS など）
- GitHub Secrets への自動登録（これは運用で対応）
- 新しい FastAPI エンドポイントの追加
- SDK 自動生成パイプラインの変更

### 1.6 実装案（GitHub Actions イメージ）

例：`.github/workflows/ts-e2e.yml`（新規 or 既存修正）

```yaml
jobs:
  bootstrap-apikey:
    runs-on: ubuntu-latest
    outputs:
      bootstrap_key: ${{ steps.bootstrap.outputs.NEXUSCORE_BOOTSTRAP_API_KEY }}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m venv venv
          source venv/bin/activate
          pip install -r requirements.txt

      - name: Run bootstrap_apikey CLI
        id: bootstrap
        run: |
          source venv/bin/activate
          export PYTHONPATH=src
          # DB 初期化 & サーバーとは同一 DB を参照する前提
          OUTPUT=$(python -m nexuscore.cli.bootstrap_apikey --user-login ci --key-name "CI Bootstrap Key")
          # 出力例: export NEXUSCORE_BOOTSTRAP_API_KEY="nexus_xxx..."
          KEY=$(echo "$OUTPUT" | sed -n 's/export NEXUSCORE_BOOTSTRAP_API_KEY="\([^"]*\)"/\1/p')
          echo "::add-mask::$KEY"
          echo "NEXUSCORE_BOOTSTRAP_API_KEY=$KEY" >> "$GITHUB_OUTPUT"

  ts-e2e:
    runs-on: ubuntu-latest
    needs: [bootstrap-apikey]
    env:
      NEXUSCORE_BOOTSTRAP_API_KEY: ${{ needs.bootstrap-apikey.outputs.bootstrap_key }}
      FASTAPI_BASE_URL: "http://localhost:8000"
    steps:
      - uses: actions/checkout@v4
      # FastAPI サーバー起動（別ステップ or services コンテナなど）
      # その後、TS SDK の E2E を実行
```

※ 実際には FastAPI サーバー起動・DB セットアップなどプロジェクト固有の処理に合わせて調整。

### 1.7 Definition of Done

- GitHub Actions 上で：
  - `bootstrap-apikey` ジョブが成功し、job output に有効な bootstrap key がセットされる。
  - 後続の TS E2E ジョブが、その key 経由で `/api/v1/api-keys` を叩いてテスト用 key を発行し、E2E が通る。
- ローカル環境と CI の運用フローが README / docs / .cursorrules に統一的に記載されている。
- `docs/api/CR-FASTAPI-023_COMPLETION_REPORT.md` が作成されている。

---

## 2. Cursor 用実装指示書（Implementation Instruction for Cursor）

### 2.1 変更対象ファイル

**Cursor MUST operate on:**

**新規作成**:
- `docs/spec/CR-FASTAPI-023_CI_Bootstrap_ApiKey_Automation.md`（本仕様書）
- `docs/api/CR-FASTAPI-023_COMPLETION_REPORT.md`（完了レポート）
- `.github/workflows/ts-e2e.yml`（または既存 workflow の追加セクション）

**変更**:
- `Makefile`（任意: `ci-bootstrap-apikey` ターゲット）
- `README.md`
- `docs/api/README.md`
- `sdk/typescript/README.md`
- `.cursorrules`（CI における API Key 運用ルール追記）

**Cursor MUST NOT**:
- FastAPI ルート（`src/nexuscore/api/...`）や Pydantic スキーマを変更してはならない。
- `sdk/python/` / `sdk/typescript/` の生成コードを手書き変更してはならない。

### 2.2 実装要件（GitHub Actions）

**ワークフロー追加・修正**

既に TS SDK 用の workflow がある場合はそれを拡張、ない場合は新規作成。

**要件**：
- `bootstrap-apikey` 的な job を持つこと。
- `python -m nexuscore.cli.bootstrap_apikey` を呼ぶこと。
- CLI 出力から key を抽出し、`NEXUSCORE_BOOTSTRAP_API_KEY` として job output に書き出すこと。
- `::add-mask::` を使って log に key が平文で残らないようにすること。

**Makefile（任意）**

開発者がローカルで CI と同じ挙動を再現できるよう、例えば：

```makefile
ci-bootstrap-apikey:
	. venv/bin/activate && \
	export PYTHONPATH=src && \
	python -m nexuscore.cli.bootstrap_apikey --user-login ci --key-name "CI Bootstrap Key"
```

CI 側からも使えるようにしておくと、ワークフローとローカル手順の差分が減る。

### 2.3 ドキュメント更新要件

**README.md**

「CI での API Key 取り扱い」セクションを追加：
- 初回は CR-FASTAPI-021 の CLI
- CI では CR-FASTAPI-023 の workflow で bootstrap key 自動生成
- TS E2E は CR-FASTAPI-022 の helper に任せる

**docs/api/README.md**

API Key 運用フローの図解 or 箇条書きを追加：
- local bootstrap → `/api/v1/api-keys` → TS helper → E2E

**sdk/typescript/README.md**

CI 実行例として：
- `NEXUSCORE_BOOTSTRAP_API_KEY` は CI workflow が生成してくれる前提
- 手動実行時は CLI で発行した key を export してから `npm test` すること

**.cursorrules**

追加ルール例：

```
In CI, any need for an API key MUST follow this flow:
- Use bootstrap_apikey CLI (CR-FASTAPI-021) to create the initial key.
- Expose it as NEXUSCORE_BOOTSTRAP_API_KEY via CI job outputs or environment.
- Rely on /api/v1/api-keys and helpers (CR-FASTAPI-020/022) for further keys.
- Direct DB insertion of ApiKey rows in CI is FORBIDDEN.
```

### 2.4 テスト要件（Cursor）

Cursor MUST ensure 少なくとも次を manuell に実行できる状態にすること：

```bash
# ローカルで CI 風に再現できること（オプション）
make ci-bootstrap-apikey  # or equivalent

# Python 側テスト（回帰確認）
pytest tests/cli/test_bootstrap_apikey.py -v
pytest tests/api/test_api_keys.py -v

# TS SDK 側 E2E（FastAPI 起動済み前提）
cd sdk/typescript
npm test -- tests/test_projects_e2e.test.ts
```

GitHub Actions 上では：
- `bootstrap-apikey` job が成功し、output に key が設定されていること。
- `ts-e2e` job がその key から E2E を成功裏に実行できること。

