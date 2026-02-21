# NexusCore

> **多層品質ゲートを備えた自律型マルチエージェントAI開発フレームワーク**

[![Test Coverage](https://img.shields.io/badge/coverage-87.36%25-brightgreen)](docs/FINAL_COMPREHENSIVE_TEST_REPORT.md)
[![Tests](https://img.shields.io/badge/tests-940%20passing-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**NexusCore** は、ソフトウェア開発ライフサイクル全体を支援する自律型AIエージェント群を統合したフレームワークです。要件分析からアーキテクチャ設計、コード生成、テスト、品質保証まで、各フェーズを専門エージェントが担当します。

---

## ✨ 主要機能

### 🤖 マルチエージェントシステム
- **10+ 専門エージェント**: Architect, Coder, Debugger, Tester, Guardian, Requirement, Postmortem, Knowledge Curator, Policy, Constitutional Council
- **タスクベースLLMルーティング**: 各タスクに最適なLLMを自動選択（GPT-5.1, Claude 4.5, DeepSeek R1, Gemini 3.0等）
- **コスト最適化**: 予算管理、自動フォールバック、日次上限設定

### 🛡️ 多層品質ゲート
- **Tier 1 - コード品質**
  - カバレッジ分析（80%以上）
  - Pylint（8.0/10以上）
  - Mypy型チェック
  - Banditセキュリティスキャン


- **Tier 2 - ミューテーションテスト**
  - コード変異生成
  - テストスイート強度測定
  - 生存変異の検出

[![Self-Healing Success Rate](https://your-nexuscore-host/api/v1/projects/1/badge/success_rate)](https://your-nexuscore-host/dashboard/projects/1)
[![Self-Healing Last Run](https://your-nexuscore-host/api/v1/projects/1/badge/last_run)](https://your-nexuscore-host/dashboard/projects/1)


### 🏛️ Constitutional AI ガバナンス
- ポリシー駆動の意思決定
- 修正案提案システム
- 承認ワークフロー
- 監査証跡

### 🧠 ナレッジベース統合
- 失敗事例からの学習
- パターンマッチングによる解決策提示
- グローバル/ローカルナレッジベース

---

## 📊 プロジェクト状況

| 指標 | 値 |
|------|-----|
| **テストカバレッジ** | 16.85% (Core Agents: 65-89%) |
| **包括的テスト** | 20ファイル, 431テスト合格 |
| **エージェント数** | 20+ 専門エージェント |
| **LLMプロバイダー** | 5プロバイダー（OpenAI, Anthropic, DeepSeek, Google, Kimi） |
| **品質ゲート** | 2層（静的解析＋動的テスト） |

📈 [詳細なカバレッジレポート](docs/reports/COVERAGE_SUMMARY.md) | 🏗️ [アーキテクチャドキュメント](docs/ARCHITECTURE.md)

---

## 🚀 クイックスタート

### 前提条件

- Python 3.11以上
- pip
- Git

### インストール

```bash
# リポジトリのクローン
git clone https://github.com/your-org/NexusCore.git
cd NexusCore

# 仮想環境の作成と有効化
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.template .env
# .envファイルを編集してAPIキーを設定
```

### 環境変数の設定

`.env`ファイルに以下を設定：

```env
# LLM API Keys
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
DEEPSEEK_API_KEY=your-deepseek-api-key
GEMINI_API_KEY=your-gemini-api-key

# Budget Settings
DAILY_BUDGET_USD=5.0
ENABLE_BUDGET_GUARD=true

# Quality Gate Settings
MIN_COVERAGE_PERCENTAGE=80.0
MIN_PYLINT_SCORE=8.0
MIN_MUTATION_SCORE=70.0
```

### 基本的な使用例

```python
from src.nexuscore.agents.coder_agent import CoderAgent
from src.nexuscore.llm.llm_router import LLMRouter

# LLMルーターの初期化
router = LLMRouter()

# CoderAgentの初期化
coder = CoderAgent(llm_router=router)

# コード生成
result = coder.implement_code(
    task_description="Pythonで二分探索を実装してください",
    context="データ構造の勉強用"
)

print(result["code"])
```

### テストの実行

```bash
# 包括的テストの実行
python -m pytest tests/agents/test_*_comprehensive.py -v

# カバレッジ付きでテスト実行
python -m pytest tests/agents/test_*_comprehensive.py --cov=src/nexuscore --cov-report=html

# 特定のエージェントのテスト
python -m pytest tests/agents/test_guardian_agent_comprehensive.py -v
```

---

## 📂 プロジェクト構成

```
NexusCore/
├── src/nexuscore/
│   ├── agents/              # AIエージェント実装
│   │   ├── base_agent.py           # ベースエージェント（LLM統合）
│   │   ├── architect_agent.py      # アーキテクチャ設計
│   │   ├── coder_agent.py          # コード生成
│   │   ├── debugger_agent.py       # エラー修正
│   │   ├── tester_agent.py         # テスト生成
│   │   ├── guardian_agent.py       # 品質ゲート
│   │   ├── requirement_agent.py    # 要件分析
│   │   ├── postmortem_agent.py     # 失敗分析
│   │   ├── knowledge_curator_agent.py  # ナレッジ管理
│   │   ├── policy_agent.py         # ポリシー適用
│   │   ├── constitutional_council_agent.py  # ガバナンス
│   │   └── mutation_tester_agent.py  # ミューテーションテスト
│   │
│   ├── llm/                 # LLM統合レイヤー
│   │   ├── llm_router.py           # タスクベースモデルルーティング
│   │   ├── budget_manager.py       # コスト追跡
│   │   └── providers/              # LLMプロバイダー実装
│   │
│   ├── utils/               # ユーティリティモジュール
│   │   ├── code_analyzer.py        # コード品質分析
│   │   ├── vcs.py                  # Git操作
│   │   ├── diff_tools.py           # 差分生成
│   │   └── test_generator.py      # テスト生成ユーティリティ
│   │
│   ├── core/                # オーケストレーター
│   ├── npe/                 # 予算・ポリシー・ガード機能
│   └── webapp/              # Webインターフェース
│
├── tests/                   # テストスイート
│   └── agents/              # エージェントテスト（431テスト）
│
├── docs/                    # ドキュメント
│   ├── ARCHITECTURE.md      # アーキテクチャドキュメント
│   └── reports/             # テストレポート
│
├── dev_tools/               # 開発支援ツール
├── tools/                   # 補助ユーティリティ
└── output/                  # 実行ログ・一時ファイル
```

---

## 🏗️ アーキテクチャ

### システム概要

```
User/Developer
      ↓
  Orchestrator
      ↓
  ┌─────────────┐
  │ Agent Layer │
  └─────┬───────┘
        ├→ LLM Router ──→ [GPT-5.1 | Claude 4.5 | DeepSeek | Gemini | Kimi]
        └→ Quality Gates
             ├→ Tier 1: Code Quality (Coverage, Pylint, Mypy, Bandit)
             └→ Tier 2: Mutation Testing
```

詳細は [アーキテクチャドキュメント](docs/ARCHITECTURE.md) を参照してください。

### 主要なデザインパターン

1. **エージェントパターン**: 各エージェントは`BaseAgent`を継承し、標準化されたLLM連携を実現
2. **品質ゲートパターン**: 多層検証（静的→動的）でクリティカルな問題を早期検出
3. **Constitutional AIパターン**: ポリシー駆動の意思決定と修正案システム
4. **ルーターパターン**: タスクベースのモデル選択とコスト最適化
5. **ナレッジベースパターン**: 失敗からの学習とパターンマッチング

### API 構成

NexusCore の API は以下のように構成されています：

- **FastAPI**: 公開 API 層（`/api/v1/*`）- 正式版（単一の正）
  - 外部統合向けの REST API は FastAPI ベースで実装されています
  - 統一された認証（API Key）、エラーハンドリング、OpenAPI スキーマを提供
  - すべてのクライアントは FastAPI エンドポイント（`/api/v1/*`）を使用する必要があります
  - 詳細は `docs/api/README.md` を参照してください

- **Flask**: Web UI 層（`/projects/*`, `/dashboard/*` など）- 当面存続
  - HTML テンプレート・ビューを提供する Web UI は Flask ベースで実装されています
  - Flask REST API（`/api/v1/*` 配下のエンドポイント）は **CR-FASTAPI-010 で完全削除済み**です
  - すべての REST API は FastAPI 側に統一されました
  - 詳細は `docs/api/FASTAPI_MIGRATION_STATUS.md` を参照してください

**重要**: Flask REST API (`/api/v1/*` 配下のエンドポイント) は CR-FASTAPI-010 で完全削除されました。すべてのクライアントは FastAPI エンドポイント（`/api/v1/*`）を使用する必要があります。

### アーキテクチャ: WebApp と FastAPI の責務分離

- **WebApp (Flask)**: サーバー内部 UI（人間向け HTML 画面）
  - HTML レンダリングとフォーム受け付けを担当
  - データ取得は FastAPI 経由ではなく、直接データベースアクセスまたは services 層を使用
  - FastAPI API migration の対象外（責務分離のため）
  - 詳細は `docs/api/WEBAPP_UI_API_MAPPING.md` を参照してください

- **FastAPI**: 公開 API（外部/機械向け JSON API）
  - SDK / CLI / 外部統合向けのエンドポイント（`/api/v1/*`）
  - 統一された認証、エラーハンドリング、OpenAPI スキーマを提供
  - **エラーコード**: すべてのエラーコードは `docs/api/ERROR_CODE_CATALOG.md` に定義されています（単一のソース）
  - **認証エラー時のステータスコードポリシー**:
    - **401 Unauthorized**: API Key が無効または欠如（認証フェイル）
    - **500 Internal Server Error**: DB アクセスエラーやサーバー設定エラー（認証フェイルではない）
    - **重要な原則**: 認証フェイルは決して 500 を返さない
    - 詳細は `docs/api/README.md` の「認証エラー時のステータスコードポリシー」セクションを参照してください

### SDK 自動生成

NexusCore の FastAPI API から OpenAPI 仕様書を取得し、Python / TypeScript 向け SDK を自動生成できます。

- **OpenAPI 仕様書**: FastAPI アプリから自動生成（`/api/openapi.json`）
- **SDK 生成ツール**: `tools/generate_sdk.py`（OpenAPI Generator CLI を使用）
- **生成コマンド**: `make sdk`（すべての SDK を生成）、`make sdk-python`（Python のみ）、`make sdk-ts`（TypeScript のみ）

**重要**: SDK コードは手書きせず、必ず `tools/generate_sdk.py` を使用して OpenAPI 仕様書から自動生成してください。OpenAPI 仕様書が SDK の単一のソース（Single Source of Truth）です。

#### SDK 商品化（CR-FASTAPI-018, CR-FASTAPI-019）

**Python SDK** は v0.1.0 として商品化されました。詳細は [CR-FASTAPI-018 完了レポート](docs/api/CR-FASTAPI-018_COMPLETION_REPORT.md) を参照してください。

- **バージョン**: 0.1.0
- **インストール**: `cd sdk/python && pip install .`
- **ビルド**: `make sdk-python-build`
- **TestPyPI 公開**: `make sdk-python-publish-test`（TESTPYPI_API_TOKEN 環境変数が必要）

**TypeScript SDK** も v0.1.0 として整備されました。詳細は [CR-FASTAPI-019 完了レポート](docs/api/CR-FASTAPI-019_COMPLETION_REPORT.md) を参照してください。

- **バージョン**: 0.1.0
- **インストール**: `cd sdk/typescript && npm install`
- **ビルド**: `make sdk-ts-build`
- **テスト**: `make sdk-ts-test`
- **Test npm Registry 公開**: `make sdk-ts-publish-test`（NPM_TOKEN 環境変数が必要）

#### API Key 発行 API（CR-FASTAPI-020）

認証済みユーザーが API Key を発行・管理できる正式な HTTP API が追加されました。詳細は [CR-FASTAPI-020 完了レポート](docs/api/CR-FASTAPI-020_COMPLETION_REPORT.md) を参照してください。

- **POST /api/v1/api-keys**: API Key を新規発行（認証必須）
- **GET /api/v1/api-keys**: API Key 一覧取得（認証必須）
- **DELETE /api/v1/api-keys/{api_key_id}**: API Key 無効化（認証必須）
- **制約**: 1ユーザーあたり最大5個の API Key 発行上限

#### API Key 運用フロー（CR-FASTAPI-021, CR-FASTAPI-022, CR-FASTAPI-023）

**初回 API Key 発行（ブートストラップ CLI）**:
```bash
# プロジェクトルートに移動（重要）
cd /home/yn441611/NexusCore

# 仮想環境を有効化
source activate

# PYTHONPATH を設定（重要）
export PYTHONPATH=src

# ユーザーが存在しない場合は自動作成
python -m nexuscore.cli.bootstrap_apikey \
  --user-login dev \
  --user-name "Dev User" \
  --key-name "Local Dev Key"

# 出力をコピーして環境変数に設定
export NEXUSCORE_API_KEY="nexus_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**2本目以降の API Key 発行**:
```bash
# 既存の API Key で認証して新しい API Key を発行
curl -X POST http://localhost:8000/api/v1/api-keys \
  -H "X-API-Key: existing-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "CI/CD Key"}'
```

**TypeScript E2E テスト用**:
```bash
# ブートストラップキーを設定
export NEXUSCORE_BOOTSTRAP_API_KEY="nexus_xxx..."

# E2E テスト実行（helper が自動的に API Key を発行）
cd sdk/typescript
npm test -- tests/test_projects_e2e.test.ts
```

**CI での API Key 取り扱い（CR-FASTAPI-023）**:

GitHub Actions では、`.github/workflows/ts-e2e.yml` が自動的に bootstrap API Key を生成し、後続の TS E2E テストジョブに渡します。

**CI フロー**:
1. `bootstrap-apikey` ジョブが `bootstrap_apikey` CLI を実行して bootstrap key を生成
2. 生成された key を job output として後続ジョブに渡す
3. `ts-e2e` ジョブが `NEXUSCORE_BOOTSTRAP_API_KEY` 環境変数を受け取り、E2E テストを実行
4. E2E テスト内の helper (`getE2EApiKey()`) が自動的にテスト用 API Key を発行

**ローカルで CI フローを再現**:
```bash
# CI と同じ方法で bootstrap key を生成
make ci-bootstrap-apikey
npm test -- tests/test_projects_e2e.test.ts
```

詳細は [CR-FASTAPI-021 完了レポート](docs/api/CR-FASTAPI-021_COMPLETION_REPORT.md) と [CR-FASTAPI-022 完了レポート](docs/api/CR-FASTAPI-022_COMPLETION_REPORT.md) を参照してください。

### E2E テスト

生成された SDK と FastAPI アプリの連携を実際に検証する E2E テストを実行できます：

```bash
# SDK を生成（事前に実行）
make sdk-python

# E2E テストを実行
make test-e2e
```

**注意**: SDK が生成されていない場合、E2E テストは自動的にスキップされます。
これは「テスト環境の問題」であり、SDK / API 実装のバグではありません。

詳細は `docs/api/README.md` の「SDK 自動生成」と「E2E テスト」セクションを参照してください。

---

## 🛠️ 使用技術

| カテゴリ | 技術 |
|---------|------|
| **言語** | Python 3.11+ |
| **AI/LLM** | OpenAI GPT, Anthropic Claude, DeepSeek, Google Gemini, Kimi |
| **テスト** | pytest, pytest-cov, カスタムミューテーションテスト |
| **品質** | pylint, mypy, bandit |
| **VCS** | GitPython |
| **Web** | Flask, Gradio |
| **その他** | patch-ng, dataclasses |


1. `\\wsl.localhost\Ubuntu\home\yn441611\NexusCore`（Linux シェルでは `/home/yn441611/NexusCore`）に移動し、これを作業ルートにします。
2. システム Python には `pip` が入っていないため、`python3 -m venv venv` で仮想環境を作成します。
3. `source venv/bin/activate` で仮想環境を有効化し、`pip install -r requirements.txt` で依存をインストール。
   - 開発ツールも含める場合: `pip install -r requirements.txt -r requirements-dev.txt`
   - 主要な依存関係はバージョンレンジで固定されています（例: `openai>=1.30.0,<2.0.0`）。詳細は `requirements.txt` を参照してください。
4. 実行時は仮想環境を有効化（`source activate` または `source venv/bin/activate`）してから `python` / `pip` を呼び出してください。
   - より簡単な方法: プロジェクトルートで `source activate` を実行（推奨）
   - 詳細は `README_VENV.md` を参照してください。
5. ネイティブなログ・出力先は `/home/yn441611/NexusCore/...` に向け、権限エラーを回避します。
6. 依存を追加したら `pip freeze > requirements.lock.txt` などでロックファイルを更新して共有してください。

## 📚 ドキュメント

- [アーキテクチャドキュメント](docs/ARCHITECTURE.md) - システム設計の詳細
- [カバレッジレポート](docs/reports/COVERAGE_SUMMARY.md) - テストカバレッジの詳細
- [HTMLカバレッジレポート](docs/reports/coverage/index.html) - 対話的カバレッジレポート
- [API リファレンス](docs/API.md) - エージェントAPIドキュメント（作成予定）

---

## 🧪 テスト

### 包括的テストスイート

20の包括的テストファイル、431のテストケース：

```bash
# 全包括的テストの実行
python -m pytest tests/agents/test_*_comprehensive.py -v

# 個別エージェントのテスト
python -m pytest tests/agents/test_guardian_agent_comprehensive.py -v
python -m pytest tests/agents/test_coder_agent_comprehensive.py -v
python -m pytest tests/agents/test_debugger_agent_comprehensive.py -v
```

### テストカバレッジ

| モジュール | カバレッジ |
|-----------|----------|
| architect_agent.py | 89.13% |
| patch_applier.py | 82.98% |
| postmortem_agent.py | 84.21% |
| mutation_tester_agent.py | 78.95% |
| coder_agent.py | 71.60% |
| base_agent.py | 70.53% |
| guardian_agent.py | 69.11% |
| debugger_agent.py | 65.12% |

---

## 🔍 品質保証

### Guardian Agent による多層品質ゲート

```python
from src.nexuscore.agents.guardian_agent import GuardianAgent

guardian = GuardianAgent()

# 品質ゲートの実行
result = guardian.run_quality_gates(
    code_path="/path/to/code",
    test_path="/path/to/tests",
    constitution=constitution_config
)

if result["overall_passed"]:
    print("✅ 全ての品質ゲートに合格")
    print(f"Tier 1: {result['tier1']['passed']}")
    print(f"Tier 2: {result['tier2']['passed']}")
else:
    print("❌ 品質ゲート不合格")
    print(f"理由: {result.get('feedback')}")
```

### 品質基準

- **カバレッジ**: 80%以上
- **Pylint**: 8.0/10以上
- **Mypy**: エラーなし
- **Bandit**: セキュリティ問題なし
- **ミューテーションスコア**: 70%以上

---

## 🛡️ NexusCore安全運用ガイド

NexusCoreでは、Claude Codeを使用した開発時に破壊的操作を防止し、コード品質を保証するための安全設定を導入しています。

### 📋 安全設定ファイル

プロジェクトルートに `.claude/settings.local.json` が配置されており、以下の安全制御が有効化されています：

#### 🟢 許可される操作（自動実行）

**Git基本操作:**
```bash
git init / add / commit / status / diff / log / branch / checkout / show / reflog
```

**Python開発ツール:**
```bash
python / python3 / pytest / pip install / pip list
coverage / black / ruff / mypy / bandit
```

**NexusCore特化ツール:**
```bash
uvicorn / fastapi / playwright / redis-cli / celery / httpx
```

**Docker/WSL（読み取りのみ）:**
```bash
docker ps / logs / inspect
docker-compose config
wsl --status / --list
```

#### 🟡 確認が必要な操作（実行前に確認）

**Git高度な操作:**
```bash
git push / pull / merge / rebase / reset / clean / stash
```

**ファイル削除:**
```bash
rm *.py
rm requirements.txt / pyproject.toml / pytest.ini
```

**Docker/WSL実行:**
```bash
docker run / build
docker-compose up / down
wsl --shutdown
```

**データベース削除:**
```bash
DROP TABLE / TRUNCATE / DELETE FROM
redis-cli FLUSHALL / FLUSHDB
```

#### 🔴 常に拒否される操作

**破壊的Git操作:**
```bash
git push -f / --force
git reset --hard
git clean -fd / -fdx
```

**危険なファイル操作:**
```bash
rm -rf src/ / tests/ / .git/
sudo rm
```

### 🔐 環境変数ファイルの保護

`.env`, `.env.local`, `.env.production` などの環境変数ファイルは**読み取り専用**に設定されています：

```bash
# ✅ 許可: 読み取り
cat .env
echo $OPENAI_API_KEY

# ❌ 拒否: 書き込み
echo "NEW_KEY=xxx" > .env
rm .env
```

**⚠️ 重要:** APIキーや機密情報の変更は手動で行ってください。

### 🌿 ブランチ命名規則

NexusCore開発では以下のブランチ命名規則を推奨します：

```
claude/nexuscore-quality-*    # Claude Code作業ブランチ（推奨）
feature/*                      # 新機能開発
fix/*                          # バグ修正
test/*                         # テスト追加
```

**例:**
```bash
git checkout -b claude/nexuscore-quality-api-tests
git checkout -b feature/self-healing-v2
git checkout -b fix/coverage-report-bug
```

### ✅ 品質チェック自動実行

以下の品質チェックがコミット/プッシュ時に自動実行されます：

**Pre-commit（コミット前）:**
```bash
ruff check src/              # Lintチェック
black --check src/           # コードフォーマット確認
pytest tests/ -v --maxfail=1 # テスト実行（1つ失敗で停止）
```

**Pre-push（プッシュ前）:**
```bash
pytest tests/ --cov=src/nexuscore --cov-report=term-missing  # カバレッジ測定
bandit -r src/ -ll                                             # セキュリティスキャン
```

**最小品質基準:**
- テストカバレッジ: 80%以上
- Pylint: 8.0/10以上
- セキュリティ問題: なし

### 🚨 トラブルシューティング

**問題: git push が実行できない**
```bash
# 解決: 確認プロンプトで "yes" を入力
git push origin feature/my-branch
# → "この操作を実行しますか？ (yes/no):" と表示されたら yes を入力
```

**問題: .env ファイルを変更したい**
```bash
# 解決: エディタで手動編集（Claude Codeは読み取り専用）
code .env  # または nano .env
```

**問題: docker コマンドが実行できない**
```bash
# 解決: 読み取りコマンド（docker ps など）は自動実行、実行コマンドは確認が必要
docker ps           # ✅ 自動実行
docker-compose up   # 🟡 確認必要
```

### 📚 関連ドキュメント

- [`.claude/settings.local.json`](.claude/settings.local.json) - 安全設定の詳細
- [開発ガイドライン](#開発ガイドライン) - コード品質基準
- [品質保証](#-品質保証) - Guardian Agentによる多層品質ゲート

---

## 🤝 コントリビューション

コントリビューションを歓迎します！

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

### 開発ガイドライン

- 新機能には包括的なテストを追加
- コードは品質ゲート（Tier 1 & Tier 2）をパス
- ドキュメントを更新
- コミットメッセージは明確に

---

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

---

## 📞 サポート

- **Issues**: [GitHub Issues](https://github.com/your-org/NexusCore/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/NexusCore/discussions)
- **Email**: support@nexuscore.dev

---

## 🌟 謝辞

このプロジェクトは以下の技術・プロジェクトに支えられています：

- [OpenAI](https://openai.com/) - GPT-5.1 Codex
- [Anthropic](https://anthropic.com/) - Claude 4.5 Sonnet
- [DeepSeek](https://deepseek.com/) - DeepSeek R1
- [Google AI](https://ai.google/) - Gemini 3.0 Pro
- [pytest](https://pytest.org/) - テストフレームワーク

---


## 📚 ドキュメント構成

NexusCore プロジェクトの詳細ドキュメントは `docs/` ディレクトリに整理されています。

- **[開発ガイド（軽量版）](DEVELOPMENT.md)** - スピーディーな開発フローと最小限のルール
- **[ドキュメント全体インデックス](docs/DOCS_INDEX.md)** - すべてのドキュメントへのナビゲーション
- **[仮想環境の使い方](README_VENV.md)** - 仮想環境の簡単な使い方

**役割別の導線:**
- **新規開発者向け**: [開発ガイド（軽量版）](DEVELOPMENT.md) → [開発環境セットアップ](docs/development_setup.md) → [README_VENV.md](README_VENV.md)
- **運用担当者向け**: [Kubernetes クイックスタート](docs/k8s_quick_start_guide.md) → [SaaS アーキテクチャ](docs/saas_architecture.md)
- **AI / Cursor 向け**: [コードレビュー対応 Playbook](docs/cursor_nexuscore_playbook.md) → [Codex 指示マニフェスト](docs/codex_instruction_manifest.md)

### 軽量開発フロー（2026-02移行）

**重要**: NexusCore は軽量開発フローに移行しました。

- **旧規約（520行の.cursorrules）**: `GOVERNANCE/archive/legacy_cursorrules_520lines.md` にアーカイブ
- **新規約（168行）**: `.claude/rules.md` - 最小限のルールのみ
- **開発ガイド**: `DEVELOPMENT.md` - Tier 1/Tier 2 分類と簡易仕様

**主な変更**:
- ✅ Spec必須はTier 1タスクのみ（認証、決済、公開APIなど）
- ✅ Tier 2タスク（バグ修正、小機能）は直接実装
- ✅ 週次レビューは自動化（Code Reviewer Agent）
- ✅ 開発速度: 月間で約70%の時間短縮（28時間節約）

詳細は [開発ガイド（軽量版）](DEVELOPMENT.md) を参照してください。

---

## 🧰 補足メモ

- `.env.template` をコピーして `.env` を作成し、API キーや最大予算などを記入してください。
- `output/` 以下にログや自動テスト結果がたまりますので、コミット不要のものは `.gitignore` に入れています。
- 大型変更を加えるときは `python -m tools.list_core_files --format json` などで影響範囲を確認しつつ、`tests/` の適切なユニットを更新してください。
- 新しい LLM プロバイダ追加時は下記フローに従ってください。
  1. `src/nexuscore/llm/providers/` に `<vendor>_provider.py` を新規作成し、`BaseLLM` を継承したクラスで実装（API キーの `None` 判定と `HTTP_CLIENT_FACTORY` の Session 取得が必須）。
  2. JSON 整形／スタブ応答には `src/nexuscore/llm/helpers.py` の `_strip_jsonish` / `_stub_response` / `DEFAULT_STUB_CONTENT` を利用し、例外は `self.logger` で `real`/`stub-fallback` のモードを分かるように記録する。
  3. `src/nexuscore/llm/providers/__init__.py` に新クラスを export し、`src/nexuscore/llm/llm_router.py` の `_make_client()` へファミリ判定を追加する。
  4. `LLMRouter` のタスクモデルマップ（`TASK_MODEL_MAP_DEFAULT` など）に新モデルを登録した上で、`nexuscore/npe` の budget/policy 設定にもモデル名を加える。
  5. ランタイム状態の確認には `from nexuscore.llm.runtime import log_runtime_status` を使い、`pytest tests/llm` にプロバイダ用のスタブテスト（API キーなし時の挙動等）を追加する。
- 2025-11-22 00:51 JST / Version 2.3.5-hotfix 時点で `src/nexuscore/llm/http_client.py` に `HttpClientFactory` を実装し、429/5xx リトライや `requests` 未導入時のスタブ降格処理を一元管理しています。LLM プロバイダを追加／拡張する際はこのモジュールから Session を取得してください。

