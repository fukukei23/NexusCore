# CR-NEXUS-051-B: Retry Policy

**Version**: 1.0.0
**Date**: 2026-01-12
**Status**: Specification
**Related**: CR-NEXUS-051-A (Error Taxonomy)

---

## 1. Purpose（目的）

NexusCore における Error Taxonomy (051-A) に基づき、各例外に対する Retry / Abort / Skip の判断を一意に定義する。

### Non-goals（対象外）

- Orchestrator レベルでの最終判断（051-C 範囲）
- モデルフェイルオーバー戦略の詳細実装（別 Spec で扱う）
- エラー分類（Taxonomy）の変更（051-A を参照のみ）

---

## 2. Inputs（判断に使用する情報）

Retry Policy の判断に使用する入力情報：

1. **例外型（Exception Type）**: NexusCore 例外クラス（ModelRateLimitError 等）
2. **エラーカテゴリ（Error Category）**: `classify_error()` の戻り値（"rate_limit", "timeout" 等）
3. **試行回数（Attempt Count）**: 現在の試行回数（1-indexed）
4. **コンテキスト（Context）**: タスクタイプ、モデル ID、タイムスタンプ等

---

## 3. Decision Table（判断表：唯一の真実）

以下の表が Retry Policy の唯一の真実である。実装はこの表をそのままコード化すること。

| Exception Class | Category | Action | Max Attempts | Backoff Strategy | Notes |
|-----------------|----------|--------|--------------|------------------|-------|
| **ModelRateLimitError** | rate_limit | Retry | 5 | Exponential (2^n) + Jitter | 429 対応。最大 5 回まで |
| **ModelTimeoutError** | timeout | Retry | 3 | Linear (10s) | タイムアウト上限は 30s |
| **ModelConnectionError** | connection | Retry | 3 | Exponential (2^n) + Jitter | ネットワーク一時障害 |
| **InvalidModelOutputError** | invalid_output | Retry | 3 | Linear (5s) | JSON 不正。3 回失敗で Abort |
| **SandboxExecutionError** | sandbox | Abort | 0 | N/A | 即座に Abort。Self-heal は別 |
| **SandboxSecurityError** | sandbox | Abort | 0 | N/A | 即座に Abort。監査ログ優先 |
| **PatchApplyError** | patch_apply | Abort | 0 | N/A | 即座に Abort |
| **UnexpectedSystemError** | unexpected | Abort | 0 | N/A | 即座に Abort。Retry 禁止 |
| **Unclassifiable** | unexpected | Abort | 0 | N/A | 分類不能エラー。Retry 禁止 |

### 補足説明

#### Action の意味
- **Retry**: 指定された Max Attempts と Backoff Strategy に従って再試行
- **Abort**: 即座に処理を中断し、エラー状態として上位に報告
- **Skip**: 該当処理をスキップ（現時点では未使用。将来拡張用）

#### Max Attempts の意味
- 最大試行回数（初回含む）
- 0 の場合は即座に Abort（再試行なし）
- **有限性保証**: いかなる例外も無限リトライしない

---

## 4. Backoff Strategy（待機戦略）

### 4.1 Exponential Backoff + Jitter

```
wait_time = (base ** attempt) + random(0, jitter_max)
```

- **base**: 2（デフォルト）
- **jitter_max**: 1.0 秒（デフォルト）
- **適用対象**: ModelRateLimitError, ModelConnectionError

**例**（base=2, jitter_max=1.0）:
- Attempt 1: 2秒 + jitter (0~1秒) = 2~3秒
- Attempt 2: 4秒 + jitter (0~1秒) = 4~5秒
- Attempt 3: 8秒 + jitter (0~1秒) = 8~9秒

### 4.2 Linear Backoff

```
wait_time = base_interval
```

- **base_interval**: 固定待機時間
  - ModelTimeoutError: 10秒
  - InvalidModelOutputError: 5秒
- **適用対象**: ModelTimeoutError, InvalidModelOutputError

---

## 5. Budget/RateLimit の扱い

### 5.1 Rate Limit Error (429) の扱い

- **ModelRateLimitError** として分類
- **Max Attempts**: 5 回
- **Backoff**: Exponential (2^n) + Jitter
- **最終失敗時**: Abort（予算枯渇として上位に報告）

### 5.2 クォータ枯渇時の扱い

- 予算枯渇は ModelRateLimitError として扱う
- Retry しても予算が回復しない場合は、5 回目で Abort
- Orchestrator（051-C）レベルでの最終判断に委ねる

---

## 6. Unclassifiable / Unexpected の最終挙動

### 6.1 必須要件（MUST）

- **分類不能エラー**（`classify_error()` が "unexpected" を返す）は **即座に Abort**
- **UnexpectedSystemError** は **即座に Abort**
- **Retry 禁止**: 分類不能エラーは再試行しない

### 6.2 フォールバック保証

- `classify_error()` は常に有効なカテゴリ文字列を返す
- 分類失敗時は "unexpected" を返す（決して None や例外を投げない）
- 分類不能エラーは **安全に Abort** する

---

## 7. Observability（観測性）

### 7.1 ログに必ず残す項目

Retry 判断時に以下の項目をログに記録すること：

1. **Timestamp**: ISO 8601 形式
2. **Exception Type**: 例外クラス名
3. **Error Category**: `classify_error()` の戻り値
4. **Attempt Count**: 現在の試行回数
5. **Action**: Retry / Abort / Skip
6. **Wait Time**: 次回試行までの待機時間（秒）
7. **Context**: タスクタイプ、モデル ID、タスク ID
8. **Final Decision**: 最終試行時の判断（Abort / Success）

### 7.2 ログレベル

- **Retry 判断**: INFO
- **最終 Abort**: WARNING
- **分類不能エラー**: WARNING
- **予期しない例外**: ERROR

---

## 8. Test Requirements（テスト要件）

### 8.1 Decision Table 検証

- **パラメタライズテスト**: Decision Table の各行を機械的に検証
- **入力**: 例外型、attempt 回数
- **期待出力**: Action (Retry/Abort), Max Attempts, Backoff Strategy

### 8.2 有限性検証

- **テスト**: 各例外に対して Max Attempts を超えると Abort すること
- **検証項目**:
  - ModelRateLimitError: 5 回で Abort
  - ModelTimeoutError: 3 回で Abort
  - ModelConnectionError: 3 回で Abort
  - InvalidModelOutputError: 3 回で Abort
  - SandboxExecutionError: 即座に Abort
  - UnexpectedSystemError: 即座に Abort

### 8.3 Unexpected 処理検証

- **テスト**: UnexpectedSystemError は即座に Abort すること
- **テスト**: 分類不能エラー（"unexpected" カテゴリ）は即座に Abort すること
- **テスト**: 分類不能エラーは Retry しないこと

### 8.4 Backoff 検証

- **テスト**: Exponential Backoff の待機時間が正しく計算されること
- **テスト**: Linear Backoff の待機時間が固定値であること
- **テスト**: Jitter が適切に適用されること（0~jitter_max の範囲内）

---

## 9. Compatibility（互換性）

### 9.1 既存挙動の保証

- **051-A の例外クラス**: 変更なし（参照のみ）
- **`classify_error()`**: 変更なし（参照のみ）
- **`convert_http_error_to_nexus_error()`**: 変更なし（参照のみ）

### 9.2 変更影響

- **新規追加**: Retry 判断関数（`decide_retry()` 等）
- **既存呼び出し側**: 最小限の適用点追加（LLM 呼び出し、Sandbox 実行）
- **既存テスト**: 影響なし（新規テスト追加のみ）

---

## 10. Implementation Guidance（実装ガイダンス）

### 10.1 中核関数（例）

```python
@dataclass
class RetryDecision:
    """Retry 判断結果"""
    action: str  # "retry" | "abort" | "skip"
    reason: str  # 判断理由
    wait_seconds: float  # 次回試行までの待機時間（秒）
    should_retry: bool  # Retry すべきか


def decide_retry(
    error: Exception,
    attempt: int,
    context: Optional[Dict[str, Any]] = None
) -> RetryDecision:
    """
    例外に対する Retry / Abort / Skip を判断する。

    Args:
        error: 発生した例外
        attempt: 現在の試行回数（1-indexed）
        context: コンテキスト情報（タスクタイプ、モデル ID 等）

    Returns:
        RetryDecision: 判断結果
    """
    # Decision Table に基づいて判断
    pass
```

### 10.2 責務境界

- **Policy 層（`decide_retry()`）**: 判断のみ（決定表の適用）
- **呼び出し側**: 判断結果に従って Retry / Abort を実行
- **Orchestrator（051-C）**: 最終判断（Policy 層の結果を受けて統合判断）

---

## 11. Phase 2.5 Review Checklist

本 Spec は Phase 2.5 Independent Review で以下を評価する：

- [ ] Decision Table が唯一の真実として定義されているか
- [ ] 有限性保証（無限リトライがない）が明示されているか
- [ ] Unclassifiable / Unexpected の最終挙動が定義されているか
- [ ] Backoff Strategy が具体的に定義されているか
- [ ] 観測性（ログ項目）が定義されているか
- [ ] テスト要件が明文化されているか
- [ ] 実装詳細（具体的な関数名・ファイル名）が Spec に混入していないか

---

## 12. Related Documents

- **051-A Error Taxonomy**: `docs/spec/CR-NEXUS-051-A_ERROR_TAXONOMY.md`
- **CR-NEXUS-051 Specification**: `docs/spec/CR-NEXUS-051_ERROR_CLASSIFICATION_SPECIFICATION.md`
- **Implementation Plan**: `docs/spec/CR-NEXUS-051_IMPLEMENTATION_PLAN.md`
- **Core Errors**: `src/nexuscore/core/errors.py`

---

End of CR-NEXUS-051-B Retry Policy Specification.
