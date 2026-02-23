"""
NexusEval 評価器のテスト

外部LLM呼び出し不要（固定入力のみ）で以下を担保：
- パース失敗 / required欠落 / 型違反
- rules未指定（not_applicable）
- repeats=1 の not_measured
- repeats>1 の同値/不一致
- 閾値境界でverdictが変わる
- reportに thresholds_used が含まれる
"""

import json
from dataclasses import asdict

from nexuscore.eval.evaluator import (
    EvaluationCase,
    EvaluationConfig,
    EvaluationReport,
    Verdict,
    determine_verdict,
    evaluate_json_structured_output,
    measure_stability,
    normalize_json,
    parse_json,
    validate_rules,
    validate_schema,
)


class TestParseJson:
    """JSONパースのテスト"""

    def test_parse_valid_json(self):
        """有効なJSONのパース"""
        result = parse_json('{"key": "value"}')
        assert result.success is True
        assert result.data == {"key": "value"}
        assert len(result.errors) == 0

    def test_parse_invalid_json(self):
        """無効なJSONのパース（パース失敗）"""
        result = parse_json('{"key": "value"')
        assert result.success is False
        assert result.data is None
        assert len(result.errors) > 0
        assert "JSON parse error" in result.errors[0]

    def test_parse_non_object_json(self):
        """オブジェクトではないJSON（配列等）"""
        result = parse_json('["value1", "value2"]')
        assert result.success is False
        assert len(result.errors) > 0
        assert "not an object" in result.errors[0]


class TestValidateSchema:
    """Schema検証のテスト"""

    def test_validate_schema_pass(self):
        """Schema検証成功"""
        data = {"name": "test", "age": 25}
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        result = validate_schema(data, schema)
        assert result.pass_ is True
        assert len(result.errors) == 0

    def test_validate_schema_required_missing(self):
        """required欠落"""
        data = {"name": "test"}
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        result = validate_schema(data, schema)
        assert result.pass_ is False
        assert len(result.errors) > 0

    def test_validate_schema_type_violation(self):
        """型違反"""
        data = {"name": "test", "age": "25"}  # ageが文字列
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }
        result = validate_schema(data, schema)
        assert result.pass_ is False
        assert len(result.errors) > 0

    def test_validate_schema_none(self):
        """Schema未指定（検証スキップ）"""
        data = {"name": "test"}
        result = validate_schema(data, None)
        assert result.pass_ is True


class TestValidateRules:
    """Rules検証のテスト"""

    def test_validate_rules_not_applicable(self):
        """rules未指定（not_applicable）"""
        data = {"name": "test"}
        result = validate_rules(data, None)
        assert result.pass_ is True
        assert result.not_applicable is True

    def test_validate_rules_forbidden_value(self):
        """禁止値チェック"""
        data = {"status": "forbidden"}
        rules = {"forbidden_values": {"status": ["forbidden", "blocked"]}}
        result = validate_rules(data, rules)
        assert result.pass_ is False
        assert len(result.errors) > 0
        assert "Forbidden value" in result.errors[0]

    def test_validate_rules_forbidden_combination(self):
        """禁止組合せチェック"""
        data = {"role": "admin", "permission": "delete"}
        rules = {"forbidden_combinations": [{"role": "admin", "permission": "delete"}]}
        result = validate_rules(data, rules)
        assert result.pass_ is False
        assert len(result.errors) > 0
        assert "Forbidden combination" in result.errors[0]

    def test_validate_rules_if_then(self):
        """if-then チェック"""
        data = {"role": "admin", "level": 1}  # adminならlevel>=2が必要
        rules = {"if_then": [{"if": {"role": "admin"}, "then": {"level": 2}}]}
        result = validate_rules(data, rules)
        assert result.pass_ is False
        assert len(result.errors) > 0
        assert "If-then rule violation" in result.errors[0]

    def test_validate_rules_pass(self):
        """Rules検証成功"""
        data = {"status": "allowed", "role": "user"}
        rules = {"forbidden_values": {"status": ["forbidden"]}}
        result = validate_rules(data, rules)
        assert result.pass_ is True
        assert len(result.errors) == 0


class TestNormalizeJson:
    """JSON正規化のテスト"""

    def test_normalize_json_key_order(self):
        """キー順固定"""
        data1 = {"b": 2, "a": 1, "c": 3}
        data2 = {"a": 1, "b": 2, "c": 3}
        normalized1 = normalize_json(data1)
        normalized2 = normalize_json(data2)
        assert normalized1 == normalized2

    def test_normalize_json_nested(self):
        """ネストされたオブジェクトの正規化"""
        data = {"outer": {"b": 2, "a": 1}, "inner": [3, 1, 2]}
        normalized = normalize_json(data)
        parsed = json.loads(normalized)
        assert "outer" in parsed
        assert "inner" in parsed


class TestMeasureStability:
    """Stability測定のテスト"""

    def test_stability_repeats_1_not_measured(self):
        """repeats=1 の not_measured"""
        case1 = EvaluationCase(
            case_id="case1", input_data='{"a": 1}', parse_result=parse_json('{"a": 1}')
        )
        result = measure_stability([case1])
        assert result.measured is False
        assert result.value is None

    def test_stability_repeats_2_identical(self):
        """repeats>1 の同値（stability=1.0）"""
        case1 = EvaluationCase(
            case_id="case1",
            input_data='{"a": 1, "b": 2}',
            parse_result=parse_json('{"a": 1, "b": 2}'),
        )
        case2 = EvaluationCase(
            case_id="case2",
            input_data='{"b": 2, "a": 1}',  # キー順が違うが内容は同じ
            parse_result=parse_json('{"b": 2, "a": 1}'),
        )
        result = measure_stability([case1, case2])
        assert result.measured is True
        assert result.value == 1.0

    def test_stability_repeats_2_different(self):
        """repeats>1 の不一致（stability=0.0）"""
        case1 = EvaluationCase(
            case_id="case1", input_data='{"a": 1}', parse_result=parse_json('{"a": 1}')
        )
        case2 = EvaluationCase(
            case_id="case2", input_data='{"a": 2}', parse_result=parse_json('{"a": 2}')
        )
        result = measure_stability([case1, case2])
        assert result.measured is True
        assert result.value == 0.0


class TestDetermineVerdict:
    """Verdict判定のテスト"""

    def test_verdict_no_schema_fail(self):
        """Schema失敗でNO"""
        report = EvaluationReport(
            run_id="test",
            schema_pass_rate=0.0,
            rules_pass_rate=1.0,
            repeats=1,
            stability=measure_stability([]),
        )
        config = EvaluationConfig()
        verdict, reason = determine_verdict(report, config)
        assert verdict == Verdict.NO
        assert "Schema validation failed" in reason

    def test_verdict_no_rules_fail(self):
        """Rules失敗でNO"""
        report = EvaluationReport(
            run_id="test",
            schema_pass_rate=1.0,
            rules_pass_rate=0.0,
            repeats=1,
            stability=measure_stability([]),
        )
        config = EvaluationConfig()
        verdict, reason = determine_verdict(report, config)
        assert verdict == Verdict.NO
        assert "Rules validation failed" in reason

    def test_verdict_conditional_go_repeats_1(self):
        """repeats=1 のとき CONDITIONAL_GO（stabilityを条件にしない）"""
        report = EvaluationReport(
            run_id="test",
            schema_pass_rate=1.0,
            rules_pass_rate=1.0,
            repeats=1,
            stability=measure_stability([]),
        )
        config = EvaluationConfig()
        verdict, reason = determine_verdict(report, config)
        assert verdict == Verdict.CONDITIONAL_GO
        assert "stability not measured" in reason

    def test_verdict_go_repeats_2_stability_pass(self):
        """repeats>=2 で stability が閾値以上なら GO"""
        case1 = EvaluationCase(
            case_id="case1", input_data='{"a": 1}', parse_result=parse_json('{"a": 1}')
        )
        case2 = EvaluationCase(
            case_id="case2", input_data='{"a": 1}', parse_result=parse_json('{"a": 1}')
        )
        stability = measure_stability([case1, case2])
        report = EvaluationReport(
            run_id="test", schema_pass_rate=1.0, rules_pass_rate=1.0, repeats=2, stability=stability
        )
        config = EvaluationConfig(stability_threshold=1.0)
        verdict, reason = determine_verdict(report, config)
        assert verdict == Verdict.GO

    def test_verdict_conditional_go_repeats_2_stability_fail(self):
        """repeats>=2 で stability が閾値未満なら CONDITIONAL_GO"""
        case1 = EvaluationCase(
            case_id="case1", input_data='{"a": 1}', parse_result=parse_json('{"a": 1}')
        )
        case2 = EvaluationCase(
            case_id="case2", input_data='{"a": 2}', parse_result=parse_json('{"a": 2}')
        )
        stability = measure_stability([case1, case2])
        report = EvaluationReport(
            run_id="test", schema_pass_rate=1.0, rules_pass_rate=1.0, repeats=2, stability=stability
        )
        config = EvaluationConfig(stability_threshold=1.0)
        verdict, reason = determine_verdict(report, config)
        assert verdict == Verdict.CONDITIONAL_GO
        assert "stability below threshold" in reason


class TestEvaluateJsonStructuredOutput:
    """evaluate_json_structured_output の統合テスト"""

    def test_evaluate_with_thresholds_used(self):
        """reportに thresholds_used が含まれる"""
        inputs = ['{"name": "test", "age": 25}']
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        config = EvaluationConfig(stability_threshold=0.9)
        report = evaluate_json_structured_output(
            run_id="test_run", inputs=inputs, schema=schema, config=config
        )
        assert "thresholds_used" in asdict(report)
        assert report.thresholds_used["stability_threshold"] == 0.9
        assert report.thresholds_used["schema_required"] is True
        assert report.thresholds_used["rules_required"] is True

    def test_evaluate_repeats_1_not_measured(self):
        """repeats=1 のとき stability は not_measured"""
        inputs = ['{"a": 1}']
        report = evaluate_json_structured_output(run_id="test_run", inputs=inputs)
        assert report.repeats == 1
        assert report.stability.measured is False
        assert report.verdict == Verdict.CONDITIONAL_GO  # stabilityを条件にしない

    def test_evaluate_repeats_2_stability_measured(self):
        """repeats>=2 のとき stability を測定"""
        inputs = ['{"a": 1}', '{"a": 1}']
        report = evaluate_json_structured_output(run_id="test_run", inputs=inputs)
        assert report.repeats == 2
        assert report.stability.measured is True
        assert report.stability.value == 1.0

    def test_evaluate_parse_failure(self):
        """パース失敗時の処理"""
        inputs = ['{"invalid": json}']  # 無効なJSON
        report = evaluate_json_structured_output(run_id="test_run", inputs=inputs)
        assert len(report.cases) == 1
        assert report.cases[0].parse_result.success is False
        assert report.schema_pass_rate == 0.0
        assert report.verdict == Verdict.NO

    def test_evaluate_schema_validation(self):
        """Schema検証の統合テスト"""
        inputs = ['{"name": "test"}']  # ageが欠落
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        report = evaluate_json_structured_output(run_id="test_run", inputs=inputs, schema=schema)
        assert report.schema_pass_rate == 0.0
        assert report.verdict == Verdict.NO

    def test_evaluate_rules_validation(self):
        """Rules検証の統合テスト"""
        inputs = ['{"status": "forbidden"}']
        rules = {"forbidden_values": {"status": ["forbidden"]}}
        report = evaluate_json_structured_output(run_id="test_run", inputs=inputs, rules=rules)
        assert report.rules_pass_rate == 0.0
        assert report.verdict == Verdict.NO

    def test_evaluate_threshold_boundary(self):
        """閾値境界でverdictが変わる"""
        case1 = EvaluationCase(
            case_id="case1", input_data='{"a": 1}', parse_result=parse_json('{"a": 1}')
        )
        case2 = EvaluationCase(
            case_id="case2", input_data='{"a": 1}', parse_result=parse_json('{"a": 1}')
        )
        stability = measure_stability([case1, case2])

        # 閾値以上でGO
        report1 = EvaluationReport(
            run_id="test", schema_pass_rate=1.0, rules_pass_rate=1.0, repeats=2, stability=stability
        )
        config1 = EvaluationConfig(stability_threshold=1.0)
        verdict1, _ = determine_verdict(report1, config1)
        assert verdict1 == Verdict.GO

        # 閾値未満でCONDITIONAL_GO
        config2 = EvaluationConfig(stability_threshold=1.1)  # 1.0より大きい
        verdict2, _ = determine_verdict(report1, config2)
        assert verdict2 == Verdict.CONDITIONAL_GO
