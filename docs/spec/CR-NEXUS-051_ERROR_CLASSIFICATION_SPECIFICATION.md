# CR-NEXUS-051: エラー分類システム仕様

**文書ID**: CR-NEXUS-051
**バージョン**: 1.1.1
**最終更新**: 2025-01-06
**ステータス**: Phase 2.5 Approve（実装フェーズ移行可能）
**担当レイヤー**: コア層（リトライ戦略の基盤）

---

## 1. 概要

### 1.1 目的

エラー分類システムは、LLM API呼び出しや外部サービス統合時に発生する様々な例外を**標準化されたカテゴリ**に分類し、適切なリトライ戦略や自己修復アクションを決定するための基盤を提供します。

これは、NexusOSの**「失敗から学ぶ」自律学習サイクル**の起点となる重要なコンポーネントです。

### 1.2 設計原則

- **Resilience First**: 一時的なエラーは自動リトライ、恒久的なエラーは学習対象
- **Classification Accuracy**: 誤分類によるリソース浪費を防ぐ
- **Extensibility**: 新しいエラータイプを容易に追加可能
- **Observability**: 全てのエラーは分類結果と共にログに記録

### 1.3 自己進化サイクルとの関係

```
エラー発生
    ↓
classify_error() ← このモジュール
    ↓
├─ 一時的 → リトライ戦略 (retry_utils.py)
│
└─ 恒久的 → PostmortemAgent → FKB学習サイクル
```

---

## 2. エラー分類体系

### 2.1 カスタム例外階層

NexusCoreは独自の例外階層を定義し、外部ライブラリの例外を標準化します。

```python
Exception (Python標準)
    └── NexusCoreError (基底クラス)
        ├── ModelRateLimitError      # レートリミット (429)
        ├── ModelTimeoutError         # タイムアウト
        ├── ModelConnectionError      # ネットワーク接続エラー
        ├── InvalidModelOutputError   # LLM出力が不正 (JSON parse等)
        ├── SandboxExecutionError     # サンドボックス実行エラー
        ├── PatchApplyError           # パッチ適用失敗
        └── UnexpectedSystemError     # 想定外のエラー
```

### 2.2 分類カテゴリ

| カテゴリ | 説明 | リトライ戦略 | 優先度 |
|---------|------|-------------|--------|
| `rate_limit` | LLM APIのレートリミット (429) | 指数バックオフ (長め) | 高 |
| `timeout` | LLM応答タイムアウト | 指数バックオフ (中) | 高 |
| `connection` | ネットワーク接続エラー | 指数バックオフ (短め) | 高 |
| `invalid_output` | LLM出力が期待する形式でない | 即座にリトライ (プロンプト改善) | 中 |
| `sandbox` | テスト実行・コード実行失敗 | リトライ不可 → FKB学習 | 中 |
| `patch_apply` | パッチ適用失敗 | リトライ不可 → FKB学習 | 中 |
| `unexpected` | 想定外のエラー | リトライ不可 → PostmortemAgent | 低 |

---

## 3. 機能仕様

### 3.1 関数: `classify_error()`

#### 3.1.1 シグネチャ

```python
def classify_error(exc: Exception) -> str:
    """
    例外からエラー種別を分類する。

    Args:
        exc (Exception): 発生した例外オブジェクト

    Returns:
        str: エラー種別文字列
            - 'rate_limit'
            - 'timeout'
            - 'connection'
            - 'invalid_output'
            - 'sandbox'
            - 'patch_apply'
            - 'unexpected'

    分類ロジック:
        1. NexusCoreカスタム例外の場合: 型で直接判定
        2. 一般的な例外の場合: メッセージと型名から推論
    """
```

#### 3.1.2 分類アルゴリズム

**Phase 1: カスタム例外の型チェック**

```python
if isinstance(exc, ModelRateLimitError):
    return "rate_limit"
if isinstance(exc, ModelTimeoutError):
    return "timeout"
# ... 以下同様
```

**Phase 2: メッセージと型名からの推論**

エラーメッセージ (`str(exc)`) と型名 (`type(exc).__name__`) を小文字化し、キーワードマッチング：

| 分類 | メッセージキーワード | 型名キーワード | 判定ロジック |
|------|-------------------|---------------|-------------|
| `rate_limit` | `"429"`, `"rate limit"` | `"ratelimit"` | OR |
| `timeout` | `"timeout"`, `"timed out"` | `"timeout"` | OR |
| `connection` | `"connection"`, `"network"`, `"dns"` | `"connection"`, `"network"` | OR |
| `invalid_output` | `"json"`, `"parse"`, `"decode"` | `"json"`, `"parse"`, `"decode"` | **OR** |
| `sandbox` | `"sandbox"`, `"subprocess"` | - | メッセージのみ |
| `patch_apply` | `"patch"`, `"apply"`, `"diff"` | - | メッセージのみ |

**重要**: `invalid_output` の判定は **OR論理**

```python
has_json_in_message = any(keyword in error_str for keyword in ["json", "parse", "decode", "invalid format"])
has_json_in_type = any(keyword in error_type for keyword in ["json", "parse", "decode"])
if has_json_in_message or has_json_in_type:  # ← OR
    return "invalid_output"
```

**理由**: 以下のケースを全て検出する必要があるため

1. `JSONParseError("Something went wrong")` → 型名のみ
2. `Exception("JSON parse error")` → メッセージのみ
3. `JSONDecodeError("Failed to decode")` → 両方

AND論理では、ケース1とケース2を見逃してしまう。

#### 3.1.3 フォールバック

全てのパターンに一致しない場合：

```python
return "unexpected"
```

### 3.2 関数: `convert_http_error_to_nexus_error()`

#### 3.2.1 目的

外部ライブラリ（OpenAI SDK、Anthropic SDK等）が発生させた例外を、NexusCoreの標準例外に変換します。

#### 3.2.2 シグネチャ

```python
def convert_http_error_to_nexus_error(exc: Exception) -> NexusCoreError:
    """
    HTTP エラーや SDK エラーを NexusCore カスタム例外に変換する。

    Args:
        exc (Exception): 発生した例外（任意の型）

    Returns:
        NexusCoreError: 分類に応じたカスタム例外

    動作:
        1. classify_error() でエラーカテゴリを判定
        2. カテゴリに応じた NexusCoreError サブクラスを生成
        3. 元のエラーメッセージを保持
    """
```

#### 3.2.3 変換テーブル

| 分類カテゴリ | 変換先例外クラス |
|------------|----------------|
| `rate_limit` | `ModelRateLimitError` |
| `timeout` | `ModelTimeoutError` |
| `connection` | `ModelConnectionError` |
| `invalid_output` | `InvalidModelOutputError` |
| `sandbox` | `SandboxExecutionError` |
| `patch_apply` | `PatchApplyError` |
| `unexpected` | `UnexpectedSystemError` |

### 3.3 Retry / Failure Control Policy

#### 3.3.1 リトライ可否の判断ルール

エラー分類に基づき、リトライ可否を判定する。判定は以下のルールに従う。

**リトライ可能（Retryable）エラー**:
- `rate_limit`: レートリミットは一時的な制約であり、時間経過で解消される可能性が高い
- `timeout`: タイムアウトは一時的なネットワーク状況やサーバー負荷による可能性が高い
- `connection`: ネットワーク接続エラーは一時的な障害の可能性が高い
- `invalid_output`: LLM出力の形式エラーは、プロンプト調整や再実行で解消される可能性がある

**リトライ不可（Non-Retryable）エラー**:
- `sandbox`: サンドボックス実行エラーは、コード自体の問題である可能性が高く、同一コードの再実行では解消されない
- `patch_apply`: パッチ適用失敗は、差分の不整合や対象ファイルの状態によるものであり、再試行では解消されない
- `unexpected`: 想定外エラーは原因が不明確であり、無制限リトライはリソース浪費を招く

#### 3.3.2 リトライの有限性保証

**SHALL要件**: すべてのリトライ処理は有限回数で終了すること。

- リトライ可能エラーに対しては、最大リトライ回数が定義されること
- 最大リトライ回数に達した場合、リトライ処理は即座に終了し、エラーを上位に伝播すること
- 無限リトライループに陥る可能性のある実装は禁止される

#### 3.3.3 Backoff 戦略（意味論レベル定義）

リトライ間隔は、エラー種別に応じた適切な待機時間を設けること。

**意味論レベルの定義**:
- **増加型待機戦略**: リトライ回数の増加に応じて、待機時間を段階的に延長する戦略
- **一定待機戦略**: 各リトライにおいて、同等の待機時間を設ける戦略
- **待機なし再試行**: 待機時間を設けず、直ちに再試行を行う戦略（初回に限定される場合を含む）

**エラー種別ごとの推奨戦略**:
- `rate_limit`: 増加型待機戦略（長） - レートリミット解除を待つ必要があるため
- `timeout`: 増加型待機戦略（中） - サーバー負荷が解消されるまでの待機
- `connection`: 増加型待機戦略（短） - ネットワーク接続の復旧を待つ
- `invalid_output`: 待機なし再試行（初回） - プロンプト調整後の即座再試行

**注意**: 具体的な数値（秒数、ミリ秒数、指数の底）は実装詳細であり、本仕様では定義しない。

#### 3.3.4 Unexpected エラーのリトライ禁止

`unexpected` カテゴリに分類されたエラーは、**リトライを禁止**する。

**理由**:
- 原因が不明確なエラーの無制限リトライは、システムリソースの浪費を招く
- 想定外エラーは、根本原因の調査が必要であり、単純な再試行では解消されない
- リトライ禁止により、早期にエラーを上位に伝播し、適切なエラーハンドリング（PostmortemAgent 等）を発動させる

### 3.4 Unclassifiable / Unexpected Error Handling

#### 3.4.1 分類不能エラーの定義

以下のいずれかの条件を満たすエラーは「分類不能」とみなす：

1. `classify_error()` 関数が、定義済みの分類カテゴリ（`rate_limit`, `timeout`, `connection`, `invalid_output`, `sandbox`, `patch_apply`, `unexpected`）のいずれにも該当しない結果を返した場合
2. エラー分類処理自体が例外を発生させた場合
3. エラーオブジェクトが `None` または不正な形式である場合

#### 3.4.2 分類不能エラー時の最終フォールバック（必須定義）

分類不能エラーが発生した場合、以下の最終フォールバック処理を**必須**として定義する：

**Step 1: 安全な分類結果の返却**
- 分類不能エラーは、すべて `"unexpected"` カテゴリとして扱う
- これにより、リトライ禁止ルールが自動的に適用される

**Step 2: エラーログの記録**
- 分類不能エラーは、適切な warning レベルのログとして記録されなければならない
- ログには、元のエラー情報、分類試行時のコンテキスト、分類失敗の理由を含める

**Step 3: 上位へのエラー伝播**
- 分類不能エラーは、unexpected 系の標準エラーとして上位レイヤーへ伝播されなければならない
- 上位レイヤー（PostmortemAgent 等）が適切なエラーハンドリングを実施する

**Step 4: 監視・アラート**
- 分類不能エラーが頻発する場合、システムの監視機構にアラートを発する
- 分類ロジックの改善が必要な可能性を示唆する

#### 3.4.3 分類不能エラーの発生防止

分類不能エラーの発生を最小化するため、以下の対策を講じる：

- **包括的なフォールバック**: `classify_error()` 関数は、すべての入力に対して少なくとも `"unexpected"` を返すことを保証する
- **例外処理**: 分類処理中の例外は捕捉し、`"unexpected"` として扱う
- **入力検証**: エラーオブジェクトの形式を検証し、不正な入力に対しては早期に `"unexpected"` を返す

---

## 4. テスト要件

### 4.1 単体テスト

**ファイル**: `tests/core/test_errors.py`

**カバレッジ目標**: 98%以上

**必須テストケース**: 45個

#### 4.1.1 カスタム例外の分類 (8テスト)

- ✅ `ModelRateLimitError` → `"rate_limit"`
- ✅ `ModelTimeoutError` → `"timeout"`
- ✅ `ModelConnectionError` → `"connection"`
- ✅ `InvalidModelOutputError` → `"invalid_output"`
- ✅ `SandboxExecutionError` → `"sandbox"`
- ✅ `PatchApplyError` → `"patch_apply"`
- ✅ `NexusCoreError` (基底) → `"unexpected"`
- ✅ `UnexpectedSystemError` → `"unexpected"`

#### 4.1.2 メッセージベースの分類 (13テスト)

**Rate Limit**:
- ✅ メッセージに `"429"` 含む
- ✅ メッセージに `"rate limit"` 含む

**Timeout**:
- ✅ メッセージに `"timeout"` 含む
- ✅ メッセージに `"timed out"` 含む

**Connection**:
- ✅ メッセージに `"connection"` 含む
- ✅ メッセージに `"network"` 含む
- ✅ メッセージに `"dns"` 含む

**Invalid Output (JSON)**:
- ✅ 型名に `"json"` 含む → `"invalid_output"` (メッセージ不問)
- ✅ メッセージに `"json"` 含む → `"invalid_output"` (型名不問)
- ✅ 型名に `"parse"` 含む → `"invalid_output"`

**Sandbox**:
- ✅ メッセージに `"sandbox"` 含む
- ✅ メッセージに `"subprocess"` 含む

**Patch**:
- ✅ メッセージに `"patch"` 含む

#### 4.1.3 型名ベースの分類 (2テスト)

- ✅ `TimeoutError` (型名) → `"timeout"`
- ✅ `ConnectionError` (型名) → `"connection"`

#### 4.1.4 フォールバック (3テスト)

- ✅ 不明なエラー → `"unexpected"`
- ✅ `KeyError` → `"unexpected"`
- ✅ `AttributeError` → `"unexpected"`

#### 4.1.5 変換関数テスト (9テスト)

- ✅ Rate limit → `ModelRateLimitError`
- ✅ Timeout → `ModelTimeoutError`
- ✅ Connection → `ModelConnectionError`
- ✅ Invalid output → `InvalidModelOutputError`
- ✅ 既に `InvalidModelOutputError` → そのまま
- ✅ Sandbox → `SandboxExecutionError`
- ✅ Patch → `PatchApplyError`
- ✅ Unexpected → `UnexpectedSystemError`
- ✅ 元のメッセージを保持

#### 4.1.6 例外階層テスト (3テスト)

- ✅ 全カスタム例外が `NexusCoreError` を継承
- ✅ `NexusCoreError` が `Exception` を継承
- ✅ `except NexusCoreError` で全てキャッチ可能

#### 4.1.7 エッジケーステスト (6テスト)

- ✅ 空メッセージのエラー
- ✅ 複数キーワードを含むエラー (優先順位確認)
- ✅ 大文字小文字混在 (case-insensitive確認)
- ✅ 既に NexusCore例外 → 変換時そのまま
- ✅ 改行を含むエラーメッセージ
- ✅ 特殊文字を含むエラーメッセージ

### 4.2 統合テスト

**シナリオ**: LLM API呼び出し → エラー発生 → 分類 → リトライ

```python
def test_llm_error_handling_workflow():
    try:
        llm_call()
    except Exception as e:
        nexus_error = convert_http_error_to_nexus_error(e)
        error_type = classify_error(nexus_error)

        if error_type in ["rate_limit", "timeout", "connection"]:
            # リトライ戦略適用
            retry_with_backoff(llm_call)
        elif error_type in ["sandbox", "patch_apply"]:
            # FKB学習サイクル発動
            trigger_postmortem_agent(nexus_error)
        else:
            # 想定外 → アラート
            alert_dev_team(nexus_error)
```

---

## 5. 非機能要件

### 5.1 パフォーマンス

- **PR-1**: 分類処理は1ms以内に完了すること
- **PR-2**: 文字列マッチングは正規表現ではなく `in` 演算子を使用（高速化）

### 5.2 拡張性

- **EX-1**: 新しいエラーカテゴリの追加は10行以内のコード変更で可能
- **EX-2**: 将来的に機械学習ベースの分類への移行を考慮

### 5.3 監査可能性

- **AU-1**: 分類結果は必ずログに記録（`logger.info()`レベル）
- **AU-2**: 誤分類の疑いがある場合、`logger.warning()` で警告

---

## 6. 実装詳細

### 6.1 モジュール構成

```
src/nexuscore/core/
├── __init__.py
├── errors.py            ← このモジュール
└── retry_utils.py       ← エラー分類を使用
```

### 6.2 依存関係

- **標準ライブラリ**: `logging`, `typing`
- **外部ライブラリ**: なし

### 6.3 ログ仕様

**ロガー名**: `nexuscore.core.errors`

**ログレベル**:
- `DEBUG`: 分類プロセスの詳細
- `INFO`: 分類結果
- `WARNING`: 誤分類の可能性がある場合

---

## 7. 既知の制限事項

### 7.1 現在の制限

1. **言語依存**: エラーメッセージが英語以外の場合、誤分類の可能性
2. **キーワードの重複**: `"timeout in json parsing"` のような複合エラーは最初のマッチで決定
3. **SDK固有エラー**: 各LLM SDKの独自例外は手動でマッピングが必要

### 7.2 将来の改善計画

- **多言語対応**: 主要言語のキーワードを追加
- **優先順位ルール**: 複数カテゴリに該当する場合の明示的な優先順位
- **SDK自動検出**: 実行時にインストール済みSDKを検出し、自動マッピング

---

## 8. 参照

- **実装ファイル**: `src/nexuscore/core/errors.py`
- **テストファイル**: `tests/core/test_errors.py`
- **関連モジュール**: `src/nexuscore/core/retry_utils.py`
- **親仕様**: NexusOS技術ホワイトペーパー（自己進化エンジン）
- **関連仕様**:
  - CR-NEXUS-050 (NPE仕様)
  - CR-NEXUS-052 (品質ゲート)

---

**承認者**: NexusCore開発チーム
**次回レビュー日**: 2026-03-28
