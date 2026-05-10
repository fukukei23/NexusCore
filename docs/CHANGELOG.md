# Changelog

NexusCore のプロジェクト固有変更履歴。
形式は [Keep a Changelog](https://keepachangelog.com/ja/) に準拠。

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
