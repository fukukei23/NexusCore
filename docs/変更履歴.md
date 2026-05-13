# Changelog

NexusCore のプロジェクト固有変更履歴。
形式は [Keep a Changelog](https://keepachangelog.com/ja/) に準拠。

---

## [8.2.2] - 2026-05-12

### Fixed
- テストスイートハング修正: `pytest.ini` の `addopts` に `-m "not integration" --timeout=120` を追加 — `test_integration_llm.py`（実際のLLM API呼び出し）をデフォルトで除外

### Changed
- P1-1: APIルートのHTTPException判定を `isinstance(e, HTTPException)` に統一、バックグラウンドタスクのエラー分類を追加（ValueError/ConnectionError/ImportError）
- P1-2: `authority_runner.py` を3モジュールに分割（`context.py`, `state.py`, `phase_logging.py`）— 428→293行
- P1-3: LLMリトライロジック共通化 — `BaseLLM.execute_real_or_fallback()` 抽出、3プロバイダーを `_build_real_call()` クロージャパターンに統一
- P1-5: `GuardianAgent` を2モジュールに分割（`commit_workflow.py`, `review_executor.py`）— 388→317行

---

## [8.2.1] - 2026-05-11

### Added
- P2-2: Settings UI Gradioタブ追加（`ui/settings_tab.py`） — LLM プロバイダー状態・プロファイル情報・タスクルーティングの読み取り専用ダッシュボード
- P2-3: フェーズ実行に tqdm 進捗バーとタイミングログを追加（`orchestrator/authority_runner.py`）
- P2-5: `webapp/db_helpers.py` 新規作成 — Webapp DBクエリ共通ヘルパー（13関数）
- P2-1: subqueryload でN+1クエリ解消、DB count()クエリでPython集計排除

### Changed
- P2-6: 12ファイルの未使用import除去（28→12、残りは意図的re-export）
- P2-4: 15ファイル160件の print()→logger 移行（残り37件は意図的）
- P2-5: views_projects/dashboard/logs の重複クエリパターンを共通ヘルパー化

---

## [8.2.0] - 2026-05-10

### Added
- P1-1: GitHub OAuth認証ルーター（`api/routes/auth.py`）をFastAPIで新規実装 — Starlette OAuthクライアント、SessionMiddleware対応

### Changed
- P0-1: `_get_user_id_from_auth()` のDRY解消 — 3ファイルの重複定義を `dependencies/auth.py` に統合
- P0-1: `sandbox_executor.py` のハードコード値（メモリ/CPU制限）を環境変数化
- P0-2: `npe/budget.py`, `gemini_provider.py` の broad `except Exception:` を具体的例外型に修正
- P0-3: `deps/orchestrator.py` → `dependencies/orchestrator.py` に統合、`deps/` ディレクトリ削除
- P0-3(v2): `self_healing_service.py`（1,006行）を3モジュールに分割（`git_operations`, `test_runner`, `patch_workflow`）
- P0-4: `ProjectCreateRequest` にパストラバーサル防止・URL検証のPydantic validator追加
- P1-2: `unified_gradio_ui.py`（826行）を6モジュールに分割（_state, _llm_init, code_prompt_tab, ai_revision_tab, test_runner_tab, history_diff_tab）
- P1-3: `orchestrator_inline.py` を `orchestrator_helper.py` に統合、inline.py は後方互換re-exportのみ
- P2-1: `orchestrator/explainability.py` にモジュール・関数docstringを追加
- P2-3: `utils/clean_output.py` にモジュール・関数docstringを追加
- P2-4: `api/utils/run_view.py` → `run_view_adapter.py` にリネーム（役割明確化）

### Removed
- P0-2: `api/server.py`（非推奨Flask 303行）を `archive/` に移動。`execute.py` の `tasks` 参照をローカル変数に変更
- P2-2: `utils/math_ops.py`（`add()` のみ、未使用）および関連テストを削除
- P1-1: `views_api_test.py`（シミュレーションのみ）を `archive/` に移動
