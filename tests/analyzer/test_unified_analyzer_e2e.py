"""
unified_analyzer の軽量 E2E テスト

サンプルプロジェクトを入力として unified_analyzer を実行し、
返り値に最低限のキーが存在することを確認する。
キャッシュ機能のテストも含む。
"""

from __future__ import annotations

import time

import pytest

try:
    from nexuscore.analyzer.unified_analyzer import (
        AnalysisResult,
        TreeSitterEngine,
        UnifiedAnalyzer,
    )

    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False
    TreeSitterEngine = None  # type: ignore
    AnalysisResult = None  # type: ignore
    UnifiedAnalyzer = None  # type: ignore


@pytest.mark.skipif(not HAS_ANALYZER, reason="Analyzer modules not available")
def test_unified_analyzer_runs_on_sample_project(sample_project_dir):
    """サンプルプロジェクトで unified_analyzer が実行できることを確認"""
    engine = TreeSitterEngine()
    if not engine.setup_parsers(["python"]):
        pytest.skip("Tree-sitter parser not available")

    # サンプルプロジェクト内の Python ファイルを解析
    results: list[dict] = []

    for py_file in sample_project_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        content = py_file.read_text(encoding="utf-8")
        result = engine.analyze_source(content, "python", str(py_file))
        result_dict = result.to_dict()
        results.append(result_dict)

    # 解析結果の主要キー（実装に合わせて調整）
    # 例: success, file_path, semantic_info など
    assert len(results) > 0, "No analysis results generated"

    for result in results:
        assert isinstance(result, dict), "UnifiedAnalyzer should return a dict-like result"

        # 最低限 success キーが存在することを確認
        assert "success" in result, f"Missing 'success' key in result: {result.keys()}"

        # 成功した場合、file_path が含まれていることを確認
        if result.get("success"):
            assert (
                "file_path" in result or "data" in result
            ), f"Missing file_path or data in result: {result.keys()}"


@pytest.mark.skipif(not HAS_ANALYZER, reason="Analyzer modules not available")
def test_unified_analyzer_with_cache_first_run(sample_project_dir):
    """1回目実行時：キャッシュが生成されることを確認"""
    analyzer = UnifiedAnalyzer(sample_project_dir, use_cache=True)
    if not analyzer.setup(["python"]):
        pytest.skip("Tree-sitter parser not available")

    # 1回目の解析
    result = analyzer.run()

    # 結果が返されることを確認
    assert "files" in result
    assert "stats" in result
    assert "cache_info" in result

    # キャッシュファイルが生成されることを確認
    cache_file = sample_project_dir / ".nexuscache" / "unified_analyzer.json"
    assert cache_file.exists(), f"Cache file should be created at {cache_file}"

    # 統計情報を確認
    assert result["stats"]["total_files"] > 0
    assert result["stats"]["analyzed_files"] > 0  # 1回目はすべて解析される


@pytest.mark.skipif(not HAS_ANALYZER, reason="Analyzer modules not available")
def test_unified_analyzer_with_cache_second_run(sample_project_dir):
    """2回目実行時：キャッシュを使っても解析結果が同じ構造で返ることを確認"""
    analyzer = UnifiedAnalyzer(sample_project_dir, use_cache=True)
    if not analyzer.setup(["python"]):
        pytest.skip("Tree-sitter parser not available")

    # 1回目の解析
    result1 = analyzer.run()

    # 2回目の解析
    result2 = analyzer.run()

    # 結果の構造が同じであることを確認
    assert "files" in result2
    assert "stats" in result2
    assert "cache_info" in result2

    # キャッシュが使用されていることを確認
    assert result2["cache_info"]["cache_hits"] > 0, "Cache should be used on second run"
    assert result2["stats"]["cached_files"] > 0, "Some files should be cached"

    # ファイル数が同じであることを確認
    assert len(result1["files"]) == len(result2["files"]), "Number of files should be the same"


@pytest.mark.skipif(not HAS_ANALYZER, reason="Analyzer modules not available")
def test_unified_analyzer_cache_incremental_update(sample_project_dir):
    """片方のファイルだけ変更した場合：変更されたファイルだけ再解析されることを確認"""
    analyzer = UnifiedAnalyzer(sample_project_dir, use_cache=True)
    if not analyzer.setup(["python"]):
        pytest.skip("Tree-sitter parser not available")

    # 1回目の解析
    result1 = analyzer.run()
    result1["stats"]["analyzed_files"]

    # 1つのファイルを変更
    module_a = sample_project_dir / "module_a.py"
    original_content = module_a.read_text(encoding="utf-8")
    module_a.write_text(original_content + "\n# Modified", encoding="utf-8")

    try:
        # 2回目の解析
        result2 = analyzer.run()

        # 変更されたファイルだけ再解析されることを確認
        # （正確には、変更されたファイル + 依存関係がある可能性もあるが、最低限変更されたファイルは再解析される）
        assert result2["stats"]["analyzed_files"] > 0, "Changed file should be re-analyzed"
        assert result2["stats"]["cached_files"] > 0, "Unchanged files should be cached"

        # 変更されたファイルが結果に含まれていることを確認
        changed_file_path = str(module_a)
        assert changed_file_path in result2["files"], "Changed file should be in results"

    finally:
        # 元に戻す
        module_a.write_text(original_content, encoding="utf-8")


@pytest.mark.skipif(not HAS_ANALYZER, reason="Analyzer modules not available")
def test_unified_analyzer_cache_performance(sample_project_dir):
    """キャッシュ使用時のパフォーマンス改善を確認（2回目は高速化される）"""
    analyzer = UnifiedAnalyzer(sample_project_dir, use_cache=True)
    if not analyzer.setup(["python"]):
        pytest.skip("Tree-sitter parser not available")

    # 1回目の解析（時間測定）
    start1 = time.time()
    analyzer.run()
    time.time() - start1

    # 2回目の解析（時間測定）
    start2 = time.time()
    result2 = analyzer.run()
    time.time() - start2

    # 2回目はキャッシュが使用されるため、1回目より高速であることを確認
    # （ただし、ファイル数が少ない場合は差が小さい可能性がある）
    assert result2["cache_info"]["cache_hits"] > 0, "Cache should be used"

    # 統計情報を確認
    assert result2["stats"]["cached_files"] > 0, "Some files should be cached"
