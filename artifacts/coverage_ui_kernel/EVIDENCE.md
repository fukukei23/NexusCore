# ui層カバレッジ方針の実測証跡（2026-09-11）

判断: ①`core/nexus_os_kernel.py` + `scripts/run_vc_scout.py` を削除 ②UI描画レイヤーを `.coveragerc` omit に追加

## 測定コマンド（README・CIと同一条件）

```bash
source .venv/bin/activate && export PYTHONPATH=src
python -m pytest --tb=short --cov=src --cov-report=term-missing \
  --cov-report=xml:artifacts/coverage_ui_kernel/<tag>_coverage.xml \
  --cov-report=json:artifacts/coverage_ui_kernel/<tag>_coverage.json
# serial実行（CIと同一・-n auto不使用）
```

## 結果比較

| 項目 | baseline（変更前） | after（変更後） |
|---|---|---|
| TOTAL（stmt+branch合算） | 84.02% | **86.38%** |
| stmts | 15,570 | 14,988 |
| files | 270 | 260 |
| branch-rate (xml) | — | 0.8184 |
| テスト結果 | 2 failed（webapp flake・単独実行pass実測）/ BASELINE_EXIT=1 | 5265 passed / 187 skipped / 26 xfailed / 12 xpassed / AFTER_EXIT=0 |

生ファイル（`baseline_coverage.json` 等・計4.6MB）はリポジトリ非同梱。必要なら本表の値を `coverage.py json` で再現可能。

## 対象モジュールの実測（baseline_coverage.json より抽出）

| ファイル | stmts | miss | coverage |
|---|---|---|---|
| core/nexus_os_kernel.py | 75 | 75 | **0.00%** |
| ui 描画レイヤー9モジュール合計（omit対象） | 507 | 377 | 25.6% |
| ├ settings_tab.py | 98 | 84 | 12.50% |
| ├ code_prompt_tab.py | 94 | 70 | 20.69% |
| ├ ai_revision_tab.py | 66 | 57 | 10.98% |
| ├ history_diff_tab.py | 67 | 59 | 9.41% |
| ├ test_runner_tab.py | 49 | 40 | 16.98% |
| ├ dynamic_run_tab.py | 41 | 31 | 22.22% |
| ├ unified_gradio_ui.py | 33 | 12 | 59.46% |
| ├ _llm_init.py | 32 | 12 | 61.76% |
| └ _state.py | 27 | 12 | 42.86% |
| ui/policy_interface.py（**omit対象外・測定継続**） | 95 | 6 | 93.33% |
| ui/__init__.py | 2 | 0 | 100.00% |

## 参照関係の実測（kernel削除の根拠）

```bash
# 固定プロトコル再検索（1回目N=1 → 2回目N=1・全量性確認済み）
$ grep -rln --include='*.py' --include='*.sh' --include='*.md' --include='*.ts' \
    --include='*.js' --include='*.json' --include='*.yaml' nexus_os_kernel \
    src/ tests/ tools/ scripts/ *.py *.sh *.md
scripts/run_vc_scout.py

# 唯一の参照元は既に壊れている（kernel は src/nexuscore/core/ へ移設済み・flat import 不成立）
$ python -c "from nexus_os_kernel import get_kernel"
ModuleNotFoundError: No module named 'nexus_os_kernel'
```

- `run_vc_scout.py` のドキュメント参照: `docs/reports/FILE_MIGRATION_SUMMARY.md`（移設記録）のみ
- docs/architecture への kernel 言及: 0件（アーキ文書の更新不要を確認）

## 追加ゲート

| ゲート | 結果 | 生exit code |
|---|---|---|
| ruff（src/tests） | All checks passed! | RUFF_EXIT=0 |
| bandit `-ll`（High/Medium severity） | 0件 | BANDIT_EXIT=0 |

## 副次発見（本タスクでは未対応）

- `tests/gradio/test_unified_gradio_ui.py:27` が `run_test_handler` を import しようとして module-level skip 中（実測: `ImportError: cannot import name 'run_test_handler' from 'nexuscore.ui.unified_gradio_ui'`）。UI全体を構築するスモークテストが静かに死んでいる＝ui描画レイヤーカバレッジ崩落の構造的原因の1つ。UI E2E再評価時に要修正
