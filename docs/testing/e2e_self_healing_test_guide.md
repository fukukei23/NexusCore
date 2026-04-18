# Self-Healing E2E テストガイド

GitHub Webhook → Self-Healing → PR コメント投稿までの E2E テストを実行する手順です。

## 概要

このガイドでは、以下のフローを1本通して確認します：

1. モック Webhook を送信
2. Self-Healing Service が実行される
3. GuardianAgent がレビューを実行
4. PR にコメントが投稿される
5. ダッシュボードで履歴を確認

## 事前準備

### 1. Self-Healing 設定ファイルの確認

プロジェクトルートに `.nexus/self_healing.config.json` を作成（または確認）：

```json
{
  "label": "self-healing",
  "allowed_target_branches": ["main"],
  "test_command": "pytest -q",
  "allow_test_modification": false,
  "allow_deletions": false
}
```

### 2. テスト用 PR の準備

GitHub 側でテスト用 PR を用意：

1. 対象リポジトリ: `yourname/yourrepo`
2. base branch: 設定ファイルの `allowed_target_branches` に合わせる（例: `main`）
3. HEAD がテスト失敗するような状態の PR を作成
4. ラベル `self-healing` を付ける（または `config.label` に合わせる）
5. HEAD SHA を取得:
   ```bash
   cd /path/to/your/local/repo
   git rev-parse HEAD
   # → 例: 0123abcd4567ef89...
   ```

### 3. GitHub トークンの準備（オプション）

PR コメント投稿をテストする場合：

1. GitHub Personal Access Token を作成
2. `repo` スコープを付与
3. 環境変数に設定:
   ```bash
   export GITHUB_SELF_HEALING_TOKEN=ghp_xxxxxxxxxxxx
   ```

## 実行手順

### 1. NexusCore サーバの起動

```bash
cd /path/to/nexuscore-project

# 仮想環境を有効化
source myenv_linux/bin/activate  # WSL/Linux
# または
.\venv\Scripts\activate  # Windows

# 環境変数を設定
export NEXUS_PROJECT_ROOT=$(pwd)
export GITHUB_SELF_HEALING_TOKEN=<PR へのコメント投稿ができるトークン>  # 可能なら

# Flask サーバを起動
python src/nexuscore/api/server.py
```

サーバが `http://127.0.0.1:5001` で起動していることを確認。

### 2. モック Webhook の送信

別のターミナルで：

```bash
cd /path/to/nexuscore-project
source myenv_linux/bin/activate  # 必要なら

python tools/mock_github_pr_webhook.py \
  --url http://127.0.0.1:5001/api/github/webhook \
  --repo-full-name yourname/yourrepo \
  --pr-number 1 \
  --head-sha 0123abcd4567ef89 \
  --label self-healing \
  --base-branch main
```

### 3. 期待される挙動

#### サーバ側ログ

ターミナルのサーバ側ログに以下が表示される：

```
INFO - GitHub webhook received: event=pull_request delivery=xxx
INFO - Processing self-healing for yourname/yourrepo PR #1 (head=0123abc)
INFO - Cloning repo: https://github.com/yourname/yourrepo.git -> ...
INFO - Running tests with command: pytest -q
...
```

#### PR コメント（GITHUB_SELF_HEALING_TOKEN が設定されている場合）

対象 PR に NexusCore のコメントが1件追加され、以下が表示される：

- **Status**: `fixed` / `not_fixed` / `no_issues` / `blocked_tests` などのステータス
- **Guardian Review** セクション（GuardianAgent がレビューした場合）:
  - Status: `approved` または `needs_manual_review`
  - Comment: GuardianAgent が生成した説明コメント
- **Patch Preview** セクション:
  - ```diff ... ``` 形式でパッチの内容が表示

## 確認ポイント

### 1. PR コメントで確認すること

PR を開いて、Self-Healing コメントに以下が含まれているか確認：

- ✅ Status 行（`fixed` / `not_fixed` / `blocked_tests` など）
- ✅ Guardian Review セクション（GuardianAgent が実行された場合）
- ✅ Patch Preview セクション（パッチが生成された場合）
- ✅ Run ID と Session ID

### 2. ローカルログ・履歴で確認すること

#### 実行履歴ファイル

```bash
cat .nexus/history/self_healing.log.jsonl | tail -1 | jq .
```

確認項目：
- `status` が期待通り（`fixed` / `not_fixed` など）
- `details.guardian_status` / `details.guardian_comment` が入っている
- `details.patch_preview` が入っている（パッチが生成された場合）

#### Streamlit ダッシュボード

```bash
./scripts/run_self_healing_dashboard.sh .
```

ブラウザで以下を確認：
- Total runs が増えている
- 最新の Run が表示されている
- Status Summary に新しいステータスが反映されている
- Recent Runs に詳細が表示されている

## トラブルシューティング

### Webhook が受け付けられない

**症状**: `404 Not Found` または `405 Method Not Allowed`

**解決方法**:
- サーバが起動しているか確認
- URL が正しいか確認（`/api/github/webhook`）
- Flask サーバのポート番号を確認（デフォルト: 5001）

### ラベルが一致しない

**症状**: `"PR does not meet criteria for self-healing (missing label, draft, etc.)"`

**解決方法**:
- PR に `self-healing` ラベルが付いているか確認
- 設定ファイルの `label` と一致しているか確認
- `--label` オプションで正しいラベル名を指定

### ブランチが許可されていない

**症状**: `"Ignoring PR with base branch 'xxx' (allowed: ['main'])"`

**解決方法**:
- PR の base ブランチが `allowed_target_branches` に含まれているか確認
- `--base-branch` オプションで正しいブランチ名を指定
- 設定ファイルの `allowed_target_branches` を確認

### PR コメントが投稿されない

**症状**: Self-Healing は実行されるが PR にコメントが追加されない

**解決方法**:
- `GITHUB_SELF_HEALING_TOKEN` が設定されているか確認
- トークンに `repo` スコープが付与されているか確認
- GitHub API のレート制限に達していないか確認

### テストが実行されない

**症状**: `"Tests already passing. No self-healing needed."` が返される

**解決方法**:
- テストが実際に失敗する状態になっているか確認
- `test_command` が正しいか確認
- テストコマンドを手動で実行して確認

## 次のステップ

- 実際の GitHub リポジトリで Webhook を設定
- CI/CD パイプラインに統合
- カスタムエージェントの追加
- より複雑なテストケースの追加

