# CR-NEXUS-054： ゴール駆動・動的オーケストレーション（Dynamic Goal-Driven Orchestration）

- **CR-ID**: CR-NEXUS-054
- **Status**: In-Progress
- **Author**: Claude Fable 5（設計） / GLM-5.1（テスト・ドキュメント量産）
- **Date**: 2026-06-10
- **Related CR**: CR-NEXUS-017（Resume再構築）, CR-NEXUS-019（状態機械契約）, CR-NEXUS-052（品質ゲート）

## 1. 概要（Overview）

現行の `Orchestrator.run_full_project()` は7フェーズ（Context→Requirements→Planning→Architecture→Implementation→Testing→Review）を**固定順で直列実行**する「ベルトコンベア型」である。本CRでは、これを**ゴール駆動の動的フロー（現場監督型）**に進化させる。

- 実行前に「ゴール（達成条件）」を `GoalSpec` として宣言する
- ループの各ステップで `GoalEvaluator` が現在の `OrchestratorContext` を採点する
- `DynamicRouter` が「未達の条件」と「直前の結果」を見て**次に実行すべきアクションをその場で選択**する
- 失敗時は全体やり直しではなく、**必要なフェーズだけ再実行**する
- 全ルーティング判断は `DecisionTrace` に理由付きで記録され、説明可能性を担保する

## 2. 変更理由（Why）

1. **無駄なフェーズ実行**: 軽微なタスクでも全7フェーズが直列で走る（Architectureはスタブでも必ず通過）
2. **失敗時の全停止**: 1フェーズの例外で全体が停止し、部分的なやり直しができない（Resume機構はあるが「同じ固定順」の再開のみ）
3. **ゴール概念の不在**: 「いつ完了か」がフェーズ消化でしか定義されず、成果物の品質条件（テスト存在・コード非空など）と紐づいていない
4. **業界トレンドとの整合**: ゴール駆動・動的グラフ型のエージェントオーケストレーション（orchestrator-workers / evaluator-optimizer パターン）が主流になっており、SaaS化（Phase 2）前にコアを近代化する必要がある

## 3. スコープ（Scope）

### In Scope（Phase A — 本CR）

- `core/goal_spec.py`: `GoalSpec` / `SuccessCriterion` / `GoalEvaluator`（ルールベース・決定的・LLM不使用）
- `core/dynamic_router.py`: `ActionRegistry`（既存 `run_*_phase` をアクションとして登録）+ `RuleBasedRouter`
- `core/dynamic_orchestrator.py`: `DynamicRunLoop` — 既存 `Orchestrator` を**コンポジションで**駆動するループ（既存クラスは無改変）
- `DecisionTrace`: 各ステップの「選択アクション・理由・状態スナップショット」を記録
- 予算制御: `max_actions`（既定12）・アクション毎リトライ上限（既定2）
- ユニットテスト（GLM生成→Fable検証）

### In Scope（Phase B — 2026-06-10 完了）

- `core/llm_assisted_router.py`: LLMAssistedRouter — LLM提案 + ルールベース必須フォールバック
  - 設計原則: ①リトライ判断はLLMに委ねない（決定的）②無効提案・JSON破損・LLM障害・予算超過は必ずフォールバック ③`max_llm_calls` でルーティングLLMコストに上限
  - `from_llm_router()` で既存 `nexuscore.llm.LLMRouter`（軽量ティア `task="classification"`）と統合
- `core/measured_criteria.py`: 実測ベース SuccessCriterion（`QualityRegenLoop` 統合）
  - `coverage_criterion` / `lint_clean_criterion` + `PhaseCachedCheck`（phase_log変化時のみ再計測）

### Out of Scope（Phase C以降に分割）

- CLI `--dynamic` フラグ・Gradio UI統合 → Phase C
- `run_full_project()` の置き換え・廃止（後方互換のため当面併存）

## 4. 実装方針（Design / Implementation Plan）

### 4.1 アーキテクチャ（コンポジション方式）

```
DynamicRunLoop(orchestrator, goal_spec)
   │  while not evaluator.satisfied(ctx) and budget remains:
   ├─ GoalEvaluator.evaluate(ctx)      → 未達条件リスト
   ├─ RuleBasedRouter.next_action(...)  → ActionDecision(action, reason)
   ├─ ActionRegistry.execute(action, ctx) → 既存 run_*_phase を呼ぶ
   └─ DecisionTrace.record(...)
```

- **既存 `Orchestrator` / `PhaseRunnerMixin` は無改変**（Surgical Changes原則）。`DynamicRunLoop` が外側からフェーズメソッドを呼ぶ
- アクション失敗（例外）はループが捕捉し、リトライ予算内なら同アクションを再試行。予算超過で `GoalResult(success=False)` を理由付きで返す（全体を例外で落とさない）

### 4.2 GoalSpec / SuccessCriterion

```python
@dataclass
class SuccessCriterion:
    name: str                                  # 例: "has_implementation"
    check: Callable[[OrchestratorContext], bool]
    description: str = ""

@dataclass
class GoalSpec:
    description: str                           # ゴールの自然言語記述
    criteria: list[SuccessCriterion]
    max_actions: int = 12
    max_retries_per_action: int = 2
    skip_actions: frozenset[str] = frozenset() # 例: {"architecture"}
```

- 標準クライテリア集を `standard_criteria()` で提供: `has_specs` / `has_plan` / `has_implementation` / `has_tests` / `review_done`
- カスタム条件は `check` に任意の callable を渡せる（Phase Bでカバレッジ計測等を追加）

### 4.3 RuleBasedRouter（決定的・LLMコストゼロ）

未達条件→アクションの対応表で次の一手を選ぶ。依存順（specs→plan→code→tests→review）を解決し、`skip_actions` は飛ばす。直前に失敗したアクションはリトライ残があれば優先再実行。

### 4.4 ファイル構成

| ファイル | 内容 | 担当 |
|---|---|---|
| `src/nexuscore/core/goal_spec.py` | GoalSpec / SuccessCriterion / GoalEvaluator / standard_criteria | Fable 5 |
| `src/nexuscore/core/dynamic_router.py` | ActionRegistry / ActionDecision / RuleBasedRouter | Fable 5 |
| `src/nexuscore/core/dynamic_orchestrator.py` | DynamicRunLoop / GoalResult / DecisionTrace | Fable 5 |
| `tests/core/test_goal_spec.py` ほか3ファイル | ユニットテスト | GLM生成→Fable検証 |

## 5. テスト方針（Testing Strategy）

- **正常系**: 全条件未達から開始→requirements→planning→implementation→testing→review の順で収束し `success=True`
- **スキップ**: `skip_actions={"architecture"}` でArchitectureを通らない / 既に `specs` があるcontextではrequirementsを飛ばす
- **失敗リトライ**: implementationが1回例外→リトライで成功→ループ継続
- **予算超過**: 常に失敗するアクションで `max_retries_per_action` 超過→`success=False` + trace に理由
- **max_actions 超過**: 無限ループ防止の検証
- **DecisionTrace**: 各ステップに action / reason が記録されること
- **回帰**: 既存 `run_full_project` 系テストへの影響ゼロ（既存コード無改変のため）

## 6. 完了条件（Definition of Done）

- [x] Phase A コード実装完了（goal_spec / dynamic_router / dynamic_orchestrator）— 2026-06-10
- [x] Phase A テストパス（新規48テスト、ruff / mypy クリーン）— 2026-06-10
- [x] Phase B コード実装完了（llm_assisted_router / measured_criteria）— 2026-06-10
- [x] Phase B テストパス（新規18テスト、ruff / mypy クリーン）— 2026-06-10
- [ ] Spec 更新（本書 Status → Completed）※Phase C 完了時
- [x] docs/変更履歴.md 追記 — 2026-06-10
- [ ] 完了レポート作成（Phase C完了時）

## 7. 参照（References）

- `docs/overview/03_Development_Roadmap.md` v1.3（Phase 1完了 → 動的化はPhase 2前の基盤近代化）
- Anthropic "Building Effective Agents"（orchestrator-workers / evaluator-optimizer パターン）
- 既存実装: `core/phase_runner_mixin.py`（フェーズ実体）, `core/orchestrator_models.py`（Context）, `core/quality_regen_loop.py`（Phase B統合予定）
