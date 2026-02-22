# CR-NEXUS-023: Multi-Runner / 同時 Resume / 競合整合性契約定義

（Concurrency / Locking / Consistency Contract）

SRS Traceability

Related SRS: docs/srs/NEXUSCORE_SRS.md

This CR satisfies: FR-1; FR-8; NFR-1; NFR-9

## 1. 概要（Overview）

本 CR は、NexusCore が 複数 Runner（Multi-Runner）環境で動作する場合における、

- 同一 run_id に対する 同時 Resume
- RunState の 競合更新
- ロック・排他制御の 責務と正本

を 契約（Contract）として定義する。

目的：

- 「どの Runner が正しいか」で揉めない設計にする
- 同じ Run を 2台の Runner が同時に再開する事故を制度的に防ぐ
- 分散・並列化を 安全に可能にする前提条件を固定する

本 CR は 設計契約のみであり、

- ロック実装方式（FS / DB / Redis 等）
- 分散アルゴリズム
- 性能最適化

は要求しない。

## 2. 背景（Background）

CR-NEXUS-017〜022 により、以下はすでに確立している。

- RunState は Resume の唯一の SOT（CR-017）
- RunState の完全性は Runner が検証（CR-022）
- 状態遷移の正本は Runner（CR-019）
- 外部 I/O はイベントのみ（CR-021）

しかし、Runner が1つとは限らない状況では次の問題が発生する。

- 同じ run_id を 2つの Runner が同時に Resume
- 状態更新の競合（上書き・ロスト）
- どちらが「正しく再開したか」不明

これを防ぐため、競合時に何が正しいかを“コードではなく契約”で固定する。

## 3. 基本原則（Concurrency Principles）

- 同一 run_id は 同時に1つの Runner のみが実行可能
- 競合解決の正本は Runner
- Orchestrator は並行性・競合を一切扱わない
- ロックは Resume / 状態遷移の境界でのみ必要

## 4. 競合シナリオの定義

本 CR が対象とする競合は以下。

### 4.1 同時 Resume

Runner A と Runner B が同一 run_id に対して Resume を要求

### 4.2 状態更新競合

RUNNING / RESUMING 中に別 Runner が状態を書き換えようとする

### 4.3 再試行競合

Resume 失敗後、複数 Runner が再試行を行う

## 5. 排他（Lock）契約モデル

### 5.1 排他の抽象モデル

本 CR は、以下の 抽象契約のみを定義する。

- Resume 開始前に 排他権の取得を試行する
- 排他権を取得できなかった Runner は 実行を開始してはならない
- 排他権は run_id 単位で管理される

※ 実装方式は未確定。

### 5.2 排他の有効期間

- 排他権は RUNNING / RESUMING の間のみ有効
- 状態が Terminal（SUCCEEDED / FAILED / ABORTED / EXPIRED）に遷移した時点で解放される
- 異常終了時の解放方法は実装・運用に委ねる（本 CR 外）

## 6. 競合発生時の正規挙動

### 6.1 Resume 競合時

- 先に排他権を取得した Runner のみが Resume を継続
- 他 Runner は以下のいずれかを行うことが望ましい：
  - Resume を中断
  - 状態を再読込して待機
  - 利用者に「既に実行中」である旨を通知

### 6.2 状態更新競合時

- Runner は 自身が排他権保持者である場合のみ RunState を更新してよい
- 排他権を持たない Runner による更新は 不正更新とみなす

## 7. Status / Explainability との整合

競合により Resume できなかった場合：

- status を FAILED にする必要はない
- Explainability 上は「競合による再開不可」と説明可能
- 競合は エラーではなく設計上の事象として扱う

## 8. Trust Boundary との関係（CR-022）

- 排他権の有無は Runner 内でのみ信頼される
- 外部（API / Web）からの「自分が実行者だ」という主張は信頼しない
- 排他情報の改ざん検知は CR-022 の完全性モデルに従う

## 9. 禁止事項（Hard Constraints）

- 同一 run_id を複数 Runner が同時に RUNNING にすること
- Orchestrator にロック・排他責務を持たせること
- 排他権なしで RunState を更新すること
- 外部入力で排他状態を指定すること

## 10. 非目標（Explicit Non-Goals）

本 CR は以下を目的としない。

- ロック実装方式の決定
- 分散ロックの可用性設計
- フェイルオーバー戦略
- パフォーマンス保証

## 11. 非機能要件（NFR）

- 競合が発生しても RunState が破壊されない
- 同時 Resume により 二重実行が起きない
- core/orchestrator.py 無変更を前提とする

## 12. リスク・制約

- 排他が導入されない実装では並行 Resume は防げない
- ただし 契約があることで破壊的実装を防止できる

## 13. 完了条件（Done Definition）

- 同時 Resume / Multi-Runner 競合が契約として定義されている
- 排他権の責務主体（Runner）が固定されている
- 競合時の正規挙動が明文化されている
- CR-NEXUS-016〜022 と矛盾しない

## 14. 備考（Contract Layer の完成）

本 CR により、NexusCore の Contract Layer は以下を満たす。

- 単一実行でも安全
- 複数 Runner でも破綻しない
- 分散・並行化に進める

これで Contract Layer は論理的に完全に閉じる。

---

## Cursor に対する指示書（CR-NEXUS-023 用）

以下を そのまま Cursor に貼り付けて使用してください。

#project: NexusCore

Task:
docs/spec/CR-NEXUS-023_Multi_Runner_Concurrency_Contract.md を新規追加する（docs-only）。

Scope:
- Multi-Runner / 同時 Resume / 競合整合性の契約定義のみ
- 実装コードには一切触れない

Rules:
- docs/spec/ 配下に配置
- CR タイトル・章立て・番号は変更しない
- 冒頭に以下の SRS Traceability を必ず含める

SRS Traceability:
- Related SRS: docs/srs/NEXUSCORE_SRS.md
- This CR satisfies: FR-1; FR-8; NFR-1; NFR-9

Constraints:
- 排他・競合の正本は Runner と明記する
- Orchestrator に競合責務を持たせない
- ロック方式は未確定とする
- RunState は CR-NEXUS-020 を前提とする
- Explainability は CR-NEXUS-018 と整合させる
- TODO や実装提案を追加しない
- core/orchestrator.py 無変更前提

Acceptance:
- 同時 Resume の競合モデルが明文化されている
- 排他権の概念と有効期間が定義されている
- CR-NEXUS-016〜022 と整合している


