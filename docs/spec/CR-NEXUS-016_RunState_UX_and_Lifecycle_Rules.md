# CR-NEXUS-016: RunState UX 整理およびライフサイクル運用ルール定義（改訂版）

SRS Traceability

Related SRS: docs/srs/NEXUSCORE_SRS.md

This CR satisfies: FR-1; NFR-1; NFR-2

## 1. 概要（Overview）

本 CR は、既に実装済みである RunState（Pause / Resume 機構）について、
ユーザー体験（UX）および運用ライフサイクルの不明確さを解消することを目的とする。

本 CR は 新規ロジックの追加を目的としない。
対象は以下に限定される。

- CLI 出力における run_id 提示の整理
- RunState 永続データの運用ルール（TTL / 破棄責務）の明文化
- 商用運用を想定した最低限の制約条件の定義

## 2. 背景（Background）

CR-NEXUS-015 により以下が成立した。

- AuthorityLevel に基づく停止
- フェーズ境界での Pause
- run_id を用いた Resume
- RunState の JSON 永続化

一方で、次の点が仕様として未定義であった。

- run_id がいつ・どの形式でユーザーに提示されるか
- RunState がいつまで有効か
- 不要になった RunState の管理責務がどこにあるか

これらは UX 混乱および SaaS 運用時の障害要因となるため、本 CR で整理する。

## 3. SRS トレーサビリティ（Traceability）

- SRS-ID: SRS-NEXUS-CORE-CTRL-001
  - 人間が AI 実行を制御・停止・再開できること
- SRS-ID: SRS-NEXUS-OPS-001
  - 実行状態が観測・説明可能であること

## 4. スコープ（In Scope / Out of Scope）

### In Scope

- CLI 出力仕様（run_id の提示方法）
- RunState の保存期間（TTL）に関する運用ルール
- RunState 削除責務の明文化（自動／手動）

### Out of Scope

- RunState 保存形式の変更
- Resume ロジックの再設計
- Orchestrator / core 層の変更
- API 化対応（別 CR）

## 5. 現状仕様（As-Is）

- RunState は `var/run_state/<run_id>.json` に保存される
- Pause 時に保存され、Resume 時に参照される
- run_id は内部的に生成されているが、UX 上の提示規則は未定義

## 6. 変更仕様（To-Be）

### 6.1 CLI UX：run_id 提示ルール

#### 原則

- run_id は必ずユーザーに明示される
- 提示箇所は CLI 標準出力に限定する
- run_id は一意であり、意味的解釈を前提としない識別子とする

#### 出力例（参考）

```
[INFO] Run started
[INFO] run_id: 20251217-140341-abcdef
[INFO] authority_level: partial
```

#### Pause 時

```
[PAUSED] Run paused at phase: implementation
[PAUSED] run_id: 20251217-140341-abcdef
[PAUSED] Resume with: --resume-run-id 20251217-140341-abcdef
```

### 6.2 RunState ライフサイクル運用ルール

#### 有効期間（TTL）

- デフォルト TTL：7日
- TTL は「最終更新時刻（pause / resume）」基準とする
- TTL 超過の RunState は 「再開非保証」 とする
- 実装必須ではなく、運用ルールとしての規定とする

#### TTL 超過時の期待挙動（運用定義）

TTL 超過の RunState が指定された場合、
NexusCore は Resume を試行してもよいが、
その結果について成功保証を行わない。

CLI 実装においては、
TTL 超過を検知した場合に Warning を表示することが望ましい。

（本 CR は実装義務を課さない）

### 6.3 RunState 削除責務

| 削除種別 | 責務 |
|---|---|
| 手動削除 | 運用者（CLI / ファイルシステム操作） |
| 自動削除 | 将来拡張（本 CR では実装しない） |

原則として：

- NexusCore 本体は 自動削除を行わない
- 削除は運用レイヤまたは将来 CR に委ねる

## 7. 非機能要件（NFR）

- core/orchestrator.py を変更しない
- 既存テストの意味論を壊さない
- run_id がログ・監査で一意に追跡可能であること

## 8. リスク・制約

TTL を運用ルールのみに留めるため、
実装・運用依存による RunState の残存が起き得る。

ただしこれは CR-NEXUS-020 以降の API / Worker 管理で解決する前提とする。

## 9. 完了条件（Done Definition）

- run_id 提示仕様が CR に明記されている
- RunState の TTL / 削除責務が文書化されている
- 実装変更が必要な場合でも runner 層に限定される
- SRS / Charter に矛盾しない

## 10. 備考

本 CR は UX / 運用定義 CRであり、
将来の API 化・分散実行における破壊的変更を防ぐための
**緩衝層（Contract Layer）**として位置づける。

---

## Cursor に対する指示書（CR-NEXUS-016 用）

以下を そのまま Cursor に貼り付けて使用してください。

#project: NexusCore

Task:
CR-NEXUS-016_RunState_UX_and_Lifecycle_Rules.md を新規追加する。

Scope:
- 新規ドキュメント追加のみ
- 既存の SRS / Charter / Governance / 実装コードには一切触れない

Rules:
- docs/spec/ 配下に配置すること
- CR タイトル・章立て・番号は変更しない
- 冒頭に以下の SRS Traceability を必ず含める

SRS Traceability:
- Related SRS: docs/srs/NEXUSCORE_SRS.md
- This CR satisfies: FR-1; NFR-1; NFR-2

Constraints:
- 本 CR は docs-only CR とする
- 新規ロジック・実装提案・TODO を追加しない
- AuthorityLevel / RunState の意味論は拡張しない

Acceptance:
- run_id の性質（一意・非意味的識別子）が明文化されている
- TTL 超過時の期待挙動が「運用定義」として記載されている
- core/orchestrator.py 無変更の前提が維持されている



