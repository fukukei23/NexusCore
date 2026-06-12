# Review Packet: CR-NEXUS-051-B (Retry Policy)

**Review Type**: Phase 3 Independent Review
**Review Date**: 2026-01-12
**Reviewer**: Independent Context (Separate from Implementation)
**Spec Version**: 1.0.0
**Spec Location**: `docs/spec/CR-NEXUS-051-B_RETRY_POLICY.md`

---

## 1. Review Target

### Spec
- **File**: `docs/spec/CR-NEXUS-051-B_RETRY_POLICY.md`
- **Purpose**: Define Retry / Abort / Skip decision logic based on Error Taxonomy (051-A)

### Tests
- **File**: `tests/core/test_retry_policy.py`
- **Coverage**: Decision Table, Finite Retries, Unexpected Handling, Backoff Strategy

### Implementation
- **File**: `src/nexuscore/core/retry_policy.py`
- **Entry Point**: `decide_retry(error, attempt, context) -> RetryDecision`

---

## 2. Phase 3 Review Criteria

Phase 3 Review evaluates **"Is this Spec ready for implementation?"** based on:

1. **Completeness**: Are all required specifications defined?
2. **Safety**: Are retry/failure controls and infinite loop risks addressed?
3. **Extensibility**: Can the design accommodate future changes?
4. **Implicit Specifications**: Are implementation details leaking into the Spec?

---

## 3. Review Findings

### 3.1 High Severity Issues

None identified.

### 3.2 Medium Severity Issues

None identified.

### 3.3 Low Severity Issues

None identified.

---

## 4. Evaluation by Criteria

### 4.1 Completeness

**Status**: ✅ Pass

- **Decision Table** (Section 3): Clearly defines Action, Max Attempts, and Backoff Strategy for each exception class
- **Backoff Strategy** (Section 4): Exponential and Linear backoff are defined with concrete formulas
- **Unclassifiable / Unexpected Handling** (Section 6): Explicitly defines immediate Abort with no retry
- **Observability** (Section 7): Required log fields are enumerated
- **Test Requirements** (Section 8): Test cases are clearly specified

**Evidence**:
- Decision Table includes all 8 exception classes from 051-A
- Max Attempts are explicitly defined (0 for immediate abort, 3-5 for retryable)
- Backoff formulas are provided with default values

### 4.2 Safety

**Status**: ✅ Pass

- **Finite Retry Guarantee**: Max Attempts are capped (5 max), preventing infinite retry loops
- **Unexpected Error Handling**: UnexpectedSystemError and unclassifiable errors immediately Abort (no retry)
- **Retry Prohibition**: Sandbox and security errors do not retry (max_attempts=0)

**Evidence**:
- Section 3: Decision Table explicitly sets max_attempts=0 for non-retryable errors
- Section 6: "Retry 禁止" (Retry Prohibited) is clearly stated for unexpected errors
- Section 8.2: Finite retry tests verify max attempts are enforced

**Risk Assessment**:
- No risk of infinite retry loops
- No risk of retrying dangerous operations (sandbox security violations)
- Budget exhaustion is handled (ModelRateLimitError max 5 attempts, then Abort)

### 4.3 Extensibility

**Status**: ✅ Pass

- **Decision Table as SSOT**: Adding new exception classes only requires updating the Decision Table
- **Backoff Strategy Pluggability**: Exponential and Linear backoff are cleanly separated
- **Context Parameter**: `context: Optional[Dict[str, Any]]` allows future extensions without breaking changes

**Evidence**:
- Section 10.2: Clear separation between Policy layer (`decide_retry()`) and execution layer
- Decision Table structure supports new exception classes without code restructuring
- Backoff strategies are isolated functions (`_calculate_exponential_backoff()`, `_calculate_linear_backoff()`)

### 4.4 Implicit Specifications

**Status**: ✅ Pass

- **Spec focuses on "What" not "How"**: Decision Table defines behavior, not implementation details
- **Function names are examples**: Section 10.1 uses "例" (example) to indicate guidance, not mandates
- **Implementation freedom**: Specific variable names and internal structure are left to implementation

**Evidence**:
- Section 10.1: Function signature is marked as "例" (example)
- Section 10.2: Responsibility boundaries are defined at architectural level, not code level
- Section 11: Phase 3 checklist explicitly guards against "実装詳細の混入" (implementation detail leakage)

---

## 5. Test Coverage Verification

### 5.1 Decision Table Tests

**Status**: ✅ Pass

- All 8 exception classes are tested
- Parametrized tests cover multiple attempt counts
- Max attempts enforcement is verified

**Evidence**: `tests/core/test_retry_policy.py` includes 17 parametrized test cases covering all Decision Table rows.

### 5.2 Finite Retry Tests

**Status**: ✅ Pass

- Tests verify that retries stop at max attempts
- Tests cover ModelRateLimitError (5 max), ModelTimeoutError (3 max), ModelConnectionError (3 max), InvalidModelOutputError (3 max)

**Evidence**: `test_finite_retries_*` functions explicitly test up to max attempts + 1.

### 5.3 Unexpected Handling Tests

**Status**: ✅ Pass

- UnexpectedSystemError, SandboxExecutionError, SandboxSecurityError immediately Abort
- No retry is performed

**Evidence**: `test_unexpected_no_retry`, `test_sandbox_execution_no_retry`, `test_sandbox_security_no_retry`.

### 5.4 Backoff Tests

**Status**: ✅ Pass

- Exponential backoff formula is validated (2^n + jitter)
- Linear backoff is validated (fixed interval)

**Evidence**: `test_exponential_backoff_*`, `test_linear_backoff_*`.

---

## 6. Compatibility with 051-A

**Status**: ✅ Pass

- Spec references 051-A Error Taxonomy as foundation
- No changes to 051-A exception classes
- Decision Table aligns with 051-A's Retryable column

**Evidence**:
- Section 1: "Related: CR-NEXUS-051-A (Error Taxonomy)"
- Section 9.1: "051-A の例外クラス: 変更なし（参照のみ）"
- Decision Table (Section 3) maps directly to 051-A classes

---

## 7. Phase 3 Checklist

| Criteria | Status | Notes |
|----------|--------|-------|
| Decision Table が唯一の真実として定義されているか | ✅ Pass | Section 3 明記 |
| 有限性保証（無限リトライがない）が明示されているか | ✅ Pass | Max Attempts 定義済み |
| Unclassifiable / Unexpected の最終挙動が定義されているか | ✅ Pass | Section 6 明記 |
| Backoff Strategy が具体的に定義されているか | ✅ Pass | Section 4 に式あり |
| 観測性（ログ項目）が定義されているか | ✅ Pass | Section 7 明記 |
| テスト要件が明文化されているか | ✅ Pass | Section 8 明記 |
| 実装詳細（具体的な関数名・ファイル名）が Spec に混入していないか | ✅ Pass | Section 10 は例示のみ |

---

## 8. Verdict

**Result**: ✅ **Approve**

**Summary**:
- CR-NEXUS-051-B Retry Policy Spec は実装フェーズへ進行可能
- すべての Phase 3 評価基準を満たしている
- 安全性（有限性保証、Unexpected 処理）が明確に定義されている
- テスト要件が明文化されており、実装の品質を担保できる

**Conditions**:
None. 無条件 Approve.

**Rationale**:
- High Severity 事項なし
- 051-A との整合性あり
- 実装ガイダンスが適切（詳細すぎず、曖昧すぎない）
- Phase 3 チェックリストすべて満たす

---

## 9. Post-Review Actions

1. **Decision Log に本レビュー結果を追記すること**（append-only）
2. **実装時は Section 3（Decision Table）を唯一の真実として扱うこと**
3. **テストが 100% 通過することを確認してから PR を作成すること**

---

## 10. Sign-off

**Reviewer**: Independent Review Context (Separate AI Session)
**Date**: 2026-01-12
**Verdict**: Approve
**Next Step**: Implementation フェーズへ進行可

---

End of Review Packet.
