"""
graph_builder の軽量 E2E テスト

サンプルプロジェクトを渡したときに、グラフ生成が通り、
ノードとエッジが最低限存在することを確認する。
"""

from __future__ import annotations

import pytest

try:
    from nexuscore.analyzer.graph_builder import DependencyGraphBuilder
    from nexuscore.analyzer.unified_analyzer import AnalysisResult, TreeSitterEngine

    HAS_ANALYZER = True
except ImportError:
    HAS_ANALYZER = False
    DependencyGraphBuilder = None  # type: ignore
    TreeSitterEngine = None  # type: ignore
    AnalysisResult = None  # type: ignore


@pytest.mark.skipif(not HAS_ANALYZER, reason="Analyzer modules not available")
def test_graph_builder_builds_dependency_graph(sample_project_dir):
    """サンプルプロジェクトで依存グラフが構築できることを確認"""
    # TreeSitterEngine で各ファイルを解析
    engine = TreeSitterEngine()
    if not engine.setup_parsers(["python"]):
        pytest.skip("Tree-sitter parser not available")

    results: list[AnalysisResult] = []

    # module_a.py を解析
    module_a_path = sample_project_dir / "module_a.py"
    if module_a_path.exists():
        content = module_a_path.read_text(encoding="utf-8")
        result = engine.analyze_source(content, "python", str(module_a_path))
        results.append(result)

    # module_b.py を解析
    module_b_path = sample_project_dir / "module_b.py"
    if module_b_path.exists():
        content = module_b_path.read_text(encoding="utf-8")
        result = engine.analyze_source(content, "python", str(module_b_path))
        results.append(result)

    # DependencyGraphBuilder でグラフを構築
    builder = DependencyGraphBuilder()
    graph = builder.build(results)

    # graph の API に合わせて最低限の検証を行う
    # networkx.DiGraph の場合
    nodes = list(graph.nodes())
    edges = list(graph.edges())

    assert nodes, "Graph nodes should not be empty"
    assert edges, "Graph edges should not be empty"

    # サンプルプロジェクトのモジュールが含まれていること
    node_strs = [str(n) for n in nodes]
    assert any("module_a" in n for n in node_strs), f"module_a not found in nodes: {node_strs}"
    assert any("module_b" in n for n in node_strs), f"module_b not found in nodes: {node_strs}"
