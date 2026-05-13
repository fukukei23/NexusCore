# CR-FASTAPI-021: API Key ブートストラップ CLI - 完了レポート

## 1. 実装日時
2025年12月9日

## 2. 目的・ゴール
初回 API Key を発行するための公式 CLI ツールを提供し、「DB を直接叩いて API Key を作成する」手動運用を廃止する。ユーザーが存在しない場合は自動的に作成する。

## 3. 実装ステップの要約

1. **CLI モジュール作成**:
   - `src/nexuscore/cli/__init__.py` を新規作成
   - `src/nexuscore/cli/bootstrap_apikey.py` を新規作成
   - **ロジック関数 `bootstrap_apikey_for_app()` を分離**: テストから直接呼び出し可能な純粋関数として実装
   - **CLI 関数 `bootstrap_apikey_main()` をラッパー化**: `bootstrap_apikey_for_app()` を呼び出すラッパーとして実装
   - `argparse` を使用して `--user-login`, `--user-name`, `--key-name` を受け取る
   - Flask アプリコンテキストを使用して DB にアクセス
   - User が存在しない場合は `cli_bootstrap_{login}` 形式の `github_id` で自動作成
   - API Key を生成し、標準出力に `export NEXUSCORE_API_KEY="..."` を出力
   - DB が未初期化の場合は `db.create_all()` を自動実行
   - **SQLAlchemy detached オブジェクト問題の解決**: `expunge()` 前に属性を明示的に読み込み、セッション外でも属性にアクセス可能に

2. **テスト作成**:
   - `tests/cli/test_bootstrap_apikey.py` を新規作成
   - **テスト用 app フィクスチャ**: `tmp_path` を使用した SQLite DB を用意
   - **ロジック関数の直接テスト**: `bootstrap_apikey_for_app()` を直接呼び出して検証
   - **CLI 関数のテスト**: `monkeypatch` で `create_app` をモックして検証
   - 初回実行時の User + ApiKey 作成を検証
   - 2回目以降の User 再利用と ApiKey 追加を検証
   - デフォルト名の使用を検証
   - 標準出力の `export` コマンド出力を検証

3. **ドキュメント更新**:
   - `.cursorrules` に API Key 運用フローのルールを追加
   - `README.md` に初回 API Key 発行手順を追加（`PYTHONPATH=src` の設定方法を含む）
   - `docs/api/README.md` に CLI 使用方法を追加

## 4. 変更ファイル一覧

- **新規作成**:
  - `src/nexuscore/cli/__init__.py`
  - `src/nexuscore/cli/bootstrap_apikey.py`
  - `tests/cli/__init__.py`
  - `tests/cli/test_bootstrap_apikey.py`
  - `docs/api/CR-FASTAPI-021_完了報告.md`
- **変更**:
  - `.cursorrules`
  - `README.md`
  - `docs/api/README.md`

## 5. 実行したテストコマンドと結果

**Unit テスト**:
```bash
pytest tests/cli/test_bootstrap_apikey.py -v
```
**結果**: すべてのテストが成功（5テスト）
```
tests/cli/test_bootstrap_apikey.py::test_bootstrap_apikey_first_time_creates_user_and_key PASSED
tests/cli/test_bootstrap_apikey.py::test_bootstrap_apikey_second_time_reuses_user PASSED
tests/cli/test_bootstrap_apikey.py::test_bootstrap_apikey_default_key_name PASSED
tests/cli/test_bootstrap_apikey.py::test_bootstrap_apikey_main_returns_zero_on_success PASSED
tests/cli/test_bootstrap_apikey.py::test_bootstrap_apikey_main_outputs_export_command PASSED

====== 5 passed, 16 warnings in 1.48s ======
```

**関連APIテスト**:
```bash
pytest tests/api/test_api_keys.py -v
```
**結果**: すべてのテストが成功（9テスト）
```
tests/api/test_api_keys.py::test_issue_api_key_success PASSED
tests/api/test_api_keys.py::test_issue_api_key_without_auth PASSED
tests/api/test_api_keys.py::test_issue_api_key_limit_exceeded PASSED
tests/api/test_api_keys.py::test_list_api_keys_success PASSED
tests/api/test_api_keys.py::test_list_api_keys_empty PASSED
tests/api/test_api_keys.py::test_revoke_api_key_success PASSED
tests/api/test_api_keys.py::test_revoke_api_key_not_found PASSED
tests/api/test_api_keys.py::test_revoke_api_key_forbidden PASSED
tests/api/test_api_keys.py::test_issue_api_key_default_name PASSED

====== 9 passed, 16 warnings in 1.88s ======
```

**実際の動作確認**:
```bash
cd /home/yn441611/NexusCore
source activate
export PYTHONPATH=src
python -m nexuscore.cli.bootstrap_apikey --user-login dev --key-name "Local Dev Key"
```
**結果**:
- 既存ユーザー `dev` (id=1) を使用
- API Key "Local Dev Key" (id=2) を作成
- 標準出力に `export NEXUSCORE_API_KEY="nexus_..."` を出力
- 正常終了（exit code 0）

## 6. 設計上の改善点

- **ロジックと CLI の分離**: `bootstrap_apikey_for_app()` と `bootstrap_apikey_main()` を分離し、テスト容易性を向上
- CLI ツールとして統一されたインターフェースを提供
- ユーザー自動作成により、初回セットアップが容易に
- 標準出力に `export` コマンドを出力することで、環境変数設定が簡単に
- DB への直接操作を禁止し、運用フローを明確化
- テスト用 app をフィクスチャで用意することで、テストの独立性を確保
- **SQLAlchemy detached オブジェクト問題の解決**: `expunge()` 前に属性を明示的に読み込むことで、セッション外でも属性にアクセス可能に

## 7. 既知の制約・今後の課題

- `github_id` は `cli_bootstrap_{login}` 形式の暫定値を使用（GitHub OAuth 連携は未実装）
- エラーハンドリングは基本的なもののみ（DB 接続エラーなどは今後の拡張）
- "Database URL not found." という警告が表示されるが、動作には影響なし（デフォルト SQLite DB を使用）

## 8. 次のステップ

- CR-FASTAPI-022 と連携して TypeScript E2E テストでの使用を検証
- 本番環境での使用を想定したエラーハンドリングの強化

