# CR-NEXUS-019: Run / Resume ステータスモデル定義

（State Machine Contract）

SRS Traceability

Related SRS: docs/srs/NEXUSCORE_SRS.md

This CR satisfies: FR-1; FR-4; NFR-1; NFR-5

## 1. 概要（Overview）

本 CR は、NexusCore の Run / Pause / Resume における
**成否ステータス（Status）と状態遷移（State Machine）**を「契約」として定義する。

目的は以下。

- 監査・運用・API化に耐える **共通語彙（ステータス）**の確立
- Resume 失敗時の説明責務（CR-NEXUS-018）と整合した 失敗の表現方式の固定
- RunState 永続化（CR-NEXUS-015）と整合した 状態遷移の正本の確立

本 CR は 状態モデルの定義のみであり、実装変更・ログ形式・UI 表示の統一は要求しない。

## 2. 背景（Background）

- CR-NEXUS-015：Pause / Resume 実装（RunState 永続化）
- CR-NEXUS-016：UX / 運用契約
- CR-NEXUS-017：Resume は Orchestrator 再構築（RunState SOT）
- CR-NEXUS-018：Resume 失敗時の説明責務（Runner 正本）

しかし、現状は以下が暗黙。

- Run の「成功」「失敗」「中断」「一時停止」の表現が一貫していない
- Resume 失敗が「例外」なのか「状態」なのか曖昧
- 後続の API / Worker 管理に必要な状態語彙が未固定

よって、本 CR で 状態の正本（Runner）と状態語彙を固定する。

## 3. 基本原則（State Machine Principles）

- 状態（Status）の正本は Runner とする
- Orchestrator は状態の正本にならない（内部例外は事実だが、状態契約ではない）
- RunState は状態の永続表現であり、Runner が更新する
- Resume は「イベント」であり、状態遷移を引き起こす

## 4. 用語（Terms）

- Status: Run の外部観測可能な状態（契約語彙）
- Event: 状態遷移を引き起こす入力（例: pause 요청, resume 요청）
- RunState: 永続化される状態表現（JSON）
- Terminal Status: 終端状態（以降の遷移は原則なし）

## 5. ステータス語彙（Contract Status Set）

本 CR は、Run / Resume の状態を以下に限定する。

### 5.1 Non-terminal（非終端）

#### CREATED

run_id が生成され RunState が作成されたが、実行は未開始

#### RUNNING

実行中

#### PAUSED

フェーズ境界で停止し、再開可能

#### RESUMING

Resume 要求を受け、再構築・再開処理中

#### STOPPED

外部 stop 指示により停止（再開の扱いは別契約：原則再開非保証）

### 5.2 Terminal（終端）

#### SUCCEEDED

正常完了

#### FAILED

失敗して終了（原因分類は CR-NEXUS-018 を参照）

#### ABORTED

運用判断で破棄（RunState を再利用しない意思決定を含む）

#### EXPIRED

TTL 超過により再開非保証となり、運用上破棄扱い

## 6. 状態遷移（State Transitions）

### 6.1 遷移表（契約）

| From | Event | To | Notes |
|---|---|---|---|
| CREATED | start_run | RUNNING | 新規 Run 開始 |
| RUNNING | pause_boundary | PAUSED | フェーズ境界で一時停止 |
| RUNNING | stop_requested | STOPPED | 外部 stop 指示 |
| RUNNING | completed | SUCCEEDED | 正常完了 |
| RUNNING | error | FAILED | 実行失敗 |
| PAUSED | resume_requested | RESUMING | Resume 開始 |
| RESUMING | resume_ok | RUNNING | 再開成功 |
| RESUMING | resume_failed | FAILED | Resume 失敗（説明は CR-018） |
| PAUSED | abort | ABORTED | 破棄 |
| STOPPED | abort | ABORTED | 破棄 |
| PAUSED | ttl_expired | EXPIRED | 運用上の破棄扱い |
| EXPIRED | (any) | (no guarantee) | 本 CR では遷移保証しない |

### 6.2 禁止遷移（明示）

- SUCCEEDED / FAILED / ABORTED / EXPIRED から RUNNING への遷移を正規ルートとして認めない
- Orchestrator から直接 Status を更新してはならない（正本は Runner）

## 7. RunState へのマッピング（Persistent Representation）

RunState は最低限以下のフィールドを持つことが望ましい。

- run_id
- status（上記 Contract Status Set）
- authority_level
- next_phase（PAUSED の場合は必須）
- updated_at（TTL 判定用）
- last_error（FAILED の場合は推奨：分類コード＋短文）

※ フィールド追加は別 CR で扱う。ここでは契約上の期待値のみを定義する。

## 8. Explainability（CR-NEXUS-018 との整合）

- FAILED には必ず「Why（分類）」が紐づくことが望ましい
- Runner は FAILED 遷移時に What / Why / Next Action を生成可能であることが望ましい
- ただしログ形式や出力形式は本 CR の責務外

## 9. 非目標（Explicit Non-Goals）

本 CR は以下を目的としない。

- 具体的なログスキーマ定義
- CLI / UI 表示の統一
- 自動リトライ、自己修復ポリシー
- 分散実行の整合性プロトコル

## 10. 非機能要件（NFR）

- core/orchestrator.py は無変更であること
- 既存 Pause / Resume 実装（CR-015）と矛盾しないこと
- 状態遷移が監査可能であること（run_id 単位）

## 11. リスク・制約

- STOPPED と ABORTED の境界は運用設計に依存する
- EXPIRED は現状 docs-only であり、実装は将来 CR に委ねる

## 12. 完了条件（Done Definition）

- Run / Resume の Status 語彙が固定されている
- 状態遷移表が定義されている
- Runner が正本であることが明文化されている
- CR-NEXUS-015〜018 と整合している

## 13. 備考

本 CR は Contract Layer のうち、
Run の状態語彙と監査可能性を固定する。

これにより API 化・Worker 管理・ダッシュボード可視化が
「状態語彙のブレなし」で実装可能になる。

---

## Cursor に対する指示書（CR-NEXUS-019 用）

以下を そのまま Cursor に貼り付けて使用してください。

#project: NexusCore

Task:
CR-NEXUS-019_Run_Resume_Status_State_Machine_Contract.md を新規追加する。

Scope:
- docs-only（設計CR）の追加のみ
- 実装コードには一切触れない

Rules:
- docs/spec/ 配下に配置すること
- CR タイトル・章立て・番号は変更しない
- 冒頭に以下の SRS Traceability を必ず含める

SRS Traceability:
- Related SRS: docs/srs/NEXUSCORE_SRS.md
- This CR satisfies: FR-1; FR-4; NFR-1; NFR-5

Constraints:
- Runner 正本（status 更新主体）を必ず明記する
- Orchestrator は status 正本にならないことを明記する
- TODO や実装提案は追加しない
- core/orchestrator.py 無変更を前提とする

Acceptance:
- Status 語彙が列挙されている（Non-terminal / Terminal）
- 状態遷移表が明確に定義されている
- CR-NEXUS-015〜018 と整合している


