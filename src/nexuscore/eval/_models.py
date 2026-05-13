from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Verdict(StrEnum):
    """評価結果の判定"""

    GO = "GO"
    CONDITIONAL_GO = "CONDITIONAL_GO"
    NO = "NO"


@dataclass
class EvaluationConfig:
    """評価設定（閾値はここから注入）"""

    schema_required: bool = True
    rules_required: bool = True
    stability_threshold: float = 1.0


@dataclass
class ParseResult:
    """JSONパース結果"""

    success: bool
    data: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class SchemaValidationResult:
    """Schema検証結果"""

    pass_: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class RulesValidationResult:
    """Rules検証結果"""

    pass_: bool
    errors: list[str] = field(default_factory=list)
    not_applicable: bool = False


@dataclass
class StabilityResult:
    """Stability測定結果"""

    measured: bool
    value: float | None = None
    errors: list[str] = field(default_factory=list)


@dataclass
class EvaluationCase:
    """評価ケース（1回の実行）"""

    case_id: str
    input_data: str
    schema: dict[str, Any] | None = None
    rules: dict[str, Any] | None = None
    parse_result: ParseResult | None = None
    schema_result: SchemaValidationResult | None = None
    rules_result: RulesValidationResult | None = None


@dataclass
class EvaluationReport:
    """評価レポート（全ケースの集計結果）"""

    run_id: str
    task_type: str = "json_structured_output"
    repeats: int = 1
    cases: list[EvaluationCase] = field(default_factory=list)
    schema_pass_rate: float = 0.0
    rules_pass_rate: float = 0.0
    stability: StabilityResult = field(default_factory=lambda: StabilityResult(measured=False))
    verdict: Verdict = Verdict.NO
    verdict_reason: str = ""
    thresholds_used: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationRun:
    """評価実行（複数ケースの実行単位）"""

    run_id: str
    config: EvaluationConfig
    cases: list[EvaluationCase] = field(default_factory=list)
    report: EvaluationReport | None = None
