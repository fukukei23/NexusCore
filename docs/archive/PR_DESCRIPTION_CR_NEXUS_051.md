# CR-NEXUS-051: Error Classification System Implementation

## Spec
- **Spec**: `docs/spec/CR-NEXUS-051_ERROR_CLASSIFICATION_SPECIFICATION.md` v1.1.1
- **Gate**: Strict (エラー処理・再試行・自律挙動)
- **IRG**: Phase 2.5 Approve (v2)

## 実装要件（Spec 3.3 / 3.4）

### Spec 3.3: Retry / Failure Control Policy
- ✅ **3.3.1**: retryable: `rate_limit`, `timeout`, `connection`, `invalid_output`
- ✅ **3.3.1**: non-retryable: `sandbox`, `patch_apply`, `unexpected`
- ✅ **3.3.2**: リトライの有限性保証（max_retries で制御）
- ✅ **3.3.3**: Backoff 戦略（意味論レベル: 増加型/一定/待機なし）
- ✅ **3.3.4**: `unexpected` は必ず retry しない

### Spec 3.4: Unclassifiable / Unexpected Error Handling
- ✅ **3.4.2 Step 1**: 分類不能エラーは `"unexpected"` として扱う
- ✅ **3.4.2 Step 2**: warning レベルのログ記録
- ✅ **3.4.2 Step 3**: unexpected 系の標準エラーとして上位伝播
- ✅ **3.4.3**: 分類処理中の例外を捕捉し `"unexpected"` を返す

## 変更ファイル

### 実装ファイル
1. **src/nexuscore/core/errors.py**
   - `classify_error()`: 分類不能エラー時のフォールバック処理を追加（3.4.2）
   - `convert_http_error_to_nexus_error()`: 変換処理中の例外捕捉を追加（3.4.3）
   - 入力検証（None チェック）を追加
   - ログ記録を強化（5.3 AU-1）

2. **src/nexuscore/core/retry_utils.py**
   - `retry_with_context()`: Spec 3.3.1 のリトライ可否判定ルールを実装
   - `invalid_output` を retryable に追加
   - `unexpected` のリトライ禁止を明示的に実装（3.3.4）
   - 分類不能エラー時のフォールバックフックを追加（3.4.2）
   - logger が None でも落ちない（必ずロガーを確保）

### テストファイル
3. **tests/core/test_errors.py**
   - `TestUnclassifiableErrorHandling` クラスを追加（3テスト）
     - `test_classify_none_error`: None エラーオブジェクトの処理
     - `test_classify_error_with_exception_during_classification`: 分類処理中の例外
     - `test_convert_unclassifiable_error`: 分類不能エラーの変換

4. **tests/core/test_retry_utils.py**
   - `TestSpec33RetryControlPolicy` クラスを追加（10テスト）
     - `test_retryable_rate_limit`: rate_limit はリトライ可能
     - `test_retryable_timeout`: timeout はリトライ可能
     - `test_retryable_connection`: connection はリトライ可能
     - `test_retryable_invalid_output`: invalid_output はリトライ可能
     - `test_non_retryable_sandbox`: sandbox はリトライ不可
     - `test_non_retryable_patch_apply`: patch_apply はリトライ不可
     - `test_non_retryable_unexpected`: unexpected はリトライ禁止
     - `test_retry_finiteness_guarantee`: リトライの有限性保証
     - `test_backoff_strategy_semantic_level`: Backoff 戦略の意味論レベル
     - `test_logger_none_safety`: logger が None でも動作
   - `test_invalid_model_output_error_not_retried` を修正
     - → `test_invalid_model_output_error_is_retried` に変更（Spec 3.3.1 に準拠）

## テスト結果

### 実行コマンド
```bash
cd /home/yn441611/NexusCore
python -m pytest tests/core/test_errors.py tests/core/test_retry_utils.py -v
```

### 結果
```
86 passed in 5.32s
```

### テストケース一覧

**新規追加テスト（13ケース）**:
- `TestUnclassifiableErrorHandling` (3テスト)
- `TestSpec33RetryControlPolicy` (10テスト)

**既存テスト修正**:
- `test_invalid_model_output_error_not_retried` → `test_invalid_model_output_error_is_retried`

## 実装差分

```bash
$ git diff --stat
 src/nexuscore/core/errors.py      | 211 ++++++++++++++++++++++++++------------
 src/nexuscore/core/retry_utils.py |  43 ++++++--
 tests/core/test_errors.py         |  43 ++++++++
 tests/core/test_retry_utils.py   | 188 +++++++++++++++++++++++++++++++--
 4 files changed, 403 insertions(+), 82 deletions(-)
```

## 実装詳細

### errors.py の主な変更
- `classify_error()`: try-except で分類処理中の例外を捕捉
- 入力検証（None チェック）を追加
- 分類結果のログ記録を追加（INFO レベル）
- 分類不能エラー時の warning ログを追加

### retry_utils.py の主な変更
- `invalid_output` を retryable カテゴリに追加
- `unexpected` のリトライ禁止を明示的に実装
- 分類処理中の例外を捕捉し、non-retryable として扱う
- logger_instance が None の場合の安全な処理

## 検証項目

- ✅ retryable: rate_limit, timeout, connection, invalid_output
- ✅ non-retryable: sandbox, patch_apply, unexpected
- ✅ unexpected は必ず retry しない
- ✅ retry は有限で停止（max_retries）
- ✅ backoff は意味論レベル（増加型/一定/待機なし）
- ✅ logger が None でも落ちない（必ずロガーを確保）
- ✅ 分類不能エラー時の最終フォールバック（3.4.2 Step 1-3）

## 後方互換性

- ✅ 既存の `retry_with_context()` のシグネチャは維持
- ✅ 既存の呼び出し元が動作することを確認
- ✅ デフォルト動作は変更なし（`invalid_output` の扱いのみ変更）

---

**実装完了**: すべての Spec 要件を満たし、86テストが通過

