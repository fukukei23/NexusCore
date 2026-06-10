# CR-NEXUS-054 ゴール駆動・動的オーケストレーション 完了レポート

## 概要

- **日付**: 2026-06-10
- **ステータス**: Completed
- **仕様書**: `docs/spec/CR-NEXUS-054_Dynamic_Goal_Driven_Orchestration.md`

**目的**: 固定7フェーズ直列パイプライン（`run_full_project`）を、ゴール達成条件を見て次アクションをその場で選ぶ「ゴール駆動・動的フロー」に進化させる。既存の `Orchestrator` は無改変（コンポジション方式）とし、完全な後方互換を維持する。

---

## 実装内容

### Phase A: 動的ループ基盤 (Commit: `c3012344`)
**テスト48件追加**
- `core/goal_spec.py`: `GoalSpec`, `GoalEvaluator`, `standard_criteria` を実装し、ゴール定義と評価の基盤を構築。
- `core/dynamic_router.py`: `ActionRegistry` と `RuleBasedRouter` を実装し、ルールベースのアクション決定を可能にした。
- `core/dynamic_orchestrator.py`: `DynamicRunLoop`, `DecisionTrace`, `GoalResult` を実装し、動的な実行ループのコアを完成させた。

### Phase B: LLM支援と実測ベース評価 (Commit: `6d4b33c7`)
**テスト18件追加**
- `core/llm_assisted_router.py`: `LLMAssistedRouter` を実装。LLMの提案に対し三重ガード（無効提案、LLM障害、予算超過）を適用し、異常時は必ずルールベースにフォールバック。リトライ判断は決定的（Deterministic）に処理。
- `core/measured_criteria.py`: `coverage_criterion`, `lint_clean_criterion` および `PhaseCachedCheck` を実装し、静的解析やカバレッジに基づく実測ベースの達成条件を追加。

### Phase C: CLI/UI統合と既存バグ修正
**テスト6件追加**
- `main_cli.py`: `--dynamic`, `--dynamic-llm-routing`, `--max-actions`, `--skip-actions` の各フラグを追加。
- `ui/dynamic_run_tab.py`: 統合UIに「Dynamic Run」タブを新設。
- **バグ修正**: `Orchestrator` に `context_agent` フィールドが欠落しており、CLIフルパイプラインが `TypeError` で起動不能だった問題を解消。

---

## 実現した機能

1. **不要フェーズのスキップ**: ゴール達成状態に応じた無駄な処理の省略。
2. **途中状態からの再開**: 中断されたプロジェクトの動的再開。
3. **アクション単位リトライ**: 全体停止なしに個別アクションをリトライ可能。
4. **判断理由の記録**: `DecisionTrace` による、全判断履歴の理由付き記録。
5. **LLM支援ルーティング**: LLMの提案による最適なアクション選択。
6. **実測ベース達成条件**: テストカバレッジやLint結果に基づく確実な達成判定。

---

## 品質検証

- **新規テスト**: 72件（全スイート4,600件超パス）
- **静的解析**: `ruff` および `mypy` クリーンを維持。

---

## 使い方

**CLIの場合**:
```bash
python main_cli.py --project-path /tmp/demo "要件" --dynamic --skip-actions architecture
```

**UIの場合**:
統合UIの「Dynamic Run」タブから操作可能。

---

## 既知の制約と今後

- **段階的移行**: 既存の `run_full_project` から動的フローへの移行を段階的に進める。
- **修復アクションの統合**: 今後 `DebuggerAgent` の修復アクションを動的ループに統合する。
- **SaaS化（Phase 2）**: ゴールテンプレートの提供により、SaaS環境での利用を促進する。

---

## 開発体制（LLM分担）

- 設計・コア実装・検証: Claude Fable 5
- 実装ドラフト・完了レポート起案: GLM-5.1
- テスト量産: MiniMax M2.7（Phase A/B、GLMタイムアウト時のフォールバック）/ GLM-5.1（Phase C）
