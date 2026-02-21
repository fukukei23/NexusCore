"""
NexusTrace: 最小保存機能

入口③ NexusTrace の最小実装。
GuardDecision などの重要イベントを JSONL 形式で保存する。
"""

from nexuscore.trace.trace_writer import (
    TraceWriter,
    write_guard_decision_event,
)

__all__ = [
    "TraceWriter",
    "write_guard_decision_event",
]
