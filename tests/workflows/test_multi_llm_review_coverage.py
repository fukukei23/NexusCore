"""Issue #74: multi_llm_review + context_agent の未カバー行テスト"""

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ======================== multi_llm_review ========================

from nexuscore.workflows.multi_llm_review import (
    ConsensusResult,
    ModelReview,
    ReviewItem,
    _merge_consensus,
    _parse_models,
    make_summary_prompt,
)


class TestMultiLLMReviewPureFunctions:
    """純関数のテスト — 外部依存なし"""

    def test_parse_models_basic(self):
        assert _parse_models("a, b, c") == ["a", "b", "c"]

    def test_parse_models_empty(self):
        assert _parse_models("") == []

    def test_parse_models_whitespace(self):
        assert _parse_models("  gemini  ,  claude  ") == ["gemini", "claude"]

    def test_make_summary_prompt(self):
        result = make_summary_prompt("pytest失敗レビュー", "code here")
        assert "pytest失敗レビュー" in result
        assert "code here" in result
        assert "JSONスキーマ厳守" in result

    def test_merge_consensus_single_review(self):
        review = ModelReview(
            model="gpt-4o",
            summary={"issues": [{"title": "bug1"}], "severity": "high", "confidence": 0.9},
            raw="",
            ok=True,
        )
        result = _merge_consensus([review])
        assert result.issues == ["bug1"]
        assert result.confidence == 0.9
        assert "gpt-4o" in result.contributing_models[0]

    def test_merge_consensus_dedup(self):
        r1 = ModelReview(
            model="a",
            summary={"issues": [{"title": "bug1"}], "severity": "high", "confidence": 0.8},
            ok=True,
        )
        r2 = ModelReview(
            model="b",
            summary={"issues": [{"title": "bug1"}, {"title": "bug2"}], "severity": "medium", "confidence": 0.6},
            ok=True,
        )
        result = _merge_consensus([r1, r2])
        assert result.issues == ["bug1", "bug2"]
        assert abs(result.confidence - 0.7) < 0.01

    def test_merge_consensus_empty(self):
        result = _merge_consensus([])
        assert result.issues == []
        assert result.confidence == 0.0

    def test_merge_consensus_failed_model(self):
        review = ModelReview(
            model="dead-model",
            summary={"issues": [], "severity": "low", "confidence": 0.0},
            ok=False,
            error="auth error",
        )
        result = _merge_consensus([review])
        assert "(fail)" in result.contributing_models[0]

    def test_merge_consensus_max_5_issues(self):
        reviews = [
            ModelReview(
                model=f"m{i}",
                summary={"issues": [{"title": f"issue{j}"} for j in range(3)], "severity": "low", "confidence": 0.5},
                ok=True,
            )
            for i in range(3)
        ]
        result = _merge_consensus(reviews)
        assert len(result.issues) <= 5

    def test_review_item_defaults(self):
        item = ReviewItem(path="a.py", content="code")
        assert item.error == ""

    def test_consensus_result_defaults(self):
        cr = ConsensusResult()
        assert cr.issues == []
        assert cr.file_fixes == {}
        assert cr.confidence == 0.0
        assert cr.contributing_models == []


# ======================== context_agent ========================

from nexuscore.analyzer.context_agent import ContextAgent


class TestContextAgentFindProjectRoot:
    """_find_project_root (lines 31-37) のカバレッジ"""

    def test_finds_git_dir(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        (project / ".git").mkdir()

        with patch.object(Path, "cwd", return_value=project):
            with patch.object(ContextAgent, "load_or_create_context", return_value={}):
                agent = ContextAgent()
            assert ".git" in agent.project_root or agent.project_root == str(project)

    def test_finds_pyproject_toml(self, tmp_path):
        project = tmp_path / "proj"
        project.mkdir()
        (project / "pyproject.toml").write_text("[project]\nname='test'")

        with patch.object(Path, "cwd", return_value=project):
            with patch.object(ContextAgent, "load_or_create_context", return_value={}):
                agent = ContextAgent()
            assert "proj" in agent.project_root


class TestContextAgentSafeDetectFrameworks:
    """_safe_detect_frameworks (lines 138-156) のstreamlit分岐"""

    def test_streamlit_detected(self, tmp_path):
        (tmp_path / "requirements.txt").write_text("streamlit\ngradio")

        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        fw = agent._safe_detect_frameworks()
        assert "streamlit" in fw
        assert "gradio" in fw

    def test_no_requirements_file(self, tmp_path):
        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        fw = agent._safe_detect_frameworks()
        assert fw == []


class TestContextAgentSafeCountExceptions:
    """_safe_count_files / _safe_count_python_files の例外分岐 (lines 170-172, 185-187)"""

    def test_count_files_exception(self, tmp_path):
        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        with patch("os.walk", side_effect=PermissionError("denied")):
            assert agent._safe_count_files() == 0

    def test_count_python_files_exception(self, tmp_path):
        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        with patch("os.walk", side_effect=OSError("err")):
            assert agent._safe_count_python_files() == 0


class TestContextAgentGeneratePrompt:
    """generate_enhanced_test_prompt (line 347) のカバレッジ"""

    def test_returns_prompt_string(self, tmp_path):
        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        result = agent.generate_enhanced_test_prompt("def add(a,b): return a+b")
        assert "pytest" in result
        assert "add" in result


class TestContextAgentAnalyzeRequest:
    """analyze_code_request と _generate_recommendations のカバレッジ"""

    def test_analyze_code_request(self, tmp_path):
        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        agent.context_profile = {
            "dev_policy": {
                "test_import_policy": "関数を直接埋め込み",
                "error_language": "日本語",
                "quality_requirements": ["docstring必須", "エラーハンドリング必須"],
                "security_policy": ["APIキー環境変数管理"],
            }
        }
        result = agent.analyze_code_request("テストとAPI")
        assert "context" in result
        assert "prevention_rules" in result
        assert len(result["recommendations"]) >= 2

    def test_recommendations_empty_policy(self, tmp_path):
        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        agent.context_profile = {}
        rules = {
            "test_imports": False,
            "env_var_only": False,
            "require_docstring": False,
            "require_error_handling": False,
        }
        recs = agent._generate_recommendations("hello", {}, rules)
        assert recs == []


class TestContextAgentUpdateContext:
    """update_context の分岐 (lines 293-327)"""

    def test_update_with_analyzer_failure(self, tmp_path):
        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        agent.context_profile = {"existing": True}
        agent.analyzer = MagicMock()
        agent.analyzer.detect_tech_stack.side_effect = RuntimeError("boom")

        with patch.object(agent, "save_context"):
            result = agent.update_context()
        assert result["existing"] is True
        assert "last_updated" in result

    def test_update_without_analyzer(self, tmp_path):
        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        agent.context_profile = {"v": 1}
        agent.analyzer = None

        with patch.object(agent, "save_context"):
            result = agent.update_context()
        assert result["v"] == 1


class TestContextAgentSaveLoadContext:
    """save_context / load_cached_context のカバレッジ"""

    def test_save_and_load(self, tmp_path):
        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        data = {"key": "value", "nested": {"a": 1}}
        agent.save_context(data)

        loaded = agent.load_cached_context()
        assert loaded["key"] == "value"

    def test_load_corrupted_cache(self, tmp_path):
        cache_file = tmp_path / ".nexus_context.json"
        cache_file.write_text("{invalid json")

        with patch.object(ContextAgent, "load_or_create_context", return_value={}):
            agent = ContextAgent(project_root=str(tmp_path))
        with patch.object(agent, "create_new_context", return_value={"fallback": True}):
            result = agent.load_cached_context()
        assert result.get("fallback") is True
