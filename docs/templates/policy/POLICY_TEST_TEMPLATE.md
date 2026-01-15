# Policy Test Template

## Purpose
- Decision Table が SSOT として実装されていることをテストで固定する。

## Required Test Cases
1) Decision Table coverage
- すべての行を parametrize で検証する（入力→期待 decision）。

2) Finite guarantee
- 上限回数を超えたら必ず ABORT/STOP になること。

3) Fallback rule
- Unclassifiable/Unexpected は Retry しない（安全側）。

4) Strategy
- Backoff の計算が仕様どおり（必要に応じて）。

## Skeleton (pytest)
- テストは public API を叩く（内部実装に過度依存しない）。
- 例: decide_* / evaluate_* の戻り値を検証する。
