"""
NexusEval: JSON構造出力評価モジュール

入口② NexusEval の最小実装。
JSON構造出力を、教師データなしで評価する最小基盤を提供する。
"""

from nexuscore.eval.evaluator import (
    EvaluationCase,
    EvaluationReport,
    EvaluationRun,
    evaluate_json_structured_output,
)

__all__ = [
    "EvaluationRun",
    "EvaluationCase",
    "EvaluationReport",
    "evaluate_json_structured_output",
]
