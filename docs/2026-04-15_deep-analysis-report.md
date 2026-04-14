# リポジトリ深層分析レポート: NexusCore

**分析日**: 2026-04-15
**リポジトリ**: https://github.com/fukukei23/NexusCore
**最新コミット**: a5ae7f56 (Auto backup: 2026-04-14 02:00:01)
**分析方法**: Claude Code (GLM-5.1) がソースコードを直接読取

---

## 1. 概要

- **一文説明**: 多層品質ゲートを備えた自律型マルチエージェントAI開発フレームワーク。要件分析からアーキテクチャ設計、コード生成、テスト、品質保証までを10以上の専門エージェントが担当する
- **主要言語・FW**: Python 3.11+（メイン）、TypeScript（SDK/VSCode拡張）、FastAPI + Flask（API）、Gradio + Streamlit（UI）、Celery + Redis（非同期タスク）、PostgreSQL（DB）
- **コード規模**: src/nexuscore/ に193ファイル・38,520行、tests/ に420ファイル

---

## 2. アーキテクチャ全体像

### ディレクトリ構造

```
NexusCore/
├── src/nexuscore/           # メインパッケージ（193ファイル、38,520行）
│   ├── agents/              # 15+専門エージェント群
│   ├── analyzer/            # コード分析
│   ├── api/                 # FastAPI API（routes/schemas/deps）
│   ├── audio/               # 音声処理
│   ├── cli/                 # CLI
│   ├── config/              # 設定・憲法
│   ├── core/                # Orchestrator + SessionControl
│   ├── diff/                # 差分解析
│   ├── eval/                # 評価
│   ├── gradio_app/          # Gradio UI
│   ├── guard/               # ガード（PolicyEngine）
│   ├── governance/          # ガバナンス
│   ├── integration/         # GitHub等統合
│   ├── llm/                 # LLMルーター・8プロバイダー
│   ├── modules/             # モジュール
│   ├── npe/                 # Nexus Protocol Engine
│   ├── orchestrator/        # オーケストレータ
│   ├── services/            # サービス層
│   ├── trace/               # トレース
│   ├── ui/                  # UI
│   ├── utils/               # ユーティリティ
│   ├── ventures/            # 新規事業
│   ├── webapp/              # Flask Webアプリ・DBモデル
│   └── workflows/           # ワークフロー
├── tests/                   # 420テストファイル、32ディレクトリ
├── config/                  # constitution.yaml + policy_rules.json
├── k8s/                     # Kubernetes manifest（Deployment/HPA/Monitoring）
├── sdk/typescript/          # OpenAPI生成TypeScript SDK
├── vscode-extension/        # VSCode拡張機能
├── docs/                    # 22ルートドキュメント + 11サブディレクトリ
├── tools/                   # 42個のユーティリティツール
├── scripts/                 # 起動・テスト・デプロイスクリプト
├── app/                     # Flask SaaSアプリ
├── docker-compose.yml       # 開発環境（Redis + PostgreSQL）
├── docker-compose.saas.yml  # SaaS用（Redis + Webapp + Celery + DB）
├── Dockerfile.webapp        # Multi-stage build
└── Makefile                 # 開発タスク自動化
```

### モジュール分割・レイヤー

| レイヤー | 構成要素 | 責務 |
|---------|---------|------|
| **Agent** | 15+の専門エージェント（BaseAgent継承） | 各開発フェーズの実行 |
| **Orchestrator** | Orchestrator + SessionControl | 全エージェントの統括・順序制御 |
| **LLM** | ルーター + 8プロバイダー | タスク分類→モデル選定→API呼び出し |
| **NPE** | Nexus Protocol Engine | 予算管理・シークレットマスキング・ガード付きLLM呼び出し |
| **Guard** | PolicyEngine | Allow/Hold/Block判定 |
| **API** | FastAPI（新規:8000）+ Flask（既存:5000） | REST API提供 |
| **Persistence** | SQLAlchemy + PostgreSQL/SQLite | データ永続化 |

---

## 3. エントリポイントと実行フロー

### 起動コマンド・メインエントリ

| エントリ | コマンド | ポート |
|---------|---------|-------|
| CLI | `python main_cli.py "要求" --project-path ./project` | — |
| FastAPI | `make server` → uvicorn | 8000 |
| Flask+SaaS | `gunicorn -w 4 -b 0.0.0.0:5000` | 5000 |
| Gradio UI | `python gradio_app.py` | 7860（デフォルト） |

### 実行フロー（CLI）

```
1. argparse → requirement, project-path, language, constitution-text, verbose
2. ロギング初期化（StreamHandler + FileHandler）
3. fkb_local.json をプロジェクトディレクトリにコピー
4. 15のエージェントインスタンス化
5. LLMRouter初期化
6. Orchestratorに全エージェント注入
7. orchestrator.run_full_project(user_requirement, language) 実行
8. 成果物Smoke Test（hello.py存在確認・実行確認）
9. codex_history/ に成果物自動保存
```

---

## 4. データフロー

```
ユーザー要求（CLI/API/UI）
    ↓
Orchestrator.run_full_project()
    ↓
RequirementAgent → 要求仕様化
    ↓
ArchitectAgent → アーキテクチャ設計
    ↓
PlannerAgent → 実装計画
    ↓
CoderAgent → コード生成
    ↓
TesterAgent → テスト生成・実行
    ↓
GuardianAgent → 品質ゲート（Tier1: カバレッジ/Pylint/MyPy/Bandit）
    ↓               （Tier2: ミューテーションテスト）
PolicyEngine → Allow/Hold/Block判定
    ↓
DebuggerAgent → デバッグ（ナレッジベース活用）
    ↓
PatchApplier → パッチ適用
    ↓
成果物（hello.py + README.md）+ Smoke Test
```

各エージェントのLLM呼び出し経路:
```
BaseAgent.execute_llm_task()
  → LLMRouter.complete()
    → NPE guarded_llm_call()（予算チェック・シークレットマスキング）
      → Provider（GLM/MiniMax/OpenAI等）→ HTTP API呼び出し
```

---

## 5. 設定・環境変数の管理

### 設定ファイル

| ファイル | 用途 |
|---------|------|
| `.env.template` | 41個の環境変数テンプレート |
| `config/constitution.yaml` | プロジェクト憲法 v7.25.0（品質ゲート・セキュリティ・環境別設定） |
| `config/policy_rules.json` | 12個のポリシー（SEC/PERF/MAINTAIN/STYLE/LINT/TEST/BP） |
| `sandbox_policy.yml` | サンドボックス実行ポリシー（CPU 30秒、メモリ1024MB、NW禁止） |
| `pyproject.toml` | Black/Ruff/Mutmut/Bandit設定 |
| `pytest.ini` | テスト設定（testpaths, markers, norecursedirs） |

### 必須環境変数（主要）

| 変数 | 用途 |
|------|------|
| `GLM_API_KEY`, `MINIMAX_API_KEY` | 現在の主要LLMプロバイダー |
| `OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY` | 旧プロバイダー |
| `DATABASE_URL` | PostgreSQL接続（SaaS） |
| `REDIS_URL` | Celery broker |
| `FLASK_SECRET_KEY` | Flask秘密鍵 |
| `NEXUS_LLM_DAILY_CAP_USD` | 日次LLM予算上限 |
| `NEXUS_REQUEST_TIMEOUT_SEC` | HTTP タイムアウト（デフォルト120秒） |
| `SLACK_WEBHOOK_URL` | 通知用 |

### 環境別品質ゲート（constitution.yaml）

| 環境 | カバレッジ | Pylint | ミューテーション |
|------|----------|--------|----------------|
| 開発 | 80% | 7.0 | 70% |
| ステージング | 90% | — | 80% |
| 本番 | 95% | 9.0 | 85% |

---

## 6. 外部依存関係とAPI連携

### 主要パッケージ

| カテゴリ | パッケージ |
|---------|-----------|
| AI/ML | torch 2.2.2+cpu, tensorflow >=2.14.0, google-generativeai >=0.4.0 |
| Web | FastAPI >=0.110.0, Flask >=3.0.0, Gradio >=4.16.0, Streamlit >=1.29.0 |
| 非同期 | Celery >=5.3.0, Redis >=5.0.0, websockets >=12.0 |
| テスト | pytest >=7.4.0, pytest-cov >=4.1.0, pytest-mock >=3.12.0 |
| DB | Flask-SQLAlchemy, Flask-Migrate |
| HTTP | httpx >=0.25.0, requests >=2.31.0 |
| セキュリティ | pyjwt >=2.8.0 |

### LLMプロバイダー（8種）

| プロバイダー | 実装ファイル | 認証方式 |
|-------------|------------|---------|
| GLM | `glm_provider.py` | API Key（GLM_API_KEY） |
| MiniMax | `minimax_provider.py` | API Key（MINIMAX_API_KEY） |
| OpenAI | `openai_provider.py` | API Key |
| Gemini | `gemini_provider.py` | API Key |
| Anthropic | `anthropic_provider.py` | API Key |
| DeepSeek | `deepseek_provider.py` | API Key |
| Moonshot | `moonshot_provider.py` | API Key |
| Local | `local_provider.py` | ローカルエンドポイント |

### 外部API連携
- **GitHub Webhook**: PR/Pushイベント受信 → 自動パイプライン起動
- **Slack Webhook**: 実行結果通知

---

## 7. エラーハンドリングとロギング

### エラーハンドリング

| コンポーネント | 戦略 |
|--------------|------|
| LLMルーター | 429/5xx系エラー時に3回/指数バックオフで自動リトライ（v2.3.5-robust） |
| Orchestrator | try/except/finally + SystemExit制御 + codex_history自動保存 |
| PolicyEngine | GuardDecision Enum（ALLOW/HOLD/BLOCK）段階的判定 |
| BudgetManager | v1/v2後方互換ラッパー、preflight_check失敗時はTrue返却 |
| サンドボックス | 最大1回リトライ（TimeoutError/TransientSandboxError対象） |

### ロギング

| 項目 | 内容 |
|------|------|
| フォーマット | `%(asctime)s - %(levelname)-8s - %(name)-20s - %(message)s` |
| 出力先 | StreamHandler + FileHandler（nexus_core_run.log） |
| レベル | INFO（デフォルト）/ DEBUG（--verbose） |
| LLM呼び出し | llm_calls.jsonl（provider/input_tokens/output_tokens/cost） |
| テスト履歴 | test_history/（90+ JSONファイル） |
| パッチ履歴 | patch_history/（30+ JSONファイル） |

---

## 8. テスト戦略

### テスト構成
- **ファイル数**: 420テストファイル
- **ディレクトリ**: 32サブディレクトリ
- **マーカー**: slow, characterization, contract, regression
- **目標カバレッジ**: 80%+

### 品質ゲート（2層）
- **Tier 1（静的解析）**: カバレッジ80%+ / Pylint 8.0+ / MyPy / Bandit
- **Tier 2（動的テスト）**: ミューテーションテスト（対象: mutation_tester_agent.py）

### CI/CDパイプライン

| ワークフロー | 内容 |
|------------|------|
| ci.yml | Bandit スキャン + pytest（Python 3.9-3.12）+ Codecov |
| nexuscore-safe-tests.yml | CI環境用ダミーAPIキー、統合テスト除外 |
| ts-e2e.yml | FastAPI起動 → TypeScript SDK E2Eテスト |
| auto_backup.yml | 自動バックアップ |

### conftest.py配置
- ルート（tests/conftest.py）
- tests/analyzer/, tests/core/, tests/agents/, tests/e2e/

---

## 9. ビルド・デプロイ手法

### Docker構成

| 構成 | サービス |
|------|---------|
| 開発（docker-compose.yml） | Redis 7.2 + PostgreSQL 16.1 |
| SaaS（docker-compose.saas.yml） | Redis 7 + Webapp（gunicorn）+ Celery Worker + PostgreSQL 15 |

### Dockerfile.webapp
- Multi-stage build（Builder: Python 3.12-slim → Runtime: Python 3.12-slim）
- 非rootユーザー（appuser）で実行
- Healthcheck: curl /health
- CMD: `gunicorn --workers 4 --timeout 120`

### Kubernetes
- **orchestrator-worker-deployment.yaml**: Celery worker（レプリカ3、HPA最大10、CPU 70%/メモリ80%でスケール）
- **nexuscore-secrets.yaml**: Secretテンプレート（DB/Redis/JWT/Slack）
- **monitoring/**: Prometheus + Grafana + Celery Exporter

### Makefile主要ターゲット

| ターゲット | 用途 |
|-----------|------|
| `make venv/install-dev` | 環境構築 |
| `make qa` | format + lint-fix + typecheck + test |
| `make server` | FastAPI起動 |
| `make sdk/sdk-ts` | TypeScript SDK生成・ビルド |
| `make test-e2e` | E2Eテスト |

---

## 10. 拡張ポイントとカスタマイズ方法

| 拡張対象 | 方法 |
|---------|------|
| **エージェント追加** | BaseAgent継承 → SYSTEM_PROMT + execute_llm_task()実装 → Orchestratorに注入 |
| **LLMプロバイダー追加** | providers/にBaseLLM継承クラス実装 → provider_factory.pyに登録 |
| **ポリシー追加** | config/policy_rules.jsonに新ルール定義（SEC/PERF/MAINTAIN/STYLE/LINT/TEST/BP） |
| **API拡張** | routes/にFastAPIルーター追加 → schemas/にPydanticモデル定義 |
| **TypeScript SDK** | OpenAPI生成ベース（api.ts 124KB自動生成） |
| **VSCode拡張** | extension.tsでFastAPI連携（nexuscore.executeTask コマンド） |

---

## 11. 既知の制約・注意点

| 項目 | 内容 |
|------|------|
| **LLMコスト** | エージェント群が多数のLLM呼び出しを行う。NEXUS_LLM_DAILY_CAP_USDでの予算管理が必須 |
| **OpenAI SDK除去** | コミット 36ee57ae でOpenAI SDK依存を除去しGLM/MiniMax HTTP直接呼び出しに移行済み |
| **テスト履歴蓄積** | test_history/に90+、patch_history/に30+のJSON蓄積（要クリーンアップ） |
| **デュアルAPI** | FastAPI（新規:8000）とFlask（既存:5000）の並存。段階的移行中 |
| **Heavy依存** | torch/tensorflowがrequirements.txtに含まれる（CPU版のみ使用） |
| **環境変数** | 41個の環境変数が必要。設定管理が煩雑 |
| **WSL互換** | WSL固有のパス問題に対処するコードが散在（activate_venv.sh等） |
| **NLargest commit** | main_cli.pyに日本語コメント混在、codex_bridgeフォルダに旧統合コード残存 |
