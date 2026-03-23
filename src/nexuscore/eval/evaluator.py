"""
NexusEval: JSON構造出力評価器

最小仕様:
- task_type = json_structured_output（固定）
- 正解 = 制約条件集合（schema + rules）。教師データに依存しない。
- repeats>=2 のとき stability を測定（正規化後のJSON同値比較）。
- repeats=1 のとき stability は not_measured として明示。verdictは stability を条件にしない。
- report に thresholds_used を必ず含める（後追い再現のため）。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

try:
    import jsonschema
    from jsonschema import ValidationError, validate
except ImportError:
    jsonschema = None
    validate = None
    ValidationError = None


class Verdict(StrEnum):
    """評価結果の判定"""

    GO = "GO"
    CONDITIONAL_GO = "CONDITIONAL_GO"
    NO = "NO"


@dataclass
class EvaluationConfig:
    """評価設定（閾値はここから注入）"""

    # Schema 検証の閾値（必須通過）
    schema_required: bool = True

    # Rules 検証の閾値（必須通過）
    rules_required: bool = True

    # Stability の閾値（repeats>=2 の場合のみ適用）
    stability_threshold: float = 1.0  # 1.0 = 100% 一致

    # Verdict 判定の閾値
    # GO: schema_pass=True AND rules_pass=True AND (stability>=threshold OR repeats==1)
    # CONDITIONAL_GO: schema_pass=True AND rules_pass=True AND stability<threshold AND repeats>1
    # NO: schema_pass=False OR rules_pass=False


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
    not_applicable: bool = False  # rules未指定の場合


@dataclass
class StabilityResult:
    """Stability測定結果"""

    measured: bool
    value: float | None = None  # 0.0-1.0 (1.0 = 完全一致)
    errors: list[str] = field(default_factory=list)


@dataclass
class EvaluationCase:
    """評価ケース（1回の実行）"""

    case_id: str
    input_data: str  # JSON文字列（パース前）
    schema: dict[str, Any] | None = None  # JSON Schema
    rules: dict[str, Any] | None = None  # Rules定義（禁止値/禁止組合せ/if-then）
    parse_result: ParseResult | None = None
    schema_result: SchemaValidationResult | None = None
    rules_result: RulesValidationResult | None = None


@dataclass
class EvaluationReport:
    """評価レポート（全ケースの集計結果）"""

    run_id: str
    task_type: str = "json_structured_output"  # 固定
    repeats: int = 1
    cases: list[EvaluationCase] = field(default_factory=list)

    # Metrics
    schema_pass_rate: float = 0.0
    rules_pass_rate: float = 0.0
    stability: StabilityResult = field(default_factory=lambda: StabilityResult(measured=False))

    # Verdict
    verdict: Verdict = Verdict.NO
    verdict_reason: str = ""

    # 必須: 閾値の記録（後追い再現のため）
    thresholds_used: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvaluationRun:
    """評価実行（複数ケースの実行単位）"""

    run_id: str
    config: EvaluationConfig
    cases: list[EvaluationCase] = field(default_factory=list)
    report: EvaluationReport | None = None


def parse_json(input_data: str) -> ParseResult:
    """
    JSON文字列をパースする。

    Args:
        input_data: JSON文字列

    Returns:
        ParseResult: パース結果（失敗時はerrorsにエラー情報を収集）
    """
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
    """
    JSONを正規化する（キー順固定等）。

    正規化方針:
    - キーをアルファベット順にソート
    - ネストされたオブジェクトも再帰的にソート
    - 最終的にJSON文字列として返す

    Args:
        data: JSONオブジェクト

    Returns:
        正規化されたJSON文字列
    """

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
    """
    JSON Schema検証を実行する。

    Args:
        data: 検証対象のJSONオブジェクト
        schema: JSON Schema（Noneの場合は検証スキップ）

    Returns:
        SchemaValidationResult: 検証結果
    """
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
    """
    Rules検証を実行する（最小：禁止値/禁止組合せ/if-then）。

    Args:
        data: 検証対象のJSONオブジェクト
        rules: Rules定義（Noneの場合はnot_applicable）

    Returns:
        RulesValidationResult: 検証結果
    """
    if rules is None:
        return RulesValidationResult(pass_=True, not_applicable=True)

    errors: list[str] = []

    # 禁止値チェック
    if "forbidden_values" in rules:
        forbidden = rules["forbidden_values"]
        if isinstance(forbidden, dict):
            for key, forbidden_list in forbidden.items():
                if key in data and data[key] in forbidden_list:
                    errors.append(f"Forbidden value '{data[key]}' found for key '{key}'")

    # 禁止組合せチェック
    if "forbidden_combinations" in rules:
        forbidden_combos = rules["forbidden_combinations"]
        if isinstance(forbidden_combos, list):
            for combo in forbidden_combos:
                if isinstance(combo, dict):
                    # すべての条件が一致する場合に禁止
                    match = all(data.get(k) == v for k, v in combo.items())
                    if match:
                        errors.append(f"Forbidden combination detected: {combo}")

    # if-then チェック
    if "if_then" in rules:
        if_then_rules = rules["if_then"]
        if isinstance(if_then_rules, list):
            for rule in if_then_rules:
                if isinstance(rule, dict) and "if" in rule and "then" in rule:
                    if_cond = rule["if"]
                    then_cond = rule["then"]

                    # if条件を評価
                    if_match = True
                    if isinstance(if_cond, dict):
                        if_match = all(data.get(k) == v for k, v in if_cond.items())

                    # if条件が真の場合、then条件をチェック
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
    """
    Stabilityを測定する（repeats>=2 の場合のみ）。

    Args:
        cases: 評価ケースのリスト（repeats回分）

    Returns:
        StabilityResult: 測定結果（repeats=1の場合はnot_measured）
    """
    if len(cases) < 2:
        return StabilityResult(measured=False)

    # パース成功したケースのみを対象
    parsed_cases = [
        c for c in cases if c.parse_result and c.parse_result.success and c.parse_result.data
    ]

    if len(parsed_cases) < 2:
        return StabilityResult(
            measured=True, value=0.0, errors=["Less than 2 cases with successful JSON parse"]
        )

    # 正規化されたJSON文字列を比較
    normalized_strings = []
    for case in parsed_cases:
        try:
            normalized = normalize_json(case.parse_result.data)  # type: ignore[union-attr, arg-type]
            normalized_strings.append(normalized)
        except Exception as e:
            return StabilityResult(
                measured=True,
                value=0.0,
                errors=[f"Failed to normalize JSON in case {case.case_id}: {str(e)}"],
            )

    # すべての正規化JSONが同一かチェック
    first = normalized_strings[0]
    all_match = all(s == first for s in normalized_strings)

    stability_value = 1.0 if all_match else 0.0

    return StabilityResult(measured=True, value=stability_value)


def determine_verdict(report: EvaluationReport, config: EvaluationConfig) -> tuple[Verdict, str]:
    """
    Verdictを判定する。

    判定ルール:
    - GO: schema_pass=True AND rules_pass=True AND (stability>=threshold OR repeats==1)
    - CONDITIONAL_GO: schema_pass=True AND rules_pass=True AND stability<threshold AND repeats>1
    - NO: schema_pass=False OR rules_pass=False

    Args:
        report: 評価レポート
        config: 評価設定

    Returns:
        (Verdict, reason): 判定結果と理由
    """
    schema_pass = report.schema_pass_rate >= 1.0
    rules_pass = report.rules_pass_rate >= 1.0

    if not schema_pass:
        return Verdict.NO, "Schema validation failed"
    if not rules_pass:
        return Verdict.NO, "Rules validation failed"

    # repeats=1 の場合は stability を条件にしない
    if report.repeats == 1:
        return (
            Verdict.CONDITIONAL_GO,
            "Schema and rules passed (stability not measured for repeats=1)",
        )

    # repeats>=2 の場合は stability を条件にする
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

    # stability測定に失敗した場合
    return Verdict.CONDITIONAL_GO, "Schema and rules passed but stability measurement failed"


def evaluate_json_structured_output(
    run_id: str,
    inputs: list[str],  # JSON文字列のリスト（repeats回分）
    schema: dict[str, Any] | None = None,
    rules: dict[str, Any] | None = None,
    config: EvaluationConfig | None = None,
) -> EvaluationReport:
    """
    JSON構造出力を評価する（メイン関数）。

    Args:
        run_id: 実行ID
        inputs: JSON文字列のリスト（repeats回分）
        schema: JSON Schema（Noneの場合は検証スキップ）
        rules: Rules定義（Noneの場合はnot_applicable）
        config: 評価設定（Noneの場合はデフォルト設定）

    Returns:
        EvaluationReport: 評価レポート
    """
    if config is None:
        config = EvaluationConfig()

    repeats = len(inputs)
    cases: list[EvaluationCase] = []

    # 各入力に対して評価ケースを実行
    for i, input_data in enumerate(inputs):
        case_id = f"{run_id}_case_{i+1}"
        case = EvaluationCase(
            case_id=case_id,
            input_data=input_data,
            schema=schema,
            rules=rules,
        )

        # JSONパース
        parse_result = parse_json(input_data)
        case.parse_result = parse_result

        # パース成功時のみ検証を実行
        if parse_result.success and parse_result.data:
            # Schema検証
            schema_result = validate_schema(parse_result.data, schema)
            case.schema_result = schema_result

            # Rules検証
            rules_result = validate_rules(parse_result.data, rules)
            case.rules_result = rules_result
        else:
            # パース失敗時は検証結果を空にする
            case.schema_result = SchemaValidationResult(pass_=False, errors=parse_result.errors)
            case.rules_result = RulesValidationResult(pass_=False, errors=parse_result.errors)

        cases.append(case)

    # Metrics集計
    schema_pass_count = sum(1 for c in cases if c.schema_result and c.schema_result.pass_)
    rules_pass_count = sum(1 for c in cases if c.rules_result and c.rules_result.pass_)
    schema_pass_rate = schema_pass_count / len(cases) if cases else 0.0
    rules_pass_rate = rules_pass_count / len(cases) if cases else 0.0

    # Stability測定
    stability = measure_stability(cases)

    # レポート作成
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

    # Verdict判定
    verdict, reason = determine_verdict(report, config)
    report.verdict = verdict
    report.verdict_reason = reason

    return report
