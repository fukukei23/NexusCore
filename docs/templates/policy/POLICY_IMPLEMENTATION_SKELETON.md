# Policy Implementation Skeleton (Guidance)

## Responsibility Boundary
- Policy: 判断（Decision）を返す
- Caller (Orchestrator/Runner): 判断に従い実行する

## Required Properties
- SSOT: Decision Table を単一真実源として実装する
- Finite: 無限ループ/無限リトライが不可能であること
- Observability: decision と terminal reason をログで追跡できること
- Safe default: unexpected は安全側（retryしない）

## Suggested API Shape
- decide_policy(error, attempt, context) -> Decision
- Decision includes: action, reason, backoff_seconds, max_attempts
