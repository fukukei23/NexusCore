# harness 題庫（dogfooding定題プール・v4仕様）

> v4設計正典: obsidian-ssot `00_SYSTEM/マルチLLMレビュー/2026-09-09_ハーネス計測段階拡張レビュー/revised_proposal.md`「r3 統合 — パラメータ確定版 v4」
> 運用: ラッパー `scripts/run_harness_task.py` が未消化お題をカテゴリ均等化強制で抽出・実行後に `[x]` 化（原子的更新）
> お題は**実際の未解決小課題から作る**（v4要件・人工的な空タスク禁止）。消化したお題は `[x]` になるが、行は残す（実績として保持・シードスクリプトで補充）

## 無人用（読む系）

- [ ] コード読解: tests/harness/ 配下でカバレッジが相対的に低い領域を特定し、未テストの分岐トップ3を列挙して報告する（実装の変更はしない）
- [ ] エラー診断: harness全体テストで出る20件のwarningを分類し、修正優先度付きで報告する（修正はしない）
- [ ] 設定・docs生成: tool_policy.yaml の deny_patterns の網羅性を評価し、防御漏れ候補を報告する（policy変更はしない）
- [ ] コード読解: loop.py の state.save() 呼び出し経路を全て列挙し、保存漏れシナリオ候補を報告する（実装の変更はしない）
- [x] 設定・docs生成: docs/開発ガイド.md と harness_cli --help の不整合を列挙して報告する（修正はしない）
- [ ] エラー診断: run_state の quarantine ファイルが発生する経路を整理して報告する（実装の変更はしない）
- [ ] コード読解: api/harness_routes.py と cli/harness_cli.py の機能差を一覧化して報告する（実装の変更はしない）

## 手動用（書く系・ask承認込み・ふくけい付き添いで消化）

- [ ] テスト作成: バックログP2「CLI結合レベルのask配線+deny_patterns自動テスト実装」のうちdeny_patterns CLI結合テストを1件実装する
- [ ] docs修正: docs/開発ガイド.md と harness_cli --help の不整合のうち、CC報告で確定した分を修正する
- 手動用テンプレート（実装着手前は下記を使わない・実課題が出来次第追加）:
- [ ] docs修正: 変更履歴と実装のズレが次回CC報告で確定した分を1件修正する
- [ ] テスト作成: watchdog_stop 経路のE2Eテスト（履歴50run同質化を模したfixture）を1件実装する
