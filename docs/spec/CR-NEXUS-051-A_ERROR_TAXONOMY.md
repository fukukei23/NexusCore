# CR-NEXUS-051-A: Error Taxonomy（例外分類）

**Version**: 1.0.0
**Date**: 2026-01-12
**Status**: Confirmed
**Related**: CR-NEXUS-051 (Error Classification Specification)

---

## 1. 目的

NexusCore における例外を「どう扱うべきか（Retry/Abort/Skip）」に基づいて分類し、
051-B（Retry Logic）、051-C（Orchestrator Integration）における判断基盤とする。

---

## 2. Error Taxonomy 確定表

| Class | Trigger例 | Default Action | Retryable | Notes |
|-------|-----------|----------------|-----------|-------|
| **ModelRateLimitError** | HTTP 429 | Retry (backoff) | Yes | 051-Bで詳細化 |
| **ModelTimeoutError** | 応答タイムアウト | Retry | Yes | タイムアウト上限は051-B |
| **ModelConnectionError** | 一時的ネット断 | Retry | Yes | 恒久エラーは別扱い |
| **InvalidModelOutputError** | JSON崩れ | Retry→Failover候補 | Conditional | 回数上限は051-B |
| **SandboxExecutionError** | pytest失敗 | Abort（原則） | No | Self-healは別チケット |
| **SandboxSecurityError** | 危険操作検知 | Abort | No | 監査ログ優先 |
| **PatchApplyError** | パッチ適用失敗 | Abort（原則） | No | 051-B範囲外 |
| **UnexpectedSystemError** | 想定外の例外 | Abort | No | フォールバック先 |

### 補足説明

#### Retryable の定義
- **Yes**: 同一モデルでの再試行が推奨される（ネットワーク・レートリミット等の一時的障害）
- **Conditional**: 再試行条件が複雑（同一モデル再試行 or モデル切替は051-Bで定義）
- **No**: 再試行しても成功しない（ロジックエラー・セキュリティ違反等）

#### Default Action の意味
- **Retry (backoff)**: 指数バックオフでの再試行
- **Retry**: 即座または短時間での再試行
- **Retry→Failover候補**: 再試行後、モデル切替を検討
- **Abort**: 処理を中断し、エラー状態として上位に報告

---

## 3. 実装状況

### 3.1 既存例外クラス（src/nexuscore/core/errors.py）

すべての分類が既に実装済み。コード追加は不要。

```python
class NexusCoreError(Exception):
    """Base class for NexusCore-specific errors."""

class ModelRateLimitError(NexusCoreError):
    """LLM API のレートリミット（429）"""

class ModelTimeoutError(NexusCoreError):
    """LLM 応答タイムアウト"""

class ModelConnectionError(NexusCoreError):
    """ネットワーク系の一時的なエラー"""

class InvalidModelOutputError(NexusCoreError):
    """LLM 出力が期待する JSON/構造になっていない"""

class SandboxExecutionError(NexusCoreError):
    """テスト実行・コード実行系のエラー"""

class SandboxSecurityError(NexusCoreError):
    """サンドボックスセキュリティ違反（禁止モジュールの利用など）"""

class PatchApplyError(NexusCoreError):
    """patch_applier の適用失敗"""

class UnexpectedSystemError(NexusCoreError):
    """想定外の例外ラッパ"""
```

### 3.2 分類関数

`classify_error(exc: Exception) -> str`
- 例外オブジェクトを受け取り、カテゴリ文字列を返す
- 既存実装済み（src/nexuscore/core/errors.py:61-172）

`convert_http_error_to_nexus_error(exc: Exception) -> NexusCoreError`
- HTTP/SDK エラーを NexusCore 例外に変換
- 既存実装済み（src/nexuscore/core/errors.py:175-222）

---

## 4. 次フェーズへの接続

### 051-B: Retry Logic（未実施）
- 各例外に対する再試行回数、バックオフ戦略、タイムアウト上限の定義
- InvalidModelOutputError の Failover 条件詳細化

### 051-C: Orchestrator Integration（未実施）
- Orchestrator への例外伝播
- Orchestrator レベルでの最終判断（Abort/Skip/Retry）

---

## 5. 変更禁止事項（051-A範囲）

- 例外クラスの削除・リネーム
- リトライロジックの追加・変更
- 既存挙動の変更
- テストの追加（既存テストの健全性確認のみ許可）

---

## 6. 参照ドキュメント

- **Canonical Spec**: `docs/spec/CR-NEXUS-051_ERROR_CLASSIFICATION_SPECIFICATION.md`
- **Implementation Plan**: `docs/spec/CR-NEXUS-051_IMPLEMENTATION_PLAN.md`
- **Core Errors**: `src/nexuscore/core/errors.py`

---

End of CR-NEXUS-051-A Error Taxonomy Document.
