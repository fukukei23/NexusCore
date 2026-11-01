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

- [x] コード読解: src/nexuscore/agents/ 配下の12エージェント（BaseAgent継承）の継承構造と、各エージェントがoverrideしているフック（pre/post/should_run等）の対応表を報告する（実装の変更はしない）
- [x] コード読解: src/nexuscore/core/ のジョブ状態機械（pending/running/done/failed/cancelled）の遷移を起こすメソッドと、各状態が許容する操作の対応表を報告する（実装の変更はしない）
- [x] コード読解: src/nexuscore/llm/llm_profiles.py の9プロファイル定義と、task_model_map.py のタスク→モデル割当の対応関係を、フォールバックチェーン付きで一覧化して報告する（実装の変更はしない）
- [x] エラー診断: src/nexuscore/npe/ の予算管理（monthly_tokens）と消費ログの集計経路を追い、消費ログ欠落が起きる可能性がある箇所を列挙して報告する（修正はしない）
- [x] エラー診断: src/nexuscore/api/ のRESTエンドポイント定義（harness_routes除く）で、リクエストバリデーション失敗時に返るエラー形式がFastAPI標準と揃っていないものを特定して報告する（修正はしない）
- [x] エラー診断: src/nexuscore/webapp/ のFlask SaaSアプリで、CSRF保護・CORS設定・認証必須ページの3観点がルートごとにどう適用されているかを表にして報告する（修正はしない）
- [x] コード読解: src/nexuscore/utils/ 配下のユーティリティが使われている全箇所（grep）を列挙し、再利用機会があるのに独自実装になっている候補を報告する（リファクタ提案はしない）
- [x] 設定・docs生成: docs/testing/testing_guide.md のテスト戦略と実装（tests/ 配下の構成・fixture方針・モック方針）の整合性を照合し、乖離箇所を報告する（修正はしない）
- [x] 設定・docs生成: docs/setup/development_setup.md の手順を README.md から参照した場合の動作整合性を確認し、矛盾・抜け落ちを報告する（修正はしない）
- [x] 設定・docs生成: docs/architecture/ARCHITECTURE_CORE.md の図と実コード構造（src/nexuscore/ のディレクトリツリー）の乖離を列挙して報告する（修正はしない）
- [x] エラー診断: pytest実行時のconftest.py 4ファイル（tests/、tests/agents/、tests/harness/、tests/integration/）のfixture衝突・session scope矛盾を洗い出し、報告する（修正はしない）
- [x] コード読解: src/nexuscore/harness/agents/（あれば）と src/nexuscore/agents/ の役割分担を表にして報告する（実装の変更はしない）
- [x] コード読解: .env.template に列挙された環境変数とコード側の os.environ.get 参照の差分（コード参照だが未記載、または.template記載だが参照なし）を列挙して報告する（修正はしない）
- [x] 設定・docs生成: docs/変更履歴.md の直近30件と直近30コミットの対応関係にズレがあるかを突き合わせ、未記載コミット・コミット未記載の履歴変更を報告する（修正はしない）
- [x] エラー診断: src/nexuscore/api/ のOpenAPI仕様（/api/docs）と実エンドポイントの不整合（schema欠落・response例と実装の差）を列挙して報告する（修正はしない）

<!-- 2026-11-01 補充（無人用0題→10-25〜10-31に7晩連続STOP・10-06と同型の再発）。
     v4要件どおり実在の未解決小課題から作成。2026-09-19補充と同様、
     対象ファイルを明示し探索範囲を限定する書き方に統一。 -->
- [ ] コード読解: src/nexuscore/llm/task_model_map.py のタスク→モデル割当と src/nexuscore/llm/llm_profiles.py の実providers定義を突合し、存在しないprovider参照・フォールバック切れの候補を報告する（実装の変更はしない）
- [ ] コード読解: src/nexuscore/harness/circuit_breaker.py の HALF_OPEN→CLOSED/OPEN の再遷移条件のテストが tests/harness/ に存在するかを確認し、未テスト遷移を列挙して報告する（実装の変更はしない）
- [ ] コード読解: src/nexuscore/utils/json_sanitizer.py の直近修復（コミット d12fe36d・15471055）で追加された分岐のうち tests 配下で未カバーのものを列挙して報告する（実装の変更はしない）
- [ ] コード読解: 環境変数 NEXUS_REVIEW_MODE の全参照箇所を列挙し、default=multi への変更（コミット 6fba25d3）の影響範囲（呼び出し経路・.env.template・docs記載の有無）を報告する（実装の変更はしない）
- [ ] コード読解: multi-LLM consensus review 配線（コミット 188a8e66）の呼び出し経路を追い、tests/ 配下でどの分岐が未テストかを列挙して報告する（実装の変更はしない）
- [ ] コード読解: src/nexuscore/harness/tool_gate.py が tool_policy.yaml の各 allow/deny パターンをどの判定関数で消費しているか対応表を作り、policyに書かれても消費されない（実効性のない）パターンを報告する（設定・実装とも変更しない）
- [ ] エラー診断: artifacts/harness/metrics_history.jsonl の直近60runを集計し、abort_reason=limits（soft_token_limit超過）がどのカテゴリ・トークン帯に集中するかを報告する（実装の変更はしない）
- [ ] エラー診断: artifacts/harness/.notify.fail の記録（2026-09-11〜18の403連発）と現行 notify_failure の実装（scripts/run_harness_task.py のUser-Agent明示）を突合し、再発防止策が現コードで成立しているかを根拠付きで報告する（実装の変更はしない）
- [ ] エラー診断: pytest全体実行で出る warning を分類し、2026-10上旬の前回分類との差分（新規warning）を修正優先度付きで報告する（修正はしない）
- [ ] エラー診断: src/nexuscore/npe/ の消費ログ（monthly_tokens記録先）について、ファイル肥大化・ローテーション不在の有無を調査し、90日運用でのディスク増加見積りを報告する（実装の変更はしない）
- [ ] エラー診断: src/nexuscore/api/ のミドルウェア適用順序（CORS・認証・レート制限）を抽出し、保護漏れの可能性があるルートを列挙して報告する（修正はしない）
- [ ] 設定・docs生成: docs/変更履歴.md と直近30コミット（2026-10-08以降のエントリ不在含む）を突合し、未記載コミット・記載漏れエントリを一覧化して報告する（修正はしない）
- [ ] 設定・docs生成: docs/adr/ 配下の全ADRと現状実装の一致・不一致を項目ごとに照合し、未実装または乖離しているADRを列挙して報告する（修正はしない）
- [ ] 設定・docs生成: docs/harness_題庫.md のヘッダ記載「シードスクリプトで補充」の実体（scripts/ 配下にseedスクリプトが存在するか）を確認し、記載が誤りなら訂正案を、正しいなら所在と使い方を報告する（修正はしない）
- [ ] 設定・docs生成: README.md のコマンド・手順と現在の CLI 実体（main_cli.py・harness_cli --help・Makefile）の差分を列挙し、陳腐化している記述を報告する（修正はしない）

## 手動用（書く系・ask承認込み・ふくけい付き添いで消化）

- [x] テスト作成: バックログP2「CLI結合レベルのask配線+deny_patterns自動テスト実装」のうちdeny_patterns CLI結合テストを1件実装する
- [x] docs修正: docs/開発ガイド.md と harness_cli --help の不整合のうち、CC報告で確定した分を修正する
- 手動用テンプレート（実装着手前は下記を使わない・実課題が出来次第追加）:
- [x] docs修正: 変更履歴と実装のズレが次回CC報告で確定した分を1件修正する
- [ ] テスト作成: watchdog_stop 経路のE2Eテスト（履歴50run同質化を模したfixture）を1件実装する
