# mutation score 実測レポート（2026-09-11）

GitHub Issue: [auto-loop] mutmut対象拡大とmutation score実測（llm_router・authority_runner等）

## 目的

カバレッジ84.08%は「テストが通過した」実績でしかなく、アサーション強度は mutation score でしか測れない。
`[tool.mutmut]` の `paths_to_mutate` を中核モジュールへ拡大し、スコアを実測する。

## 実行環境

| 項目 | 値 |
|---|---|
| mutmut | 3.5.0 |
| 実行コマンド | `mutmut run --max-children 4`（venv内） |
| 実行日時 | 2026-09-11 10:15〜10:27 JST（1回目）・10:30〜10:52（検証再実行・2回目） |
| 所要 | 約12分/回（1.55 mutations/second） |

## 実行範囲（明記義務）

**全5ファイル・1,433 mutants を完走**（対象絞りなし・途中切断なし）。

- `src/nexuscore/agents/mutation_tester_agent.py`（既存対象）
- `src/nexuscore/llm/llm_router.py`
- `src/nexuscore/orchestrator/authority_runner.py`
- `src/nexuscore/orchestrator/run_lock.py`（中核・並行制御）
- `src/nexuscore/orchestrator/run_state_integrity.py`（中核・整合検証）

`tests_dir` は上記に対応する14テストファイル + `-m "not slow"`。
`also_copy = ["src"]` を追加（mutants/ コピー内で依存モジュール import に必要・harness mutation check 実績と同一パターン）。

## 結果

score = (killed + timeout) / (killed + timeout + survived)。timeout は「変異によりテストが停止=検出」のため算入、notests（covering test なし）は分母から除外。

| ファイル | total | killed | timeout | survived | notests | score |
|---|---:|---:|---:|---:|---:|---:|
| agents/mutation_tester_agent.py | 263 | 145 | 0 | 110 | 8 | **56.9%** |
| llm/llm_router.py | 498 | 273 | 2 | 219 | 4 | **55.7%** |
| orchestrator/authority_runner.py | 308 | 104 | 179 | 25 | 0 | **91.9%** |
| orchestrator/run_lock.py | 243 | 130 | 0 | 113 | 0 | **53.5%** |
| orchestrator/run_state_integrity.py | 121 | 85 | 0 | 36 | 0 | **70.2%** |
| **ALL** | **1,433** | **737** | **181** | **503** | **12** | **64.6%** |

2回の実行で killed/survived が ±2 mutant 揺れた（735/505 ↔ 737/503・タイムアウト境界の非決定性）。

### ⚠️ 留意点

1. **authority_runner.py の timeout 179件（58%）**: テスト停止で検出したカテゴリだが、killed より多く、タイムアウト依存で検出の実態が濃い。91.9%は過大評価の可能性がある。
2. **LLMRouter.__init__ の生存98件**: コンストラクタ引数のデフォルト値（例: `log_dir: str = "logs"` → `"XXlogsXX"`）が一切アサートされていない。
3. **_try_acquire_run_lock の生存49件**: `or not run_id.strip()` → `and` の分岐反転が生存するなど、INVALID_RUN_ID 系ガードの否定系テストが薄い。

## 生き残った mutant

全503件の一覧: `artifacts/mutation/survived_mutants_20260911.txt`

上位（ファイル :: 変異対象関数 / 生存数）:

| 生存数 | 対象 |
|---:|---|
| 98 | llm_router.py :: LLMRouter.__init__ |
| 71 | mutation_tester_agent.py :: run_mutation_testing |
| 53 | llm_router.py :: LLMRouter.complete |
| 49 | run_lock.py :: _try_acquire_run_lock |
| 45 | llm_router.py :: LLMRouter.get_llm_for_task |
| 29 | run_lock.py :: refresh_run_lock |
| 21 | mutation_tester_agent.py :: _suggest_test_for_mutant |
| 20 | run_state_integrity.py :: verify_integrity |
| 16 | authority_runner.py :: run_with_authority |
| 13 | llm_router.py :: _classify_task_type |

## 検証（生exit code）

- 対象14テストファイル回帰: `233 passed, 4 skipped, 1 deselected, 1 xfailed in 3.24s / PYTEST_EXIT=0`
- pyproject.toml パース（tomllib）: paths_to_mutate=5 / tests_dir=16エントリ / `TOML_EXIT=0`
- **⚠️ mutmut run 自体の exit code は取得不能**: 1,433/1,433 完走・最終サマリー出力（`1.55 mutations/second`）後、プロセスが終了処理で停止（`ps` 実測: `STAT=Sl / WCHAN=futex_wait_queue`・50分以上継続）。SIGTERM を送信して停止した際の生コードは `MUTMUT_EXIT=143`（128+15=SIGTERM）。**スコア数値は meta ファイル（mutants/**/*.py.meta の exit_code_by_key）から直接集計したもので、プロセスの正常終了に依存しない**。
- mutmut 結果分布の実測（exit_code_by_key 集計）: `{0: 503=survived, 1: 737=killed, -24: 181=timeout(SIGXCPU), 33: 12=notests}` / sum=1433

## 範囲外（次回起票）

テスト強化は本Issueの範囲外。上記「留意点」を起票元とする:

1. llm_router `__init__`/`complete`/`get_llm_for_task` の引数・属性アサーション追加（生存216件）
2. run_lock `_try_acquire_run_lock`/`refresh_run_lock` の分岐否定系テスト追加（生存113件）
3. authority_runner の timeout 検出の精査（killed 化でスコア信頼性向上）

## 制約遵守

- テストコードは改変していない（読むのみ・`git diff` 対象は pyproject.toml / docs / artifacts のみ）
- 実行範囲・生exit code を本報告に記載済み
