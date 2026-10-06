# harness 題庫（dogfooding定題プール・v4仕様）

> v4設計正典: obsidian-ssot `00_SYSTEM/マルチLLMレビュー/2026-09-09_ハーネス計測段階拡張レビュー/revised_proposal.md`「r3 統合 — パラメータ確定版 v4」
> 運用: ラッパー `scripts/run_harness_task.py` が未消化お題をカテゴリ均等化強制で抽出・実行後に `[x]` 化（原子的更新）
> お題は**実際の未解決小課題から作る**（v4要件・人工的な空タスク禁止）。消化したお題は `[x]` になるが、行は残す（実績として保持・シードスクリプトで補充）

## 無人用（読む系）

- [x] コード読解: tests/harness/ 配下でカバレッジが相対的に低い領域を特定し、未テストの分岐トップ3を列挙して報告する（実装の変更はしない）
- [x] エラー診断: harness全体テストで出る20件のwarningを分類し、修正優先度付きで報告する（修正はしない）
- [x] 設定・docs生成: tool_policy.yaml の deny_patterns の網羅性を評価し、防御漏れ候補を報告する（policy変更はしない）
- [x] コード読解: loop.py の state.save() 呼び出し経路を全て列挙し、保存漏れシナリオ候補を報告する（実装の変更はしない）
- [x] 設定・docs生成: docs/開発ガイド.md と harness_cli --help の不整合を列挙して報告する（修正はしない）
- [x] エラー診断: run_state の quarantine ファイルが発生する経路を整理して報告する（実装の変更はしない）
- [x] コード読解: api/harness_routes.py と cli/harness_cli.py の機能差を一覧化して報告する（実装の変更はしない）

<!-- 2026-09-19 補充（残1題→枯渇直前・pool_low警告発火のため9題追加）。
     v4要件どおり実在の未解決小課題から作成。トークン爆発（2026-09-11〜18に
     45万トークン級が8run連続）の再発抑制として、対象ファイルを明示し
     探索範囲を限定する書き方に統一した。 -->
- [x] コード読解: src/nexuscore/harness/ask.py の AskSession が受け取る store 引数の使用箇所を調べ、ask履歴のべき等記録が未結線であること（docstring記載）の裏取りと、結線するなら必要な変更点を報告する（実装の変更はしない）
- [x] コード読解: src/nexuscore/llm/_routed_llm.py を読み、RoutedLLM が complete_with_tools を持たないことで harness から使えない構造を、必要なメソッドと委譲先の観点で整理して報告する（実装の変更はしない）
- [x] コード読解: src/nexuscore/harness/circuit_breaker.py の状態遷移（CLOSED/OPEN/HALF_OPEN）を、遷移を起こすメソッドと条件の対応表にして報告する（実装の変更はしない）
- [x] エラー診断: src/nexuscore/harness/tool_gate.py を読み、policy ファイル不在・空・不正YAML の3ケースで fail-closed が成立するかを経路ごとに判定して報告する（実装の変更はしない）
- [x] エラー診断: src/nexuscore/harness/run_state.py の save/load を読み、チェックサム不一致で quarantine に落ちる条件を列挙し、正常な最新stateを誤って隔離しうる経路を報告する（実装の変更はしない）
- [x] エラー診断: scripts/collect_harness_metrics.py を読み、ask応答時間p95が常にnullになる原因箇所を特定して報告する（実装の変更はしない）
- [x] 設定・docs生成: docs/adr/ADR-002-harness-ui-stack.md の決定内容と api/harness_routes.py の実装の一致・不一致を項目ごとに照合して報告する（修正はしない）
- [x] 設定・docs生成: src/nexuscore/harness/tools/write.py と exec.py のdocstringに書かれた安全策を抽出し、tool_policy.yaml の設定と対応づけて報告する（設定変更はしない）
- [x] 設定・docs生成: src/nexuscore/harness/capability.py を読み、capability登録が必要なプロバイダ一覧と現在の登録状況の差分を報告する（実装の変更はしない）

- [ ] コード読解: src/nexuscore/agents/ 配下の12エージェント（BaseAgent継承）の継承構造と、各エージェントがoverrideしているフック（pre/post/should_run等）の対応表を報告する（実装の変更はしない）
- [ ] コード読解: src/nexuscore/core/ のジョブ状態機械（pending/running/done/failed/cancelled）の遷移を起こすメソッドと、各状態が許容する操作の対応表を報告する（実装の変更はしない）
- [ ] コード読解: src/nexuscore/llm/llm_profiles.py の9プロファイル定義と、task_model_map.py のタスク→モデル割当の対応関係を、フォールバックチェーン付きで一覧化して報告する（実装の変更はしない）
- [ ] エラー診断: src/nexuscore/npe/ の予算管理（monthly_tokens）と消費ログの集計経路を追い、消費ログ欠落が起きる可能性がある箇所を列挙して報告する（修正はしない）
- [ ] エラー診断: src/nexuscore/api/ のRESTエンドポイント定義（harness_routes除く）で、リクエストバリデーション失敗時に返るエラー形式がFastAPI標準と揃っていないものを特定して報告する（修正はしない）
- [ ] エラー診断: src/nexuscore/webapp/ のFlask SaaSアプリで、CSRF保護・CORS設定・認証必須ページの3観点がルートごとにどう適用されているかを表にして報告する（修正はしない）
- [ ] コード読解: src/nexuscore/utils/ 配下のユーティリティが使われている全箇所（grep）を列挙し、再利用機会があるのに独自実装になっている候補を報告する（リファクタ提案はしない）
- [ ] 設定・docs生成: docs/testing/testing_guide.md のテスト戦略と実装（tests/ 配下の構成・fixture方針・モック方針）の整合性を照合し、乖離箇所を報告する（修正はしない）
- [ ] 設定・docs生成: docs/setup/development_setup.md の手順を README.md から参照した場合の動作整合性を確認し、矛盾・抜け落ちを報告する（修正はしない）
- [ ] 設定・docs生成: docs/architecture/ARCHITECTURE_CORE.md の図と実コード構造（src/nexuscore/ のディレクトリツリー）の乖離を列挙して報告する（修正はしない）
- [ ] エラー診断: pytest実行時のconftest.py 4ファイル（tests/、tests/agents/、tests/harness/、tests/integration/）のfixture衝突・session scope矛盾を洗い出し、報告する（修正はしない）
- [ ] コード読解: src/nexuscore/harness/agents/（あれば）と src/nexuscore/agents/ の役割分担を表にして報告する（実装の変更はしない）
- [ ] コード読解: .env.template に列挙された環境変数とコード側の os.environ.get 参照の差分（コード参照だが未記載、または.template記載だが参照なし）を列挙して報告する（修正はしない）
- [ ] 設定・docs生成: docs/変更履歴.md の直近30件と直近30コミットの対応関係にズレがあるかを突き合わせ、未記載コミット・コミット未記載の履歴変更を報告する（修正はしない）
- [ ] エラー診断: src/nexuscore/api/ のOpenAPI仕様（/api/docs）と実エンドポイントの不整合（schema欠落・response例と実装の差）を列挙して報告する（修正はしない）

## 手動用（書く系・ask承認込み・ふくけい付き添いで消化）

- [x] テスト作成: バックログP2「CLI結合レベルのask配線+deny_patterns自動テスト実装」のうちdeny_patterns CLI結合テストを1件実装する
- [x] docs修正: docs/開発ガイド.md と harness_cli --help の不整合のうち、CC報告で確定した分を修正する
- 手動用テンプレート（実装着手前は下記を使わない・実課題が出来次第追加）:
- [x] docs修正: 変更履歴と実装のズレが次回CC報告で確定した分を1件修正する
- [ ] テスト作成: watchdog_stop 経路のE2Eテスト（履歴50run同質化を模したfixture）を1件実装する
