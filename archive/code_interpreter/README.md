Archived code interpreter components
====================================

このフォルダには旧来の code_interpreter モジュールとテスト群をそのまま退避しています。
現行の NexusCore (agents + orchestrator) からは参照されておらず、今後この仕組みを再利用
したい場合は、ここから必要なファイルをコピーして新しい設計に合わせてください。

含まれる主なファイル
----------------------
- `src/` … `BaseCodeInterpreter`, `OpenCodeInterpreter`, `JupyterClient` などの実装
- `tests/` … それに対応した旧テストスイート

注意事項
--------
- 依存していたライブラリ (transformers, jupyter_client 等) は明示的に requirements から
  除外していません。必要に応じて見直してください。
- `nexuscore.code_interpreter` パッケージは ImportError を投げるスタブに置き換えています。
