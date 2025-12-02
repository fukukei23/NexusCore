"""
tree_sitter_checker の最適化機能のテスト

- キャッシュ機能のテスト
- プロファイリング統計のテスト
- タイムアウトとフェイルセーフのテスト
"""

import pytest
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

try:
    from nexuscore.utils.tree_sitter_checker import SemanticAnalyzer, AnalysisResult, CONFIG, TREE_SITTER_AVAILABLE
except ImportError:
    TREE_SITTER_AVAILABLE = False
    SemanticAnalyzer = AnalysisResult = CONFIG = None  # type: ignore[assignment]

# Tree-sitter 本体が入っていない環境では、このモジュール全体を skip
pytestmark = pytest.mark.skipif(
    not TREE_SITTER_AVAILABLE,
    reason="Tree-sitter not available: Missing: pip install tree-sitter tree-sitter-language-pack",
)


@pytest.fixture
def sample_project_dir(tmp_path: Path):
    """小さなサンプルプロジェクトを作成"""
    project_dir = tmp_path / "sample_project"
    project_dir.mkdir()

    # Python ファイルを複数作成
    (project_dir / "main.py").write_text("""
def hello():
    print("Hello, World!")

class MyClass:
    def method(self):
        pass
""")

    (project_dir / "utils.py").write_text("""
def helper():
    return 42
""")

    return project_dir


@pytest.fixture
def analyzer():
    """SemanticAnalyzer インスタンスを作成"""
    analyzer = SemanticAnalyzer(enable_cache=True)
    # パーサーをセットアップ（利用可能な場合のみ）
    try:
        analyzer.setup_parsers(['python'])
    except Exception:
        pytest.skip("Tree-sitter parser setup failed")
    return analyzer


@pytest.mark.skipif(not TREE_SITTER_AVAILABLE, reason="tree_sitter_checker not available")
class TestTreeSitterCheckerOptimized:
    """最適化機能のテスト"""

    def test_cache_functionality(self, analyzer, sample_project_dir):
        """キャッシュ機能が動作することを確認"""
        file_path = sample_project_dir / "main.py"

        # 1回目の解析
        result1 = analyzer.analyze_file(file_path)
        assert result1.success

        # 2回目の解析（キャッシュヒット）
        result2 = analyzer.analyze_file(file_path)
        assert result2.success

        # キャッシュヒットが記録されていることを確認
        stats = analyzer.get_profiling_stats()
        assert stats['cache_hits'] > 0
        assert stats['cache_misses'] > 0

    def test_profiling_stats(self, analyzer, sample_project_dir):
        """プロファイリング統計が記録されることを確認"""
        # プロファイリングを有効化
        with patch.dict(CONFIG, {'enable_profiling': True}):
            results = analyzer.analyze_project(sample_project_dir)

            stats = analyzer.get_profiling_stats()
            assert stats['total_files'] > 0
            assert 'file_times' in stats
            assert len(stats['file_times']) > 0

    def test_timeout_handling(self, analyzer, sample_project_dir):
        """タイムアウト処理が動作することを確認"""
        # タイムアウトを短く設定
        with patch.dict(CONFIG, {'timeout_seconds': 0.001}):
            # 通常のファイルはタイムアウトしないはず
            result = analyzer.analyze_file(sample_project_dir / "main.py")
            # タイムアウトが発生してもエラーで落ちないことを確認
            assert isinstance(result, AnalysisResult)

    def test_analyze_project_completes(self, analyzer, sample_project_dir):
        """プロジェクト解析が最後まで完了することを確認"""
        results = analyzer.analyze_project(sample_project_dir)

        # 結果が空でないことを確認
        assert len(results) > 0

        # すべての結果が AnalysisResult であることを確認
        for result in results.values():
            assert isinstance(result, AnalysisResult)

    def test_cache_clear(self, analyzer, sample_project_dir):
        """キャッシュクリアが動作することを確認"""
        file_path = sample_project_dir / "main.py"

        # 解析してキャッシュに保存
        analyzer.analyze_file(file_path)
        assert len(analyzer._cache) > 0

        # キャッシュをクリア
        analyzer.clear_cache()
        assert len(analyzer._cache) == 0

    def test_fail_safe_on_error(self, analyzer, tmp_path):
        """エラーが発生しても処理全体が落ちないことを確認"""
        # 存在しないファイル
        non_existent = tmp_path / "nonexistent.py"
        result = analyzer.analyze_file(non_existent)
        assert not result.success
        assert 'error' in result.data

        # サポートされていない拡張子
        unsupported = tmp_path / "file.txt"
        unsupported.write_text("test")
        result = analyzer.analyze_file(unsupported)
        assert not result.success


@pytest.mark.skipif(not TREE_SITTER_AVAILABLE, reason="tree_sitter_checker not available")
def test_tree_sitter_checker_smoke(sample_project_dir):
    """スモークテスト: 基本的な動作確認"""
    analyzer = SemanticAnalyzer()

    # パーサーが利用可能か確認
    available, msg = analyzer.check_availability()
    if not available:
        pytest.skip(f"Tree-sitter not available: {msg}")

    # パーサーをセットアップ
    if not analyzer.setup_parsers(['python']):
        pytest.skip("Parser setup failed")

    # プロジェクト解析を実行
    results = analyzer.analyze_project(sample_project_dir)

    # 結果が空でないことを確認
    assert len(results) > 0

    # 少なくとも1つのファイルが成功していることを確認
    successful = [r for r in results.values() if r.success]
    assert len(successful) > 0

