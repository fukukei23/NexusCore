# SPEC: Retry Utils (retry_utils.py)

**作成日**: 2026-01-08
**対象コード**: `src/nexuscore/core/retry_utils.py`
**根拠**: コード実装、既存テスト（tests/core/test_retry_utils.py）

---

## As-is（現状動作）

### 公開API

1. **RetryContext クラス**
   - `__init__()`: retry_count=0, last_error_class=None, error_summary=[] で初期化
   - `record_attempt(attempt: int, error: Optional[Exception])`: 試行を記録
     - attempt > 0 なら retry_count を更新
     - error があれば classify_error() で分類し、last_error_class と error_summary に追加
   - `to_dict() -> Dict[str, Any]`: {"retry_count", "last_error_class", "error_summary"} を返す
   - **根拠**: retry_utils.py:22-60

2. **retry_with_context() 関数**
   - シグネチャ: `retry_with_context(func, *, max_retries=2, base_delay=1.0, retry_on=None, logger_instance=None, context=None)`
   - **根拠**: retry_utils.py:63-179

3. **retry() デコレータ**
   - シグネチャ: `retry(func=None, *, max_retries=2, base_delay=1.0, retry_on=None, logger_instance=None)`
   - 内部で retry_with_context() を呼び出す
   - **根拠**: retry_utils.py:182-220

### 回数定義

- **max_retries**: 最大リトライ回数（デフォルト: 2）
- **試行ループ**: `for attempt in range(max_retries + 1):` （retry_utils.py:101）
  - attempt は 0-indexed
  - 最大試行回数 = max_retries + 1 回
  - 例: max_retries=2 → 試行回数は 0, 1, 2 の計3回
- **根拠**: retry_utils.py:101

### sleep呼び出し箇所

- **retry_utils.py:172**: `time.sleep(delay)` where `delay = base_delay * (2 ** attempt)`
- **呼び出し条件**: リトライ可能エラーが発生し、かつ `attempt < max_retries` の場合
- **指数バックオフ**: attempt=0 → delay=base_delay×1, attempt=1 → delay=base_delay×2, attempt=2 → delay=base_delay×4
- **根拠**: retry_utils.py:164-172

### classifierの扱い

- **retry_utils.py:113-148**: リトライ可否判断で `classify_error(e)` を呼び出し
- **正常系**:
  - `isinstance(e, retry_on)` → should_retry = True（retry_utils.py:114-115）
  - `isinstance(e, NexusCoreError)` → classify_error(e) で判定（retry_utils.py:116-127）
    - "unexpected" → should_retry = False（retry_utils.py:120-121）
    - "rate_limit", "timeout", "connection", "invalid_output" → should_retry = True（retry_utils.py:123-124）
    - その他 → should_retry = False（retry_utils.py:126-127）
  - 一般的な例外 → classify_error(e) で判定（retry_utils.py:128-138）
- **異常系（classifier例外）**:
  - `except Exception as classification_error:` で捕捉（retry_utils.py:139）
  - ログに警告を出力（retry_utils.py:141-147）
  - `should_retry = False` を設定（retry_utils.py:148）
  - **→ リトライを継続せず、次のチェックで停止する**
- **根拠**: retry_utils.py:113-148

### 最終失敗の扱い

- **停止条件**: `if attempt >= max_retries or not should_retry:` （retry_utils.py:155）
- **動作**:
  - エラーログを出力（retry_utils.py:157-161）
  - 例外を re-raise（retry_utils.py:162）
- **→ 失敗は握りつぶされず、呼び出し元に伝播する**
- **根拠**: retry_utils.py:155-162

---

## Should（期待される動作）

### 正常系

1. **初回成功時**:
   - attempt=1 で関数が成功
   - sleep 呼び出し回数 = 0 回
   - context がある場合、retry_count=0 を記録
   - **根拠**: retry_utils.py:102-107

2. **1回失敗→次成功**:
   - attempt=2 で関数が成功（0回目失敗、1回目成功）
   - sleep 呼び出し回数 = 1 回（delay = base_delay × 2^0 = base_delay）
   - context がある場合、retry_count=1、last_error_class を記録
   - **根拠**: retry_utils.py:101-172

3. **上限到達で停止**:
   - max_retries=2 の場合、3回試行後に停止（attempt=0,1,2）
   - 最後の例外を re-raise
   - **根拠**: retry_utils.py:155-162

### リトライ可否判定

- **リトライ可能**:
  - ModelRateLimitError, ModelTimeoutError, ModelConnectionError（デフォルト）
  - classify_error() が "rate_limit", "timeout", "connection", "invalid_output" を返す場合
  - **根拠**: retry_utils.py:89-95, 123-124, 135-136

- **リトライ不可**:
  - classify_error() が "unexpected", "sandbox", "patch_apply" を返す場合
  - retry_on に含まれない一般的な例外（ValueError, KeyError など）
  - **根拠**: retry_utils.py:120-121, 126-127, 137-138

---

## Must Not（絶対禁止動作）

### MN-RETRY-01: classifier例外時のリトライ継続禁止

**条件**: `classify_error(e)` が例外を投げた場合

**禁止動作**:
- リトライを継続してはならない（should_retry を True にしてはならない）
- sleep を実行してはならない
- 追加の attempt を行ってはならない

**現状の実装**:
- retry_utils.py:139-148 で classifier例外を捕捉
- ログ警告を出力
- `should_retry = False` を設定
- → 次の停止条件チェック（retry_utils.py:155）で即座に例外を re-raise
- **→ 実装済み ✓**

**テスト必要性**: classifier例外が発生した場合にリトライが停止することを明示的に検証

---

### MN-RETRY-02: 最大試行上限を超えたattempt禁止

**条件**: `max_retries` が設定されている場合

**禁止動作**:
- `max_retries + 1` 回を超えて試行してはならない
- 無限ループに陥ってはならない

**現状の実装**:
- retry_utils.py:101 `for attempt in range(max_retries + 1):` でループ回数を制限
- retry_utils.py:155 `if attempt >= max_retries or not should_retry:` で停止条件チェック
- **→ 実装済み ✓**

**テスト必要性**: max_retries=2 で3回試行後に停止することを検証（既存テスト `test_max_retries_exhausted`, `test_retry_finiteness_guarantee` で十分）

---

### MN-RETRY-03: non-retryable判定後のリトライ禁止

**条件**: `classify_error(e)` が "unexpected", "sandbox", "patch_apply" を返した場合、または retry_on に含まれない例外の場合

**禁止動作**:
- リトライしてはならない（should_retry を True にしてはならない）
- sleep を実行してはならない

**現状の実装**:
- retry_utils.py:120-121, 126-127, 132-133, 137-138 で should_retry = False を設定
- retry_utils.py:155 `if attempt >= max_retries or not should_retry:` で即座に例外を re-raise
- **→ 実装済み ✓**

**テスト必要性**: non-retryable エラーで即座に停止することを検証（既存テスト `test_non_retryable_sandbox`, `test_non_retryable_patch_apply`, `test_non_retryable_unexpected` で十分）

---

## 非決定性要素

### time.sleep の実行

- **課題**: retry_utils.py:172 で実 `time.sleep()` を呼び出し
- **影響**: テスト実行時間が長くなる、wall-clock 依存のタイミング問題が発生する可能性
- **対策**: テストでは `time.sleep` をモックして、呼び出し回数と引数を観測する
- **fixture名**: `mock_sleep` （tests/conftest.py に追加予定）

---

## 変更履歴

- 2026-01-08: 初版作成（Batch 0 ミニ - 逆TDD テスト整備）
