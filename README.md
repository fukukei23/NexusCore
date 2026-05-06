# NexusCore

> **Multi-agent AI development framework with multi-tier quality gates**
>
> NexusCore is an autonomous multi-agent system where 14 specialized AI agents collaborate across the entire software development lifecycle — from requirements analysis to architecture design, code generation, testing, and quality assurance. Features intelligent LLM routing across 8 providers and a 2-tier quality gate system.

---

**NexusCore** は、ソフトウェア開発ライフサイクル全体を支援する自律型AIエージェント群を統合したフレームワークです。要件分析からアーキテクチャ設計、コード生成、テスト、品質保証まで、各フェーズを専門エージェントが担当します。

[![CI](https://github.com/fukukei23/NexusCore/actions/workflows/ci.yml/badge.svg)](https://github.com/fukukei23/NexusCore/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/fukukei23/NexusCore/branch/main/graph/badge.svg)](https://codecov.io/gh/fukukei23/NexusCore)
[![Python](https://img.shields.io/badge/python-3.12+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

![NexusCore Unified UI](docs/images/unified_ui.png)

<details>
<summary>UI Screenshots</summary>

| Code Generation | Review | Workflow |
|:---:|:---:|:---:|
| ![Code Generation](docs/images/ui_code_generation.png) | ![Review](docs/images/ui_review.png) | ![Workflow](docs/images/ui_workflow.png) |

</details>

---

## 特徴

### マルチエージェントシステム

14の専門エージェントが協調動作し、開発プロセス全体を自動化します。

| エージェント | 担当領域 |
|-------------|---------|
| Architect | アーキテクチャ設計 |
| Coder | コード生成 |
| Debugger | エラー修正・デバッグ |
| Tester | テスト自動生成 |
| Guardian | 多層品質ゲート |
| Requirement | 要件分析・仕様化 |
| Postmortem | 失敗分析・事後検証 |
| Knowledge Curator | ナレッジ管理 |
| Policy | ポリシー適用 |
| Constitutional Council | ガバナンス・意思決定 |
| Mutation Tester | テストスイート強度測定 |
| Planner | 実装計画 |
| Context | プロジェクトコンテキスト管理 |

### LLMルーティング（2層構成）

各タスクに最適なLLMを自動選択し、コストと品質のバランスを最適化します。

| ティア | プロバイダー | モデル | 用途 |
|---|---|---|---|
| 品質 | OpenAI / Anthropic / Google | GPT-5.5 / Sonnet 4.6 / Gemini 3.1 Pro | コード生成・推論・設計 |
| 軽量 | GLM / MiniMax / DeepSeek / Moonshot | GLM-5.1 / MiniMax M2.7 / DeepSeek / Moonshot | チャット・分類・分析 |

```
Task → LLM Router → [GPT-5.5 | Sonnet 4.6 | Gemini 3.1 Pro | GLM-5.1 | DeepSeek | Moonshot | MiniMax]
                      ↕
                 Budget Manager（日次上限・フォールバック制御）
```

### 多層品質ゲート

2段階の品質検証で、高品質なコードを保証します。

- **Tier 1 - 静的解析**: カバレッジ80%+ / Pylint 8.0+ / Mypy / Bandit
- **Tier 2 - 動的テスト**: ミューテーションテストによるテストスイート強度測定

### ガバナンス自動化

- **CR（Change Request）管理**: 仕様書ベースの開発フロー
- **Authority Runner**: 権限レベルに応じた段階的実行制御（HUMAN_CONTROLLED / PARTIALLY_AUTONOMOUS / FULLY_AUTONOMOUS）
- **Spec-driven開発**: `docs/spec/` 配下でCR仕様書を管理

---

## なぜNexusCoreを作ったか

AIコーディングツール（Claude Code, Cursor等）が普及する中で、**「AIエージェントの出力をどう品質担保するか」** が最大の課題だと考えました。NexusCoreは、AIに実装を委ねつつ、人間が評価関数として機能する — そのためのインフラとして設計しました。

- **27種のタスクを自動分類**し、最適なLLMにルーティング
- **予算管理（NPE）** で日次上限・コスト超過を自動制御
- **12種のポリシーエンジン** でセキュリティ・パフォーマンス問題を自動検出
- **4,895テストケース** でシステム動作を継続検証

---

## アーキテクチャ

```
User / Developer
       ↓
   Orchestrator
       ↓
  ┌──────────────┐
  │ Agent Layer   │
  │ 14 Specialized Agents
  └──────┬───────┘
         ├→ LLM Router ──→ [GPT-5.5 | Sonnet 4.6 | Gemini 3.1 | GLM-5.1 | DeepSeek | Moonshot | MiniMax]
         │       ↕
         │   Budget Manager
         └→ Quality Gates
              ├→ Tier 1: Coverage / Pylint / Mypy / Bandit
              └→ Tier 2: Mutation Testing
```

### API構成

| レイヤー | フレームワーク | 役割 |
|---------|-------------|------|
| 公開API | **FastAPI** (`/api/v1/*`) | 外部統合向けREST API。OpenAPI仕様・SDK自動生成対応 |
| Web UI | **Gradio** | 統合UI（コード生成→修正→テスト→履歴） |

- SDK自動生成: OpenAPI仕様書から Python / TypeScript 向けSDKを生成（`make sdk`）
- 認証: API Key認証（`POST /api/v1/api-keys` で発行）

---

## プロジェクト状況

| 指標 | 値 |
|------|-----|
| テスト数 | 4,895 テストケース（CI自動検証） |
| エージェント数 | 14専門エージェント |
| LLMプロバイダー | 8プロバイダー（OpenAI, Anthropic, Google, GLM, MiniMax, DeepSeek, Moonshot, Local） |
| 品質ゲート | 2層（静的解析 + 動的テスト） |
| CI | GitHub Actions（push/PR時自動テスト + セキュリティスキャン） |

---

## Roadmap

- [ ] **SaaS化**: マルチテナント対応・サブスクリプション課金
- [ ] **エージェントプラグインシステム**: サードパーティエージェントの追加機構
- [ ] **リアルタイムコラボレーション**: WebSocketベースのマルチユーザー同時編集
- [ ] **セルフホスト対応**: Docker Compose / K8s Helm Chart提供
- [ ] **多言語対応**: UI・エージェントプロンプトの国際化

---

## プロジェクト構成

```
NexusCore/
├── src/nexuscore/
│   ├── agents/              # AIエージェント（14専門エージェント + BaseAgent）
│   ├── analyzer/            # コード解析（AST, 依存グラフ）
│   ├── api/                 # FastAPI公開API（/api/v1/*）
│   ├── audio/               # 音声入力（Whisper統合）
│   ├── cli/                 # CLIツール
│   ├── config/              # 設定・憲法ローダー・ポリシー
│   ├── core/                # オーケストレーター, リトライポリシー, セッション管理
│   ├── diff/                # コード差分の意味的解析
│   ├── eval/                # JSON構造出力評価
│   ├── governance/          # CR仕様管理
│   ├── guard/               # 品質ゲート・自動レビュー・ポリシーエンジン
│   ├── integration/         # GitHub PR連携
│   ├── llm/                 # LLM統合レイヤー（Router, Budget, Providers）
│   ├── modules/             # 機能モジュール（Whisper等）
│   ├── npe/                 # 予算・ポリシー・ガードエンジン
│   ├── orchestrator/        # 実行管理（Authority Runner, 状態管理）
│   ├── services/            # Self-Healing Service, パッチ適用
│   ├── trace/               # 実行トレース
│   ├── ui/                  # Gradio統合UI
│   ├── utils/               # コード分析, Git操作, 差分生成, テスト戦略
│   └── webapp/              # Web UI (Flask, レガシー)
│
├── tests/                   # テストスイート（agents/api/core/等で構造化）
├── docs/                    # ドキュメント群
│   ├── governance/          # 統治ルール
│   ├── overview/            # ビジョン, アーキテクチャ, ロードマップ
│   ├── spec/                # CR仕様書（Spec-driven開発）
│   └── api/                 # API契約, エラーコードカタログ
├── tools/                   # scaffold_cr.py, update_ci_safe_lock.py
└── sdk/                     # 自動生成SDK (Python / TypeScript)
```

---

## クイックスタート

### 前提条件

- Python 3.12+
- pip
- Git
- 最低1つのLLMプロバイダーAPIキー（下記参照）

### インストール

```bash
git clone https://github.com/fukukei23/NexusCore.git
cd NexusCore

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.template .env
# .env に最低1つのLLM APIキーを設定:
#   OPENAI_API_KEY     - GPT-5.5 (コード生成・推論)
#   ANTHROPIC_API_KEY  - Claude Sonnet (レビュー・設計)
#   GEMINI_API_KEY     - Gemini 3.1 Pro (分析)
#   GLM_API_KEY        - GLM-5.1 (軽量タスク・デフォルト)
#   MINIMAX_API_KEY    - MiniMax M2.7 (軽量タスク)
#   DEEPSEEK_API_KEY   - DeepSeek (コード生成)
#   MOONSHOT_API_KEY   - Moonshot (チャット)
```

### 基本的な使用例

```python
from nexuscore.agents import CoderAgent

coder = CoderAgent()

result = coder.execute_llm_task(
    prompt="Pythonで二分探索を実装してください"
)
print(result)
```

### テスト実行

```bash
# テスト実行
python -m pytest tests/ -v

# カバレッジ付き
python -m pytest tests/ --cov=src/nexuscore --cov-report=html
```

---

## 使用技術

| カテゴリ | 技術 |
|---------|------|
| 言語 | Python 3.12+ |
| AI/LLM | OpenAI GPT-5.5, Anthropic Claude Sonnet 4.6, Google Gemini 3.1 Pro, GLM-5.1, MiniMax M2.7, DeepSeek, Moonshot |
| API | FastAPI |
| テスト | pytest, pytest-cov, カスタムミューテーションテスト |
| 品質 | pylint, mypy, bandit |
| Web UI | Gradio |
| VCS | GitPython |

---

## ドキュメント

| ドキュメント | 内容 |
|------------|------|
| [アーキテクチャ](docs/ARCHITECTURE.md) | システムアーキテクチャ詳細 |
| [プロジェクト概要](docs/overview/00_OVERVIEW_INDEX.md) | ドキュメント体系インデックス |
| [技術アーキテクチャ](docs/overview/02_Technical_Architecture.md) | NexusOSモデル, エージェント構成 |
| [開発者ガイド](docs/overview/04_Developer_Internal_Guide.md) | 環境構築・運用ガイド |
| [ガバナンス](docs/governance/NEXUSCORE_GOVERNANCE.md) | プロジェクト統治ルール |
| [API仕様](docs/api/README.md) | API仕様インデックス |
| [CRテンプレート](docs/spec/SPEC_TEMPLATE.md) | 仕様書テンプレート |
| [CI戦略](docs/CI_TEST_STRATEGY.md) | Safe/Full テスト分離 |
| [完了レポート](docs/completion_reports/README.md) | 作業進捗・完了履歴一覧 |
| [変更履歴](CHANGELOG.md) | バージョン別変更履歴 |

---

## コントリビューション

1. リポジトリをフォーク
2. フィーチャーブランチ作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. プッシュ (`git push origin feature/amazing-feature`)
5. プルリクエスト作成

**品質基準**: カバレッジ80%+ / Pylint 8.0+ / ミューテーションスコア70%+

---

## ライセンス

Apache License 2.0 - 詳細は [LICENSE](LICENSE) を参照してください。

---

## 謝辞

- [OpenAI](https://openai.com/) - GPT-5.5
- [Anthropic](https://anthropic.com/) - Claude Sonnet 4.6
- [Google AI](https://ai.google/) - Gemini 3.1 Pro
- [Zhipu AI](https://www.zhipuai.cn/) - GLM-5.1
- [DeepSeek](https://deepseek.com/) - DeepSeek
- [MiniMax](https://www.minimaxi.com/) - MiniMax M2.7
- [Moonshot AI](https://www.moonshot.cn/) - Moonshot
- [pytest](https://pytest.org/) - テストフレームワーク
