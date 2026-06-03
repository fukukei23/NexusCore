---
title: 概要
nav_order: 1
---

# NexusCore

> 📂 **[GitHub リポジトリ →](https://github.com/fukukei23/NexusCore)**{: .btn .btn-blue } — ソースコード・テスト・技術詳細はこちらから

14の specialized AI agents が協調動作し、要件分析からアーキテクチャ設計、コード生成、テスト、品質保証まで開発プロセス全体を自動化します。

## 操作デモ

<p align="center">
  <img src="{{ site.baseurl }}/screenshots/cli-pipeline.png" width="600" alt="CLI パイプライン実行">
</p>

> `python main_cli.py --project-path /tmp/demo "フィボナッチ数列を計算する関数を作成して"` を実行した様子。ユーザーの自然言語入力を受け取り、14のAIエージェント（Requirement → Architect → Planner → Coder → Tester → Debugger → Guardian...）が順次起動。

## 特徴

### 14の専門エージェント

| エージェント | 担当領域 |
|-------------|---------|
| Architect | アーキテクチャ設計 |
| Coder | コード生成 |
| Debugger | エラー修正 |
| Tester | テスト自動生成 |
| Guardian | 多層品質ゲート |
| Requirement | 要件分析 |
| Postmortem | 失敗分析 |
| Mutation Tester | テスト強度測定 |

### LLMルーティング（8プロバイダー対応）

| ティア | プロバイダー | 用途 |
|---|---|---|
| 品質 | OpenAI / Anthropic / Google | コード生成・推論 |
| 軽量 | GLM / MiniMax / DeepSeek / Moonshot | チャット・分類 |

### 多層品質ゲート

- **Tier 1**: カバレッジ80%+ / Pylint / Mypy / Bandit
- **Tier 2**: ミューテーションテストによるテストスイート強度測定

## テスト結果

<p align="center">
  <img src="{{ site.baseurl }}/screenshots/test-results.png" width="600" alt="テスト結果">
</p>

> 4,862テストが全て通過（カバレッジ81%）。全モジュールがユニットテスト・統合テストで保護。

## 技術スタック

| カテゴリ | 技術 |
|---|---|
| 言語 | Python 3.12+ |
| AI/LLM | OpenAI / Anthropic / Google / GLM / MiniMax / DeepSeek / Moonshot |
| API | FastAPI + Flask + Gradio |
| テスト | pytest (4,862 tests) |
| 品質 | pylint, mypy, bandit, mutation testing |

---

> 👉 各機能の詳細はサイドバーの **機能ショーケース** をご覧ください。
