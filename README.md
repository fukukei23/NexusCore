# NexusCore

> **多層品質ゲートを備えた自律型マルチエージェントAI開発フレームワーク**

[![Test Coverage](https://img.shields.io/badge/coverage-16.85%25-yellow)](docs/reports/COVERAGE_SUMMARY.md)
[![Tests](https://img.shields.io/badge/tests-431%20passing-brightgreen)](tests/agents/)
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

---

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

**Built with ❤️ using AI-driven development**
