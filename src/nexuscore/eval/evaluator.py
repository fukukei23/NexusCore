"""
NexusEval: JSON構造出力評価器

split: models + validators extracted → evaluator is orchestration only.
"""

from __future__ import annotations

from typing import Any

from nexuscore.eval._models import (  # noqa: F401 — legacy re-exports
    EvaluationCase,
    EvaluationConfig,
    EvaluationReport,
    EvaluationRun,
    ParseResult,
    RulesValidationResult,
    SchemaValidationResult,
    StabilityResult,
    Verdict,
)
from nexuscore.eval._validators import (  # noqa: F401 — legacy re-exports
    measure_stability,
    normalize_json,
    parse_json,
    validate_rules,
    validate_schema,
)


def determine_verdict(report: EvaluationReport, config: EvaluationConfig) -> tuple[Verdict, str]:
    """
    Verdictを判定する。

    - GO: schema_pass AND rules_pass AND (stability>=threshold OR repeats==1)
    - CONDITIONAL_GO: schema_pass AND rules_pass AND stability<threshold AND repeats>1
    - NO: schema_pass=False OR rules_pass=False
    """
    schema_pass = report.schema_pass_rate >= 1.0
    rules_pass = report.rules_pass_rate >= 1.0

    if not schema_pass:
        return Verdict.NO, "Schema validation failed"
    if not rules_pass:
        return Verdict.NO, "Rules validation failed"

    if report.repeats == 1:
        return (
            Verdict.CONDITIONAL_GO,
            "Schema and rules passed (stability not measured for repeats=1)",
        )

    if report.stability.measured:
        if (
            report.stability.value is not None
            and report.stability.value >= config.stability_threshold
        ):
            return Verdict.GO, f"All validations passed (stability={report.stability.value:.2f})"
        else:
            stability_val = report.stability.value if report.stability.value is not None else 0.0
            return (
                Verdict.CONDITIONAL_GO,
                f"Schema and rules passed but stability below threshold (stability={stability_val:.2f}, threshold={config.stability_threshold:.2f})",
            )

    return Verdict.CONDITIONAL_GO, "Schema and rules passed but stability measurement failed"


def evaluate_json_structured_output(
    run_id: str,
    inputs: list[str],
    schema: dict[str, Any] | None = None,
    rules: dict[str, Any] | None = None,
    config: EvaluationConfig | None = None,
) -> EvaluationReport:
    """JSON構造出力を評価する（メイン関数）。"""
    if config is None:
        config = EvaluationConfig()

    repeats = len(inputs)
    cases: list[EvaluationCase] = []

    for i, input_data in enumerate(inputs):
        case_id = f"{run_id}_case_{i+1}"
        case = EvaluationCase(
            case_id=case_id,
            input_data=input_data,
            schema=schema,
            rules=rules,
        )

        parse_result = parse_json(input_data)
        case.parse_result = parse_result

        if parse_result.success and parse_result.data:
            case.schema_result = validate_schema(parse_result.data, schema)
            case.rules_result = validate_rules(parse_result.data, rules)
        else:
            case.schema_result = SchemaValidationResult(pass_=False, errors=parse_result.errors)
            case.rules_result = RulesValidationResult(pass_=False, errors=parse_result.errors)

        cases.append(case)

    schema_pass_count = sum(1 for c in cases if c.schema_result and c.schema_result.pass_)
    rules_pass_count = sum(1 for c in cases if c.rules_result and c.rules_result.pass_)
    schema_pass_rate = schema_pass_count / len(cases) if cases else 0.0
    rules_pass_rate = rules_pass_count / len(cases) if cases else 0.0

    stability = measure_stability(cases)

    report = EvaluationReport(
        run_id=run_id,
        task_type="json_structured_output",
        repeats=repeats,
        cases=cases,
        schema_pass_rate=schema_pass_rate,
        rules_pass_rate=rules_pass_rate,
        stability=stability,
        thresholds_used={
            "schema_required": config.schema_required,
            "rules_required": config.rules_required,
            "stability_threshold": config.stability_threshold,
        },
    )

    verdict, reason = determine_verdict(report, config)
    report.verdict = verdict
    report.verdict_reason = reason

    return report
