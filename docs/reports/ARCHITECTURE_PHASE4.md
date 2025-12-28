# NexusCore フェーズ4: アーキテクチャ完全実装タスク仕様書

**作成日**: 2025-12-28
**対象**: Claude Code / Cursor AI
**推定工数**: 2-3週間（AI実行では 3-4時間）
**前提条件**: フェーズ1-3が完了していること

---

## 📋 概要

フェーズ4では、フェーズ3で開始したアーキテクチャ改善を**完全実装**し、残りの改善項目にも着手します。

### フェーズ3の残作業

| タスク | 現状 | 目標 | 優先度 |
|--------|------|------|--------|
| Task 2: ロギング標準化 | 15% (3/194 print削除) | 80%+ | 🔴 HIGH |
| Task 3: 設定管理統一化 | 基本実装のみ | 完全移行 | 🔴 HIGH |

### 新規タスク

| タスク | 深刻度 | 推定工数 | 優先度 |
|--------|--------|---------|--------|
| Task 4: 巨大サービス分解 | HIGH | 12-16h | 🟡 MEDIUM |
| Task 5: エラーハンドリング統一 | MEDIUM | 6-8h | 🟢 LOW |

---

## 🎯 フェーズ4の実装範囲

時間とリソースの制約を考慮し、以下に焦点を当てます：

### ✅ 完全実装

1. **Task 2 完全実装**: 主要15ファイルのロガー移行 + 主要print文削除
2. **Task 3 完全実装**: Webapp + 主要モジュールの統一設定への移行

### 📋 計画作成

3. **Task 4 詳細計画**: 巨大サービスクラス分解の設計書作成
4. **Task 5 基本設計**: エラーハンドリング統一のガイドライン作成

---

## 📝 Task 2: ロギング標準化 完全実装

### 優先移行対象ファイル（15ファイル）

#### Tier 1: Critical Modules（5ファイル）- 最優先

1. **`src/nexuscore/core/orchestrator.py`** (707行)
   - Orchestratorのメインロジック
   - 多数のログ出力とprint文
   - **移行内容**:
     * `logging.getLogger(__name__)` → `get_logger(__name__)`
     * print文の削除/logger変換

2. **`src/nexuscore/core/errors.py`** (152行) ← 既にフェーズ2で移行済み
   - Skip（既に標準ロギング不使用）

3. **`src/nexuscore/core/retry_utils.py`** (192行)
   - リトライロジック
   - **移行内容**:
     * line 17: `logger = logging.getLogger(__name__)` → `from nexuscore.logging_standard import get_logger; logger = get_logger(__name__)`

4. **`src/nexuscore/npe/engine.py`**
   - NPEエンジンのコアロジック
   - **移行内容**: print文のlogger変換

5. **`src/nexuscore/api/server.py`**
   - API サーバー
   - **移行内容**: logging標準化

#### Tier 2: Agent Modules（4ファイル）

6. **`src/nexuscore/agents/base_agent.py`**
7. **`src/nexuscore/agents/coder_agent.py`**
8. **`src/nexuscore/agents/context_agent.py`**
9. **`src/nexuscore/agents/tester_agent.py`**

#### Tier 3: LLM & Service Modules（3ファイル）

10. **`src/nexuscore/llm/llm_router.py`**
11. **`src/nexuscore/services/self_healing_service.py`**
12. **`src/nexuscore/orchestrator.py`** (メインエントリーポイント)

#### Tier 4: Webapp Modules（3ファイル）

13. **`src/nexuscore/webapp/__init__.py`** ← 既に一部移行済み
14. **`src/nexuscore/webapp/views_projects.py`**
15. **`src/nexuscore/webapp/db_logger.py`**

### 実装パターン

#### パターンA: logging.getLogger の置き換え

**Before**:
```python
import logging
logger = logging.getLogger(__name__)
```

**After**:
```python
from nexuscore.logging_standard import get_logger
logger = get_logger(__name__)
```

#### パターンB: print文の置き換え

**Before**:
```python
print(f"[Orchestrator] Starting job: {job_id}")
print(f"ERROR: Failed to execute: {error}")
```

**After**:
```python
logger.info(f"Starting job: {job_id}")
logger.error(f"Failed to execute: {error}")
```

#### パターンC: クラス内ロガー

**Before**:
```python
class MyAgent:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
```

**After**:
```python
from nexuscore.logging_standard import get_logger

class MyAgent:
    def __init__(self):
        self.logger = get_logger(__name__)
```

---

## 📝 Task 3: 設定管理統一化 完全実装

### 移行対象ファイル

#### 主要移行ファイル（3ファイル）

1. **`src/nexuscore/webapp/__init__.py`**
   - `AppConfig` → `get_config()` への移行
   - Flask設定の更新

2. **`src/nexuscore/config/config.py`**
   - 後方互換性プロキシの実装
   - DEPRECATED警告の追加

3. **`src/nexuscore/llm/config.py`**
   - LLM設定の統一config への統合

### 実装手順

#### ステップ1: webapp/__init__.py の完全移行

**Before** (lines 36-38):
```python
app.config["SECRET_KEY"] = AppConfig.FLASK_SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = AppConfig.DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
```

**After**:
```python
from nexuscore.config.unified_config import get_config

config = get_config()
app.config.update(config.to_flask_config())
```

#### ステップ2: config.py の後方互換性プロキシ化

**新規実装**:
```python
"""
DEPRECATED: Use nexuscore.config.unified_config instead

This module is kept for backward compatibility only.
"""
import warnings
from nexuscore.config.unified_config import get_config

class AppConfig:
    """
    DEPRECATED: Use get_config() from nexuscore.config.unified_config

    This class proxies to the unified config system for backward compatibility.
    """

    def __init__(self):
        warnings.warn(
            "AppConfig is deprecated. Use get_config() from "
            "nexuscore.config.unified_config instead.",
            DeprecationWarning,
            stacklevel=2
        )

    @classmethod
    @property
    def FLASK_SECRET_KEY(cls):
        return get_config().flask_secret_key

    @classmethod
    @property
    def DATABASE_URI(cls):
        return get_config().database.uri

    # ... 他のプロパティも同様
```

---

## 📝 Task 4: 巨大サービスクラス分解（計画）

### 対象ファイル

**`src/nexuscore/services/self_healing_service.py`** (1,003行)

### 問題分析

**現在の構造**:
- Lines 1-100: Service orchestration & initialization
- Lines 100-300: Pull request processing
- Lines 300-600: Sandbox execution & test validation
- Lines 600-900: Patch application & validation
- Lines 900-1003: History logging & result aggregation

### 分解計画

```
src/nexuscore/services/
├── __init__.py
├── self_healing_service.py          (150行 - orchestrator only)
├── pr_processor.py                  (200行 - PR parsing & context)
├── sandbox_tester.py                (180行 - test execution)
├── patch_validator.py               (150行 - patch safety checks)
└── healing_result_aggregator.py     (100行 - result compilation)
```

### 抽出メソッド

**pr_processor.py** (新規):
```python
class PullRequestProcessor:
    """Pull request parsing and context extraction"""

    def extract_related_files(self, pr_diff: str) -> List[str]:
        """Extract files affected by PR"""
        pass

    def build_context(self, files: List[str]) -> str:
        """Build LLM context from files"""
        pass
```

**sandbox_tester.py** (新規):
```python
class SandboxTester:
    """Test execution in isolated environment"""

    def run_test_and_collect_results(
        self,
        test_file: str,
        command: str
    ) -> TestResult:
        """Execute tests and collect results"""
        pass
```

**patch_validator.py** (新規):
```python
class PatchValidator:
    """Patch safety validation"""

    def validate_patch_safety(self, patch: str) -> bool:
        """Validate patch doesn't contain危険なcode"""
        pass
```

### 実装の影響範囲

- **Breaking Changes**: 既存のimport文の更新が必要
- **Migration Path**: 段階的移行（旧クラス→新クラス）
- **Testing**: 各モジュールの単体テスト作成

---

## 📝 Task 5: エラーハンドリング統一（ガイドライン）

### 現状の問題

- 25+ファイルで広範囲の `except Exception` 使用
- Silent failures（エラーログなし）
- 一貫性のない fallback 処理

### 推奨パターン

#### パターン1: リトライ可能エラー

```python
from nexuscore.core.retry_utils import retry
from nexuscore.core.errors import ModelTimeoutError

@retry(max_retries=3, base_delay=1.0)
def call_llm_api(prompt: str) -> str:
    # LLM API呼び出し
    pass
```

#### パターン2: Fallback付きエラー

```python
from nexuscore.logging_standard import get_logger

logger = get_logger(__name__)

def process_with_fallback(data: str) -> str:
    try:
        return expensive_operation(data)
    except Exception as e:
        logger.warning(f"Expensive operation failed: {e}, using fallback")
        return fallback_operation(data)
```

#### パターン3: Fatal エラー

```python
def critical_operation():
    try:
        result = do_critical_task()
    except Exception as e:
        logger.critical(f"Critical task failed: {e}", exc_info=True)
        raise  # 必ず再発生
```

---

## ✅ フェーズ4完了条件

### Task 2（ロギング標準化）

- [ ] 15ファイルのロガー移行完了
- [ ] 主要50個のprint文削除
- [ ] ロギング標準化率 80%以上

### Task 3（設定管理統一化）

- [ ] `webapp/__init__.py` の完全移行
- [ ] `config.py` の後方互換プロキシ化
- [ ] 既存コードが動作継続

### Task 4（サービス分解計画）

- [ ] 詳細な分解設計書作成
- [ ] 抽出メソッドのインターフェース定義
- [ ] 移行パスの文書化

### Task 5（エラーハンドリング）

- [ ] ガイドライン文書作成
- [ ] 推奨パターンの定義

---

## 🚀 実行手順

### Phase A: Task 2実装（2時間）

1. Tier 1ファイル（5個）のロガー移行
2. Tier 2ファイル（4個）のロガー移行
3. Tier 3-4ファイル（6個）のロガー移行
4. print文の削除/logger変換

### Phase B: Task 3実装（1時間）

1. webapp/__init__.py の移行
2. config.py のプロキシ化
3. 動作確認

### Phase C: Task 4-5計画（1時間）

1. サービス分解設計書作成
2. エラーハンドリングガイドライン作成

---

**この仕様書に従って、フェーズ4の実装を完了させてください。**
