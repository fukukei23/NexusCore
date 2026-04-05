# CR-NEXUS-053: 次期開発タスク仕様書（Next Steps）

**文書ID**: CR-NEXUS-053
**バージョン**: 1.2
**作成日**: 2026-04-04
**最終更新**: 2026-04-05
**ステータス**: In Progress
**調査ベース**: ローカルクローン `/home/yn441611/NexusCore` の全面調査結果（手動調査 + 自動エージェント調査）

---

## 1. 調査サマリー

### 1.1 現状スナップショット

| 指標 | 値 |
|---|---|
| **バージョン** | 8.2.0J |
| **最終コミット** | 2026-04-05 (CR-NEXUS-051 P3/P4 + CR-055 + CR-057 + CR-E3) |
| **テスト** | Core 145 passed / debugger_agent 5FAIL / guardian_agent 1FAIL |
| **カバレッジ** | Core+LLM層 90.96% / retry_policy.py 97.30% |
| **アクティブブランチ** | mainのみ（クリーンアップ完了） |
| **完了CR** | CR-051 P2-P4, CR-055, CR-057, CR-E3 |
| **CI/CD** | GitHub Actions: Daily Backup + CI/CD (Bandit/Lint/Test) |

### 1.2 判定: 開発フェーズ

- **フェーズ**: CR-051完了 → P0テスト修正 → CR-052実装移行点
- CR-051エラー分類システム（P1）は完了（retry_policy 97.30%）
- ブランチクリーンアップ完了（mainのみ）
- 残: P0テスト修正6件、CR-052品質ゲート未着手

---

## 2. 優先タスク（Priority Order）

### 🔴 P0: テスト修正（緊急）

**問題**: `test_debugger_agent_comprehensive.py` で5件FAIL確認

```
tests/agents/test_debugger_agent_comprehensive.py::TestCreateDiff::test_create_diff_relative_path_error FAILED
tests/agents/test_debugger_agent_comprehensive.py::TestEdgeCases::test_debug_and_patch_empty_error_log FAILED
tests/agents/test_debugger_agent_comprehensive.py::TestEdgeCases::test_generate_fixed_code_empty_response FAILED
tests/agents/test_debugger_agent_comprehensive.py::TestEdgeCases::test_generate_fixed_code_diff_format_response FAILED
tests/agents/test_debugger_agent_comprehensive.py::TestEdgeCases::test_find_solution_invalid_regex FAILED
```

**関連**: `test_guardian_agent_comprehensive.py::test_init_with_git_error` もFAIL

**作業内容**:
1. FAIL原因を特定（API変更追従漏れの可能性大）
2. テストを現行実装に合わせて修正
3. `make test` で全パス確認

**見積**: 小（1-2時間）

---

### ✅ P1: CR-NEXUS-051 エラー分類システム実装（完了）

**ステータス**: ✅ 完了（2026-04-05）
**コミット**: `9e45b73a`
**Spec**: `docs/spec/CR-NEXUS-051_ERROR_CLASSIFICATION_SPECIFICATION.md` (v1.1.1)
**Plan**: `docs/spec/CR-NEXUS-051_IMPLEMENTATION_PLAN.md`

**実装済**:
1. `errors.py` — 例外階層・`classify_error()`・`convert_http_error_to_nexus_error()` + docstring改善（CR-057）
2. `retry_utils.py` — RetryContext・リトライ戦略（エラー分類に基づく）
3. `retry_policy.py` — ポリシー定義・定数化（P3）・環境変数対応（P4）・構造化ログ（P4）
4. `validate_decision_table()` — Spec準拠検証（CR-055）

**カバレッジ**: retry_policy.py **97.30%** / 合計 **90.96%**

**成果物**:
- 例外階層: `NexusCoreError` → 8カスタム例外
- `classify_error()`: 任意の例外を標準カテゴリに分類
- リトライ戦略: エラーカテゴリに基づく自動リトライ（一時的）or 即時失敗（恒久的）
- 環境変数: `NEXUS_RETRY_*` で実行時設定変更可能

---

### 🟡 P2: CR-NEXUS-052 品質ゲート実装

**現状**: 実装準備完了
**Spec**: `docs/spec/CR-NEXUS-052_QUALITY_GATE_SPECIFICATION.md`
**Impl**: `docs/spec/CR-NEXUS-052-IMPL_QUALITY_GATE_IMPLEMENTATION_SPEC.md`

**実装対象**:
1. `src/nexuscore/agents/guardian_agent.py` 拡張 — 統合分析関数・憲法統合
2. `code_analyzer.py` 拡張 — Tier 1品質ゲートの自動実行
3. レポート生成 — 品質ゲート結果の標準フォーマット出力

**依存**: CR-051の完了後（エラー分類を品質ゲートで使用）

---

### 🟡 P3: テストカバレッジ改善（全体16.85% → 30%目標）

**現状**: Core+LLM層は87%だが、エージェント層・Web層が低い

**優先対象**:
1. `orchestrator/authority_runner.py` (789行) — テスト不足
2. `agents/guardian_agent.py` (766行) — テスト拡充
3. `agents/constitutional_council_agent.py` (601行) — テスト拡充
4. `agents/tester_agent.py` (588行) — テスト拡充

---

### ✅ P4: 古いブランチ・ファイルのクリーンアップ（完了）

**ステータス**: ✅ 完了（2026-04-05）

**結果**:
- ローカル: 12 → **2**（main + worktree使用中→後に削除）
- リモート: 24 → **1**（origin/mainのみ）
- 23件のstale remote-tracking refs をprune済み
- worktree `/home/yn441611/NexusCore_PR_052` も削除済み

---

### 🟢 P5: Docker/K8s環境の検証

**現状**: `docker-compose.yml`, `docker-compose.saas.yml`, `k8s/` が存在するが動作確認状況不明

**作業**:
1. `docker-compose up` での基本起動確認
2. `.env` のAPIキー設定確認（テンプレートはあり）
3. `k8s/` マニフェストの妥当性確認

---

## 3. 推奨ロードマップ

```
✅ Phase 0（完了）: P1 CR-051 実装、P4 ブランチクリーンアップ
  ↓
🔴 Phase 1（現在）: P0 テスト修正（debugger_agent 5FAIL, guardian_agent 1FAIL）
  ↓
Phase 2: P2 CR-052 品質ゲート実装
  ↓
Phase 3: P5 Docker/K8s検証
```

---

## 4. 注意事項

### 4.1 ガバナンス遵守

NexusCoreはSTIT+IRGガバナンスを採用しているため、機能実装時は以下を参照:
- `GOVERNANCE/MASTER_PROTOCOL_TEMPLATE.md`
- `GOVERNANCE/HYGIENE_CHECK.md`
- `docs/ARCHITECTURE.md`（Gate/SSOT Entrypoint）

### 4.2 Gate分類

- **P0（テスト修正）**: Fast Gate（既存機能の軽微な改善）
- **P1（CR-051）**: Standard Gate（Phase 2.5承認済み）
- **P2（CR-052）**: Standard Gate（実装準備完了）
- **P3（カバレッジ）**: Fast Gate
- **P4-P5**: Fast Gate

### 4.3 削除禁止ディレクトリ

`core/`, `lib/`, `tools/`, `docs/`, `agents/`, `scheduled-tasks/` は削除・移動禁止

---

## 5. 未解決事項（2026-04-05時点）

| # | 件名 | 状態 | 影響 |
|---|---|---|---|
| 1 | debugger_agentテスト5件FAIL | 🔴 未解決 | CI品質ゲート通過不能の可能性 |
| 2 | guardian_agentテスト1件FAIL | 🔴 未解決 | 同上 |
| 3 | ~~CR-051エラー分類未実装~~ | ✅ 完了 | — |
| 4 | CR-052品質ゲート未実装 | ⏳ 保留 | 自律品質保証がブロック |
| 5 | ~~全体テストカバレッジ16.85%~~ | ✅ Core改善（90.96%） | — |
| 6 | ~~古いリモートブランチ10+残存~~ | ✅ 完了 | — |
| 7 | テストコレクションエラー30件 | 🔴 未解決 | テスト実行前にコレクション失敗 |
| 8 | self_healing_service.py GitHub API未実装 | TODO | 自己修復の自動化が不完全 |
| 9 | tree_sitter_checker.py キャッシュ未実装 | TODO | 解析パフォーマンス低下 |
| 10 | Gradio UI LLM統合未完了 | TODO | Web UI機能不完全 |
| 11 | `type: ignore` 30箇所 | 低優先 | 型安全性の部分的欠如 |

---

## 6. 追加調査データ（自動エージェント調査）

### 6.1 テスト詳細

- **全テスト数**: 4,732テスト（コレクション時）
- **テストファイル数**: 398ファイル
- **ソースファイル数**: 192ファイル
- **コレクションエラー**: 30件（主に gradio_app, integration）
- **スキップテスト**: 10+ファイルで `pytest.mark.skip` 使用

### 6.2 TODO分布（39件）

| ファイル | 件数 | 内容 |
|---|---|---|
| `services/self_healing_service.py` | 複数 | Coverage統合、GitHub API連携 |
| `utils/tree_sitter_checker.py` | 12 | キャッシュ、プロファイリング、並列処理 |
| `ui/unified_gradio_ui.py` | 3 | LLM統合、DebuggerAgent統合 |

### 6.3 依存関係

- **パッケージ数**: 60+
- **Python対応**: 3.9-3.12
- **torch**: CPU版明示指定 (`torch==2.2.2+cpu`)
- **主要LLM SDK**: openai, anthropic, google-generativeai, deepseek

### 6.4 WIPコミット

- ~~`wip: CR-NEXUS-051 implementation in progress`~~ — ブランチ削除済み（mainマージ完了）
- 全WIPブランチクリーンアップ完了（2026-04-05）
