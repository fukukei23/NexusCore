#!/bin/bash
# docs/ ルート散乱ファイル整理スクリプト
# 実行前に内容を確認し、必要に応じて調整すること
# 実行方法: cd ~/NexusCore && bash dev_tools/reorganize_docs.sh

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

echo "=== docs/ ルートファイル整理開始 ==="

# --- reports/ へ移動（分析・監査レポート） ---
git mv docs/2026-04-15_deep-analysis-report.md docs/reports/
git mv docs/COVERAGE_ANALYSIS.md docs/reports/
git mv docs/COVERAGE_PRIORITY_ANALYSIS.md docs/reports/
git mv docs/CR_AND_REPORTS_SAVE_LOCATIONS.md docs/reports/
git mv docs/audit_report_duediligence.md docs/reports/
git mv docs/coverage_phase3_summary.md docs/reports/
git mv docs/coverage_phase3_summary_ci.md docs/reports/
git mv docs/developer_skill_audit_report.md docs/reports/
git mv docs/enterprise_architecture_analysis_report.md docs/reports/
git mv docs/FILE_MIGRATION_SUMMARY.md docs/reports/

echo "[1/8] reports/ 移動完了"

# --- testing/ へ移動（テストガイド・結果・戦略） ---
git mv docs/CI_TEST_STRATEGY.md docs/testing/
git mv docs/COMPREHENSIVE_PROVIDER_TESTING_FINAL.md docs/testing/
git mv docs/FINAL_COMPREHENSIVE_TEST_REPORT.md docs/testing/
git mv docs/FINAL_TEST_RESULTS.md docs/testing/
git mv docs/TEST_EXECUTION_GUIDE.md docs/testing/
git mv docs/TEST_RESULTS_SUMMARY.md docs/testing/
git mv docs/e2e_self_healing_test_guide.md docs/testing/
git mv docs/e2e_test_results.md docs/testing/
git mv docs/e2e_testing_guide.md docs/testing/
git mv docs/test_coverage_job_state_machine.md docs/testing/
git mv docs/test_result_reporting.md docs/testing/
git mv docs/test_results_celery_job_state_machine.md docs/testing/
git mv docs/test_results_job_state_machine.md docs/testing/
git mv docs/test_strategy.md docs/testing/
git mv docs/testing_guide.md docs/testing/
git mv docs/testing_policy_ui.md docs/testing/
git mv docs/testing_strategy_phase3.md docs/testing/

echo "[2/8] testing/ 移動完了"

# --- setup/ へ移動（環境構築・セットアップ） ---
git mv docs/celery_setup.md docs/setup/
git mv docs/development_setup.md docs/setup/
git mv docs/saas_celery_supervisor.conf docs/setup/
git mv docs/saas_celery_systemd.service docs/setup/
git mv docs/saas_mvp_setup.md docs/setup/
git mv docs/venv_unification_summary.md docs/setup/
git mv docs/k8s_connection_guide.md docs/setup/
git mv docs/k8s_quick_start_guide.md docs/setup/
git mv docs/k8s_setup_status.md docs/setup/
git mv docs/k8s_worker_scaling_guide.md docs/setup/
git mv docs/saas_mvp_implementation_summary.md docs/setup/

echo "[3/8] setup/ 移動完了"

# --- tools/ へ移動（開発ツール・Cursor設定） ---
git mv docs/CI_SAFE_LOCK.md docs/tools/
git mv docs/CURSOR_OUTPUT_IMPROVEMENT.md docs/tools/
git mv docs/CURSOR_WSL_OUTPUT_VERIFICATION.md docs/tools/
git mv docs/TERMINAL_TIPS.md docs/tools/
git mv docs/cursor_chat_sync_location.md docs/tools/
git mv docs/cursor_japanese_activate.md docs/tools/
git mv docs/cursor_japanese_setup.md docs/tools/
git mv docs/cursor_mobile_chat_sync.md docs/tools/
git mv docs/cursor_nexuscore_playbook.md docs/tools/
git mv docs/cursor_settings_quick_guide.md docs/tools/
git mv docs/log_history_management_verification.md docs/tools/
git mv docs/makefile_guide.md docs/tools/
git mv docs/tree_sitter_checker_optimization.md docs/tools/

echo "[4/8] tools/ 移動完了"

# --- integrations/ へ移動（外部サービス連携） ---
git mv docs/SLACK_NOTIFICATION_TROUBLESHOOTING.md docs/integrations/
git mv docs/SLACK_WEBHOOK_URL_SETUP.md docs/integrations/
git mv docs/atelier_kyo_manager_integration.md docs/integrations/
git mv docs/slack_notification_setup.md docs/integrations/
git mv docs/slack_notification_troubleshooting.md docs/integrations/

echo "[5/8] integrations/ 移動完了"

# --- wsl/ へ移動（WSL固有） ---
git mv docs/NexusCore_WSL_Setup_Guide_2025.pdf docs/wsl/
git mv docs/wsl_auto_venv_setup.md docs/wsl/
git mv docs/wsl_venv_auto_activate_fix.md docs/wsl/

echo "[6/8] wsl/ 移動完了"

# --- specs/ へ移動（仕様・設計書） ---
git mv docs/AGENTS_DEEP_DIVE.md docs/specs/
git mv docs/STIT_STANDARD.md docs/specs/
git mv docs/codex_instruction_manifest.md docs/specs/
git mv docs/job_state_machine_implementation.md docs/specs/
git mv docs/semantic_diff_design.md docs/specs/

echo "[7/8] specs/ 移動完了"

# --- 各所へ散在移動 ---
git mv docs/ARCHITECTURE.md docs/architecture/
git mv docs/DOCS_INDEX.md docs/overview/
git mv docs/ONBOARDING_FLOW.md docs/governance/
git mv docs/external_api_verification.md docs/api/
git mv docs/external_run_api_examples.md docs/api/
git mv docs/saas_architecture.md docs/plans/
git mv docs/saas_badges.md docs/plans/
git mv docs/k8s_implementation_summary.md docs/setup/
git mv docs/k8s_next_steps.md docs/setup/

# --- archive/ へ移動（完了済み・一時的ファイル） ---
git mv docs/HANDOVER_INDEX.md docs/archive/
git mv docs/HANDOVER_QUICK_REFERENCE.md docs/archive/
git mv docs/SESSION_HANDOFF.md docs/archive/
git mv docs/handover_checklist.md docs/archive/
git mv docs/handover_report.md docs/archive/
git mv docs/handover_summary.md docs/archive/

echo "[8/8] 散在・archive 移動完了"

echo ""
echo "=== 整理完了 ==="
echo "残留ファイル確認:"
ls docs/*.* 2>/dev/null || echo "（docs/ 直下にファイルなし - 整理完了）"
echo ""
echo "ディレクトリ別ファイル数:"
for d in docs/*/; do echo "  $(basename $d): $(ls -1 "$d" 2>/dev/null | wc -l)"; done
