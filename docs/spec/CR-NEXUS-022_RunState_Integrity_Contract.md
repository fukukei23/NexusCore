# CR-NEXUS-022: RunState 完全性・改ざん検知契約定義

（Integrity / Tamper Detection / Trust Boundary Contract）

SRS Traceability

Related SRS: docs/srs/NEXUSCORE_SRS.md

This CR satisfies: FR-1; FR-6; FR-7; NFR-1; NFR-8

## 1. 概要（Overview）

本 CR は、RunState（CR-020）について
**完全性（Integrity）・改ざん検知（Tamper Detection）・信頼境界（Trust Boundary）**を
設計契約（Contract）として定義する。

目的：

- RunState が どこまで信頼できるデータかを明文化する
- CLI / API / Web / Worker / Storage 間で
  「信頼してよい」「検証すべき」境界を固定する
- 将来の API 公開・SaaS 化・マルチ Runner 環境における
  RunState 改ざんリスクを設計段階で封じる

本 CR は 契約定義のみであり、

- 暗号アルゴリズムの確定
- 署名鍵管理
- 実装コード変更

は要求しない。

## 2. 背景（Background）

これまでに以下が成立している。

- CR-017：RunState は Resume の唯一の SOT
- CR-019：Status 遷移は Runner 正本
- CR-020：RunState JSON スキーマ契約
- CR-021：RunState I/O 契約（外部投影）

この構造では、RunState が以下の経路を通る可能性がある。

- ファイルシステム保存
- API 経由取得・更新
- Web UI 参照
- 将来の外部連携

つまり、RunState は攻撃・誤操作・不整合の対象になり得る。

よって、

- 「壊れた RunState をどう扱うか」
- 「誰が RunState を信頼してよいか」

を契約として固定する必要がある。

## 3. 基本原則（Integrity Principles）

- RunState は 不変データではない（更新される）
- ただし 正当な更新経路は Runner に限定される
- RunState の完全性検証は Runner の責務
- Orchestrator は RunState の完全性を検証しない
- 完全性検証に失敗した RunState は 再開正本にならない

## 4. Trust Boundary（信頼境界）の定義

### 4.1 信頼される境界（Trusted）

以下は 信頼境界内とする。

- Runner プロセス内部
- Runner が生成・更新した直後の RunState
- Runner が検証済みと判断した RunState

### 4.2 非信頼境界（Untrusted）

以下は 信頼できない入力として扱う。

- 外部ストレージから読み込んだ RunState
- API 経由で渡された RunState
- 手動編集された RunState
- Web UI から送信された RunState データ

→ これらは 必ず検証対象。

## 5. 完全性検証モデル（Conceptual）

### 5.1 検証対象

完全性検証の対象は以下。

- RunState の 構造（schema_version / 必須フィールド）
- RunState の 内容（status × next_phase 整合など）
- RunState の 改ざん有無（検知）

### 5.2 改ざん検知の抽象モデル

本 CR は、以下の 抽象モデルのみを契約とする。

- RunState に対して 検証可能な完全性指標を付与できる
- Runner はそれを用いて 検証成功／失敗を判定できる

方式は以下のいずれでもよい（例示）

- ハッシュ（checksum）
- HMAC
- デジタル署名

※ 具体方式・フィールド名は本 CR では固定しない。

## 6. RunState への影響（Schema との関係）

### 6.1 スキーマ拡張の扱い

完全性情報は、CR-020 の以下いずれかに格納され得る。

- metadata 内の拡張フィールド
- 将来の MINOR schema_version による追加フィールド

本 CR は 必須フィールド追加を要求しない。

### 6.2 検証失敗時の扱い

完全性検証に失敗した RunState は、以下として扱う。

- Resume 正本として使用してはならない
- status を直接更新してはならない
- Runner は FAILED または ABORTED 相当として扱う判断を行い得る

※ 実際の status 遷移は CR-019 に従う。

## 7. Explainability との整合（CR-018）

完全性検証失敗は 説明対象の失敗理由になり得る。

失敗分類例（参考）

- STATE_INVALID
- STATE_TAMPERED

分類語彙の確定は本 CR の責務外。

## 8. 禁止事項（Hard Constraints）

- Orchestrator が RunState の完全性を検証すること
- 検証されていない RunState を Resume 正本として扱うこと
- 外部入力 RunState を「信頼済み」と仮定すること
- 完全性検証を UI / API クライアント側に委ねること

## 9. 非目標（Explicit Non-Goals）

本 CR は以下を目的としない。

- 暗号アルゴリズム選定
- 鍵管理・ローテーション設計
- 性能最適化
- 監査ログの形式定義

## 10. 非機能要件（NFR）

- 完全性検証は Runner 内で完結すること
- 検証失敗は 黙って無視されないこと
- core/orchestrator.py 無変更を前提とする

## 11. リスク・制約

- 検証を導入しない実装では改ざん検知は保証されない
- ただし 契約があることで将来導入が破壊的にならない

## 12. 完了条件（Done Definition）

- RunState の信頼境界が明文化されている
- 完全性・改ざん検知の責務主体（Runner）が固定されている
- 検証失敗時の扱いが契約として定義されている
- CR-016〜021 と矛盾しない

## 13. 備考

本 CR により、NexusCore は

- 「状態を保存できる」
- 「状態を再開できる」
- 「状態を信頼できる／できないを判断できる」

という 商用・API・監査耐性の最終要件を満たす。

---

## Cursor に対する指示書（CR-NEXUS-022 用）

以下を そのまま Cursor に貼り付けて使用してください。

#project: NexusCore

Task:
docs/spec/CR-NEXUS-022_RunState_Integrity_Contract.md を新規追加する（docs-only）。

Scope:
- RunState 完全性・改ざん検知・信頼境界の契約定義のみ
- 実装コードには一切触れない

Rules:
- docs/spec/ 配下に配置
- CR タイトル・章立て・番号は変更しない
- 冒頭に以下の SRS Traceability を必ず含める

SRS Traceability:
- Related SRS: docs/srs/NEXUSCORE_SRS.md
- This CR satisfies: FR-1; FR-6; FR-7; NFR-1; NFR-8

Constraints:
- Runner を完全性検証の正本にする
- Orchestrator に検証責務を持たせない
- 暗号方式・鍵管理は未確定とする
- RunState スキーマは CR-NEXUS-020 を前提とする
- TODO や実装提案を追加しない
- core/orchestrator.py 無変更前提

Acceptance:
- Trust Boundary が明文化されている
- 完全性検証の責務主体が明示されている
- 検証失敗時の扱いが契約化されている
- CR-016〜021 と整合している


