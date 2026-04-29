# NexusCore

> **多層品質ゲートを備えた自律型マルチエージェントAI開発フレームワーク**

[![Tests](https://img.shields.io/badge/tests-4838%20passed-brightgreen)](tests/)
[![Coverage](https://img.shields.io/badge/coverage-80.22%25-brightgreen)](docs/FINAL_COMPREHENSIVE_TEST_REPORT.md)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

**NexusCore** は、ソフトウェア開発ライフサイクル全体を支援する自律型AIエージェント群を統合したフレームワークです。要件分析からアーキテクチャ設計、コード生成、テスト、品質保証まで、各フェーズを専門エージェントが担当します。

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

```
Task → LLM Router → [OpenAI GPT-5.5 | Anthropic Sonnet 4.6 | Google Gemini 3.1 | GLM-5.1 | MiniMax M2.7]
                      ↕
                 Budget Manager（日次上限・フォールバック制御）
```

### 多層品質ゲート

品質重視タスクにGPT-5.5/Sonnet 4.6、軽量タスクにGLM-5.1/MiniMax M2.7を自動選択し、コストと品質のバランスを最適化します。

```
Task → LLM Router → [OpenAI GPT-5.5 | Anthropic Sonnet 4.6 | Google Gemini 3.1 | GLM-5.1 | MiniMax M2.7]
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

## アーキテクチャ

```
User / Developer
       ↓
   Orchestrator
       ↓
  ┌──────────────┐
  │ Agent Layer   │
  │ 10+ Specialized Agents
  └──────┬───────┘
         ├→ LLM Router ──→ [GPT | Claude | DeepSeek | Gemini | Kimi]
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
| Web UI | **Gradio** | 統合UI（解析→修正→テスト→履歴） |

- SDK自動生成: OpenAPI仕様書から Python / TypeScript 向けSDKを生成（`make sdk`）
- 認証: API Key認証（`POST /api/v1/api-keys` で発行）

---

## プロジェクト状況

| 指標 | 値 |
|------|-----|
| テストスイート | 392テストファイル |
| テストカバレッジ | 80%+ |
| エージェント数 | 14専門エージェント |
| LLMプロバイダー | 5プロバイダー（OpenAI, Anthropic, Google, GLM, MiniMax） |
| 品質ゲート | 2層（静的解析 + 動的テスト） |

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

- Python 3.11+
- pip
- Git

### インストール

```bash
git clone https://github.com/fukukei23/NexusCore.git
cd NexusCore

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install -r requirements.txt
cp .env.template .env
# .env にAPIキーを設定
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
| 言語 | Python 3.11+ |
| AI/LLM | OpenAI GPT-5.5, Anthropic Sonnet 4.6, Google Gemini 3.1, GLM-5.1, MiniMax M2.7 |
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

MIT License - 詳細は [LICENSE](LICENSE) を参照してください。

---

## 謝辞

- [OpenAI](https://openai.com/) - GPT
- [Anthropic](https://anthropic.com/) - Claude
- [DeepSeek](https://deepseek.com/) - DeepSeek
- [Google AI](https://ai.google/) - Gemini
- [pytest](https://pytest.org/) - テストフレームワーク
