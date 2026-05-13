# NexusCore ドキュメント全体インデックス

> **NexusCore プロジェクトのドキュメント全体マップ**
>
> このファイルは、`docs/` ディレクトリ配下のすべてのドキュメントへのナビゲーションを提供します。
> 特定のカテゴリのローカルインデックス（例: `HANDOVER_INDEX.md`）がある場合は、そちらも参照してください。

---

## 📚 役割別ナビゲーション

### 🆕 新規開発者向け

**セットアップから開発フローまで**

1. **[開発環境セットアップ](development_setup.md)** - 開発環境の構築方法
2. **[README_VENV.md](../README_VENV.md)** - 仮想環境の簡単な使い方
3. **[Makefile ガイド](makefile_guide.md)** - Makefile の使い方
4. **[テスト戦略](test_strategy.md)** - テストの考え方と実装方針
5. **[テスト実行ガイド](TEST_EXECUTION_GUIDE.md)** - テストの実行方法

**関連ドキュメント:**
- [atelier-kyo-manager 統合](atelier_kyo_manager_integration.md) - 外部プロジェクトとの統合
- [WSL セットアップガイド](NexusCore_WSL_Setup_Guide_2025.pdf) - WSL 環境のセットアップ（PDF）

---

### 🚀 運用担当者向け

**Kubernetes、SaaS、通知設定**

#### Kubernetes / インフラ

1. **[Kubernetes クイックスタートガイド](k8s_quick_start_guide.md)** - 初心者向け K8s セットアップ
2. **[K8s 接続ガイド](k8s_connection_guide.md)** - クラスターへの接続方法
3. **[K8s ワーカースケーリングガイド](k8s_worker_scaling_guide.md)** - ワーカーのスケーリング
4. **[K8s セットアップ状況](k8s_setup_status.md)** - 現在のセットアップ状況
5. **[K8s 実装サマリー](k8s_implementation_summary.md)** - 実装内容のまとめ
6. **[K8s 次のステップ](k8s_next_steps.md)** - 今後の展開

#### SaaS / 運用

1. **[SaaS アーキテクチャ](saas_architecture.md)** - SaaS MVP の全体設計
2. **[SaaS MVP セットアップ](saas_mvp_setup.md)** - MVP のセットアップ手順
3. **[SaaS MVP 実装サマリー](saas_mvp_implementation_summary.md)** - 実装内容のまとめ
4. **[SaaS バッジ設定](saas_badges.md)** - バッジの設定方法
5. **[Celery セットアップ](celery_setup.md)** - Celery の設定

#### Slack / 通知

1. **[Slack Webhook URL 設定](SLACK_WEBHOOK_URL_SETUP.md)** - Webhook URL の取得方法
2. **[Slack 通知セットアップ](slack_notification_setup.md)** - 通知機能の設定
3. **[Slack 通知トラブルシューティング](SLACK_NOTIFICATION_TROUBLESHOOTING.md)** - 問題解決ガイド

---

### 🏢 経営 / 監査向け

**アーキテクチャ分析と監査レポート**

1. **[エンタープライズアーキテクチャ分析レポート](enterprise_architecture_analysis_report.md)** - 全体アーキテクチャの分析
2. **[開発者スキル監査レポート](developer_skill_audit_report.md)** - 開発者スキルの評価
3. **[デューデリジェンス監査レポート](audit_report_duediligence.md)** - デューデリジェンス結果

---

### 🤖 AI / Cursor 向け

**AI 開発支援ツール向けの指示とプレイブック**

1. **[NexusCore コードレビュー対応 Playbook](cursor_nexuscore_playbook.md)** - CR対応のテンプレートと手順
2. **[Codex 指示マニフェスト](codex_instruction_manifest.md)** - Codex への指示事項
3. **[Cursor 設定クイックガイド](cursor_settings_quick_guide.md)** - Cursor の設定方法
4. **[Cursor チャット同期場所](cursor_chat_sync_location.md)** - チャット同期の設定
5. **[Cursor モバイルチャット同期](cursor_mobile_chat_sync.md)** - モバイルでの同期

---

## 📁 カテゴリ別ドキュメント一覧

### ハンドオーバー系

**開発作業の申し送り資料**

> **注意**: ハンドオーバー関連の詳細は [HANDOVER_INDEX.md](HANDOVER_INDEX.md) を参照してください。

- [HANDOVER_INDEX.md](HANDOVER_INDEX.md) - ハンドオーバー資料のインデックス
- [HANDOVER_QUICK_REFERENCE.md](HANDOVER_QUICK_REFERENCE.md) - クイックリファレンス
- [handover_checklist.md](handover_checklist.md) - チェックリスト
- [handover_report.md](handover_report.md) - 完全版レポート
- [handover_summary.md](handover_summary.md) - 簡易サマリー

---

### 仕様・CR・完了レポート系

**Spec（仕様）・Change Request・完了レポートの保存先とルール**

- [CR と実装計画の結果の保存先](CR_AND_REPORTS_SAVE_LOCATIONS.md) - Spec / 完了レポートの保存場所、完了レポートに含める項目、テスト必須ルール
- **STIT（Spec & Test Driven Iteration）**: 仕様・テスト・実装の順序と Gate は [ガバナンス/スペックテスト駆動イテレーション.md](../ガバナンス/スペックテスト駆動イテレーション.md) を参照
- **Phase 2.5（IRG）**: [docs/ARCHITECTURE.md](ARCHITECTURE.md) および [ガバナンス/templates/レビューパケット_フェーズ25_テンプレート.md](../ガバナンス/templates/レビューパケット_フェーズ25_テンプレート.md) を参照

---

### テスト戦略・結果系

**テストの設計、実行、結果レポート**

- [テスト戦略設計書](test_strategy.md) - テスト戦略の全体設計
- [テストガイド](testing_guide.md) - テストの実装ガイド
- [Phase3 テスト戦略](testing_strategy_phase3.md) - Phase3 のテスト方針
- [UI テストポリシー](testing_policy_ui.md) - UI テストのポリシー
- [テスト実行ガイド](TEST_EXECUTION_GUIDE.md) - テストの実行方法
- [テスト結果レポート](test_result_reporting.md) - テスト結果のレポート方法
- [E2E テストガイド](e2e_testing_guide.md) - E2E テストのガイド
- [Self-Healing E2E テストガイド](e2e_self_healing_test_guide.md) - Self-Healing の E2E テスト
- [E2E テスト結果](e2e_test_results.md) - E2E テストの結果

**機能別テスト結果:**
- [JobStateMachine カバレッジ](test_coverage_job_state_machine.md)
- [JobStateMachine テスト結果](test_results_job_state_machine.md)
- [Celery JobStateMachine テスト結果](test_results_celery_job_state_machine.md)

---

### NexusCore 実装詳細系

**機能実装の詳細ドキュメント**

- [JobStateMachine 実装](job_state_machine_implementation.md) - ジョブ状態遷移の実装
- [Tree-sitter チェッカー最適化](tree_sitter_checker_optimization.md) - Tree-sitter の最適化
- [外部 API 検証](外部API検証.md) - 外部 API の検証方法
- [外部 Run API 例](外部実行API例.md) - 外部から Run API を呼び出す例
- [Run レポートポリシー](run_reports_policy.md) - Run レポートの保存ポリシー
- [ログ履歴管理検証](log_history_management_verification.md) - ログ履歴管理の検証
- [Semantic Diff 設計](semantic_diff_design.md) - Semantic Diff の設計
- [Phase3 カバレッジサマリー](coverage_phase3_summary.md) - Phase3 のカバレッジ状況

---

## 📊 生成物ディレクトリ

以下のディレクトリには、自動生成されるレポートが保存されます。**編集は行わないでください。**

### `completion_reports/`

実装作業の完了レポートが保存されます。

- 命名規則: `<作業識別子>_COMPLETION_REPORT.md`
- 例: `CR-002_API_AUTHENTICATION_COMPLETION_REPORT.md`
- 詳細: [完了レポート作成ルール](../.cursorrules) を参照

### `reports/`

テスト結果レポートが自動保存されます。

- 命名規則: `TEST_RESULTS_YYYYMMDD_HHMMSS.txt`
- エラーログ: `TEST_ERRORS_YYYYMMDD_HHMMSS.txt`
- 詳細: [テスト結果レポート](test_result_reporting.md) を参照

### `run_reports/`

Self-Healing / Orchestrator 実行ごとの Run レポートが保存されます。

- 命名規則: `RUN_{run_id}.md`
- 詳細: [Run レポートポリシー](run_reports_policy.md) を参照

---

## 🔗 関連リンク

- [README.md](../README.md) - プロジェクトの概要とクイックスタート
- [README_VENV.md](../README_VENV.md) - 仮想環境の簡単な使い方

---

**最終更新**: 2025-12-02

