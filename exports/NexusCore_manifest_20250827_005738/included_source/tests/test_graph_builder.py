#!/usr/bin/env python3
# ==============================================================================
# ファイル名: tests/test_graph_builder.py
# 機能: graph_builder.py の単体テスト
# バージョン: 1.0.0
# ==============================================================================

import unittest
import sys
from pathlib import Path

# --- テスト対象のモジュールをインポートするためのパスを追加 ---
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root / 'src'))

from nexuscore.analyzer.graph_builder import DependencyGraphBuilder
from nexuscore.analyzer.unified_analyzer import AnalysisResult

class TestDependencyGraphBuilder(unittest.TestCase):
    """DependencyGraphBuilderのテストスイート"""

    def test_graph_construction(self):
        """複数の解析結果からグラフが正しく構築されるかテスト"""
        # --- 模擬的な解析結果を作成 ---
        # main.py の解析結果
        main_py_results = AnalysisResult(
            success=True, file_path="main.py",
            semantic_info={
                'definitions': [
                    {'name': 'main', 'type': 'function'},
                ],
                'calls': [
                    {'name': 'MyProcessor', 'scope': 'main'},
                    {'name': 'process', 'scope': 'main'}
                ]
            }
        )
        
        # processor.py の解析結果
        processor_py_results = AnalysisResult(
            success=True, file_path="processor.py",
            semantic_info={
                'definitions': [
                    {'name': 'MyProcessor', 'type': 'class'},
                    {'name': 'process', 'type': 'function'}, # method
                ],
                'calls': [
                    {'name': 'helper_function', 'scope': 'process'}
                ]
            }
        )
        
        # utils.py の解析結果
        utils_py_results = AnalysisResult(
            success=True, file_path="utils.py",
            semantic_info={
                'definitions': [
                    {'name': 'helper_function', 'type': 'function'},
                ],
                'calls': []
            }
        )

        # --- グラフを構築 ---
        builder = DependencyGraphBuilder()
        graph = builder.build([main_py_results, processor_py_results, utils_py_results])

        # --- グラフの検証 ---
        # 4つのノードが正しく作成されたか
        self.assertEqual(graph.number_of_nodes(), 4)
        self.assertIn("main.py::main", graph.nodes)
        self.assertIn("processor.py::MyProcessor", graph.nodes)
        self.assertIn("processor.py::process", graph.nodes)
        self.assertIn("utils.py::helper_function", graph.nodes)

        # 3つのエッジ（依存関係）が正しく作成されたか
        self.assertEqual(graph.number_of_edges(), 3)
        # main -> MyProcessor (インスタンス化)
        self.assertTrue(graph.has_edge("main.py::main", "processor.py::MyProcessor"))
        # main -> process (メソッド呼び出し)
        self.assertTrue(graph.has_edge("main.py::main", "processor.py::process"))
        # process -> helper_function (関数呼び出し)
        self.assertTrue(graph.has_edge("processor.py::process", "utils.py::helper_function"))

if __name__ == '__main__':
    unittest.main(verbosity=2)
