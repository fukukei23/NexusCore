# E2E テストガイド

NexusCore Self-Healing Service の E2E テストを実行するためのガイドです。

## 概要

このガイドでは、以下の手順で E2E テストを実行します：

1. モック GitHub Webhook を送信して Self-Healing をトリガー
2. Streamlit ダッシュボードで実行履歴を確認

## 前提条件

- NexusCore プロジェクトがセットアップ済み
- Python 仮想環境が有効化されている
- `requests` ライブラリがインストールされている（`pip install requests`）

## 1. モック Webhook 送信

### 1-1. サーバの起動

まず、NexusCore の API サーバを起動します：

```bash
# 環境変数の設定（必要に応じて）
export NEXUS_PROJECT_ROOT=/path/to/nexuscore-project

# サーバ起動（例：Flask の場合）
cd /path/to/nexuscore-project
python src/nexuscore/api/server.py
```

または、既存の起動方法に従ってください。

### 1-2. モック Webhook の送信

別のターミナルで、モック Webhook を送信します：

```bash
cd /path/to/nexuscore-project

# テストしたいローカルリポジトリの HEAD SHA を確認
cd /path/to/your/local/repo
git rev-parse HEAD
# → 例: 0123abcd...

# NexusCore プロジェクトに戻る
cd /path/to/nexuscore-project

# モック Webhook を送信
python tools/mock_github_pr_webhook.py \
  --repo-full-name yourname/yourrepo \
  --pr-number 1 \
  --head-sha 0123abcd...
```

### 1-3. カスタム URL の指定

デフォルトでは `http://127.0.0.1:8000/api/github/webhook` に送信されますが、
カスタム URL を指定することもできます：

```bash
python tools/mock_github_pr_webhook.py \
  --url http://localhost:8000/api/github/webhook \
  --repo-full-name yourname/yourrepo \
  --pr-number 1 \
  --head-sha 0123abcd...
```

## 2. ダッシュボードで履歴を確認

### 2-1. ダッシュボードの起動（Linux/WSL）

```bash
cd /path/to/nexuscore-project

# スクリプトを実行
./scripts/run_self_healing_dashboard.sh .

# または、プロジェクトルートを指定
./scripts/run_self_healing_dashboard.sh /path/to/nexuscore-project
```

### 2-2. ダッシュボードの起動（Windows）

```cmd
cd C:\path\to\nexuscore-project

REM スクリプトを実行
scripts\run_self_healing_dashboard.bat .

REM または、プロジェクトルートを指定
scripts\run_self_healing_dashboard.bat C:\path\to\nexuscore-project
```

### 2-3. ダッシュボードの確認項目

ブラウザが開いたら、以下を確認してください：

- **Total runs**: 1 以上になっていること
- **Status Summary**: ステータスの分布（fixed / not_fixed / no_issues / error）が表示されていること
- **Recent Runs**: さきほどの PR 情報（run_id / repo / pr_number）が並んでいること
- **Patch Preview**: `details.patch_preview` が入っていれば、diff が Markdown 表示されていること

## 3. トラブルシューティング

### 3-1. サーバに接続できない

```
エラー: http://127.0.0.1:8000/api/github/webhook に接続できません。
サーバが起動しているか確認してください。
```

**解決方法**:
- API サーバが起動しているか確認
- ポート番号が正しいか確認
- `--url` オプションで正しい URL を指定

### 3-2. ダッシュボードに履歴が表示されない

**確認項目**:
- `.nexus/history/self_healing.log.jsonl` が存在するか
- ファイルにデータが書き込まれているか
- プロジェクトルートが正しく指定されているか

**解決方法**:
```bash
# 履歴ファイルを確認
cat .nexus/history/self_healing.log.jsonl

# プロジェクトルートを明示的に指定
./scripts/run_self_healing_dashboard.sh /path/to/nexuscore-project
```

### 3-3. Streamlit が起動しない

**確認項目**:
- Streamlit がインストールされているか（`pip install streamlit`）
- 仮想環境が有効化されているか

**解決方法**:
```bash
# Streamlit を直接実行
streamlit run src/nexuscore/ui/self_healing_dashboard.py -- --project-root .
```

## 4. 環境変数

以下の環境変数を設定することで、動作をカスタマイズできます：

- `NEXUS_PROJECT_ROOT`: NexusCore プロジェクトのルートディレクトリ
- `NEXUS_REPO_BASE_DIR`: ローカルリポジトリのベースディレクトリ（Self-Healing 用）
- `NEXUS_GITHUB_CLONE_URL_TEMPLATE`: GitHub クローン URL のテンプレート（認証が必要な場合）
- `NEXUS_SELF_HEALING_TEST_CMD`: テスト実行コマンド（デフォルト: `pytest -q`）
- `GITHUB_SELF_HEALING_TOKEN`: GitHub トークン（PR コメント投稿用、オプション）

## 5. 次のステップ

- 実際の GitHub リポジトリで Webhook を設定
- CI/CD パイプラインに統合
- カスタムエージェントの追加

