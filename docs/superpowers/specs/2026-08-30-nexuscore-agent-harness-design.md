# NexusCore エージェントハーネス設計（design spec）

- 日付: 2026-08-30
- ステータス: 設計確定（実装未着手・Phase 0から開始）
- レビュー: multi-llm-review triple（MiniMax+Gemini+OpenRouter）5ラウンド・計78件の指摘を統合
  - 経緯フル: `obsidian-ssot/00_SYSTEM/マルチLLMレビュー/2026-08-30_NexusCoreハーネス方式選定/`
- 関連: `01_DECISIONS/NexusCore/2026-04-22_自律ループ試行.md`（過去事故・本設計の直接の動機）

## 1. 背景・目的

NexusCore（Python製LLMアプリ・プロバイダアダプタ11種・エージェント12種・テスト約5,000件緑）に、Claude Codeのような**エージェントハーネス（tool callingループ＋権限ゲート＋サーキットブレーカ）を自前実装**する。

目的は3つ（排他でない・順序付き）:
1. **ポートフォリオ実績**（品質基準は「公開可能品質」で統一）
2. **NexusCore開発の自動化**（dogfooding）
3. **プロダクト機能**

直接の動機: 2026-04-22 の自律ループ試行で「429で23分中断→手動リセット→全作業消失」が発生。本設計はこの事故の再発防止を最優先要件とする。

## 2. 確定要件（brainstorming 6問で決定）

| 項目 | 決定 |
|---|---|
| スコープ | 大spec（本spec 1本・実装はPhase分解） |
| 品質基準 | 公開可能品質（テスト・文書・設計） |
| LLM対応 | 3形式（OpenAI互換/Anthropic/Gemini）＝9プロバイダ実質カバー |
| 道具追加順 | 読む→書く→撃つ |
| インターフェース | コアはライブラリ・Web UI は後半Phase |
| 完了判定 | 数値基準＋デモシナリオ両方 |

## 3. 方式選定: D案（フォーマット別Mixin共用方式）

4案比較（A個別拡張/B独立レイヤー/C公式SDK/D Mixin）のL2マトリクスでD案が51点で選定。

- tool calling処理を **Mixinとして1回だけ実装**し、実測で確定した**4クラス**（`OpenAICompatLLM`(5種継承)・`OpenAILLM`・`AnthropicLLM`・`GeminiLLM`）へMix-in
- **差分フックを最初から設計に含める**: `_adapt_tool_choice` / `_adapt_tool_result`（プロバイダ固有の差を吸収・Mixinは共通処理のみ。ラウンド1レビュー条項5）
- メソッドは `complete_with_tools()`（既存 `complete()` と別名・**既存メソッドの上書きは絶対にしない**）
- 既存12エージェント・既存テストへの影響は構造的にゼロ（既存経路を触らない）
- `LocalLLM` はダミースタブのため本番対象外（実測V3）・テスト用のtool_callダミー応答モードのみ追加
- **fail-fast条項（Phase 0・数値固定）**: ①1クラスでも既存メソッド上書きが必要なら撤退 ②リトライ実装差が3箇所以上なら撤退 → **A案（個別拡張）へフォールバック**

### 確定した3設計フォーク

1. **配置**: 新設 `src/nexuscore/harness/`（agents/=役割エージェント・orchestrator/=CR承認フローと責務分離・実測: orchestratorの消費者はCR表示系のみ）
2. **メッセージ形式**: 内部履歴=OpenAI形式統一・**tool call内部表現=正規化dict `{name, args: dict, id}`**（履歴と分離・OpenAI形式書出し時に固定ルールで文字列化）
3. **Mixin適用**: 直接Mix-in（factoryラップは委譲二重実装のため却下）+**provider単位のcapability table**（クラス一括判定は粗い・`supports_tool_calling()` ガード+Protocol型）

## 4. 権限ゲート（ToolGate）

- `harness/tool_gate.py` を新規実装・**guard/policy_engine（CR粒度）の流用禁止**（束ね承認事故防止・共通型のみ参照）
- 設定: `tool_policy.yaml`（道具別+パスパターン）
- 既定: 読む系=allow / 書く系・撃つ系=ask / 禁止リスト（`.git`・`.env` 書込・`rm -rf`・`sudo`・`git push --force` 等）=deny
- 硬いルール: **道具1回ごと個別判定（束ね承認不可）**・**fail-closed（ポリシー破損時は全拒否）**・**askタイムアウト=deny**
- ask時: ループ一時停止+状態保存 → CLI確認（Phase 2実装）→ 承認で再開
- 全判定をrunイベントログ（JSONL）に記録

## 5. サーキットブレーカ（暴走止め）

### MVP層（Phase 1で実装）

- **4ハードリミット**: ステップ25回/実行10分/tool呼出40回/トークン500k（発火**前**チェック・80%で通知）
- **計測点2点**: LLM呼出直前+tool実行境界・いずれか超過で即abort
- **プロバイダ単位ブレーカ**: CLOSED→（60秒窓内429×3・タイムアウト連続）→OPEN→（Retry-After尊重・60秒超は待機せず即切替）→HALF_OPEN（通常リクエスト全拒否・プローブは**実モデルへの最小推論リクエスト**（models一覧は不使用・直近failure_signature反映）・3回中2回成功でCLOSED）
- **状態保存の原子的化**: temp書込→fsync→`os.replace`+ファイルロック（プロセス間）+多重起動ガード+スキーマバージョン+チェックサム・**破損時はquarantine（別名保存）+全拒否+緊急通知のみ・クリアは人手コマンド限定**
- **resume（再開）はPhase 1で必須実装+検証**（abort_reason 6分類: ユーザー中断/権限拒否/ブレーカOPEN/リトライ枯渇/致命的エラー/checkpoint失敗・2段階resume=理由提示→確認→実行）
- 退避: capability表参照でtool対応済みプロバイダへ切替（フォールバック深さ上限2回・切替先バケット残量20%未満は遅延・**tool必須タスクのテキスト専用への切替禁止**・全OPENならabort+通知）
- 通知: ログ+Discord+run_state要対応フラグ（次回起動時必ず提示）
- Retry-After解析: 厳格バリデーション（不正値→60秒・下限1秒・**上限クリップはしない**（要求時間より短い再送は絶対しない=BAN対策）・未指定は指数バックオフ+ジッタ・エッジケーステストCI必須）

### 強化層（Phase 5の実測データでGo/No-Go判断・現時点で実装約束なし）

3層トークン/レートソフトリミット・適応閾値+最小サンプル10・TTL付きcapability・動的resumeバジェット+resume回数上限3回・トークンバケット適応制御・Chaos/Property-basedテスト・通知3重化の完全版・並行実行時のトークン予約

## 6. Phase構成（成功基準付き）

| Phase | 内容 | 出口条件 |
|---|---|---|
| **0: fail-fast spike** | **計測はスクリプト化してファイル出力**（MRO/上書き要否/FACTORY位置/リトライ差分/5種のtools受付+echo往復）→ **判定は別セッション+ふくけい承認**。チェックリスト4〜6項目（観測コマンド紐付け・未記入なら着手不可） | 撤退基準に該当→A案へ切替 |
| **1: MVP**（読む系） | Mixin4クラス+capability table永続化+最小ループ+read tools3種+ToolGate（読む=allow・**他=deny**・fail-closed）+ブレーカMVP+**resume実装+検証**+abort 6分類+LocalLLMダミー（テスト専用） | Phase1テスト5件緑・resume検証合格 |
| **2: 書く系** | write/edit tools+ask確認フロー（CLI）+checkpoint+べき等記録 | ask必須経由テスト3件緑 |
| **3: 撃つ系** | run_command tool+禁止パターンdeny | deny実測テスト2件緑 |
| **4: Web UI** | タスク入力・ask承認画面・実行モニタ（**着手条件: UIスタック決定済**） | テスト2件緑 |
| **5: dogfooding** | NexusCore小Issue 1個を丸ごと消化+計測6項目（429頻度/ブレーカ遷移/ask応答時間/checkpoint失敗率/abort分布/トークン量）+**強化層Go/No-Go判定書** | 判定書提出 |

各Phase後に**実用チェックポイント**（実プロバイダ必須+本番ログ添付+**中断→復帰シナリオ1件**）:
- Phase 1後: SSOT内テキスト検索を読む系道具で実行
- Phase 2後: テストファイル1行修正をask承認込みで実行
- Phase 3後: pytest実行を撃つ系道具で実行

## 7. 成功基準（完了判定）

- **必須**: ①CLI版デモシナリオ完遂（実プロバイダ+権限ゲート込み・本番ログ添付）②新規テスト12件緑（Phase配分 5/3/2/2・Phase1着手時最低件数未達なら次Phase着手不可）③既存テスト非改変証明（git diff添付）④全体pytest緑 ⑤resume検証合格
- **成果目標**: Web UI版デモシナリオ完遂
- テストマトリクス: 単体（**Retry-After解析のエッジケース**を含む）+State machine（ブレーカ遷移）+事故パターン再現（429連発→切替→全OPEN→状態保存）をMVP層で必須

## 7.5. 用語の統一（G#1 critical対応）

- Phase 1の「**run_state保存**」= ループ全体の状態（履歴・リミット消化数・ブレーカ状態）の保存/再開。Phase 1で必須実装
- Phase 2の「**tool完了checkpoint**」= べき等記録用のtool単位スナップショット（C10）。**Phase 1のresumeはrun_state保存で実現でき、Phase 2のcheckpointに依存しない**（両者は別物・混同禁止）

## 8. リスクと既知の前提

- 過去事故（2026-04-22）: 一括進行→429→リセット→消失。本設計は resume・原子的保存・段階的チェックポイントで再発防止
- `OpenAICompatLLM` へのMix-inは5サブクラス（GLM/MiniMax/OpenRouter/DeepSeek/Moonshot）へ波及 — **Phase 0で各プロバイダのtools受付可否を実測し、provider単位のcapability tableに反映**（非対応でも他プロバイダは動く）
- Mixin/メッセージ変換の型揺れ（Gemini `functionCall` args=オブジェクト vs OpenAI=文字列JSON）→ 変換レイヤーに型正規化テスト必須（ネスト/無効JSON/深度超過/空を含むスイート）

## 9. 対象外（本specでは扱わない）

- 複数エージェント協調（planner/worker）・MCP経由のtool・サブエージェント並列（強化層以降で再評価）
- orchestrator/CR承認フローとの統合（再検討条件: harness から orchestrator 機能の呼出が必要になった時点）
- 同一セッション内マルチプロバイダ切替（発生したらメッセージ形式フォークをreopen）

## 10. 実装時に固定する詳細契約（round6 specレビュー・28件採用分）

Phase実装時に参照する詳細契約（ラウンド6で3機が指摘した曖昧箇所の確定値・実装着手前にここを正とする）:

| 項目 | 確定値 |
|---|---|
| Phase 0出力パス | `artifacts/phase0/<ISO8601>/` 配下に固定（CHECKLIST記入が完了条件・雛形をコミット） |
| 「既存メソッド上書き」の定義 | 子クラスでのインスタンスメソッド新規定義のみを「上書き」とカウント（`__init_subclass__`注入・Mixin自体の新メソッド追加は許容） |
| 撤退判定 | `artifacts/phase0/CRITERIA.md` に凍結・「リトライ実装差」=バックオフ戦略/Retry-After解析/最大試行回数の実装有無の差分を指す |
| capability tableスキーマ | `{provider_id, supports_tool_calling: bool, last_verified_at, schema_version}`・更新契機3系統（Phase 0バルク書込/Mixin初期化時/明示的refreshコマンド） |
| tool call id生成 | provider側idを優先保持・無ければMixin内でUUID v4補完・フォーマット `^[a-zA-Z0-9_-]{1,64}$` にサニタイズ |
| メッセージ変換のネスト深度上限 | 32階層・超過時はValueError→abort（abort_reason=致命的エラー） |
| バックオフ既定値 | base=2.0秒・max=300秒・full jitter（Retry-After未指定時） |
| ファイルロック | `fcntl.flock` に固定・動作環境はLinux（WSL含む）前提・Windows対応はPhase 5以降のバックログ |
| resume確認の主体 | CLI対話ユーザー・非対話モードは明示トークンopt-in時のみ無人resume可・**確認不在時のデフォルト=abort+状態保存（自動続行禁止）** |
| askタイムアウト後のフロー | deny結果をtool_resultとしてLLMへ返し継続を試みる・継続不能判断時はabort（abort_reason=権限拒否） |
| ask待ちの状態保存 | ask確認待ちもrun_stateに保存（プロセス再起動後もask状態から復帰） |
| プロバイダ切替順序 | `tool_policy.yaml` の `provider_priority` 配列で固定（ラウンドロビン/コスト最適化は強化層） |
| 切替時のLLMインスタンス | ループはステップ毎にcapabilityチェック→routerから取得し直す（インスタンスを保持し続けない） |
| 禁止リストの粒度 | MVPはグローバルdeny（粗い・安全側）・道具別コンテキスト考慮はPhase 3で精緻化 |
| 要対応フラグの解消 | `--ack-run-state <id>` の明示ACKのみ（自動ACK禁止・CLI起動時バナー+Web UIダッシュボードに表示） |
| Discord通知の管理 | Webhook URLは環境変数 `NEXUSCORE_DISCORD_WEBHOOK` のみ・設定ファイルに書かない・未設定時はログのみ |
| Phase 4着手条件 | UIスタック決定は**Phase 3完了時まで**（決定ADRをPhase 3の成果物に含める） |
| Phase 5のGo/No-Go | 計測6項目に参考閾値案を付記（最終閾値はdogfooding開始時に確定・判定書はテンプレ化し前Phase比を記載） |
| 実測V3の出典 | 2026-08-30の `src/nexuscore/llm/providers/local_provider.py` 実測（レビュー出力 `00_SYSTEM/マルチLLMレビュー/2026-08-30_NexusCoreハーネス方式選定/revised_proposal.md` 証跡3） |

## 11. レビュー履歴

- 設計レビュー5ラウンド（78件）+ spec本文レビュー1ラウンド（28件）= 計106件を統合
- 出典: `obsidian-ssot/00_SYSTEM/マルチLLMレビュー/2026-08-30_NexusCoreハーネス方式選定/`（review_log 6本・revised_proposal 6本）
