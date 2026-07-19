# 設計spec: 固定パイプライン「12エージェント実稼働化」

- 日付: 2026-07-17
- ステータス: 承認済み（ユーザーレビュー待ち）
- 関連: SSOT `01_DECISIONS/NexusCore/2026-07-17_技術品質監査-主張と実装の乖離.md`（監査C-1/C-2/H-2）
- レビュー: GLM（条件付き承認）・Gemini 2.5 Pro（指摘7点反映済み）

## 1. 背景と目的

2026-07-17の技術品質監査で以下が確定した:

- **C-1**: 固定パイプライン（`Orchestrator.run_full_project`）は12エージェント中4体（requirement/planner/coder/tester）しか呼ばず、architect/debugger/guardian/policy/postmortem/knowledge_curator の6体は注入されるが未使用（`core/`・`orchestrator/` 配下で呼び出しゼロ件）。
- **C-2**: `run_implementation_phase` が生成コードを無条件に `hello.py` へ書き込み、`main_cli.py` の Smoke Test も `hello.py`＋標準出力 `"Hello"` を前提にハードコード。

本改修の目的は **「12エージェント協調」という主張と実装を一致させる** こと。方針は「案A: 固定パイプライン拡張を先に、動的ループ(DynamicRunLoop)への展開は後続」（ユーザー承認済み）。

## 2. 全体構成（3 Stage）

```
Stage 1: 土台修正（C-2解消・planを契約にする）
Stage 2: 品質ループ（architect/debugger/guardian の実稼働・協調の核心）
Stage 3: 学習レイヤー（postmortem/knowledge_curator/policy の接続）
```

実装は Stage 順。各 Stage 完了ごとに全テスト実行＋commit（小さく積む）。

## 3. Stage 1 — 土台修正

### 3-1. plan スキーマ拡張（planner が契約を出す）

planner の plan JSON に `target_files` を新設:

```json
{
  "functions_to_implement": [...],
  "target_files": [
    {"path": "app/calculator.py", "role": "implementation"},
    {"path": "tests/test_calculator.py", "role": "test"}
  ]
}
```

- `role` は列挙型: `implementation` / `test` / `config`。
  - `test`: Phase 5 のテスト対象ルーティングと Smoke Test の検査対象判定に使用。
  - `config`: 構文チェック対象外（py_compile は .py のみ）。
- planner プロンプトに `target_files` 生成指示を追加。
- **フォールバック（劣化モード）**: `target_files` が欠落・不正な場合、要件文字列から導出したスラッグで `main.py` 1枚に縮退。劣化モードであることを WARN ログに明示する。architect はこの場合もコード設計方針の注入は行う（ファイル構成には関与しない。責務: ファイル構成=planner・コード設計方針=architect という契約）。

### 3-2. 実装フェーズの書き換え（hello.py 固定の廃止）

- `run_implementation_phase`: plan の `target_files`（role=implementation/config）を**依存順に1ファイルずつ** coder に生成させる。
- **ファイル間整合の担保**: coder 呼び出し時、**生成済みファイル全てをコンテキストに渡す**（既存の `existing_code` 引数を活用）。GLMレビュー重大指摘②への対応。
- README 自動生成は固定文言をやめ、実際の生成ファイル一覧＋要件から組み立てる。

### 3-3. Smoke Test の再定義（main_cli.py）

- 旧: `hello.py` 存在＋実行stdout に `"Hello"`。
- 新: plan の `target_files` が全て実在＋`.py` ファイルが `py_compile` で構文チェック通過。

## 4. Stage 2 — 品質ループ

### 4-1. Phase 3: architect 実稼働

- `architect.design_architecture(specs, plan)` を呼び、結果を `context.architecture` に格納。
- coder のプロンプトに設計方針として注入する（「格納するだけ」にしない。使われる設計にする）。

### 4-2. Phase 5: テスト実行＋debugger ループ

```
テスト生成 → run_in_sandbox で実行
  失敗 → debugger.debug_and_patch(エラーログ, 対象ファイル) → パッチ適用 → 再実行
  リトライ上限: 3回（NEXUS_DEBUG_MAX_RETRIES で変更可）
```

- **テストファイルの書き出し責務**: tester が生成したテストコードは、plan の `target_files` の `role=test` パスへ**テスティングフェーズが**書き出す（coder は書かない）。`role=test` のエントリが無い場合は `tests/test_main.py` に縮退（劣化モードと同様に WARN ログ）。

- サンドボックスは既存 `run_in_sandbox`（timeout＋POSIX rlimit）を使用。
- **制約の明記**: これは実分離（コンテナ/namespace）ではない。本格隔離は監査 H-1 の別タスク（バックログ登録済み）に委譲し、本specのスコープ外とする。

### 4-3. Phase 6: guardian レビューループ

```
guardian.review(コード, テスト, テスト結果, 憲法, タスク)
  REJECT → feedback_for_coder を coder に渡して再実装 → 再テスト（4-2） → 再レビュー
  リトライ上限: 2回（NEXUS_REVIEW_MAX_RETRIES で変更可）
```

- レビュー方式は LLM レビュー（`guardian.review()`）。重量級 `review_with_quality_gates()`（pylint/coverage/mutation）は**組み込まない。未使用のフラグや分岐もコードに残さない**（YAGNI・GLM指摘反映）。必要になった時に本specの「将来課題」を参照して起票する。
- coder 再実装プロンプトには「前回コード＋guardian の feedback_for_coder＋失敗したテスト結果」を含める（レビューフィードバック契約の明確化・Gemini指摘反映）。

### 4-4. 終端状態（3値・fail-closed系）

| 終端 | exit code | トリガー条件 |
|---|---|---|
| `APPROVED` | 0 | guardian が APPROVE |
| `NEEDS_HUMAN_REVIEW` | 2 | (a) review リトライ枯渇で REJECT のまま、または (b) debug リトライ枯渇でテスト失敗のまま |
| `ERROR` | 1 | 予期しない例外のみ |

- `NEEDS_HUMAN_REVIEW` 時は guardian の最終フィードバック＋成果物一覧を `<project_path>/review_report.md` に保存する。
- 設計根拠: fail-open（困ったら通す）は監査 H-2 で批判した設計の再生産になるため排除。「自律の限界で人間に渡す」を明示的な正常出口として設計（sentaku D案・ユーザー確定）。Self-Healing 系の既存語彙 `MANUAL_REVIEW` と概念的に一貫。

### 4-5. リトライ上限の根拠

- debug=3回・review=2回で総LLM呼び出し数が有界。「3回で直らないものは人間案件」（既存バックログの人間エスカレーション方針と一貫）。env で調整可能。

## 5. Stage 3 — 学習レイヤー

- **postmortem**: `NEEDS_HUMAN_REVIEW` またはテスト失敗枯渇時に `postmortem.analyze()` で失敗分析。
- **knowledge_curator**: 分析結果を既存の fkb_local.json 機構に蓄積。**汚染防止: そのパッチで実際にテストが通った（検証済み）解のみ記録する**（GLMレビュー重大指摘④反映）。新規DBは作らない。
- **debugger との接続**: 次回実行時に既存 `_find_solution_from_kb` が蓄積知見を参照（既存機構への接続のみ）。
- **policy_agent**: guardian 承認後の commit 可否判定元として接続（`review_and_commit(allow_commit=...)` の判定に使用）。

## 6. 横断事項

### 6-1. 空応答の扱い（H-2 の局所修正）

- BaseAgent のグローバルな「失敗時に `""`/`"{}"` を黙って返す」挙動は**今回は変更しない**（既存4,801テストへの波及回避）。
- 代わりに**新パイプラインコード側で「エージェント出力が空 = 失敗」として扱い**、リトライ/終端判定に乗せる。影響範囲を新コードに閉じる。
- 注記: 空文字ハンドリングが分散するため、BaseAgent の例外化は将来の別タスク（監査 H-2 恒久対応）とする。

### 6-2. ループ状態管理

- リトライカウンタ・最終フィードバック・生成済みファイル一覧は `OrchestratorContext` の明示フィールドで管理（暗黙の self 属性に持たせない）。状態リセット漏れ（ステートリーク）をユニットテストで検証する。

### 6-3. plan JSON パースの堅牢化

- 既存の fence 除去（`clean_output`）を planner 出力にも適用。パース失敗時は 3-1 のフォールバック（劣化モード）に接続。

### 6-4. テスト戦略

- TDD。エージェントは全てモックし、以下をユニットテストで固める:
  - ループ制御（debug 3回/review 2回の上限・カウンタリセット）
  - 終端判定（APPROVED/NEEDS_HUMAN_REVIEW/ERROR の3値と exit code）
  - plan フォールバック（target_files 欠落/不正/劣化モードログ）
  - ファイル間コンテキスト伝搬（生成済みファイルが後続 coder 呼び出しに渡ること)
  - FKB 記録ガード（検証済み解のみ記録）
- 既存 4,801 テストの緑維持を回帰ゲートとする。

### 6-5. ドキュメント整合

- CLAUDE.md「14エージェント」→ 12 に是正。
- README のパイプライン説明（「12のAIエージェントが順次起動」）を新実装の実態に合わせて更新。

## 7. スコープ外（別タスク・バックログ管理）

- サンドボックスの本格隔離（監査 H-1）
- BaseAgent 空応答の例外化（監査 H-2 恒久対応）
- 実行時アーティファクトの .gitignore 整理（監査 H-3）
- DynamicRunLoop への横展開（案B・固定パイプライン完成後に再評価）
- 品質ゲート（pylint/coverage/mutation）のパイプライン組み込み
- 自動修正成功率の評価指標（運用データが溜まってから）

## 8. レビュー履歴

- GLM: 条件付き承認 → 重大指摘4件のうち②③④を設計反映、①（フォールバック責務矛盾）は「劣化モード明示＋責務契約の明文化」で対応（3-1）。
- Gemini 2.5 Pro: 高2件・中3件 → サンドボックス制約明記（4-2）・フィードバック契約（4-3）・role定義（3-1）・リトライ上限根拠（4-5）・NEEDS_HUMAN_REVIEWトリガー明文化（4-4）を反映。
