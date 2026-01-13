# Decision Log

> 重要な判断・却下（Reject）・方針変更の記録（append-only）

## 目的

このファイルは、NexusCore プロジェクトにおける重要な意思決定を記録します。
過去エントリを編集せず、新しいエントリを末尾に追記する形式（append-only）で運用します。

## 記録対象

- 重要な設計判断
- 方針変更
- Review 結果（Approve/Reject）
- 却下された提案とその理由

## フォーマット

```markdown
## YYYY-MM-DD: [タイトル]

**Context**: 背景・状況
**Decision**: 決定内容
**Rationale**: 理由
**Alternatives Considered**: 検討した代替案
**Review Result**: [Approve/Reject] (Phase 2.5 実施時)
**Related Spec**: [Spec へのリンク]
```

---

## エントリ

### 2025-01-05: STIT+IRG ガバナンス同居導入（Bootstrap）

**Context**: NexusCore リポジトリに STIT+IRG（Spec & Test Driven Iteration + Independent Review Gate）のガバナンス運用を導入するため、Project Profile と GOVERNANCE 資産を同居させる。

**Decision**:
- `PROJECT_PROFILES/PROJECT_PROFILE_NEXUSCORE.md` を初稿（プレースホルダー込み）で作成
- `GOVERNANCE/` 一式を Bootstrap Draft として作成（テンプレートGitの正式版は後で移植予定）
- `DECISION_LOGS/DECISION_LOG.md` を新規作成
- ルート `README.md` に STIT+IRG 導線を追加
- `docs/ARCHITECTURE.md` に Gate 参照を追加

**Rationale**:
- テンプレートGit（STIT+IRG registry）の SSOT が未提供のため、Bootstrap Draft で運用開始可能な状態を整備
- 既存のアプリコード・挙動は変更せず、「横に足す」方式で同居
- 正式版移植時は `GOVERNANCE/IMPORT_MAPPING.md` を参照

**Alternatives Considered**:
- テンプレートGitの SSOT を待つ → 却下（運用開始を優先）
- 既存ファイルを移動 → 却下（既存構造を壊さない方針）

**Review Result**: N/A (Bootstrap 作業のため Phase 2.5 は未実施)

**Related Spec**: N/A (Bootstrap 作業)

---

### 2025-01-05: 衛生チェック対象限定と再発防止ルール固定

**Context**: STIT+IRG導入作業後に、`docs/` 配下の既存ドキュメント（WSLパス等の運用手順を含む）がテンプレ衛生ルールで自動置換される懸念が発生。既存の運用手順を破壊しないよう、衛生チェック対象を限定する必要がある。

**Decision**:
- 衛生チェック対象を **GOVERNANCE/**, **PROJECT_PROFILES/**, **DECISION_LOGS/** に限定
- `docs/` 配下は対象外（既存の運用手順として必要なパスを含む場合がある）
- 全.mdファイルを対象にした衛生チェックは禁止
- `GOVERNANCE/HYGIENE_CHECK.md` に限定対象版の手順を明文化
- `PROJECT_PROFILE_NEXUSCORE.md` の Documentation Constraints に適用範囲を明記

**Rationale**:
- 既存の `docs/` 配下ドキュメントは、WSL環境での運用手順として `/home/yn441611/NexusCore` などの絶対パスを含む場合がある
- これらは「環境依存パス」ではなく「運用手順として必要な情報」である
- ガバナンス資産（GOVERNANCE等）のみを対象とすることで、既存ドキュメントを保護しつつ、新規資産の品質を保証できる

**Alternatives Considered**:
- `docs/` も含めて全.mdをチェック → 却下（既存ドキュメントの破壊リスク）
- チェック対象を明示せずに運用 → 却下（再発防止のため明文化が必要）

**Review Result**: N/A (緊急対応のため Phase 2.5 は未実施)

**Related Spec**: N/A (再発防止ルール固定)

---

### 2025-01-05: Phase 2.5 Review – CR-NEXUS-051 Error Classification

**Context**: CR-NEXUS-051 に基づくエラー分類仕様について、実装前の Phase 2.5 独立レビューを実施した。

**Decision**: 本仕様は現時点では **Reject** とする。

**Rationale**:
- Retry/backoff 戦略が仕様として未定義
- 分類不能エラー発生時の最終挙動が定義されていない
- 将来の分類拡張時に条件分岐が肥大化するリスクがある

**Alternatives Considered**:
- 現状のまま実装進行 → 却下（安全性リスクが高い）
- 仕様修正後に再レビュー → 採用（本判定の前提）

**Review Result**: Reject (Phase 2.5 Independent Review)

**Related Spec**:
- `docs/spec/CR-NEXUS-051_ERROR_CLASSIFICATION_SPECIFICATION.md`
- Review Packet: `GOVERNANCE/review_packets/RP-NEXUS-051_PHASE25_INDEPENDENT_REVIEW.md`

**Consequence**:
- 本 Spec は修正が必要
- 修正後、再度 Phase 2.5 Review を実施すること
- 修正が完了するまで実装フェーズへ進行しない

---

### 2025-01-06: Phase 2.5 Review (v2) – CR-NEXUS-051 Error Classification

**Context**: CR-NEXUS-051 エラー分類仕様について、v1 レビューで Reject された事項を解消した改訂 Spec (v1.1) に対する Phase 2.5 再レビューを実施した。

**Decision**: 本仕様（v1.1）は **Approve** とする。実装フェーズへ進行可能。

**Rationale**:
- v1 レビューで指摘された High Severity 事項（retry/backoff 戦略の未定義、分類不能エラー時の最終挙動未定義）がすべて解消された
- セクション 3.3（Retry / Failure Control Policy）で、リトライ可否の判断ルール、有限性保証、backoff 戦略が意味論レベルで定義された
- セクション 3.4（Unclassifiable / Unexpected Error Handling）で、分類不能エラー時の最終フォールバックが必須定義として記載された
- リトライの有限性が SHALL 要件として保証され、無限リトライループのリスクが排除された
- Unexpected エラーのリトライ禁止が明示され、安全性が確保された

**Alternatives Considered**:
- Conditional Approve → 却下（High Severity 事項はすべて解消されており、条件付き承認の必要はない）
- Reject → 却下（実装進行を阻害する問題は残存していない）

**Review Result**: Approve (Phase 2.5 Independent Review v2)

**Related Spec**:
- `docs/spec/CR-NEXUS-051_ERROR_CLASSIFICATION_SPECIFICATION.md` (v1.1)
- Review Packet (v1): `GOVERNANCE/review_packets/RP-NEXUS-051_PHASE25_INDEPENDENT_REVIEW.md`
- Review Packet (v2): `GOVERNANCE/review_packets/RP-NEXUS-051_PHASE25_INDEPENDENT_REVIEW_v2.md`

**Consequence**:
- 本 Spec (v1.1) は実装フェーズへ進行可能
- v1 レビューで Reject された事項は解消済み
- 実装時は、セクション 3.3 および 3.4 の要件を遵守すること

---

### 2026-01-12: Phase 2.5 Review – CR-NEXUS-051-B Retry Policy

**Context**: CR-NEXUS-051-B Retry Policy 仕様について、実装前の Phase 2.5 独立レビューを実施した。本 Spec は 051-A Error Taxonomy を前提とし、各例外に対する Retry / Abort / Skip の判断ロジックを定義する。

**Decision**: 本仕様（v1.0.0）は **Approve** とする。実装フェーズへ進行可能。

**Rationale**:
- **Decision Table**: 8つの例外クラスすべてに対して Action, Max Attempts, Backoff Strategy が明確に定義されている
- **有限性保証**: Max Attempts が明示的に設定され（0, 3, 5）、無限リトライのリスクが排除されている
- **Unexpected 処理**: UnexpectedSystemError および分類不能エラーは即座に Abort（Retry 禁止）が明記されている
- **Backoff Strategy**: Exponential と Linear の具体的な計算式が提供されている
- **観測性**: ログに記録すべき項目が明文化されている
- **テスト要件**: Decision Table 検証、有限性検証、Unexpected 処理検証、Backoff 検証が明文化されている
- **実装詳細の混入なし**: Spec は意味論レベルの定義に留まり、実装詳細（具体的な関数名・ファイル名）は例示のみ

**Alternatives Considered**:
- Conditional Approve → 却下（すべての Phase 2.5 評価基準を満たしており、条件付き承認の必要はない）
- Reject → 却下（実装進行を阻害する問題は存在しない）

**Review Result**: Approve (Phase 2.5 Independent Review)

**Related Spec**:
- `docs/spec/CR-NEXUS-051-B_RETRY_POLICY.md` (v1.0.0)
- `docs/spec/CR-NEXUS-051-A_ERROR_TAXONOMY.md` (前提)
- Review Packet: `GOVERNANCE/review_packets/RP-NEXUS-051-B_PHASE25_RETRY_POLICY.md`

**Consequence**:
- 本 Spec (v1.0.0) は実装フェーズへ進行済み（テスト 30 passed）
- Decision Table を唯一の真実として実装すること
- 051-A の例外クラスは変更しないこと（参照のみ）
- 051-C（Orchestrator Integration）とは分離して扱うこと

**Implementation Summary**:
- **Spec**: `docs/spec/CR-NEXUS-051-B_RETRY_POLICY.md`
- **Tests**: `tests/core/test_retry_policy.py` (30 tests, all passed)
- **Implementation**: `src/nexuscore/core/retry_policy.py` (`decide_retry()` function)
- **Branch**: `claude/cr-nexus-051-b-retry-policy`

---
