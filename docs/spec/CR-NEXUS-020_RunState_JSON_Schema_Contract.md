# CR-NEXUS-020: RunState JSON スキーマ契約定義

（Field / Optionality / Versioning Contract）

SRS Traceability

Related SRS: docs/srs/NEXUSCORE_SRS.md

This CR satisfies: FR-1; FR-4; FR-5; NFR-1; NFR-6

## 1. 概要（Overview）

本 CR は、Pause / Resume のために永続化される **RunState（JSON）**について、
**フィールド定義（Field）／必須・任意（Optionality）／バージョニング（Versioning）**を
「スキーマ契約（Schema Contract）」として定義する。

目的：

- RunState を API / Worker / CLI / 監査で共有できる 安定した永続契約にする
- CR-NEXUS-019 の Status 状態機械を RunState に確実にマッピングする
- CR-NEXUS-017 の再構築モデル（RunState SOT）における 復元可能性の境界を固定する
- CR-NEXUS-018 の Explainability（失敗説明）に必要な最小情報を保持する

本 CR は スキーマの定義のみであり、
パーサ・バリデータ・マイグレーションの実装は要求しない。

## 2. 背景（Background）

- CR-NEXUS-015：RunState 永続化（JSON）
- CR-NEXUS-016：RunState 運用（TTL 等）
- CR-NEXUS-017：Resume は再構築（RunState が SOT）
- CR-NEXUS-018：Resume 失敗説明（Runner 正本）
- CR-NEXUS-019：Status / State Machine の契約化

現状、RunState は動作しているが、以下が契約として未固定。

- JSON のフィールド集合
- 必須／任意
- 破壊的変更を避けるためのバージョニング規約

これを固定しないまま API 化すると、永続互換性で破綻する。

## 3. 基本原則（Schema Principles）

- RunState は 永続契約である（短命キャッシュではない）
- 正本は Runner（RunState の生成・更新主体）
- 後方互換性を優先する（既存 run_id を壊さない）
- フィールド追加は許容するが、削除・意味変更は破壊的変更とみなす
- Unknown field は無視可能であることが望ましい（Forward compatibility）

## 4. 用語（Terms）

- Schema Version: RunState の JSON 構造の版
- Required: 存在しない場合、RunState は無効と判定され得る
- Optional: 省略可。存在する場合のみ利用
- Compatibility: 旧版 RunState を新 Runner が扱える性質

## 5. RunState JSON：トップレベル契約

### 5.1 トップレベル必須フィールド（Required）

| Field | Type | Meaning |
|---|---|---|
| schema_version | string | スキーマ版（例: "1.0"） |
| run_id | string | 一意・非意味的識別子（CR-016） |
| status | string | CR-019 の Status 語彙 |
| authority_level | string | human / partial / full |
| next_phase | string or null | 再開点（PAUSED 時は必須、他は null 可） |
| updated_at | string (ISO 8601) | 最終更新時刻（TTL 判定の基準） |

必須制約：

- status == "PAUSED" の場合、next_phase は null ではならない
- status in {"SUCCEEDED","FAILED","ABORTED","EXPIRED"} の場合、next_phase は null であることが望ましい

### 5.2 トップレベル任意フィールド（Optional）

| Field | Type | Meaning |
|---|---|---|
| created_at | string (ISO 8601) | 作成時刻 |
| stop_reason | string | 停止理由（例: AUTHORITY_GATE, EXTERNAL_STOP） |
| last_error | object | 失敗説明の最小情報（CR-018） |
| context_snapshot | object | 再構築に必要な最小コンテキスト（CR-015/017） |
| history | array | 状態遷移の履歴（監査目的、将来用） |
| metadata | object | 拡張情報（将来互換用の入れ物） |

## 6. last_error（Explainability Minimal Record）

### 6.1 目的

FAILED の場合に、Runner が説明（What/Why/Next Action）を生成するための最小情報。

### 6.2 形（推奨スキーマ）

last_error は以下を推奨する（任意フィールド）。

| Field | Type | Required | Meaning |
|---|---|---|---|
| code | string | yes | CR-018 の分類（STATE_INVALID 等） |
| message | string | yes | 短い説明（機械・人間両方を想定） |
| phase | string | no | 失敗した phase（わかる場合） |
| occurred_at | string (ISO 8601) | no | 発生時刻 |
| next_action | string | no | 推奨行動（再試行/破棄/再実行） |

制約：

- status == "FAILED" の場合、last_error.code と last_error.message を 保持することが望ましい（必須化はしない）

## 7. context_snapshot（Reconstruction Input）

### 7.1 原則

RunState の SOT を維持するため、Resume に必要な情報は context_snapshot に閉じるのが望ましい。

ただし本 CR は内容の完全標準化を行わず、「入れ物」を契約化する。

### 7.2 形（最小）

context_snapshot は object とし、Runner が必要に応じて格納する。
内部キーは将来拡張し得るため、unknown key を許容する。

## 8. history（Audit Trail, Optional）

history は将来の監査・可視化のための任意フィールド。

各要素は以下を推奨。

| Field | Type | Meaning |
|---|---|---|
| at | string (ISO 8601) | 記録時刻 |
| from | string | 旧 status |
| event | string | event 名 |
| to | string | 新 status |
| note | string | 補足 |

## 9. バージョニング規約（Versioning）

### 9.1 方式

schema_version は "MAJOR.MINOR" 形式の文字列とする（例: "1.0"）

### 9.2 互換性ルール

#### MINOR 変更（例: 1.0 → 1.1）

- フィールド追加のみ
- 既存フィールドの意味変更なし
- 旧 Runner でも「無視して動く」ことが望ましい

#### MAJOR 変更（例: 1.x → 2.0）

- 必須フィールドの追加、削除、意味変更
- 破壊的変更
- マイグレーション方針は別 CR とする

### 9.3 Unknown field の扱い（Forward compatibility）

- Runner は unknown field を無視できることが望ましい
- Runner は unknown field を保持したまま更新できることが望ましい（Read-Modify-Write）

## 10. 非目標（Explicit Non-Goals）

本 CR は以下を目的としない。

- JSON Schema（Draft）としての完全形式化
- マイグレーション手順・ツール
- 署名・暗号化・改ざん検知
- 具体的な保存パス規約（CR-015 に従う）

## 11. 非機能要件（NFR）

- 既存 RunState（CR-015 実装）と整合し得ること
- RunState は監査・説明に耐える最小情報を保持できること
- core/orchestrator.py は無変更であること

## 12. リスク・制約

- history / context_snapshot は任意であるため、運用・監査の粒度は実装に依存する
- schema_version 運用を誤ると互換性が破綻する（運用ルールが重要）

## 13. 完了条件（Done Definition）

- RunState の必須／任意フィールドが契約化されている
- status と next_phase の整合制約が明文化されている
- schema_version の互換ルールが明文化されている
- CR-NEXUS-015〜019 と矛盾しない

---

## Cursor に対する指示書（CR-NEXUS-020 用）

以下を そのまま Cursor に貼り付けて使用してください。

#project: NexusCore

Task:
docs/spec/CR-NEXUS-020_RunState_JSON_Schema_Contract.md を新規追加する（docs-only）。

Scope:
- スキーマ契約（Field / Optionality / Versioning）の定義のみ
- 実装コードには一切触れない

Rules:
- docs/spec/ 配下に配置
- CR タイトル・章立て・番号は変更しない
- 冒頭に以下の SRS Traceability を必ず含める

SRS Traceability:
- Related SRS: docs/srs/NEXUSCORE_SRS.md
- This CR satisfies: FR-1; FR-4; FR-5; NFR-1; NFR-6

Constraints:
- Runner が RunState の生成・更新主体（正本）であることを明記
- status 語彙は CR-NEXUS-019 と一致させる
- Explainability は CR-NEXUS-018 と整合させる
- Versioning ルール（MAJOR/MINOR）を明記
- TODO や実装提案は追加しない
- core/orchestrator.py 無変更を前提とする

Acceptance:
- 必須/任意フィールドが表で定義されている
- status と next_phase の整合制約が明文化されている
- schema_version の互換ルールが明文化されている
- CR-015〜019 と整合している


