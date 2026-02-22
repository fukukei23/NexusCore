# NEXUSCORE Contract Layer Freeze Policy (CR-NEXUS-016〜023)

## 1. Freeze 宣言（Freeze Declaration）

本ドキュメントは、NexusCore の **Contract Layer** を構成する CR-NEXUS-016〜023 を
**凍結（Freeze）**する運用ルールを定義する。

- CR-NEXUS-016〜023 は **Contract Layer** として凍結する
- **直接編集は禁止**（誤字修正も原則禁止）

Freeze Target（本文変更禁止）:

- `docs/spec/CR-NEXUS-016_*.md`
- `docs/spec/CR-NEXUS-017_*.md`
- `docs/spec/CR-NEXUS-018_*.md`
- `docs/spec/CR-NEXUS-019_*.md`
- `docs/spec/CR-NEXUS-020_*.md`
- `docs/spec/CR-NEXUS-021_*.md`
- `docs/spec/CR-NEXUS-022_*.md`
- `docs/spec/CR-NEXUS-023_*.md`

## 2. 変更ルート（唯一の正規ルート / Append-only）

Contract Layer の変更が必要な場合、**既存 CR を編集して置換してはならない**。

唯一の正規ルートは以下とする。

- **新しい CR を追加**し、差分として Contract を拡張／上書きする（Append-only 原則）
- 新 CR には必ず **「CR-NEXUS-016〜023 のどの条項を拡張/上書きするか」**を明記する
- 既存 CR の“本文置換”は行わない（参照関係を追加して積み上げる）

## 3. 例外規定（最小）

例外的に既存 CR（016〜023）を編集してよいのは、次に限る。

- **リンク切れ修正**
- **表記ゆれ統一**

ただし、以下は禁止する。

- 意味論（Semantics）の変更
- 契約内容（定義・制約・責務境界・用語）の変更

例外編集を行った場合、編集対象の CR 内に変更理由を追記せず、代わりに
コミットメッセージ等で **短文の変更理由**を残す（例: "Fix broken link only"）。

## 4. 実装フェーズのルール（Implementation Conformance）

以後の実装・修正は **CR-NEXUS-016〜023（Contract Layer）に従う**。

- 実装側の都合で Contract Layer を変更して整合を取ることは禁止（逆方向禁止）
- もし実装が Contract と矛盾した場合、矛盾を解消する正規手段は **新CRの追加**のみとする

## 5. 参照一覧（Contract Layer Index）

CR-NEXUS-016〜023 は、以下の役割で Contract Layer を構成する。

| CR | ファイル | 役割（Contract Scope） |
|---|---|---|
| CR-NEXUS-016 | `docs/spec/CR-NEXUS-016_RunState_UX_and_Lifecycle_Rules.md` | UX / 運用（run_id提示、TTL/削除責務） |
| CR-NEXUS-017 | `docs/spec/CR-NEXUS-017_Resume_Orchestrator_Reconstruction_Model.md` | 再構築モデル（ResumeはOrchestrator再構築、RunState SOT） |
| CR-NEXUS-018 | `docs/spec/CR-NEXUS-018_Resume_Failure_Explainability_Contract.md` | 説明責務（Resume失敗の説明正本=Runner、What/Why/Next Action） |
| CR-NEXUS-019 | `docs/spec/CR-NEXUS-019_Run_Resume_Status_State_Machine_Contract.md` | 状態語彙・状態遷移（State Machine、正本=Runner） |
| CR-NEXUS-020 | `docs/spec/CR-NEXUS-020_RunState_JSON_Schema_Contract.md` | RunState JSON スキーマ（Field/Optionality/Versioning） |
| CR-NEXUS-021 | `docs/spec/CR-NEXUS-021_RunState_IO_Contract.md` | 入出力（入力=Event、出力=RunState投影、Orchestrator非正本） |
| CR-NEXUS-022 | `docs/spec/CR-NEXUS-022_RunState_Integrity_Contract.md` | 完全性・改ざん検知（Trust Boundary、検証正本=Runner） |
| CR-NEXUS-023 | `docs/spec/CR-NEXUS-023_Multi_Runner_Concurrency_Contract.md` | 並行性・競合（Multi-Runner、同時Resume、排他概念、正本=Runner） |


