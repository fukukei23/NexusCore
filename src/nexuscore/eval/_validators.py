"""NexusEval validators — JSON parsing, schema/rules validation, stability measurement."""

from __future__ import annotations

import json
from typing import Any

from nexuscore.eval._models import (
    EvaluationCase,
    ParseResult,
    RulesValidationResult,
    SchemaValidationResult,
    StabilityResult,
)

try:
    import jsonschema
    from jsonschema import ValidationError, validate
except ImportError:
    jsonschema = None
    validate = None
    ValidationError = None


def parse_json(input_data: str) -> ParseResult:
    """JSON文字列をパースする。"""
    errors: list[str] = []
    data: dict[str, Any] | None = None

    try:
        data = json.loads(input_data)
        if not isinstance(data, dict):
            errors.append(f"JSON is not an object, got {type(data).__name__}")
            return ParseResult(success=False, errors=errors)
        return ParseResult(success=True, data=data)
    except json.JSONDecodeError as e:
        errors.append(f"JSON parse error: {str(e)}")
        return ParseResult(success=False, errors=errors)
    except Exception as e:
        errors.append(f"Unexpected error during JSON parse: {str(e)}")
        return ParseResult(success=False, errors=errors)


def normalize_json(data: dict[str, Any]) -> str:
    """JSONを正規化する（キー順固定等）。"""

    def _sort_keys(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: _sort_keys(v) for k, v in sorted(obj.items())}
        elif isinstance(obj, list):
            return [_sort_keys(item) for item in obj]
        else:
            return obj

    normalized = _sort_keys(data)
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True)


def validate_schema(data: dict[str, Any], schema: dict[str, Any] | None) -> SchemaValidationResult:
    """JSON Schema検証を実行する。"""
    if schema is None:
        return SchemaValidationResult(pass_=True)

    if jsonschema is None:
        return SchemaValidationResult(pass_=False, errors=["jsonschema library is not installed"])

    errors: list[str] = []
    try:
        validate(instance=data, schema=schema)
        return SchemaValidationResult(pass_=True)
    except ValidationError as e:
        errors.append(f"Schema validation error: {e.message}")
        if e.path:
            errors.append(f"  Path: {list(e.path)}")
        return SchemaValidationResult(pass_=False, errors=errors)
    except Exception as e:
        errors.append(f"Unexpected error during schema validation: {str(e)}")
        return SchemaValidationResult(pass_=False, errors=errors)


def validate_rules(data: dict[str, Any], rules: dict[str, Any] | None) -> RulesValidationResult:
    """Rules検証を実行する（禁止値/禁止組合せ/if-then）。"""
    if rules is None:
        return RulesValidationResult(pass_=True, not_applicable=True)

    errors: list[str] = []

    if "forbidden_values" in rules:
        forbidden = rules["forbidden_values"]
        if isinstance(forbidden, dict):
            for key, forbidden_list in forbidden.items():
                if key in data and data[key] in forbidden_list:
                    errors.append(f"Forbidden value '{data[key]}' found for key '{key}'")

    if "forbidden_combinations" in rules:
        forbidden_combos = rules["forbidden_combinations"]
        if isinstance(forbidden_combos, list):
            for combo in forbidden_combos:
                if isinstance(combo, dict):
                    match = all(data.get(k) == v for k, v in combo.items())
                    if match:
                        errors.append(f"Forbidden combination detected: {combo}")

    if "if_then" in rules:
        if_then_rules = rules["if_then"]
        if isinstance(if_then_rules, list):
            for rule in if_then_rules:
                if isinstance(rule, dict) and "if" in rule and "then" in rule:
                    if_cond = rule["if"]
                    then_cond = rule["then"]

                    if_match = True
                    if isinstance(if_cond, dict):
                        if_match = all(data.get(k) == v for k, v in if_cond.items())

                    if if_match:
                        if isinstance(then_cond, dict):
                            for key, expected_value in then_cond.items():
                                if key not in data or data[key] != expected_value:
                                    errors.append(
                                        f"If-then rule violation: if {if_cond} then {key}={expected_value}, "
                                        f"but got {key}={data.get(key)}"
                                    )

    return RulesValidationResult(pass_=len(errors) == 0, errors=errors, not_applicable=False)


def measure_stability(cases: list[EvaluationCase]) -> StabilityResult:
    """Stabilityを測定する（repeats>=2 の場合のみ）。"""
    if len(cases) < 2:
        return StabilityResult(measured=False)

    parsed_cases = [
        c for c in cases if c.parse_result and c.parse_result.success and c.parse_result.data
    ]

    if len(parsed_cases) < 2:
        return StabilityResult(
            measured=True, value=0.0, errors=["Less than 2 cases with successful JSON parse"]
        )

    normalized_strings = []
    for case in parsed_cases:
        try:
            normalized = normalize_json(case.parse_result.data)
            normalized_strings.append(normalized)
        except Exception as e:
            return StabilityResult(
                measured=True,
                value=0.0,
                errors=[f"Failed to normalize JSON in case {case.case_id}: {str(e)}"],
            )

    first = normalized_strings[0]
    all_match = all(s == first for s in normalized_strings)

    stability_value = 1.0 if all_match else 0.0

    return StabilityResult(measured=True, value=stability_value)
