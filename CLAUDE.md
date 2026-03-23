# CLAUDE.md - NexusCore 開発ガイド

## 🎯 プロジェクト概要

**NexusCore** は、AI エージェントを使用したソフトウェア開発の自動化フレームワークです。

- **目的**: 自律的に動作する 18 個以上の AI エージェントが、コード修復、テスト生成、デバッグを自動化
- **技術スタック**: Python、FastAPI、Flask、Celery、Redis、複数の LLM プロバイダー
- **バージョン**: 8.2.0J（最終更新: 2026-03-23）
- **アーキテクチャ**: SaaS 対応の分散マイクロサービス
- **言語対応**: 日本語のみ

### 何ができるのか？
- **自動コード修復**: エラーを検出し、自動で修正を提案・適用
- **テスト生成**: コードからテストケースを自動生成
- **インテリジェント デバッグ**: スタックトレースの分析と自動診断
- **マルチプロバイダー LLM**: OpenAI、Gemini、Claude、DeepSeek など複数の AI モデルに対応
- **予算・ポリシー管理**: トークン使用量の追跡と支出制御
- **Web UI**: リアルタイム監視用の Gradio ダッシュボード＆管理用 Flask アプリ

---

## 🚀 クイックスタート

### 1. 環境セットアップ
```bash
# リポジトリクローン（既に完了）
cd /home/user/NexusCore

# Python 仮想環境作成
python -m venv .venv
source .venv/bin/activate

# 依存パッケージインストール
pip install -r requirements.txt
```

### 2. 設定ファイルの準備
```bash
# テンプレートをコピー
cp .env.template .env

# エディタで .env を開き、API キーを設定
# 例: OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY など
```

### 3. セットアップ確認
```bash
# コード品質チェック（フォーマット、リント、型チェック、テスト）
make qa
```

### 4. 初回実行
```bash
# CLI で直接実行
PYTHONPATH=src python main_cli.py \
  --project-path /tmp/test \
  --language ja \
  "あなたの開発タスクをここに入力"

# または Web UI を使用
PYTHONPATH=src python gradio_app.py
# ブラウザで http://localhost:7860 にアクセス
```

---

## 📂 プロジェクト構成

```
NexusCore/
├── src/nexuscore/
│   ├── agents/                 # 18個の自律エージェント
│   │   ├── requirement_agent.py       # 要件解析
│   │   ├── architect_agent.py         # 設計・アーキテクチャ
│   │   ├── planner_agent.py           # タスク計画
│   │   ├── coder_agent.py             # コード生成
│   │   ├── tester_agent.py            # テスト生成
│   │   ├── debugger_agent.py          # デバッグ実行
│   │   ├── guardian_agent.py          # コードレビュー・品質確認
│   │   ├── policy_agent.py            # ポリシー適用
│   │   ├── postmortem_agent.py        # 失敗分析
│   │   ├── knowledge_curator_agent.py # ナレッジ管理
│   │   └── ...その他
│   │
│   ├── core/                   # オーケストレーション・実行
│   │   ├── orchestrator.py             # メインワークフロー
│   │   ├── job_state_machine.py        # ジョブのライフサイクル
│   │   ├── sandbox_executor.py         # 安全なコード実行
│   │   ├── notifier.py                 # イベント通知（Slack など）
│   │   └── ...その他
│   │
│   ├── llm/                    # LLM プロバイダ抽象化層
│   │   ├── llm_router.py               # 動的モデルルーティング
│   │   ├── task_model_map.py           # タスク→モデル対応
│   │   ├── providers/                  # 各プロバイダの実装
│   │   │   ├── openai_provider.py
│   │   │   ├── gemini_provider.py
│   │   │   ├── anthropic_provider.py
│   │   │   └── ...その他
│   │   └── http_client.py              # HTTP クライアント（リトライ機能付き）
│   │
│   ├── npe/                    # 予算・ポリシー・ログ管理
│   │   ├── budget.py                   # トークン & コスト管理
│   │   ├── policies.py                 # ポリシールール
│   │   ├── logger.py                   # 構造化ログ
│   │   └── engine.py                   # NPE エンジン
│   │
│   ├── webapp/                 # SaaS 用 Flask アプリ
│   │   ├── models.py                   # SQLAlchemy ORM モデル
│   │   ├── auth.py                     # GitHub OAuth
│   │   ├── views_projects.py           # プロジェクト管理エンドポイント
│   │   ├── views_dashboard.py          # ダッシュボード
│   │   └── ...その他
│   │
│   ├── gradio_app/             # インタラクティブ UI
│   │   ├── app_ui.py                   # Gradio ダッシュボード
│   │   ├── dashboard.py                # リアルタイム監視
│   │   └── ...その他
│   │
│   ├── api/                    # 外部連携用 FastAPI サーバー
│   │   ├── server.py                   # REST API
│   │   └── github_webhook_handler.py   # GitHub ウェブフック
│   │
│   └── utils/                  # ユーティリティ関数
│
├── tests/                      # 包括的なテストスイート（100+ テスト）
│   ├── agents/
│   ├── core/
│   ├── llm/
│   └── conftest.py             # pytest フィクスチャ
│
├── docs/                       # ドキュメント
│   ├── development_setup.md
│   ├── saas_architecture.md
│   ├── k8s_setup_status.md
│   ├── job_state_machine_implementation.md
│   └── ...その他
│
├── .env.template               # 環境変数テンプレート
├── requirements.txt            # Python 依存パッケージ
├── Makefile                    # ビルド・テストコマンド
├── main_cli.py                 # メイン CLI エントリーポイント
└── README.md                   # プロジェクト説明
```

---

## 🛠️ 開発ワークフロー

### 環境構築
```bash
# 仮想環境作成（初回のみ）
make venv

# 開発ツール（Black、Ruff、Mypy）をインストール
make install-dev

# 仮想環境を有効化
source .venv/bin/activate
```

### 日常開発

```bash
# コードをフォーマット（Black で自動整形）
make format

# コード品質チェック（Ruff でリント）
make lint

# 型チェック（Mypy で静的型解析）
make typecheck

# テスト実行
make test

# テスト実行＋カバレッジレポート表示
make test-coverage

# すべての品質チェック（推奨）
make qa
```

### アプリケーション実行

```bash
# CLI モード（開発・テスト用）
PYTHONPATH=src python main_cli.py --project-path /tmp/test "実行するタスク"

# Web UI（Gradio ダッシュボード）
PYTHONPATH=src python gradio_app.py
# ブラウザで http://localhost:7860 にアクセス

# API サーバー（外部連携用）
PYTHONPATH=src python -m src.nexuscore.api.server

# Docker で実行（推奨）
docker-compose up
```

---

## 🔑 開発で知っておくべき重要概念

### 1. マルチエージェント オーケストレーション
NexusCore は 18 個の専門化されたエージェントで構成されています：

| エージェント | 役割 |
|---|---|
| `requirement_agent` | ユーザーの要件を解析し、機能仕様に変換 |
| `architect_agent` | システム設計とアーキテクチャを決定 |
| `planner_agent` | 実装手順を計画し、タスクを分解 |
| `coder_agent` | 実際のコードを生成 |
| `tester_agent` | テストケースを自動生成 |
| `debugger_agent` | エラーの原因を特定し修正を試行 |
| `guardian_agent` | コードレビュー、セキュリティチェック |
| `policy_agent` | 企業ポリシーの適用と検証 |
| `postmortem_agent` | 失敗の根本原因を分析 |

**メインのオーケストレーター**: `src/nexuscore/core/orchestrator.py` で全体フローを管理

### 2. 複数の LLM プロバイダー対応
複数の AI モデルに対応し、動的にルーティングします：

```bash
# .env ファイルで API キーを設定
OPENAI_API_KEY=sk-...              # GPT-4, GPT-3.5-turbo
GEMINI_API_KEY=...                 # Google Gemini
ANTHROPIC_API_KEY=sk-ant-...       # Claude
PERPLEXITY_API_KEY=...             # Perplexity
DEEPSEEK_API_KEY=...               # DeepSeek
KIMI_API_KEY=...                   # Moonshot Kimi
```

**実装**: `src/nexuscore/llm/llm_router.py` で自動ルーティング

### 3. NPE（Non-Prompt Engineering）- 予算・ポリシー管理
トークン使用量と支出を厳密に追跡・制御：

```python
# 実装位置: src/nexuscore/npe/

# 1. 予算追跡
budget.py          # プロバイダごとのトークン & ドル単位での支出管理

# 2. ポリシー適用
policies.py        # 企業ルールの実装・検証

# 3. ログ管理
logger.py          # 構造化ログ（ファイル & データベース）
```

### 4. ジョブ状態機械
ジョブのライフサイクルを管理：

```
PENDING → RUNNING → SUCCESS / FAILED
  ↓
   再開可能（ジョブレジューム機能）
```

実装: `src/nexuscore/core/job_state_machine.py`

### 5. サンドボックス実行
生成されたコードを安全に実行：
- タイムアウト設定
- リソース制限（メモリ、CPU）
- 出力キャプチャと ログ記録

実装: `src/nexuscore/core/sandbox_executor.py`

---

## 📊 テストについて

### テスト戦略
- **フレームワーク**: pytest
- **カバレッジ目標**: 80% 以上
- **主要テスト対象**: エージェント、LLM ルーティング、オーケストレーター、API エンドポイント

### テスト実行
```bash
# すべてのテスト実行
make test

# カバレッジ付きで実行
make test-coverage

# 特定のテストファイルのみ
PYTHONPATH=src pytest tests/agents/test_coder_agent.py -v

# 特定のテスト関数のみ
PYTHONPATH=src pytest tests/core/test_orchestrator.py::test_job_state_transition -v
```

### テスト結果
- **HTML カバレッジレポート**: `htmlcov/index.html`
- **統計サマリー**: ターミナル出力に表示

---

## ✅ コード品質基準

NexusCore では以下の基準を厳格に適用しています：

### Black（コードフォーマッター）
```bash
make format
# 行長: 88 文字、シングルクォート、末尾カンマなど自動統一
```

### Ruff（リンター）
```bash
make lint
# PEP 8 準拠、未使用インポート、複雑さチェック
```

### Mypy（型チェッカー）
```bash
make typecheck
# 型アノテーション検証（厳密モード）
```

### すべてまとめて
```bash
make qa
# 上記 3 つ + テスト実行（最も推奨）
```

---

## 🔐 環境設定（.env）

### テンプレートから作成
```bash
cp .env.template .env
```

### 必須設定（最低ひとつの LLM プロバイダー）
```ini
# OpenAI
OPENAI_API_KEY=sk-...

# Google Gemini
GEMINI_API_KEY=...

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...
```

### 推奨設定
```ini
# データベース
DATABASE_URL=sqlite:///nexuscore.db

# ログレベル
LOG_LEVEL=INFO

# Slack 通知（オプション）
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# GitHub OAuth（Web UI 使用時）
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# 予算管理
DAILY_SPENDING_LIMIT=100  # USD/day
TOKEN_WARNING_THRESHOLD=80000
```

---

## 📚 重要ファイルと場所

| ファイル | 説明 |
|---|---|
| `main_cli.py` | メイン CLI エントリーポイント |
| `gradio_app.py` | Gradio Web UI 起動スクリプト |
| `src/nexuscore/utils/config.py` | 設定読み込み |
| `src/nexuscore/npe/logger.py` | ログ（ファイル & データベース） |
| `src/nexuscore/core/orchestrator.py` | メインワークフロー |
| `src/nexuscore/webapp/views_*.py` | Flask ルート定義 |
| `src/nexuscore/api/server.py` | FastAPI エンドポイント |
| `logs/` | 実行ログディレクトリ |
| `docs/` | プロジェクトドキュメント |

---

## 🐛 デバッグのコツ

### 1. ログを確認
```bash
# ログディレクトリ
ls -la logs/

# 最新のログを表示
tail -f logs/latest.log

# データベースログを SQL で検索
sqlite3 nexuscore.db "SELECT * FROM ExecutionLog ORDER BY timestamp DESC LIMIT 10;"
```

### 2. 詳細ログを有効化
```bash
# .env に以下を追加
LOG_LEVEL=DEBUG

# CLI 実行時
PYTHONPATH=src python main_cli.py --debug ...
```

### 3. Gradio ダッシュボードで監視
```bash
PYTHONPATH=src python gradio_app.py
# リアルタイムでジョブ実行を追跡
```

### 4. テストを詳細表示
```bash
PYTHONPATH=src pytest tests/ -vv --tb=long
```

### 5. 特定のエージェントをテスト
```bash
PYTHONPATH=src pytest tests/agents/test_coder_agent.py -v --pdb
```

---

## ⚠️ よくある問題と解決方法

| 問題 | 原因 | 解決策 |
|---|---|---|
| `ModuleNotFoundError` | Python パス設定なし | `PYTHONPATH=src` を付加 |
| `API key not found` | .env に API キー未設定 | `.env.template` をコピーしてキーを追加 |
| `Redis connection failed` | Redis サーバー未起動 | `docker-compose up` で起動 |
| `Permission denied` | ファイルの実行権限なし | `chmod +x filename` |
| `Port already in use` | ポート競合 | ポート番号を変更するか、既存プロセスを停止 |
| テスト失敗 | 依存パッケージ古い | `pip install -r requirements.txt --upgrade` |

---

## ⚠️ ドキュメント貼り付けミスへの注意

### 重要な確認事項

ドキュメントを作成・修正する際に、**他のプロジェクトのコードや内容を誤って貼り付けないよう注意が必要です**。NexusCore プロジェクトに関連のない内容が混在してしまう可能性があります。

### チェックリスト

ドキュメント作成時は以下を確認してください：

- ✅ **プロジェクト名**: 「NexusCore」に関連した内容のみ
- ✅ **ファイルパス**: `/home/user/NexusCore/` 配下のパスのみ記載
- ✅ **モジュール名**: `nexuscore` パッケージ配下のモジュールのみ
- ✅ **テクノロジー**: FastAPI、Flask、Celery、Redis など、このプロジェクトで使用しているものだけ
- ✅ **エージェント名**: requirement_agent、architect_agent、coder_agent など、実際に存在するエージェント
- ✅ **コマンド例**: `make qa`、`PYTHONPATH=src python` など、このプロジェクト特有のコマンド

### 貼り付けミスを発見した場合

もし間違ったドキュメントをアップロード・貼り付けしてしまった場合：

1. **修正を依頼してください** - 「XXX という別プロジェクトの内容が含まれているので修正してください」と明示的に指摘
2. **改めて作成します** - ドキュメント全体を削除して、NexusCore 専用の内容で再作成
3. **確認後にプッシュ** - 修正内容を確認してから git push します

### 例：貼り付けミスの指摘方法

```
❌ 貼り付けミス：
「このドキュメントに、atelier-kyo-manager というプロジェクトの構成が含まれています。
NexusCore のみで書き直してください」

✅ 正しい修正：
「わかりました。CLAUDE.md を NexusCore 専用に修正し、他プロジェクトの内容をすべて削除します」
```

---

## 🚢 Git ワークフロー

### 開発ブランチ
```bash
# 現在の作業ブランチを確認
git branch

# 新しいブランチを作成
git checkout -b docs/新機能

# このブランチに変更をコミット
git add .
git commit -m "feat: 変更内容"
git push -u origin docs/新機能
```

### コミット前のチェックリスト
```bash
# 1. 品質チェック実行
make qa

# 2. テストパス確認
make test-coverage

# 3. ブランチ確認
git status

# 4. コミット実行
git add .
git commit -m "feat: 変更内容を明確に説明"

# 5. プッシュ
git push -u origin <ブランチ名>
```

### コミットメッセージのルール
```
feat:  新機能追加
fix:   バグ修正
docs:  ドキュメント更新
test:  テスト追加・変更
refactor: コード整理（機能変化なし）
perf:  パフォーマンス改善
chore: ビルド・設定・依存パッケージ更新

例:
feat: coder_agent に型注釈サポートを追加
fix: orchestrator の状態遷移バグを修正
docs: CLAUDE.md に環境変数セクションを追加
```

---

## 📖 さらに詳しく知りたい場合

プロジェクトドキュメント（`docs/` ディレクトリ）:
- `development_setup.md` - 詳細なセットアップガイド
- `saas_architecture.md` - システムアーキテクチャ全体像
- `k8s_setup_status.md` - Kubernetes デプロイメントガイド
- `job_state_machine_implementation.md` - ジョブ実行ライフサイクル詳細
- その他多数の設計ドキュメント

---

## 💡 Claude Code に相談すべき場合

以下の場合は Claude Code に相談してください：

- **エージェントの動作を変更したい** - エージェントロジックの修正
- **新しいエージェントを追加したい** - マルチエージェント構造の拡張
- **LLM ルーティングを調整したい** - プロバイダ選択ロジックの最適化
- **テストカバレッジを向上したい** - テスト追加・改善
- **オーケストレーター周りの不具合** - ワークフロー実行の問題
- **ジョブ実行が失敗する** - デバッグと状態分析

---

## 🎉 開発を始める準備ができました！

```bash
# 1. 仮想環境を有効化
source .venv/bin/activate

# 2. 品質チェック実行
make qa

# 3. 最初のタスク実行
PYTHONPATH=src python main_cli.py \
  --project-path /tmp/test \
  --language ja \
  "開発したい機能を説明"
```

不明な点があれば、いつでもドキュメントを参照するか Claude Code に質問してください！
