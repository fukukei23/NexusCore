# Changelog

NexusCore のプロジェクト固有変更履歴。
形式は [Keep a Changelog](https://keepachangelog.com/ja/) に準拠。

---

## [8.2.0] - 2026-05-10

### Changed
- P0-1: `_get_user_id_from_auth()` のDRY解消 — 3ファイルの重複定義を `dependencies/auth.py` に統合
- P0-3: `deps/orchestrator.py` → `dependencies/orchestrator.py` に統合、`deps/` ディレクトリ削除

### Removed
- P0-2: `api/server.py`（非推奨Flask 303行）を `archive/` に移動。`execute.py` の `tasks` 参照をローカル変数に変更
- P2-2: `utils/math_ops.py`（`add()` のみ、未使用）および関連テストを削除

### Changed
- P2-1: `orchestrator/explainability.py` にモジュール・関数docstringを追加
- P2-3: `utils/clean_output.py` にモジュール・関数docstringを追加
- P2-4: `api/utils/run_view.py` → `run_view_adapter.py` にリネーム（役割明確化）
