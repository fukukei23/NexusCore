# NexusCore フェーズ3: アーキテクチャ改善タスク仕様書

**作成日**: 2025-12-27
**対象**: Claude Code / Cursor AI
**推定工数**: 3週間（AI実行では 4-6時間）
**前提条件**: フェーズ1（セキュリティ）、フェーズ2（テストカバレッジ）が完了していること

---

## 📋 概要

フェーズ3では、プロジェクトの **アーキテクチャ品質** を向上させ、保守性・拡張性・テスト容易性を改善します。

### アーキテクチャ分析結果

包括的なコードベース分析により、以下の問題が特定されました：

| 問題 | 深刻度 | 影響範囲 | 推定工数 |
|------|--------|----------|---------|
| ①循環インポートリスク | 🔴 CRITICAL | NPE ↔ Webapp | 4-6時間 |
| ②ロギング標準化不足 | 🟡 HIGH | 40+ファイル, 194個のprint文 | 8-10時間 |
| ③設定管理の分散 | 🟡 HIGH | 4つの独立した設定システム | 10-12時間 |
| ④巨大サービスクラス | 🟡 HIGH | 1,003行のモノリシック | 12-16時間 |
| ⑤エラーハンドリング統一不足 | 🟢 MEDIUM | 25+ファイル | 6-8時間 |

**総コード影響**: 2,297行
**総推定工数**: 40-52時間

---

## 🎯 フェーズ3の焦点（優先実装）

時間とリソースの制約を考慮し、フェーズ3では **最も影響の大きい3つの問題** に焦点を当てます：

### ✅ 実装対象

1. **Task 1**: 循環インポートリスクの解消（CRITICAL）
2. **Task 2**: ロギング標準化（HIGH）
3. **Task 3**: 設定管理の統一化（HIGH）

### ⏸️ 次フェーズへ延期

4. **Task 4**: 巨大サービスクラスの分解（HIGH） → フェーズ4へ
5. **Task 5**: エラーハンドリング統一（MEDIUM） → フェーズ4へ

---

## 📝 タスク詳細

---

### **Task 1: 循環インポートリスクの解消**

**深刻度**: 🔴 CRITICAL
**推定工数**: 4-6時間
**優先度**: 最高

#### 問題の詳細

**現状の依存関係**:
```
Core/NPE Layer:
  npe/logger.py:74
    → from nexuscore.webapp.db_logger import enhance_log_transaction

Webapp Layer:
  webapp/models.py
    → from nexuscore.webapp import db

Orchestrator:
  core/orchestrator.py
    → from nexuscore.npe.engine import NPEEngine
```

**問題点**:
- コア層（NPE）がウェブアプリ層（Webapp）をインポートしている
- CLI実行時にFlask/SQLAlchemyが必要になる
- テスト時にWebappのモック構築が必須
- クリーンアーキテクチャ違反（上位層が下位層に依存）

#### 実装手順

##### 1.1 ロギングインターフェースの作成

**新規ファイル**: `src/nexuscore/core/logging_interface.py`

```python
"""
ロギングプロバイダーインターフェース

Core層とWebapp層の依存関係を切り離すための抽象化層
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path


class LoggingProvider(ABC):
    """
    ロギング拡張のための抽象インターフェース

    Core層はこのインターフェースのみに依存し、
    具体的な実装（Webapp DBロガー等）は実行時に注入される。
    """

    @abstractmethod
    def enhance_transaction(
        self,
        log_data: Dict[str, Any],
        log_file: Path
    ) -> None:
        """
        ログトランザクションの拡張処理

        Args:
            log_data: ログデータ（dict形式）
            log_file: ログファイルパス
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """プロバイダー名を返す（デバッグ用）"""
        pass


class NoOpLoggingProvider(LoggingProvider):
    """
    何もしないロギングプロバイダー（CLI/テスト用のデフォルト）
    """

    def enhance_transaction(
        self,
        log_data: Dict[str, Any],
        log_file: Path
    ) -> None:
        # 何もしない（ファイルログのみで十分）
        pass

    def get_provider_name(self) -> str:
        return "NoOpProvider"


# グローバルプロバイダーレジストリ
_logging_provider: Optional[LoggingProvider] = None


def register_logging_provider(provider: LoggingProvider) -> None:
    """
    ロギングプロバイダーを登録する

    Webappの初期化時に呼び出され、DB拡張ロガーを登録する。
    CLI実行時は呼び出されず、デフォルトのNoOpProviderが使用される。

    Args:
        provider: ロギングプロバイダーの実装
    """
    global _logging_provider
    _logging_provider = provider
    print(f"[LoggingProvider] Registered: {provider.get_provider_name()}")


def get_logging_provider() -> LoggingProvider:
    """
    現在のロギングプロバイダーを取得

    Returns:
        登録されたプロバイダー、または NoOpProvider
    """
    global _logging_provider
    if _logging_provider is None:
        _logging_provider = NoOpLoggingProvider()
    return _logging_provider
```

##### 1.2 NPE Loggerの更新

**変更ファイル**: `src/nexuscore/npe/logger.py`

**変更前** (lines 74-82):
```python
try:
    from nexuscore.webapp.db_logger import enhance_log_transaction
    enhance_log_transaction(log_data, log_file)
except ImportError:
    # Webapp が利用できない環境（CLI実行等）では無視
    pass
except Exception:
    # ログ拡張の失敗は既存の処理を止めない
    pass
```

**変更後**:
```python
# Webappへの直接依存を削除し、インターフェース経由でアクセス
from nexuscore.core.logging_interface import get_logging_provider

try:
    provider = get_logging_provider()
    provider.enhance_transaction(log_data, log_file)
except Exception as e:
    # ログ拡張の失敗は既存の処理を止めない
    print(f"[NPE-Logger] Warning: Failed to enhance log: {e}")
```

##### 1.3 Webapp DB Loggerのアダプター作成

**新規ファイル**: `src/nexuscore/webapp/logging_provider.py`

```python
"""
Webapp用のロギングプロバイダー実装
"""
from pathlib import Path
from typing import Dict, Any

from nexuscore.core.logging_interface import LoggingProvider


class WebappLoggingProvider(LoggingProvider):
    """
    WebappのDB拡張ロガーをラップするプロバイダー
    """

    def enhance_transaction(
        self,
        log_data: Dict[str, Any],
        log_file: Path
    ) -> None:
        """
        既存のDB拡張ロガーを呼び出す
        """
        from nexuscore.webapp.db_logger import enhance_log_transaction
        enhance_log_transaction(log_data, log_file)

    def get_provider_name(self) -> str:
        return "WebappDBProvider"
```

##### 1.4 Webapp初期化コードの更新

**変更ファイル**: `src/nexuscore/webapp/__init__.py`

**追加コード** (create_app関数内、初期化の最後):
```python
def create_app(testing: bool = False) -> Flask:
    """Flask アプリケーションを作成する"""
    app = Flask(__name__)

    # ... 既存の初期化コード ...

    # NEW: ロギングプロバイダーを登録
    from nexuscore.webapp.logging_provider import WebappLoggingProvider
    from nexuscore.core.logging_interface import register_logging_provider

    register_logging_provider(WebappLoggingProvider())
    print("[WebApp] Logging provider registered successfully")

    return app
```

#### 検証方法

##### テスト1: CLI実行（Webappなし）

```bash
# NPE単独実行が成功することを確認
cd /home/user/NexusCore
python -c "
from nexuscore.npe.engine import NPEEngine
from nexuscore.npe.logger import audit_log

# ログ記録が成功すること（DB拡張なしで）
audit_log('test', {}, operation_type='test')
print('✅ CLI execution successful without webapp')
"
```

**期待結果**: ImportError が発生せず、ファイルログのみが記録される

##### テスト2: Webapp統合（DB拡張あり）

```bash
# Webappが起動し、DB拡張ログが有効になることを確認
python -c "
from nexuscore.webapp import create_app
from nexuscore.core.logging_interface import get_logging_provider

app = create_app(testing=True)
provider = get_logging_provider()
print(f'Provider: {provider.get_provider_name()}')
assert provider.get_provider_name() == 'WebappDBProvider'
print('✅ Webapp logging provider active')
"
```

**期待結果**: `WebappDBProvider` が登録されている

##### テスト3: 循環インポートチェック

```bash
# 循環インポートが存在しないことを確認
python -c "
import sys
import importlib

# コアモジュールのインポート（webappをインポートしない）
import nexuscore.npe.logger
import nexuscore.npe.engine
import nexuscore.core.orchestrator

# webappがインポートされていないことを確認
assert 'nexuscore.webapp.db_logger' not in sys.modules
print('✅ No circular import detected')
"
```

#### 完了条件

- [ ] `core/logging_interface.py` が作成される
- [ ] `webapp/logging_provider.py` が作成される
- [ ] `npe/logger.py` から `webapp` への直接インポートが削除される
- [ ] `webapp/__init__.py` でプロバイダー登録が行われる
- [ ] CLI実行テストが成功する
- [ ] Webapp統合テストが成功する
- [ ] 循環インポートチェックが成功する

---

### **Task 2: ロギング標準化**

**深刻度**: 🟡 HIGH
**推定工数**: 8-10時間
**優先度**: 高

#### 問題の詳細

**現状の問題**:
- `logging.getLogger()` の使用方法が40+ファイルで不統一
- 194個の `print()` 文が散在（本番環境でログ集約不可）
- 4つの独立したロギングシステムが共存：
  1. `utils/log_config.py` - メインログ
  2. `npe/logger.py` - NPE監査ログ（JSONL）
  3. `webapp/db_logger.py` - DBログ
  4. `llm/runtime.py` - LLMランタイムログ

#### 実装手順

##### 2.1 標準化ロガーファクトリーの作成

**新規ファイル**: `src/nexuscore/logging_standard.py`

```python
"""
NexusCore 標準ロギングファクトリー

すべてのモジュールはこのファクトリーを使用してロガーを取得する。
これにより、ロギング設定の一元管理と統一されたフォーマットが実現される。
"""
from __future__ import annotations
import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler


class NexusCoreLogger:
    """標準ロガーファクトリー"""

    _configured = False
    _log_dir: Optional[Path] = None

    @classmethod
    def get_logger(
        cls,
        name: str,
        audit: bool = False
    ) -> logging.Logger:
        """
        標準ロガーを取得

        Args:
            name: モジュール名（常に __name__ を使用）
            audit: True の場合、監査ログも有効化

        Returns:
            設定済みの Logger インスタンス

        Usage:
            from nexuscore.logging_standard import NexusCoreLogger
            logger = NexusCoreLogger.get_logger(__name__)
        """
        # 初回設定
        if not cls._configured:
            cls._setup_root_config()
            cls._configured = True

        # nexuscore. プレフィックスを付与
        logger = logging.getLogger(f"nexuscore.{name}")

        # 監査ログが必要な場合は追加ハンドラーを設定
        if audit and not cls._has_audit_handler(logger):
            cls._add_audit_handler(logger)

        return logger

    @classmethod
    def _setup_root_config(cls):
        """ルートロガーの初期設定"""
        root_logger = logging.getLogger("nexuscore")
        root_logger.setLevel(logging.INFO)
        root_logger.propagate = False  # 重複ログ防止

        # ログディレクトリの取得
        cls._log_dir = cls._get_logs_dir()
        cls._log_dir.mkdir(parents=True, exist_ok=True)

        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(cls._get_formatter())
        root_logger.addHandler(console_handler)

        # ファイルハンドラー（ローテーション付き）
        file_handler = RotatingFileHandler(
            cls._log_dir / "nexuscore.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(cls._get_formatter(verbose=True))
        root_logger.addHandler(file_handler)

    @staticmethod
    def _get_formatter(verbose: bool = False) -> logging.Formatter:
        """ログフォーマッターを取得"""
        if verbose:
            return logging.Formatter(
                "%(asctime)s [%(levelname)8s] %(name)s (%(filename)s:%(lineno)d) - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        else:
            return logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                datefmt="%H:%M:%S"
            )

    @staticmethod
    def _get_logs_dir() -> Path:
        """ログディレクトリのパスを取得"""
        # 環境変数で上書き可能
        import os
        log_dir_env = os.getenv("NEXUS_LOG_DIR")
        if log_dir_env:
            return Path(log_dir_env)

        # デフォルト: プロジェクトルート/logs
        project_root = Path(__file__).parent.parent.parent
        return project_root / "logs"

    @staticmethod
    def _has_audit_handler(logger: logging.Logger) -> bool:
        """監査ハンドラーが既に追加されているかチェック"""
        return any(
            isinstance(h, logging.FileHandler) and "audit" in str(h.baseFilename)
            for h in logger.handlers
        )

    @classmethod
    def _add_audit_handler(cls, logger: logging.Logger):
        """監査ログ用の追加ハンドラーを設定"""
        audit_file = cls._log_dir / "audit.jsonl"
        audit_handler = RotatingFileHandler(
            audit_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10
        )
        audit_handler.setLevel(logging.INFO)

        # JSON形式のフォーマッター（簡易版）
        audit_handler.setFormatter(logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": "%(message)s"}',
            datefmt="%Y-%m-%dT%H:%M:%S"
        ))
        logger.addHandler(audit_handler)


# エイリアス（簡潔な利用のため）
get_logger = NexusCoreLogger.get_logger
```

##### 2.2 既存コードの移行パターン

**移行パターン1**: 標準的な `logging.getLogger(__name__)`

**変更前**:
```python
import logging
logger = logging.getLogger(__name__)
```

**変更後**:
```python
from nexuscore.logging_standard import get_logger
logger = get_logger(__name__)
```

**移行パターン2**: クラス内での使用

**変更前**:
```python
import logging

class MyAgent:
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
```

**変更後**:
```python
from nexuscore.logging_standard import get_logger

class MyAgent:
    def __init__(self):
        self.logger = get_logger(__name__)  # __name__ を使用（一貫性のため）
```

**移行パターン3**: print() 文の置き換え

**変更前**:
```python
print(f"[NPE-PolicyScanner] Context scan initiated...")
print(f"[NPE-PolicyScanner] RESULT: Sensitive pattern found. Match: '{match}'")
```

**変更後**:
```python
from nexuscore.logging_standard import get_logger
logger = get_logger(__name__)

logger.info("Context scan initiated...")
logger.warning(f"RESULT: Sensitive pattern found. Match: '{match}'")
```

##### 2.3 優先移行対象ファイル（20ファイル）

以下のファイルを優先的に移行します：

**Core Modules** (5ファイル):
1. `src/nexuscore/core/orchestrator.py`
2. `src/nexuscore/core/errors.py`
3. `src/nexuscore/core/retry_utils.py`
4. `src/nexuscore/core/job_state_machine.py`
5. `src/nexuscore/core/notifier.py`

**NPE Modules** (3ファイル):
6. `src/nexuscore/npe/engine.py`
7. `src/nexuscore/npe/logger.py` (print文を logger に置き換え)
8. `src/nexuscore/npe/policies.py` (print文を logger に置き換え)

**Agent Modules** (4ファイル):
9. `src/nexuscore/agents/base_agent.py`
10. `src/nexuscore/agents/coder_agent.py`
11. `src/nexuscore/agents/context_agent.py`
12. `src/nexuscore/agents/tester_agent.py`

**LLM Modules** (3ファイル):
13. `src/nexuscore/llm/llm_router.py`
14. `src/nexuscore/llm/config.py`
15. `src/nexuscore/llm/runtime.py`

**Service Modules** (3ファイル):
16. `src/nexuscore/services/self_healing_service.py`
17. `src/nexuscore/orchestrator.py`
18. `src/nexuscore/api/server.py`

**Webapp Modules** (2ファイル):
19. `src/nexuscore/webapp/__init__.py`
20. `src/nexuscore/webapp/db_logger.py`

#### 検証方法

```bash
# ロギング標準化のテスト
python -c "
from nexuscore.logging_standard import get_logger

logger = get_logger(__name__)
logger.info('Test info message')
logger.warning('Test warning message')
logger.error('Test error message')

print('✅ Logging standardization successful')
"

# ログファイルが生成されることを確認
ls -lh logs/nexuscore.log
```

#### 完了条件

- [ ] `logging_standard.py` が作成される
- [ ] 20個の優先ファイルが移行される
- [ ] NPE modules の `print()` 文が `logger` に置き換えられる
- [ ] ログファイルが正しく生成される
- [ ] ログローテーションが機能する

---

### **Task 3: 設定管理の統一化**

**深刻度**: 🟡 HIGH
**推定工数**: 10-12時間
**優先度**: 高

#### 問題の詳細

**現状の4つの独立した設定システム**:

1. **AppConfig** (`config/config.py`) - Flask設定
2. **SelfHealingConfig** (`config/self_healing_config.py`) - JSON設定ファイル
3. **LLMRouterConfig** (`llm/config.py`) - .env読み込み
4. **env_loader** (`config/env_loader.py`) - 別の.env読み込み

**問題点**:
- どの設定が権威的かわからない
- `.env` ファイルが複数箇所で重複読み込みされる
- 設定検証がない（必須変数チェック、型チェック等）
- テスト時の設定上書きが困難

#### 実装手順

##### 3.1 統一設定システムの作成

**新規ファイル**: `src/nexuscore/config/unified_config.py`

```python
"""
NexusCore 統一設定システム

すべての設定を一元管理し、環境変数とファイルベース設定を統合する。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional
import os
import json


@dataclass
class DatabaseConfig:
    """データベース設定"""
    uri: str
    track_modifications: bool = False

    @classmethod
    def from_env(cls) -> "DatabaseConfig":
        return cls(
            uri=os.getenv("DATABASE_URI", "sqlite:///nexuscore.db"),
            track_modifications=os.getenv(
                "SQLALCHEMY_TRACK_MODIFICATIONS", "false"
            ).lower() == "true"
        )

    def validate(self) -> None:
        """設定の妥当性をチェック"""
        if not self.uri:
            raise ValueError("DATABASE_URI is required")


@dataclass
class CeleryConfig:
    """Celery設定"""
    broker_url: str
    result_backend: str

    @classmethod
    def from_env(cls) -> "CeleryConfig":
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        return cls(
            broker_url=os.getenv("CELERY_BROKER_URL", redis_url),
            result_backend=os.getenv(
                "CELERY_RESULT_BACKEND",
                redis_url.replace(":0", ":1")
            )
        )

    def validate(self) -> None:
        """設定の妥当性をチェック"""
        if not self.broker_url:
            raise ValueError("CELERY_BROKER_URL is required")


@dataclass
class AutonomyConfig:
    """自律性レベル設定"""
    user: int = 1
    admin: int = 2
    system: int = 3

    @classmethod
    def from_env(cls) -> "AutonomyConfig":
        return cls(
            user=int(os.getenv("NEXUS_ROLE_MAX_AUTONOMY_USER", "1")),
            admin=int(os.getenv("NEXUS_ROLE_MAX_AUTONOMY_ADMIN", "2")),
            system=int(os.getenv("NEXUS_ROLE_MAX_AUTONOMY_SYSTEM", "3"))
        )

    def validate(self) -> None:
        """設定の妥当性をチェック"""
        if not (0 <= self.user <= 5):
            raise ValueError("User autonomy must be 0-5")
        if not (0 <= self.admin <= 5):
            raise ValueError("Admin autonomy must be 0-5")
        if not (0 <= self.system <= 5):
            raise ValueError("System autonomy must be 0-5")


@dataclass
class LLMConfig:
    """LLM設定"""
    default_model: str = "gpt-4"
    timeout: int = 60
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            default_model=os.getenv("NEXUS_DEFAULT_MODEL", "gpt-4"),
            timeout=int(os.getenv("NEXUS_LLM_TIMEOUT", "60")),
            max_retries=int(os.getenv("NEXUS_LLM_MAX_RETRIES", "3"))
        )

    def validate(self) -> None:
        """設定の妥当性をチェック"""
        if self.timeout <= 0:
            raise ValueError("LLM timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries must be non-negative")


@dataclass
class NexusConfig:
    """
    NexusCore統一設定

    すべての設定を集約し、環境変数とファイルベース設定を統合する。
    """

    flask_secret_key: str
    database: DatabaseConfig
    celery: CeleryConfig
    autonomy: AutonomyConfig
    llm: LLMConfig
    self_healing: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, config_file: Optional[Path] = None) -> "NexusConfig":
        """
        環境変数とファイルから設定をロード

        Args:
            config_file: 追加設定ファイルのパス（オプション）

        Returns:
            統一設定オブジェクト
        """
        # Self-healing設定をファイルからロード
        sh_config = cls._load_self_healing_config(config_file)

        # 各サブシステムの設定を作成
        config = cls(
            flask_secret_key=os.getenv(
                "FLASK_SECRET_KEY",
                "dev-secret-key-change-in-production"
            ),
            database=DatabaseConfig.from_env(),
            celery=CeleryConfig.from_env(),
            autonomy=AutonomyConfig.from_env(),
            llm=LLMConfig.from_env(),
            self_healing=sh_config
        )

        # 設定の妥当性を検証
        config.validate()

        return config

    @staticmethod
    def _load_self_healing_config(
        config_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Self-healing設定をファイルからロード"""
        if config_file is None:
            config_file = Path(".nexus/self_healing.config.json")

        if config_file.exists():
            try:
                return json.loads(config_file.read_text())
            except Exception as e:
                print(f"Warning: Failed to load {config_file}: {e}")
                return {}
        return {}

    def validate(self) -> None:
        """すべてのサブ設定の妥当性をチェック"""
        self.database.validate()
        self.celery.validate()
        self.autonomy.validate()
        self.llm.validate()

        # Flask secret keyの検証
        if self.flask_secret_key == "dev-secret-key-change-in-production":
            if os.getenv("FLASK_ENV") == "production":
                raise ValueError(
                    "Must set FLASK_SECRET_KEY in production environment"
                )

    def to_flask_config(self) -> Dict[str, Any]:
        """Flask設定辞書に変換"""
        return {
            "SECRET_KEY": self.flask_secret_key,
            "SQLALCHEMY_DATABASE_URI": self.database.uri,
            "SQLALCHEMY_TRACK_MODIFICATIONS": self.database.track_modifications,
        }


# グローバル設定インスタンス（シングルトン）
_config: Optional[NexusConfig] = None


def get_config(reload: bool = False) -> NexusConfig:
    """
    グローバル設定インスタンスを取得

    Args:
        reload: True の場合、設定を再読み込み

    Returns:
        NexusConfig インスタンス
    """
    global _config
    if _config is None or reload:
        _config = NexusConfig.from_env()
    return _config


def set_config(config: NexusConfig) -> None:
    """
    グローバル設定を上書き（テスト用）

    Args:
        config: 設定オブジェクト
    """
    global _config
    _config = config
```

##### 3.2 既存設定システムの移行

**変更ファイル1**: `src/nexuscore/config/config.py`

**変更前**:
```python
class AppConfig:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")
    # ... 多数の環境変数読み込み
```

**変更後**:
```python
# 後方互換性のため、統一設定へのプロキシとして機能
from nexuscore.config.unified_config import get_config

class AppConfig:
    """
    DEPRECATED: Use nexuscore.config.unified_config.get_config() instead

    This class is kept for backward compatibility only.
    """

    @classmethod
    def _get_unified_config(cls):
        return get_config()

    @property
    def SECRET_KEY(self) -> str:
        return self._get_unified_config().flask_secret_key

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return self._get_unified_config().database.uri

    # ... 他のプロパティも同様に移行
```

**変更ファイル2**: `src/nexuscore/webapp/__init__.py`

**変更前**:
```python
from nexuscore.config.config import AppConfig

def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.from_object(AppConfig)
    # ...
```

**変更後**:
```python
from nexuscore.config.unified_config import get_config

def create_app(testing: bool = False) -> Flask:
    app = Flask(__name__)

    # 統一設定をロード
    config = get_config()
    app.config.update(config.to_flask_config())

    # ...
```

#### 検証方法

```bash
# 統一設定のテスト
python -c "
from nexuscore.config.unified_config import get_config

config = get_config()
print(f'Database URI: {config.database.uri}')
print(f'Celery Broker: {config.celery.broker_url}')
print(f'LLM Model: {config.llm.default_model}')

# 検証が機能することを確認
config.validate()
print('✅ Configuration unified successfully')
"
```

#### 完了条件

- [ ] `unified_config.py` が作成される
- [ ] `AppConfig` が統一設定へのプロキシになる
- [ ] `webapp/__init__.py` が統一設定を使用する
- [ ] 設定検証が機能する
- [ ] 既存コードが動作し続ける（後方互換性）

---

## ✅ フェーズ3完了条件

### 各タスクの完了条件

**Task 1（循環インポート）**:
- [ ] Core層とWebapp層の依存が切り離される
- [ ] CLI実行がWebappなしで成功する
- [ ] 循環インポートチェックが成功する

**Task 2（ロギング）**:
- [ ] 標準ロガーファクトリーが作成される
- [ ] 20個の優先ファイルが移行される
- [ ] NPE modules の print文が削除される

**Task 3（設定管理）**:
- [ ] 統一設定システムが作成される
- [ ] Webapp が統一設定を使用する
- [ ] 設定検証が機能する

### 全体の完了条件

- [ ] すべての既存テストが PASSED
- [ ] 新規テストが追加される（各タスクに対して）
- [ ] ドキュメントが更新される
- [ ] コミット＆プッシュが完了

---

## 📊 成功メトリクス

| メトリクス | 現状 | 目標 | 達成後 |
|----------|------|------|--------|
| 循環依存数 | 1個 | 0個 | ✅ |
| 標準化されたロガー使用率 | 0% | 80%+ | ✅ |
| 独立した設定システム数 | 4個 | 1個 | ✅ |
| print文の数 | 194個 | 50個以下 | ✅ |

---

## 🚀 実行手順（Claude Code / Cursor）

### ステップ1: Task 1（循環インポート）を実装

```bash
# 1. インターフェースとプロバイダーを作成
# 2. NPE Loggerを更新
# 3. Webapp初期化を更新
# 4. テストを実行
pytest tests/npe/ -v
```

### ステップ2: Task 2（ロギング）を実装

```bash
# 1. 標準ロガーファクトリーを作成
# 2. 優先20ファイルを移行
# 3. NPE print文を置き換え
# 4. ログファイル生成を確認
ls -lh logs/
```

### ステップ3: Task 3（設定管理）を実装

```bash
# 1. 統一設定を作成
# 2. 既存システムを移行
# 3. 検証を追加
# 4. テストを実行
python -c "from nexuscore.config.unified_config import get_config; get_config().validate()"
```

### ステップ4: コミット＆プッシュ

```bash
git add src/nexuscore/core/logging_interface.py \
        src/nexuscore/webapp/logging_provider.py \
        src/nexuscore/logging_standard.py \
        src/nexuscore/config/unified_config.py \
        # ... その他の変更ファイル

git commit -m "arch: Implement Phase 3 architecture improvements

- Decouple Core/NPE from Webapp (circular import fix)
- Standardize logging across 20+ modules
- Unify configuration management into single system

Coverage improvements:
- Circular dependencies: 1 → 0
- Standardized logging: 0% → 80%
- Configuration systems: 4 → 1
- Print statements: 194 → <50
"

git push origin claude/code-review-assessment-01PQXiLvM9oaUfBZaJfABDm6
```

---

**この仕様書に従って、フェーズ3のアーキテクチャ改善を完了させてください。**
