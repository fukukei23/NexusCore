"""
Comprehensive tests for analyzer/graph_builder.py

依存関係グラフ構築の包括的テスト
"""
import sys
from unittest.mock import Mock, MagicMock, patch

import pytest

# networkxのモック化（必要に応じて）
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    # networkxをモック化してimportエラーを回避
    sys.modules['networkx'] = MagicMock()
    import networkx as nx

# networkxモジュールをモック化してからimport
from nexuscore.analyzer.graph_builder import DependencyGraphBuilder
from nexuscore.analyzer.unified_analyzer import AnalysisResult


# ============================================================================
# DependencyGraphBuilder 初期化テスト
# ============================================================================
class TestDependencyGraphBuilderInit:
    @pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
    def test_init_creates_graph(self):
        """初期化時にグラフを作成"""
        builder = DependencyGraphBuilder()

        assert builder.graph is not None
        assert isinstance(builder.graph, nx.DiGraph)

    @pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
    def test_init_creates_definitions_dict(self):
        """初期化時に定義辞書を作成"""
        builder = DependencyGraphBuilder()

        assert builder.definitions is not None
        assert isinstance(builder.definitions, dict)
        assert len(builder.definitions) == 0

    @pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
    def test_init_graph_is_directed(self):
        """グラフが有向グラフ"""
        builder = DependencyGraphBuilder()

        assert isinstance(builder.graph, nx.DiGraph)

    # Note: test_init_raises_error_without_networkx は環境依存のため省略
    # networkxがインストールされていない場合、モジュールimport時にエラーが発生する


# ============================================================================
# build メソッドテスト - 基本機能
# ============================================================================
@pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
class TestBuildBasic:
    def test_build_empty_results(self):
        """空の結果リストでグラフ構築"""
        builder = DependencyGraphBuilder()
        results = []

        graph = builder.build(results)

        assert isinstance(graph, nx.DiGraph)
        assert graph.number_of_nodes() == 0
        assert graph.number_of_edges() == 0

    def test_build_single_file_single_definition(self):
        """単一ファイル・単一定義"""
        builder = DependencyGraphBuilder()

        # Mockの解析結果を作成
        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "test.py",
            "semantic_info": {
                "definitions": [
                    {"name": "func_a", "type": "function"}
                ],
                "calls": []
            }
        }

        graph = builder.build([result])

        assert graph.number_of_nodes() == 1
        assert "test.py::func_a" in graph.nodes

    def test_build_single_file_multiple_definitions(self):
        """単一ファイル・複数定義"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "module.py",
            "semantic_info": {
                "definitions": [
                    {"name": "ClassA", "type": "class"},
                    {"name": "func_b", "type": "function"},
                    {"name": "var_c", "type": "variable"}
                ],
                "calls": []
            }
        }

        graph = builder.build([result])

        assert graph.number_of_nodes() == 3
        assert "module.py::ClassA" in graph.nodes
        assert "module.py::func_b" in graph.nodes
        assert "module.py::var_c" in graph.nodes

    def test_build_multiple_files(self):
        """複数ファイル"""
        builder = DependencyGraphBuilder()

        result1 = Mock(spec=AnalysisResult)
        result1.to_dict.return_value = {
            "success": True,
            "file_path": "file1.py",
            "semantic_info": {
                "definitions": [{"name": "func_a", "type": "function"}],
                "calls": []
            }
        }

        result2 = Mock(spec=AnalysisResult)
        result2.to_dict.return_value = {
            "success": True,
            "file_path": "file2.py",
            "semantic_info": {
                "definitions": [{"name": "func_b", "type": "function"}],
                "calls": []
            }
        }

        graph = builder.build([result1, result2])

        assert graph.number_of_nodes() == 2
        assert "file1.py::func_a" in graph.nodes
        assert "file2.py::func_b" in graph.nodes

    def test_build_with_call_relationship(self):
        """呼び出し関係を含む構築"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "app.py",
            "semantic_info": {
                "definitions": [
                    {"name": "main", "type": "function"},
                    {"name": "helper", "type": "function"}
                ],
                "calls": [
                    {"scope": "main", "name": "helper"}
                ]
            }
        }

        graph = builder.build([result])

        assert graph.number_of_nodes() == 2
        assert graph.number_of_edges() == 1
        assert graph.has_edge("app.py::main", "app.py::helper")


# ============================================================================
# build メソッドテスト - エッジケース
# ============================================================================
@pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
class TestBuildEdgeCases:
    def test_build_failed_analysis_result(self):
        """失敗した解析結果をスキップ"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": False,  # 解析失敗
            "file_path": "error.py"
        }

        graph = builder.build([result])

        assert graph.number_of_nodes() == 0

    def test_build_no_semantic_info(self):
        """semantic_infoがない結果をスキップ"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "incomplete.py"
            # semantic_info がない
        }

        graph = builder.build([result])

        assert graph.number_of_nodes() == 0

    def test_build_empty_semantic_info(self):
        """空のsemantic_info"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "empty.py",
            "semantic_info": {}
        }

        graph = builder.build([result])

        assert graph.number_of_nodes() == 0

    def test_build_none_semantic_info(self):
        """Noneのsemantic_info"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "none.py",
            "semantic_info": None
        }

        graph = builder.build([result])

        assert graph.number_of_nodes() == 0

    def test_build_call_to_undefined_function(self):
        """未定義関数への呼び出し（エッジなし）"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "caller.py",
            "semantic_info": {
                "definitions": [
                    {"name": "main", "type": "function"}
                ],
                "calls": [
                    {"scope": "main", "name": "undefined_func"}  # 未定義
                ]
            }
        }

        graph = builder.build([result])

        assert graph.number_of_nodes() == 1
        assert graph.number_of_edges() == 0  # エッジは追加されない

    def test_build_duplicate_definitions_same_name(self):
        """同名の定義が複数ある場合"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "dup.py",
            "semantic_info": {
                "definitions": [
                    {"name": "func", "type": "function"},
                    {"name": "func", "type": "function"}  # 同名
                ],
                "calls": []
            }
        }

        graph = builder.build([result])

        # 同じノードIDなので1つだけ
        assert graph.number_of_nodes() == 1

        # definitionsマッピングには両方登録される
        assert "func" in builder.definitions
        assert len(builder.definitions["func"]) == 2


# ============================================================================
# ノード属性テスト
# ============================================================================
@pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
class TestNodeAttributes:
    def test_node_has_type_attribute(self):
        """ノードにtype属性がある"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "test.py",
            "semantic_info": {
                "definitions": [
                    {"name": "MyClass", "type": "class"}
                ],
                "calls": []
            }
        }

        graph = builder.build([result])
        node_data = graph.nodes["test.py::MyClass"]

        assert "type" in node_data
        assert node_data["type"] == "class"

    def test_node_has_file_attribute(self):
        """ノードにfile属性がある"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "module.py",
            "semantic_info": {
                "definitions": [
                    {"name": "func", "type": "function"}
                ],
                "calls": []
            }
        }

        graph = builder.build([result])
        node_data = graph.nodes["module.py::func"]

        assert "file" in node_data
        assert node_data["file"] == "module.py"

    def test_different_types_have_correct_attributes(self):
        """異なる型のノードが正しい属性を持つ"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "types.py",
            "semantic_info": {
                "definitions": [
                    {"name": "ClassA", "type": "class"},
                    {"name": "func_b", "type": "function"},
                    {"name": "var_c", "type": "variable"}
                ],
                "calls": []
            }
        }

        graph = builder.build([result])

        assert graph.nodes["types.py::ClassA"]["type"] == "class"
        assert graph.nodes["types.py::func_b"]["type"] == "function"
        assert graph.nodes["types.py::var_c"]["type"] == "variable"


# ============================================================================
# 統合テスト
# ============================================================================
@pytest.mark.skipif(not HAS_NETWORKX, reason="networkx not installed")
class TestGraphBuilderIntegration:
    def test_complex_multi_file_dependency(self):
        """複雑な複数ファイル依存関係"""
        builder = DependencyGraphBuilder()

        # File 1: main.py
        result1 = Mock(spec=AnalysisResult)
        result1.to_dict.return_value = {
            "success": True,
            "file_path": "main.py",
            "semantic_info": {
                "definitions": [
                    {"name": "main", "type": "function"}
                ],
                "calls": [
                    {"scope": "main", "name": "process"},
                    {"scope": "main", "name": "validate"}
                ]
            }
        }

        # File 2: utils.py
        result2 = Mock(spec=AnalysisResult)
        result2.to_dict.return_value = {
            "success": True,
            "file_path": "utils.py",
            "semantic_info": {
                "definitions": [
                    {"name": "process", "type": "function"},
                    {"name": "validate", "type": "function"}
                ],
                "calls": [
                    {"scope": "process", "name": "helper"}
                ]
            }
        }

        # File 3: helper.py
        result3 = Mock(spec=AnalysisResult)
        result3.to_dict.return_value = {
            "success": True,
            "file_path": "helper.py",
            "semantic_info": {
                "definitions": [
                    {"name": "helper", "type": "function"}
                ],
                "calls": []
            }
        }

        graph = builder.build([result1, result2, result3])

        # 検証
        assert graph.number_of_nodes() == 4
        assert graph.number_of_edges() >= 2

        # main -> process, main -> validate
        assert graph.has_edge("main.py::main", "utils.py::process")
        assert graph.has_edge("main.py::main", "utils.py::validate")

        # process -> helper
        assert graph.has_edge("utils.py::process", "helper.py::helper")

    def test_build_returns_same_graph_instance(self):
        """buildが同じグラフインスタンスを返す"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "test.py",
            "semantic_info": {
                "definitions": [{"name": "func", "type": "function"}],
                "calls": []
            }
        }

        graph = builder.build([result])

        assert graph is builder.graph

    def test_definitions_mapping_populated(self):
        """定義マッピングが正しく構築される"""
        builder = DependencyGraphBuilder()

        result = Mock(spec=AnalysisResult)
        result.to_dict.return_value = {
            "success": True,
            "file_path": "code.py",
            "semantic_info": {
                "definitions": [
                    {"name": "func_a", "type": "function"},
                    {"name": "func_b", "type": "function"}
                ],
                "calls": []
            }
        }

        builder.build([result])

        assert "func_a" in builder.definitions
        assert "func_b" in builder.definitions
        assert builder.definitions["func_a"] == ["code.py::func_a"]
        assert builder.definitions["func_b"] == ["code.py::func_b"]
