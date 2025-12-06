# NexusCore ルートディレクトリ ファイル整理サマリー

## 実施日
2025年12月6日

## 移動したファイル一覧

### 1. テストファイル → `tests/` に移動
- `api_client_test.py` → `tests/api/`
- `test_celery_simple.py` → `tests/`
- `test_job_state_machine_simple.py` → `tests/`
- `run_policy_check_test.py` → `tests/`
- `run_quality_gate_test.py` → `tests/`
- `run_quality_loop_test.py` → `tests/`
- `run_self_heal_test.py` → `tests/`
- `verify_job_state_machine.py` → `tests/`
- `verify_output_fix.py` → `tests/`

### 2. 実行スクリプト → `scripts/` または `dev_tools/` に移動
- `run_celery_test.sh` → `scripts/`
- `run_self_healing.py` → `scripts/`
- `run_vc_scout.py` → `scripts/`
- `run_test_report.sh` → `dev_tools/`
- `run_test_with_immediate_output.py` → `dev_tools/`
- `run_tests.py` → `dev_tools/`

### 3. ドキュメントファイル → `docs/` に移動
- `COVERAGE_ANALYSIS.md` → `docs/`
- `CURSOR_OUTPUT_IMPROVEMENT.md` → `docs/`
- `CURSOR_WSL_OUTPUT_VERIFICATION.md` → `docs/`
- `WSL_AUTO_EXECUTION_STATUS.md` → `docs/wsl/`
- `WSL_OUTPUT_STATUS.md` → `docs/wsl/`
- `WSL_OUTPUT_VERIFICATION_FINAL.md` → `docs/wsl/`
- `WSL_OUTPUT_VERIFICATION_RESULT.md` → `docs/wsl/`

### 4. ユーティリティスクリプト → `dev_tools/` または `tools/` に移動
- `_extract_deps.py` → `dev_tools/`
- `fix_imports.py` → `dev_tools/`
- `project_structure_and_code_export.py` → `tools/`

### 5. 起動スクリプト → `scripts/` に移動
- `launch.bat` → `scripts/`
- `launch_all.ps1` → `scripts/`
- `launch_dev.ps1` → `scripts/`
- `launch_export_ui.bat` → `scripts/`
- `install-pyenv-win.ps1` → `scripts/`

### 6. 設定ファイル → 適切な場所に移動
- `project_structure.json` → `data/`
- `fkb_local.json` → `data/knowledge_bases/` (既に存在していたため移動なし)

### 7. エージェント/カーネルファイル → `src/nexuscore/` に移動
- `simple_context_agent.py` → `tools/`
- `nexus_os_kernel.py` → `src/nexuscore/core/`

## ルートディレクトリに残したファイル

以下のファイルはエントリーポイントまたは重要な設定ファイルのため、ルートディレクトリに残しました：

- `main_cli.py` - CLIエントリーポイント
- `gradio_app.py` - Gradioアプリエントリーポイント
- `activate` - 仮想環境有効化スクリプト
- `activate_venv.sh` - 仮想環境有効化スクリプト（エイリアス）

## 注意事項

移動したファイルを参照している他のファイルがある場合は、パスを更新する必要があります。
特に以下のファイルを確認してください：
- `README.md`
- `Makefile`
- `scripts/` 内のスクリプト
- `dev_tools/` 内のスクリプト

