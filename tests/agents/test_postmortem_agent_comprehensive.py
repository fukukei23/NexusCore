"""
postmortem_agent.py の包括的テスト

カバレッジ:
- PostmortemAgent: ポストモーテム分析エージェント
  - __init__: BaseAgentの継承
  - analyze_failure_and_suggest_fkb_entry: FKBエントリ提案
    - エラーログ分析
    - 根本原因特定
    - 解決策提案
    - JSON検証
- ヘルパー関数:
  - _truncate: コンテキスト切り詰め
  - _redact: 秘匿情報マスキング
  - _validate_and_normalize: JSON検証・正規化
"""

import json
import re
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# 依存モジュールをモック
sys.modules['nexuscore.llm.llm_router'] = MagicMock()
sys.modules['nexuscore.core.retry_utils'] = MagicMock()
sys.modules['nexuscore.core.errors'] = MagicMock()

try:
    from nexuscore.agents.postmortem_agent import (
        PostmortemAgent,
        _truncate,
        _redact,
        _validate_and_normalize,
        ALLOWED_TARGETS,
    )
    from nexuscore.agents.base_agent import BaseAgent
    HAS_POSTMORTEM_AGENT = True
except ImportError:
    HAS_POSTMORTEM_AGENT = False
    PostmortemAgent = None
    BaseAgent = None
    _truncate = None
    _redact = None
    _validate_and_normalize = None
    ALLOWED_TARGETS = None


@pytest.mark.skipif(not HAS_POSTMORTEM_AGENT, reason="postmortem_agent module not available")
class TestPostmortemAgentInit:
    """PostmortemAgent 初期化のテスト"""

    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_init_inherits_base_agent(self, mock_router_class):
        """BaseAgentを継承している"""
        mock_router_class.return_value = Mock()

        agent = PostmortemAgent()

        assert isinstance(agent, BaseAgent)
        assert hasattr(agent, 'llm_router')
        assert hasattr(agent, 'logger')

    def test_system_prompt_defined(self):
        """SYSTEM_PROMPTが定義されている"""
        assert hasattr(PostmortemAgent, 'SYSTEM_PROMPT')
        assert "根本原因分析" in PostmortemAgent.SYSTEM_PROMPT or "RCA" in PostmortemAgent.SYSTEM_PROMPT


@pytest.mark.skipif(not HAS_POSTMORTEM_AGENT, reason="postmortem_agent module not available")
class TestAnalyzeFailureAndSuggestFKBEntry:
    """PostmortemAgent.analyze_failure_and_suggest_fkb_entry() のテスト"""

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_analyze_failure_basic(self, mock_router_class):
        """基本的な失敗分析"""
        fkb_entry = {
            "id": "FKB-SUGGESTION-0001",
            "error_signature": "ImportError: cannot import name 'add'",
            "cause": "テストコードが誤った名前の関数をインポートしている",
            "target": "test_file",
            "solution_pattern": {
                "type": "llm_diagnose_and_fix",
                "instruction": "Fix the import statement to use the correct function name"
            },
            "description": "インポートエラーの解決"
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(fkb_entry)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry(
            error_log="ImportError: cannot import name 'add'",
            source_code="def add_numbers(a, b): return a + b",
            test_code="from module import add",
            source_file_path="module.py",
            test_file_path="test_module.py"
        )

        assert result is not None
        assert result["id"] == "FKB-SUGGESTION-0001"
        assert result["target"] == "test_file"

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_analyze_failure_invalid_json(self, mock_router_class):
        """無効なJSONが返された場合"""
        mock_llm = Mock()
        mock_llm.execute.return_value = "Not a valid JSON"

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry(
            error_log="Error",
            source_code="code",
            test_code="test",
            source_file_path="src.py",
            test_file_path="test.py"
        )

        assert result is None

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_analyze_failure_missing_required_keys(self, mock_router_class):
        """必須キーが欠けている場合"""
        incomplete_entry = {
            "id": "FKB-0001",
            "error_signature": "Error",
            # cause, target, solution_pattern, description が欠けている
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(incomplete_entry)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry(
            error_log="Error",
            source_code="code",
            test_code="test",
            source_file_path="src.py",
            test_file_path="test.py"
        )

        assert result is None

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_analyze_failure_invalid_target(self, mock_router_class):
        """無効なtarget値の場合"""
        fkb_entry = {
            "id": "FKB-0001",
            "error_signature": "Error",
            "cause": "Cause",
            "target": "invalid_target",  # ALLOWED_TARGETSにない値
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "Fix"},
            "description": "Desc"
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(fkb_entry)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry(
            error_log="Error",
            source_code="code",
            test_code="test",
            source_file_path="src.py",
            test_file_path="test.py"
        )

        assert result is None


@pytest.mark.skipif(not HAS_POSTMORTEM_AGENT, reason="postmortem_agent module not available")
class TestTruncate:
    """_truncate() ヘルパー関数のテスト"""

    def test_truncate_short_string(self):
        """短い文字列はそのまま返す"""
        short = "Hello, World!"
        result = _truncate(short, limit=100)

        assert result == short

    def test_truncate_long_string(self):
        """長い文字列は切り詰める"""
        long_str = "A" * 1000
        result = _truncate(long_str, limit=100)

        assert len(result) < len(long_str)
        assert "..." in result

    def test_truncate_none(self):
        """Noneが渡された場合"""
        result = _truncate(None)

        assert result is None

    def test_truncate_exact_limit(self):
        """ちょうど制限サイズの場合"""
        text = "A" * 100
        result = _truncate(text, limit=100)

        assert result == text


@pytest.mark.skipif(not HAS_POSTMORTEM_AGENT, reason="postmortem_agent module not available")
class TestRedact:
    """_redact() ヘルパー関数のテスト"""

    def test_redact_aws_key(self):
        """AWSキーをマスク"""
        text = "My AWS key is AKIAIOSFODNN7EXAMPLE"
        result = _redact(text)

        assert "AKIA" not in result
        assert "REDACTED" in result

    def test_redact_api_key(self):
        """APIキーをマスク"""
        text = "api_key='sk_test_1234567890abcdef'"
        result = _redact(text)

        assert "REDACTED" in result

    def test_redact_empty_string(self):
        """空文字列"""
        result = _redact("")

        assert result == ""

    def test_redact_none(self):
        """None"""
        result = _redact(None)

        assert result is None

    def test_redact_no_secrets(self):
        """秘匿情報がない場合はそのまま返す"""
        text = "This is a normal string"
        result = _redact(text)

        assert result == text


@pytest.mark.skipif(not HAS_POSTMORTEM_AGENT, reason="postmortem_agent module not available")
class TestValidateAndNormalize:
    """_validate_and_normalize() ヘルパー関数のテスト"""

    def test_validate_valid_payload(self):
        """有効なペイロード"""
        payload = {
            "id": "FKB-0001",
            "error_signature": "Error.*pattern",
            "cause": "Root cause",
            "target": "test_file",
            "solution_pattern": {
                "type": "llm_diagnose_and_fix",
                "instruction": "Fix the issue"
            },
            "description": "Description"
        }

        result = _validate_and_normalize(payload)

        assert result is not None
        assert result["target"] == "test_file"

    def test_validate_missing_required_key(self):
        """必須キーが欠けている場合"""
        payload = {
            "id": "FKB-0001",
            "error_signature": "Error",
            # cause, target, solution_pattern, description が欠けている
        }

        result = _validate_and_normalize(payload)

        assert result is None

    def test_validate_invalid_target(self):
        """無効なtarget"""
        payload = {
            "id": "FKB-0001",
            "error_signature": "Error",
            "cause": "Cause",
            "target": "invalid",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "Fix"},
            "description": "Desc"
        }

        result = _validate_and_normalize(payload)

        assert result is None

    def test_validate_target_normalization(self):
        """target値の正規化（大文字→小文字）"""
        payload = {
            "id": "FKB-0001",
            "error_signature": "Error",
            "cause": "Cause",
            "target": "TEST_FILE",  # 大文字
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "Fix"},
            "description": "Desc"
        }

        result = _validate_and_normalize(payload)

        assert result is not None
        assert result["target"] == "test_file"  # 小文字に正規化

    def test_validate_invalid_solution_pattern(self):
        """無効なsolution_pattern"""
        payload = {
            "id": "FKB-0001",
            "error_signature": "Error",
            "cause": "Cause",
            "target": "test_file",
            "solution_pattern": {"wrong_key": "value"},  # typeとinstructionがない
            "description": "Desc"
        }

        result = _validate_and_normalize(payload)

        assert result is None

    def test_validate_invalid_regex(self):
        """無効な正規表現のerror_signature"""
        payload = {
            "id": "FKB-0001",
            "error_signature": "[invalid(regex",  # 無効な正規表現
            "cause": "Cause",
            "target": "test_file",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "Fix"},
            "description": "Desc"
        }

        result = _validate_and_normalize(payload)

        assert result is None

    def test_validate_not_dict(self):
        """辞書でない場合"""
        result = _validate_and_normalize([])

        assert result is None


@pytest.mark.skipif(not HAS_POSTMORTEM_AGENT, reason="postmortem_agent module not available")
class TestEdgeCases:
    """エッジケースのテスト"""

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_empty_error_log(self, mock_router_class):
        """空のエラーログでも動作"""
        fkb_entry = {
            "id": "FKB-0001",
            "error_signature": ".*",
            "cause": "Unknown",
            "target": "both",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "Investigate"},
            "description": "Generic error"
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(fkb_entry)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry(
            error_log="",
            source_code="code",
            test_code="test",
            source_file_path="src.py",
            test_file_path="test.py"
        )

        assert result is not None

    @patch('nexuscore.agents.base_agent.HAS_RETRY', False)
    @patch('nexuscore.agents.base_agent.LLMRouter')
    def test_japanese_error_messages(self, mock_router_class):
        """日本語エラーメッセージ"""
        fkb_entry = {
            "id": "FKB-0001",
            "error_signature": "エラー.*",
            "cause": "日本語の原因説明",
            "target": "source_file",
            "solution_pattern": {"type": "llm_diagnose_and_fix", "instruction": "修正方法"},
            "description": "日本語の説明"
        }

        mock_llm = Mock()
        mock_llm.execute.return_value = json.dumps(fkb_entry, ensure_ascii=False)

        mock_router = Mock()
        mock_router.get_llm_for_task.return_value = mock_llm
        mock_router_class.return_value = mock_router

        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry(
            error_log="エラーが発生しました",
            source_code="# コード",
            test_code="# テスト",
            source_file_path="src.py",
            test_file_path="test.py"
        )

        assert result is not None
        assert "日本語" in result["cause"]

    @patch('nexuscore.agents.base_agent.LLMRouter', None)
    def test_no_llm_router_available(self):
        """LLMRouterが利用できない場合"""
        agent = PostmortemAgent()
        result = agent.analyze_failure_and_suggest_fkb_entry(
            error_log="Error",
            source_code="code",
            test_code="test",
            source_file_path="src.py",
            test_file_path="test.py"
        )

        assert result is None
