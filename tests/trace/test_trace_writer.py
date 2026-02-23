"""
NexusTrace trace_writer のテスト

仕様:
- 必須フィールドが入る
- JSONLとして2行追記できる
- override有無で構造が壊れない
- 書き込み失敗時に例外を外へ出さない（モンキーパッチ等でopenを失敗させる）
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from nexuscore.guard.policy_engine import (
    DiffInput,
    EvalInput,
    GuardDecision,
    GuardInput,
    GuardResult,
    SecurityInput,
    TestInput,
)
from nexuscore.trace.trace_writer import (
    SCHEMA_VERSION,
    TraceWriter,
    write_guard_decision_event,
)


class TestRequiredFields:
    """必須フィールドのテスト"""

    def test_required_fields_present(self):
        """必須フィールドが入る（override キーも必須）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "test.jsonl"

            guard_input = GuardInput(
                environment="production",
                security=SecurityInput(check_status="PASS", secret_found=False),
            )
            guard_result = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            write_guard_decision_event(
                guard_result=guard_result,
                guard_input=guard_input,
                trace_file=trace_file,
            )

            # ファイルを読み込んで検証
            with open(trace_file, encoding="utf-8") as f:
                line = f.readline()
                event = json.loads(line)

            # 必須フィールドの存在確認
            assert event["event_type"] == "guard_decision"
            assert event["schema_version"] == SCHEMA_VERSION
            assert "timestamp" in event
            assert event["environment"] == "production"
            assert event["policy_id"] == "nexusguard-v0.1.1"
            assert event["decision"] == "ALLOW"
            assert event["reasons"] == ["GUARD-RULE-007: all checks passed"]
            assert "artifacts" in event
            assert "code_identity" in event
            # override は必須フィールド（v0.1）
            assert "override" in event
            assert event["override"] is None  # override 無しの場合は null


class TestJsonlAppend:
    """JSONL 追記のテスト"""

    def test_jsonl_append_two_events(self):
        """JSONLとして2行追記できる"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "test.jsonl"

            guard_input1 = GuardInput(
                environment="production",
                security=SecurityInput(check_status="PASS", secret_found=False),
            )
            guard_result1 = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            guard_input2 = GuardInput(
                environment="staging",
                security=SecurityInput(check_status="UNKNOWN", secret_found=False),
            )
            guard_result2 = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            # 1行目を追記
            write_guard_decision_event(
                guard_result=guard_result1,
                guard_input=guard_input1,
                trace_file=trace_file,
            )

            # 2行目を追記
            write_guard_decision_event(
                guard_result=guard_result2,
                guard_input=guard_input2,
                trace_file=trace_file,
            )

            # ファイルを読み込んで検証
            with open(trace_file, encoding="utf-8") as f:
                lines = f.readlines()

            assert len(lines) == 2

            event1 = json.loads(lines[0])
            event2 = json.loads(lines[1])

            assert event1["environment"] == "production"
            assert event1["decision"] == "ALLOW"
            assert event2["environment"] == "staging"
            assert event2["decision"] == "ALLOW"  # staging × UNKNOWN は次判定へ（ALLOW）


class TestOverrideHandling:
    """override 有無で構造が壊れないテスト"""

    def test_with_override_false(self):
        """override=False で構造が壊れない"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "test.jsonl"

            guard_input = GuardInput(
                environment="production",
                security=SecurityInput(check_status="PASS", secret_found=False),
                override=False,
            )
            guard_result = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            write_guard_decision_event(
                guard_result=guard_result,
                guard_input=guard_input,
                trace_file=trace_file,
            )

            with open(trace_file, encoding="utf-8") as f:
                line = f.readline()
                event = json.loads(line)

            # 構造が壊れていないことを確認
            assert event["event_type"] == "guard_decision"
            assert event["decision"] == "ALLOW"
            # override キーが常に存在すること（追加テスト1）
            assert "override" in event
            # override が null であることを確認（追加テスト3：明示的に False を指定）
            assert event["override"] is None

    def test_with_override_true(self):
        """override=True の場合、override オブジェクトが保存される（追加テスト2：構造検証）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "test.jsonl"

            guard_input = GuardInput(
                environment="production",
                security=SecurityInput(check_status="PASS", secret_found=False),
                override=True,
            )
            guard_result = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            write_guard_decision_event(
                guard_result=guard_result,
                guard_input=guard_input,
                trace_file=trace_file,
            )

            with open(trace_file, encoding="utf-8") as f:
                line = f.readline()
                event = json.loads(line)

            # 構造が壊れていないことを確認
            assert event["event_type"] == "guard_decision"
            assert event["decision"] == "ALLOW"
            # override キーが常に存在すること（追加テスト1）
            assert "override" in event
            # override オブジェクトが保存されていることを確認（追加テスト2：構造検証）
            assert event["override"] is not None
            assert isinstance(event["override"], dict)
            # 必須キーの存在確認
            assert "override" in event["override"]
            assert event["override"]["override"] is True
            assert "approver" in event["override"]
            assert "expires_at" in event["override"]
            assert "override_reason" in event["override"]
            # 現時点ではすべて null（v0.1 では許容）
            assert event["override"]["approver"] is None
            assert event["override"]["expires_at"] is None
            assert event["override"]["override_reason"] is None

    def test_override_key_always_present_minimal_input(self):
        """追加テスト1：最小入力（override無し）で書き出したイベントに override キーが存在し、None である"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "test.jsonl"

            guard_input = GuardInput(
                environment="production",
                security=SecurityInput(check_status="PASS", secret_found=False),
                # override を指定しない（デフォルト False）
            )
            guard_result = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            write_guard_decision_event(
                guard_result=guard_result,
                guard_input=guard_input,
                trace_file=trace_file,
            )

            with open(trace_file, encoding="utf-8") as f:
                line = f.readline()
                event = json.loads(line)

            # override キーが常に存在すること
            assert "override" in event
            # override が null であること
            assert event["override"] is None


class TestArtifacts:
    """artifacts のテスト"""

    def test_artifacts_with_all_inputs(self):
        """すべての入力がある場合、artifacts にキーが含まれる"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "test.jsonl"

            guard_input = GuardInput(
                environment="production",
                security=SecurityInput(check_status="PASS", secret_found=False),
                eval=EvalInput(verdict="GO"),
                test=TestInput(status="PASS"),
                diff=DiffInput(high_risk=False),
            )
            guard_result = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            write_guard_decision_event(
                guard_result=guard_result,
                guard_input=guard_input,
                trace_file=trace_file,
            )

            with open(trace_file, encoding="utf-8") as f:
                line = f.readline()
                event = json.loads(line)

            artifacts = event["artifacts"]
            assert "eval_report_id" in artifacts
            assert "test_run_id" in artifacts
            assert "diff_id" in artifacts
            assert "security_scan_id" in artifacts
            # 現時点ではすべて null
            assert artifacts["eval_report_id"] is None
            assert artifacts["test_run_id"] is None
            assert artifacts["diff_id"] is None
            assert artifacts["security_scan_id"] is None

    def test_artifacts_always_has_four_keys_minimal_input(self):
        """入力が最小（参照ID無し）ケースでも、artifacts の4キーが存在し null である"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "test.jsonl"

            guard_input = GuardInput(
                environment="production",
                security=SecurityInput(check_status="PASS", secret_found=False),
            )
            guard_result = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            write_guard_decision_event(
                guard_result=guard_result,
                guard_input=guard_input,
                trace_file=trace_file,
            )

            with open(trace_file, encoding="utf-8") as f:
                line = f.readline()
                event = json.loads(line)

            artifacts = event["artifacts"]
            # 常に4キーが存在することを確認
            assert "eval_report_id" in artifacts
            assert "test_run_id" in artifacts
            assert "diff_id" in artifacts
            assert "security_scan_id" in artifacts
            # 現時点ではすべて null
            assert artifacts["eval_report_id"] is None
            assert artifacts["test_run_id"] is None
            assert artifacts["diff_id"] is None
            assert artifacts["security_scan_id"] is None

    def test_artifacts_always_has_four_keys_with_all_inputs(self):
        """すべての入力がある場合でも、artifacts の4キーが常に存在する"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "test.jsonl"

            guard_input = GuardInput(
                environment="production",
                security=SecurityInput(check_status="PASS", secret_found=False),
                eval=EvalInput(verdict="GO"),
                test=TestInput(status="PASS"),
                diff=DiffInput(high_risk=False),
            )
            guard_result = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            write_guard_decision_event(
                guard_result=guard_result,
                guard_input=guard_input,
                trace_file=trace_file,
            )

            with open(trace_file, encoding="utf-8") as f:
                line = f.readline()
                event = json.loads(line)

            artifacts = event["artifacts"]
            # 常に4キーが存在することを確認
            assert "eval_report_id" in artifacts
            assert "test_run_id" in artifacts
            assert "diff_id" in artifacts
            assert "security_scan_id" in artifacts
            # 現時点ではすべて null
            assert artifacts["eval_report_id"] is None
            assert artifacts["test_run_id"] is None
            assert artifacts["diff_id"] is None
            assert artifacts["security_scan_id"] is None


class TestWriteFailure:
    """書き込み失敗時のテスト"""

    def test_write_failure_no_exception(self):
        """書き込み失敗時に例外を外へ出さない"""
        guard_input = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
        )
        guard_result = GuardResult(
            decision=GuardDecision.ALLOW,
            reasons=["GUARD-RULE-007: all checks passed"],
        )

        # open を失敗させる（モンキーパッチ）
        with patch("builtins.open", side_effect=OSError("Permission denied")):
            # 例外が外に出ないことを確認
            try:
                write_guard_decision_event(
                    guard_result=guard_result,
                    guard_input=guard_input,
                    trace_file=Path("/invalid/path/test.jsonl"),
                )
            except Exception:
                pytest.fail("Exception should not be raised outside")

    def test_write_failure_with_invalid_path(self):
        """無効なパスでも例外を外へ出さない"""
        guard_input = GuardInput(
            environment="production",
            security=SecurityInput(check_status="PASS", secret_found=False),
        )
        guard_result = GuardResult(
            decision=GuardDecision.ALLOW,
            reasons=["GUARD-RULE-007: all checks passed"],
        )

        # 無効なパスで書き込みを試みる
        try:
            write_guard_decision_event(
                guard_result=guard_result,
                guard_input=guard_input,
                trace_file=Path("/root/invalid/path/test.jsonl"),
            )
        except Exception:
            pytest.fail("Exception should not be raised outside")


class TestTraceWriter:
    """TraceWriter クラスのテスト"""

    def test_trace_writer_write(self):
        """TraceWriter で書き込みができる"""
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_file = Path(tmpdir) / "test.jsonl"

            writer = TraceWriter(trace_file=trace_file)

            guard_input = GuardInput(
                environment="production",
                security=SecurityInput(check_status="PASS", secret_found=False),
            )
            guard_result = GuardResult(
                decision=GuardDecision.ALLOW,
                reasons=["GUARD-RULE-007: all checks passed"],
            )

            writer.write_guard_decision(
                guard_result=guard_result,
                guard_input=guard_input,
            )

            # ファイルが作成されていることを確認
            assert trace_file.exists()

            with open(trace_file, encoding="utf-8") as f:
                line = f.readline()
                event = json.loads(line)

            assert event["decision"] == "ALLOW"
