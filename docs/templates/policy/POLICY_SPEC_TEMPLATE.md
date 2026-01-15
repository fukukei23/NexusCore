# [POLICY-ID]: [POLICY-NAME] Specification

## Metadata
- PolicyId: [POLICY-ID]
- PolicyName: [POLICY-NAME]
- Status: Draft / Approved
- Owner: [OWNER]
- LastUpdated: [YYYY-MM-DD]
- Related: [RELATED-SPECS/PRS]

## 1. Purpose
- 本ポリシーが解決する問題を1〜3行で記述する。
- 「何を一意に決めるか」を明記する（曖昧表現禁止）。

## 2. Non-Goals
- 本ポリシーで扱わないことを列挙する（例：Orchestrator統合、分類設計変更、例外追加など）。

## 3. Scope
- 適用対象（どの処理に効くか）を明示する。
- 適用外（対象外）も必ず書く。

## 4. Inputs to Decision
Decision（Retry/Abort/Skip 等）に使用する入力を列挙する。
例:
- Error Category（Taxonomy に基づく）
- Exception Type
- HTTP Status（ある場合）
- Attempt Count
- Context（LLM / Sandbox / Network 等）
- Budget/RateLimit signal（ある場合）

## 5. Actions (Outputs)
本ポリシーが返し得るアクションを列挙し、意味を一意に定義する。
- [ACTION-1]
- [ACTION-2]
- [ACTION-3]

## 6. Decision Table (Single Source of Truth)
- 本表が唯一の真実（SSOT）であることを宣言する。
- 本表にないケースは「未定義」ではなく、必ず Fallback Rule に落ちること。

(Decision Table は DECISION_TABLE_TEMPLATE.md の形式を貼り付ける)

## 7. Strategy (Backoff / Limits / Thresholds)
- 有限性保証（上限回数・上限時間など）を必ず記述する。
- Backoff（指数/線形/固定/ジッタ等）を必要な粒度で定義する。

## 8. Rate Limit / Budget Handling
- 429 / quota exhausted / budget exhausted の扱いを定義する。
- Retry する場合は上限と待機戦略を明示する。
- Abort する場合はログ理由を明示する。

## 9. Fallback Rule (Unclassifiable / Unexpected)
- 分類不能、想定外、表にないケースの最終挙動を一意に定義する。
- 原則: 安全側（Retryしない）を明記する。

## 10. Observability Requirements
ログに必ず含めるべき項目を定義する（最小でよい）。
例:
- policy_id
- error_category / exception_type
- decision
- attempt / max_attempts
- backoff_seconds
- terminal_reason

## 11. Test Requirements
Decision Table と 1対1に対応したテスト観点を列挙する。
- Decision Table 全行の検証（parametrize）
- 有限性保証（上限到達で停止）
- Fallback Rule の検証
- Strategy（Backoff 等）の検証（必要なら）

## 12. Compatibility & Impact
- 既存挙動との互換性（破壊的変更の有無）
- 影響範囲（呼び出し側、ログ、監視）を明示する。

## Golden Example
- CR-NEXUS-051-B（Retry Policy）を参照する（実プロジェクトの模範例）
  - Spec: docs/spec/CR-NEXUS-051-B_RETRY_POLICY.md
  - Tests: tests/core/test_retry_policy.py
  - Impl: src/nexuscore/core/retry_policy.py
  - Review Packet: GOVERNANCE/review_packets/RP-NEXUS-051-B_PHASE25_RETRY_POLICY.md
