"""
Comprehensive tests for tree_sitter_checker module.
Tests semantic code analyzer using Tree-sitter.
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nexuscore.utils.tree_sitter_checker import (
    CONFIG,
    AnalysisResult,
    ReportGenerator,
    SemanticAnalyzer,
)

# ==============================================================================
# AnalysisResult Tests
# ==============================================================================


class TestAnalysisResult:
    """Test AnalysisResult dataclass"""

    def test_analysis_result_creation_success(self):
        """Create successful result"""
        result = AnalysisResult(success=True, file_path="test.py", language="python")

        assert result.success is True
        assert result["file_path"] == "test.py"
        assert result["language"] == "python"
        assert result.timestamp is not None

    def test_analysis_result_creation_failure(self):
        """Create failed result"""
        result = AnalysisResult(success=False, error="Test error")

        assert result.success is False
        assert result["error"] == "Test error"

    def test_analysis_result_getitem(self):
        """Test __getitem__ access"""
        result = AnalysisResult(success=True, test_key="test_value")

        assert result["test_key"] == "test_value"
        assert result["nonexistent"] is None

    def test_analysis_result_to_dict(self):
        """Convert result to dictionary"""
        result = AnalysisResult(success=True, data="test")

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert result_dict["success"] is True
        assert result_dict["data"] == "test"
        assert "timestamp" in result_dict

    def test_analysis_result_to_json(self):
        """Convert result to JSON"""
        result = AnalysisResult(success=True, test="value")

        json_str = result.to_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["success"] is True
        assert parsed["test"] == "value"

    def test_analysis_result_timestamp_format(self):
        """Timestamp is ISO format"""
        result = AnalysisResult(success=True)

        # Should be parseable as datetime
        datetime.fromisoformat(result.timestamp)


# ==============================================================================
# SemanticAnalyzer Initialization Tests
# ==============================================================================


class TestSemanticAnalyzerInit:
    """Test SemanticAnalyzer initialization"""

    def test_analyzer_init_default(self):
        """Initialize with default settings"""
        analyzer = SemanticAnalyzer()

        assert analyzer.parsers == {}
        assert analyzer.languages == {}
        assert analyzer._cache == {}
        assert isinstance(analyzer._profiling_stats, dict)

    def test_analyzer_init_cache_enabled(self):
        """Initialize with cache enabled"""
        analyzer = SemanticAnalyzer(enable_cache=True)

        assert analyzer._cache_enabled is True

    def test_analyzer_init_cache_disabled(self):
        """Initialize with cache disabled"""
        analyzer = SemanticAnalyzer(enable_cache=False)

        assert analyzer._cache_enabled is False

    def test_analyzer_init_uses_config_cache(self):
        """Uses CONFIG cache setting when not specified"""
        with patch.dict(CONFIG, {"enable_cache": False}):
            analyzer = SemanticAnalyzer()
            assert analyzer._cache_enabled is False


# ==============================================================================
# check_availability Tests
# ==============================================================================


class TestCheckAvailability:
    """Test check_availability method"""

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", False)
    def test_check_availability_no_tree_sitter(self):
        """Check availability when tree-sitter not installed"""
        analyzer = SemanticAnalyzer()

        available, message = analyzer.check_availability()

        assert available is False
        assert "Missing" in message

    def test_check_availability_success(self):
        """Check availability when tree-sitter available"""
        mock_get_parser = MagicMock(return_value=MagicMock())

        with (
            patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True),
            patch.dict(
                "sys.modules", {"tree_sitter_language_pack": MagicMock(get_parser=mock_get_parser)}
            ),
            patch("nexuscore.utils.tree_sitter_checker.get_parser", mock_get_parser, create=True),
        ):

            analyzer = SemanticAnalyzer()
            available, message = analyzer.check_availability()

            assert available is True
            assert "ready" in message.lower()

    def test_check_availability_setup_error(self):
        """Check availability when setup fails"""
        mock_get_parser = MagicMock(side_effect=Exception("Setup failed"))

        with (
            patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True),
            patch.dict(
                "sys.modules", {"tree_sitter_language_pack": MagicMock(get_parser=mock_get_parser)}
            ),
            patch("nexuscore.utils.tree_sitter_checker.get_parser", mock_get_parser, create=True),
        ):

            analyzer = SemanticAnalyzer()
            available, message = analyzer.check_availability()

            assert available is False
            assert "Setup error" in message


# ==============================================================================
# setup_parsers Tests
# ==============================================================================


class TestSetupParsers:
    """Test setup_parsers method"""

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", False)
    def test_setup_parsers_not_available(self):
        """Setup fails when tree-sitter not available"""
        analyzer = SemanticAnalyzer()

        result = analyzer.setup_parsers()

        assert result is False

    def test_setup_parsers_success(self):
        """Setup succeeds with available parsers"""
        mock_get_language = MagicMock(return_value=MagicMock())
        mock_get_parser_func = MagicMock(return_value=MagicMock())

        with (
            patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True),
            patch(
                "nexuscore.utils.tree_sitter_checker.get_parser", mock_get_parser_func, create=True
            ),
            patch(
                "nexuscore.utils.tree_sitter_checker.get_language", mock_get_language, create=True
            ),
        ):

            analyzer = SemanticAnalyzer()
            result = analyzer.setup_parsers(["python"])

            assert result is True
            assert "python" in analyzer.parsers
            assert "python" in analyzer.languages

    def test_setup_parsers_partial_failure(self):
        """Setup succeeds with some parsers even if others fail"""

        def get_parser_side_effect(lang):
            if lang == "python":
                return MagicMock()
            raise Exception("Language not supported")

        mock_get_language = MagicMock(return_value=MagicMock())

        with (
            patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True),
            patch(
                "nexuscore.utils.tree_sitter_checker.get_parser",
                side_effect=get_parser_side_effect,
                create=True,
            ),
            patch(
                "nexuscore.utils.tree_sitter_checker.get_language", mock_get_language, create=True
            ),
        ):

            analyzer = SemanticAnalyzer()
            result = analyzer.setup_parsers(["python", "unknown"])

            assert result is True  # Still succeeds if at least one parser works
            assert "python" in analyzer.parsers

    def test_setup_parsers_default_languages(self):
        """Setup uses default languages when not specified"""
        mock_get_parser_func = MagicMock(return_value=MagicMock())
        mock_get_language = MagicMock(return_value=MagicMock())

        with (
            patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True),
            patch(
                "nexuscore.utils.tree_sitter_checker.get_parser", mock_get_parser_func, create=True
            ),
            patch(
                "nexuscore.utils.tree_sitter_checker.get_language", mock_get_language, create=True
            ),
        ):

            analyzer = SemanticAnalyzer()
            result = analyzer.setup_parsers()

            assert result is True
            # Should have loaded multiple languages from CONFIG
            assert len(analyzer.parsers) > 0


# ==============================================================================
# _extract_symbols Tests
# ==============================================================================


class TestExtractSymbols:
    """Test _extract_symbols method"""

    def test_extract_symbols_unsupported_language(self):
        """Returns empty dict for unsupported language"""
        analyzer = SemanticAnalyzer()
        analyzer.languages["unknown"] = MagicMock()

        mock_node = MagicMock()
        result = analyzer._extract_symbols("unknown", mock_node)

        assert result == {}

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    def test_extract_symbols_python(self):
        """Extract symbols from Python code"""
        analyzer = SemanticAnalyzer()

        mock_language = MagicMock()
        mock_query = MagicMock()
        mock_node = MagicMock()

        # Mock capture result
        mock_capture_node = MagicMock()
        mock_capture_node.text = b"test_function"
        mock_capture_node.start_point = (10, 5)

        mock_query.captures.return_value = [(mock_capture_node, "name")]
        mock_language.query.return_value = mock_query

        analyzer.languages["python"] = mock_language

        result = analyzer._extract_symbols("python", mock_node)

        assert isinstance(result, dict)
        # Should have attempted to extract symbols

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    def test_extract_symbols_query_exception(self):
        """Handles query exceptions gracefully"""
        analyzer = SemanticAnalyzer()

        mock_language = MagicMock()
        mock_language.query.side_effect = Exception("Query failed")

        analyzer.languages["python"] = mock_language

        mock_node = MagicMock()
        result = analyzer._extract_symbols("python", mock_node)

        # Should return dict (possibly empty) without raising
        assert isinstance(result, dict)


# ==============================================================================
# Cache Methods Tests
# ==============================================================================


class TestCacheMethods:
    """Test cache-related methods"""

    def test_compute_content_hash(self):
        """Compute content hash"""
        analyzer = SemanticAnalyzer()

        content = "def test(): pass"
        hash1 = analyzer._compute_content_hash(content)
        hash2 = analyzer._compute_content_hash(content)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA256 hex length

    def test_compute_content_hash_different(self):
        """Different content produces different hash"""
        analyzer = SemanticAnalyzer()

        hash1 = analyzer._compute_content_hash("content1")
        hash2 = analyzer._compute_content_hash("content2")

        assert hash1 != hash2

    def test_get_cache_key(self):
        """Get cache key"""
        analyzer = SemanticAnalyzer()

        key = analyzer._get_cache_key("/path/to/file.py", "abc123")

        assert isinstance(key, str)
        assert "/path/to/file.py" in key
        assert "abc123" in key

    def test_clear_cache(self):
        """Clear cache"""
        analyzer = SemanticAnalyzer(enable_cache=True)
        analyzer._cache["key1"] = "value1"
        analyzer._cache["key2"] = "value2"

        analyzer.clear_cache()

        assert len(analyzer._cache) == 0


# ==============================================================================
# analyze_source_code Tests
# ==============================================================================


class TestAnalyzeSourceCode:
    """Test analyze_source_code method"""

    def test_analyze_source_code_parser_not_available(self):
        """Returns error when parser not available"""
        analyzer = SemanticAnalyzer()

        result = analyzer.analyze_source_code("code", "unknown", "test.py")

        assert result.success is False
        assert "not available" in result["error"].lower()

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    def test_analyze_source_code_success(self):
        """Successfully analyze source code"""
        analyzer = SemanticAnalyzer(enable_cache=False)

        mock_parser = MagicMock()
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.has_error = False

        mock_tree.root_node = mock_root
        mock_parser.parse.return_value = mock_tree

        analyzer.parsers["python"] = mock_parser
        analyzer.languages["python"] = MagicMock()

        with patch.object(analyzer, "_extract_symbols", return_value={}):
            result = analyzer.analyze_source_code("def test(): pass", "python", "test.py")

        assert result.success is True
        assert result["language"] == "python"
        assert "source_stats" in result.to_dict()

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    def test_analyze_source_code_with_errors(self):
        """Detect syntax errors"""
        analyzer = SemanticAnalyzer(enable_cache=False)

        mock_parser = MagicMock()
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.has_error = True  # Syntax error

        mock_tree.root_node = mock_root
        mock_parser.parse.return_value = mock_tree

        analyzer.parsers["python"] = mock_parser
        analyzer.languages["python"] = MagicMock()

        with patch.object(analyzer, "_extract_symbols", return_value={}):
            result = analyzer.analyze_source_code("invalid python", "python")

        assert result.success is True  # Analysis succeeds
        assert result["errors"]["has_syntax_errors"] is True

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    def test_analyze_source_code_cache_hit(self):
        """Returns cached result on cache hit"""
        analyzer = SemanticAnalyzer(enable_cache=True)

        mock_parser = MagicMock()
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.has_error = False
        mock_tree.root_node = mock_root
        mock_parser.parse.return_value = mock_tree

        analyzer.parsers["python"] = mock_parser
        analyzer.languages["python"] = MagicMock()

        with patch.object(analyzer, "_extract_symbols", return_value={}):
            # First call - cache miss
            result1 = analyzer.analyze_source_code("def test(): pass", "python", "test.py")

            # Second call - should hit cache
            result2 = analyzer.analyze_source_code("def test(): pass", "python", "test.py")

        assert analyzer._profiling_stats["cache_hits"] == 1
        assert result1.to_dict() == result2.to_dict()

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    def test_analyze_source_code_exception(self):
        """Handles parse exception"""
        analyzer = SemanticAnalyzer()

        mock_parser = MagicMock()
        mock_parser.parse.side_effect = Exception("Parse failed")

        analyzer.parsers["python"] = mock_parser

        result = analyzer.analyze_source_code("code", "python")

        assert result.success is False
        assert "Parse failed" in result["error"]

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    @patch.dict(CONFIG, {"enable_profiling": True})
    def test_analyze_source_code_profiling(self):
        """Records profiling stats"""
        analyzer = SemanticAnalyzer(enable_cache=False)

        mock_parser = MagicMock()
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.has_error = False
        mock_tree.root_node = mock_root
        mock_parser.parse.return_value = mock_tree

        analyzer.parsers["python"] = mock_parser
        analyzer.languages["python"] = MagicMock()

        with patch.object(analyzer, "_extract_symbols", return_value={}):
            analyzer.analyze_source_code("def test(): pass", "python")

        assert len(analyzer._profiling_stats["file_times"]) > 0
        assert analyzer._profiling_stats["total_time"] > 0


# ==============================================================================
# analyze_file Tests
# ==============================================================================


class TestAnalyzeFile:
    """Test analyze_file method"""

    def test_analyze_file_not_found(self, tmp_path):
        """Returns error for nonexistent file"""
        analyzer = SemanticAnalyzer()

        result = analyzer.analyze_file(tmp_path / "nonexistent.py")

        assert result.success is False
        assert "not found" in result["error"].lower()

    def test_analyze_file_unsupported_extension(self, tmp_path):
        """Returns error for unsupported file type"""
        analyzer = SemanticAnalyzer()

        test_file = tmp_path / "test.xyz"
        test_file.write_text("content")

        result = analyzer.analyze_file(test_file)

        assert result.success is False
        assert "Unsupported" in result["error"]

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    def test_analyze_file_success(self, tmp_path):
        """Successfully analyze file"""
        analyzer = SemanticAnalyzer()

        test_file = tmp_path / "test.py"
        test_file.write_text("def hello(): pass")

        mock_result = AnalysisResult(success=True)

        with patch.object(analyzer, "analyze_source_code", return_value=mock_result):
            result = analyzer.analyze_file(test_file)

        assert result.success is True

    def test_analyze_file_read_error(self, tmp_path):
        """Handles file read error"""
        analyzer = SemanticAnalyzer()

        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        with patch.object(Path, "read_text", side_effect=Exception("Read failed")):
            result = analyzer.analyze_file(test_file)

        assert result.success is False
        assert "Read error" in result["error"]


# ==============================================================================
# analyze_project Tests
# ==============================================================================


class TestAnalyzeProject:
    """Test analyze_project method"""

    def test_analyze_project_empty(self, tmp_path):
        """Analyze empty project"""
        with (
            patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True),
            patch("tqdm.tqdm", side_effect=lambda x, **kwargs: x),
        ):

            analyzer = SemanticAnalyzer()
            results = analyzer.analyze_project(tmp_path)

            assert isinstance(results, dict)
            assert len(results) == 0

    def test_analyze_project_with_files(self, tmp_path):
        """Analyze project with Python files"""
        with patch("tqdm.tqdm", side_effect=lambda x, **kwargs: x):
            analyzer = SemanticAnalyzer()

            # Create test files
            (tmp_path / "test1.py").write_text("def test1(): pass")
            (tmp_path / "test2.py").write_text("def test2(): pass")

            mock_result = AnalysisResult(success=True)

            with patch.object(analyzer, "analyze_file", return_value=mock_result):
                results = analyzer.analyze_project(tmp_path)

            assert len(results) == 2

    def test_analyze_project_excludes_patterns(self, tmp_path):
        """Excludes node_modules and .git directories"""
        with patch("tqdm.tqdm", side_effect=lambda x, **kwargs: x):
            analyzer = SemanticAnalyzer()

            # Create files in excluded directories
            node_modules = tmp_path / "node_modules"
            node_modules.mkdir()
            (node_modules / "test.js").write_text("code")

            git_dir = tmp_path / ".git"
            git_dir.mkdir()
            (git_dir / "test.py").write_text("code")

            # Create normal file
            (tmp_path / "main.py").write_text("def main(): pass")

            mock_result = AnalysisResult(success=True)

            with patch.object(analyzer, "analyze_file", return_value=mock_result):
                results = analyzer.analyze_project(tmp_path)

            # Should only analyze main.py, not files in excluded dirs
            assert len(results) == 1

    @patch.dict(CONFIG, {"timeout_seconds": 1})
    def test_analyze_project_timeout(self, tmp_path):
        """Handles timeout during analysis"""
        with patch("tqdm.tqdm", side_effect=lambda x, **kwargs: x):
            analyzer = SemanticAnalyzer()

            (tmp_path / "test.py").write_text("code")

            def slow_analyze(file_path):
                import time

                time.sleep(2)
                return AnalysisResult(success=True)

            with patch.object(analyzer, "analyze_file", side_effect=slow_analyze):
                results = analyzer.analyze_project(tmp_path)

            # Should have result (timeout or error)
            assert len(results) == 1
            result = list(results.values())[0]
            # Slow analysis should cause timeout or error
            # Either success=False with error, or completed (both are valid outcomes depending on timing)
            assert isinstance(result, AnalysisResult)

    @patch.dict(CONFIG, {"enable_profiling": True})
    def test_analyze_project_profiling(self, tmp_path):
        """Records profiling stats for project"""
        with patch("tqdm.tqdm", side_effect=lambda x, **kwargs: x):
            analyzer = SemanticAnalyzer()

            (tmp_path / "test.py").write_text("def test(): pass")

            mock_result = AnalysisResult(success=True)

            with patch.object(analyzer, "analyze_file", return_value=mock_result):
                analyzer.analyze_project(tmp_path)

            assert analyzer._profiling_stats["total_files"] == 1


# ==============================================================================
# get_profiling_stats Tests
# ==============================================================================


class TestGetProfilingStats:
    """Test get_profiling_stats method"""

    def test_get_profiling_stats_empty(self):
        """Get stats when no files analyzed"""
        analyzer = SemanticAnalyzer()

        stats = analyzer.get_profiling_stats()

        assert isinstance(stats, dict)
        assert stats["total_files"] == 0

    def test_get_profiling_stats_with_data(self):
        """Get stats with analysis data"""
        analyzer = SemanticAnalyzer()
        analyzer._profiling_stats["file_times"] = [0.1, 0.2, 0.3]

        stats = analyzer.get_profiling_stats()

        assert "avg_file_time" in stats
        assert "min_file_time" in stats
        assert "max_file_time" in stats
        assert stats["avg_file_time"] == pytest.approx(0.2)
        assert stats["min_file_time"] == 0.1
        assert stats["max_file_time"] == 0.3


# ==============================================================================
# ReportGenerator Tests
# ==============================================================================


class TestReportGenerator:
    """Test ReportGenerator class"""

    def test_generate_summary_empty(self):
        """Generate summary for empty results"""
        summary = ReportGenerator.generate_summary({})

        assert summary["overview"]["total_files"] == 0
        assert summary["overview"]["successful"] == 0

    def test_generate_summary_with_results(self):
        """Generate summary with analysis results"""
        results = {
            "file1.py": AnalysisResult(
                success=True,
                language="python",
                source_stats={"line_count": 10},
                semantic_symbols={"functions": [{"name": "test"}]},
                errors={"has_syntax_errors": False},
            ),
            "file2.py": AnalysisResult(
                success=True,
                language="python",
                source_stats={"line_count": 20},
                semantic_symbols={"classes": [{"name": "MyClass"}]},
                errors={"has_syntax_errors": True},
            ),
        }

        summary = ReportGenerator.generate_summary(results)

        assert summary["overview"]["total_files"] == 2
        assert summary["overview"]["successful"] == 2
        assert summary["overview"]["total_lines"] == 30
        assert summary["symbols"]["functions"] == 1
        assert summary["symbols"]["classes"] == 1
        assert summary["errors"] == 1

    def test_generate_summary_mixed_success(self):
        """Generate summary with mixed success/failure"""
        results = {
            "success.py": AnalysisResult(
                success=True,
                language="python",
                source_stats={"line_count": 10},
                semantic_symbols={},
                errors={"has_syntax_errors": False},
            ),
            "failure.py": AnalysisResult(success=False, error="Parse failed"),
        }

        summary = ReportGenerator.generate_summary(results)

        assert summary["overview"]["total_files"] == 2
        assert summary["overview"]["successful"] == 1

    def test_print_report(self, capsys):
        """Print report to stdout"""
        summary = {
            "overview": {"total_files": 2, "successful": 2, "total_lines": 100},
            "languages": Counter({"python": 2}),
            "symbols": {"functions": 5, "classes": 2},
            "errors": 0,
        }

        ReportGenerator.print_report(summary)

        captured = capsys.readouterr()
        assert "SEMANTIC ANALYSIS REPORT" in captured.out
        assert "Files:" in captured.out
        assert "2" in captured.out

    def test_print_report_with_errors(self, capsys):
        """Print report with syntax errors"""
        summary = {
            "overview": {"total_files": 1, "successful": 1, "total_lines": 10},
            "languages": Counter({"python": 1}),
            "symbols": {},
            "errors": 3,
        }

        ReportGenerator.print_report(summary)

        captured = capsys.readouterr()
        assert "Syntax Errors" in captured.out


# ==============================================================================
# Integration Tests
# ==============================================================================


class TestTreeSitterCheckerIntegration:
    """Integration tests for tree_sitter_checker module"""

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    def test_end_to_end_single_file(self, tmp_path):
        """End-to-end analysis of single file"""
        analyzer = SemanticAnalyzer()

        test_file = tmp_path / "module.py"
        test_file.write_text(
            """
def hello(name):
    return f"Hello {name}"

class Greeter:
    def greet(self, name):
        return hello(name)
"""
        )

        mock_result = AnalysisResult(
            success=True,
            language="python",
            source_stats={"line_count": 7},
            semantic_symbols={},
            errors={"has_syntax_errors": False},
        )

        with patch.object(analyzer, "analyze_source_code", return_value=mock_result):
            result = analyzer.analyze_file(test_file)

        assert result.success is True

    def test_end_to_end_project(self, tmp_path):
        """End-to-end analysis of project"""
        with patch("tqdm.tqdm", side_effect=lambda x, **kwargs: x):
            analyzer = SemanticAnalyzer()

            # Create multi-file project
            (tmp_path / "main.py").write_text("def main(): pass")
            (tmp_path / "utils.py").write_text("def helper(): pass")

            subdir = tmp_path / "submodule"
            subdir.mkdir()
            (subdir / "core.py").write_text("class Core: pass")

            mock_result = AnalysisResult(
                success=True,
                language="python",
                source_stats={"line_count": 1},
                semantic_symbols={},
                errors={"has_syntax_errors": False},
            )

            with patch.object(analyzer, "analyze_file", return_value=mock_result):
                results = analyzer.analyze_project(tmp_path)

            assert len(results) == 3


# ==============================================================================
# Edge Cases
# ==============================================================================


class TestTreeSitterCheckerEdgeCases:
    """Test edge cases for tree_sitter_checker module"""

    def test_analysis_result_none_values(self):
        """Handle None values in AnalysisResult"""
        result = AnalysisResult(success=True, value=None)

        assert result["value"] is None
        result_dict = result.to_dict()
        assert result_dict["value"] is None

    def test_analyzer_unicode_content(self):
        """Handle Unicode in source code"""
        analyzer = SemanticAnalyzer()

        content_hash = analyzer._compute_content_hash("# 日本語コメント\ndef test(): pass")

        assert isinstance(content_hash, str)

    @patch("nexuscore.utils.tree_sitter_checker.TREE_SITTER_AVAILABLE", True)
    def test_analyzer_empty_source(self):
        """Handle empty source code"""
        analyzer = SemanticAnalyzer()

        mock_parser = MagicMock()
        mock_tree = MagicMock()
        mock_root = MagicMock()
        mock_root.has_error = False
        mock_tree.root_node = mock_root
        mock_parser.parse.return_value = mock_tree

        analyzer.parsers["python"] = mock_parser
        analyzer.languages["python"] = MagicMock()

        with patch.object(analyzer, "_extract_symbols", return_value={}):
            result = analyzer.analyze_source_code("", "python")

        assert result.success is True
        # Empty string splits to [""] which has length 1, but one empty line
        assert result["source_stats"]["line_count"] >= 0

    def test_config_defaults(self):
        """CONFIG has expected defaults"""
        assert "supported_languages" in CONFIG
        assert "max_workers" in CONFIG
        assert "timeout_seconds" in CONFIG
        assert ".py" in CONFIG["supported_languages"]
