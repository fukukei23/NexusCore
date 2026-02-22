# CR-NEXUS-018: Resume 失敗時の説明責務モデル定義

（Explainability Contract）

SRS Traceability

Related SRS: docs/srs/NEXUSCORE_SRS.md

This CR satisfies: FR-1; FR-3; NFR-1; NFR-4

## 1. 概要（Overview）

本 CR は、Pause / Resume において
**Resume が失敗した場合に、NexusCore が「何を・どこまで説明する責務を負うか」**を
設計契約（Explainability Contract）として定義する。

本 CR は 説明責務の範囲と正本を定めるのみであり、
例外処理・ログ形式・UI 表示などの実装は要求しない。

## 2. 背景（Background）

CR-NEXUS-017 により、以下が設計として固定された。

- Resume は Orchestrator を再構築する
- RunState が再開の唯一の正本（SOT）である

この結果、Resume は以下の理由で失敗し得る。

- RunState が破損・欠損している
- next_phase が現在の実行構成と整合しない
- context_snapshot が不十分
- 実行環境差異（依存関係・設定差）

これらは 設計上許容された失敗であり、
重要なのは「失敗しないこと」ではなく
**「失敗理由を説明できること」**である。

## 3. 基本原則（Explainability Principles）

### 3.1 説明責務の基本原則

- Resume の失敗は 異常ではない
- NexusCore は 再開成功を保証しない
- ただし NexusCore は
  失敗理由を説明可能な状態で失敗する責務を負う

### 3.2 説明の対象

説明は以下を満たせば十分とする。

- 人間（運用者・開発者）が原因を分類できる
- 次に取るべき行動（再試行／破棄／再実行）が判断できる

## 4. 説明責務の正本（Source of Explanation）

### 4.1 正本の所在

Resume 失敗時の説明責務の正本は Runner にある。

- Orchestrator は説明責務の正本にならない
- RunState は「事実データ」であり、説明主体ではない

### 4.2 説明に用いられる情報源

Runner は、以下を根拠として説明を構成する。

- RunState（読み取り結果）
- Resume 入力（run_id 等）
- 再構築時に発生したエラー情報
- Runner 自身の判断結果

## 5. 説明レベルの定義（Explanation Levels）

説明は以下の 3段階レベルで整理される。

### Level 1: 事実説明（What）

- Resume が失敗したという事実
- どの run_id が対象か
- どのフェーズで失敗したか（可能な場合）

例：

Resume failed for run_id=XXXX at phase=implementation

### Level 2: 原因分類（Why）

失敗原因は、以下のいずれかに分類される。

#### STATE_INVALID

RunState が欠損・破損している

#### STATE_INCOMPATIBLE

RunState と現在の実行構成が整合しない

#### ENVIRONMENT_MISMATCH

実行環境差異による失敗

#### INTERNAL_ERROR

想定外の内部エラー

※ 分類は契約であり、実装は自由。

### Level 3: 行動指針（Next Action）

Runner は、最低限以下の指針を提示できることが望ましい。

- 再試行可能か
- run_id を破棄すべきか
- 新規 Run としてやり直すべきか

## 6. 非目標（Explicit Non-Goals）

本 CR は以下を目的としない。

- 失敗原因の完全自動修復
- 例外スタックトレースの完全公開
- UI 表示形式の定義
- ログフォーマットの標準化

## 7. Runner / Orchestrator の責務分離（再確認）

| 項目 | 責務 |
|---|---|
| Resume 可否判断 | Runner |
| 失敗理由の分類 | Runner |
| 説明文生成 | Runner |
| 例外発生 | Orchestrator |
| 内部エラー詳細 | Orchestrator（非正本） |

## 8. 非機能要件（NFR）

- Resume 失敗時も run_id による追跡が可能であること
- 説明は 再現性・監査性を損なわない
- core/orchestrator.py の修正を前提としない

## 9. リスク・制約

説明は最小限に留まるため、
高度なデバッグには追加ログが必要になる。

ただしそれは 本 CR の責務外とする。

## 10. 完了条件（Done Definition）

- Resume 失敗時の説明責務が文書化されている
- 説明の正本が Runner であることが明示されている
- 説明レベル（What / Why / Next Action）が定義されている
- CR-NEXUS-017 と矛盾しない

## 11. 備考

本 CR は Explainability Contractであり、
CR-NEXUS-016 / 017 で定義された Contract Layer を補完する。

本契約により NexusCore は
**「失敗しても黙らない実行基盤」**として成立する。

---

## Cursor に対する指示書（CR-NEXUS-018 用）

以下を そのまま Cursor に貼り付けて使用してください。

#project: NexusCore

Task:
CR-NEXUS-018_Resume_Failure_Explainability_Contract.md を新規追加する。

Scope:
- 設計CR（Explainability Contract）の追加のみ
- 実装コードには一切触れない

Rules:
- docs/spec/ 配下に配置すること
- CR タイトル・章立て・番号は変更しない
- 冒頭に以下の SRS Traceability を必ず含める

SRS Traceability:
- Related SRS: docs/srs/NEXUSCORE_SRS.md
- This CR satisfies: FR-1; FR-3; NFR-1; NFR-4

Constraints:
- 本 CR は設計定義のみとする
- 新規ロジック・実装・TODO を追加しない
- core/orchestrator.py 無変更を前提とする

Acceptance:
- Resume 失敗時の説明責務が Runner にあることが明示されている
- 説明レベル（What / Why / Next Action）が定義されている
- CR-NEXUS-017（再構築モデル）と整合している

## 位置づけ整理（重要）

| CR | 役割 |
|---|---|
| CR-015 | Pause / Resume 実装 |
| CR-016 | UX / 運用契約 |
| CR-017 | 再構築モデル契約 |
| CR-018 | 説明責務契約（今回） |


