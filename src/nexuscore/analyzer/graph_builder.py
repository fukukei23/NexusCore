#!/usr/bin/env python3
# ==============================================================================
# ファイル名: src/nexuscore/analyzer/graph_builder.py
# 機能: 解析結果から依存関係グラフを構築する
# バージョン: 1.0.0
# 依存関係: pip install networkx
# ==============================================================================

from typing import Dict, List, Any
import sys

try:
    import networkx as nx
except ImportError:
    print("networkx is not installed. Please run: pip install networkx", file=sys.stderr)
    nx = None

from nexuscore.analyzer.unified_analyzer import AnalysisResult

class DependencyGraphBuilder:
    """複数ファイルの解析結果から依存関係グラフを構築する。"""
    def __init__(self):
        if not nx:
            raise ImportError("networkx is required for graph building.")
        self.graph = nx.DiGraph()
        self.definitions: Dict[str, List[str]] = {}  # {symbol_name: full_node_id list}

    def build(self, results: List[AnalysisResult]) -> nx.DiGraph:
        """
        解析結果のリストからグラフを構築するメインメソッド。

        Args:
            results: TreeSitterEngineによる解析結果オブジェクトのリスト。

        Returns:
            networkx.DiGraph: 構築された依存関係グラフ。
        """
        # --- ステップ1: すべての定義をスキャンし、ノードとしてグラフに追加 ---
        for result in results:
            result_dict = result.to_dict()
            if not result_dict.get("success") or 'semantic_info' not in result_dict:
                continue
            file_path = result_dict.get('file_path')
            semantic_info = result_dict.get('semantic_info', {}) or {}
            definitions = semantic_info.get('definitions', [])

            for definition in definitions:
                symbol_name = definition['name']
                symbol_type = definition['type']
                # ノードIDは、ファイルパスとシンボル名で一意に定義
                node_id = f"{file_path}::{symbol_name}"
                
                self.graph.add_node(node_id, type=symbol_type, file=file_path)
                
                # 後で呼び出し元を解決するためのマッピングを保存
                if symbol_name not in self.definitions:
                    self.definitions[symbol_name] = []
                self.definitions[symbol_name].append(node_id)

        # --- ステップ2: すべての呼び出しをスキャンし、エッジとしてグラフに追加 ---
        for result in results:
            result_dict = result.to_dict()
            if not result_dict.get("success") or 'semantic_info' not in result_dict:
                continue

            file_path = result_dict.get('file_path')
            semantic_info = result_dict.get('semantic_info', {}) or {}
            calls = semantic_info.get('calls', [])

            for call in calls:
                caller_scope = call['scope']
                callee_name = call['name']
                
                # 呼び出し元ノードのIDを特定
                caller_node_id = f"{file_path}::{caller_scope}"
                
                # 呼び出し先ノードのIDを特定
                # (単純化のため、同じ名前の最初の定義にリンクする)
                if callee_name in self.definitions:
                    callee_node_id = self.definitions[callee_name][0]
                    
                    # 呼び出し元と呼び出し先がグラフに存在する場合のみエッジを追加
                    if self.graph.has_node(caller_node_id) and self.graph.has_node(callee_node_id):
                        self.graph.add_edge(caller_node_id, callee_node_id)
        
        return self.graph
