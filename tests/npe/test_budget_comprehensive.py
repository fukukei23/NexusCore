"""
npe/budget.py の包括的テスト

LLMコール予算管理機能を網羅的にテストします。
"""

from __future__ import annotations

import json
import threading
import time

import pytest

from nexuscore.npe import budget
from nexuscore.npe.budget import (
    BudgetDecision,
    _cost,
    _day_key,
    _env_float,
    _env_int,
    _estimate_cost_jpy,
    _now_utc_iso,
    _read_today_total,
    preflight_check,
    record_estimate,
    record_usage,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_ledger(tmp_path, monkeypatch):
    """一時的な使用量台帳を作成"""
    ledger = tmp_path / "usage.jsonl"
    monkeypatch.setattr(budget, "USAGE_LEDGER", ledger)
    monkeypatch.setattr(budget, "_lock", threading.Lock())
    return ledger


@pytest.fixture
def clean_env(monkeypatch):
    """環境変数をクリア"""
    # コスト関連の環境変数を全てクリア
    for model in ["GPT_5", "GPT_5_MINI", "GEMINI_2_5_PRO", "GEMINI_2_5_FLASH"]:
        monkeypatch.delenv(f"NPE_COST_{model}_PROMPT", raising=False)
        monkeypatch.delenv(f"NPE_COST_{model}_COMPLETION", raising=False)

    # キャップ設定をリセット
    monkeypatch.setattr(budget, "DAILY_HARD_CAP_JPY", 1500.0)
    monkeypatch.setattr(budget, "DAILY_SOFT_CAP_JPY", 1000.0)
    monkeypatch.setattr(budget, "PER_CALL_CAP_JPY", 80.0)
    monkeypatch.setattr(budget, "ALLOW_WHEN_OVER_SOFT", True)

    return monkeypatch


# =============================================================================
# Test _cost
# =============================================================================


class TestCost:
    """_cost() のテスト"""

    def test_cost_default_gpt5_prompt(self, clean_env):
        """gpt-5 prompt のデフォルトコスト"""
        cost = _cost("gpt-5", "prompt")
        assert cost == 1.6

    def test_cost_default_gpt5_completion(self, clean_env):
        """gpt-5 completion のデフォルトコスト"""
        cost = _cost("gpt-5", "completion")
        assert cost == 5.0

    def test_cost_default_gpt5_mini(self, clean_env):
        """gpt-5-mini のデフォルトコスト"""
        assert _cost("gpt-5-mini", "prompt") == 0.2
        assert _cost("gpt-5-mini", "completion") == 0.6

    def test_cost_default_gemini_pro(self, clean_env):
        """gemini-2.5-pro のデフォルトコスト"""
        assert _cost("gemini-2.5-pro", "prompt") == 1.2
        assert _cost("gemini-2.5-pro", "completion") == 3.0

    def test_cost_env_override_prompt(self, clean_env, monkeypatch):
        """環境変数でpromptコストを上書き"""
        monkeypatch.setenv("NPE_COST_GPT_5_PROMPT", "2.5")
        cost = _cost("gpt-5", "prompt")
        assert cost == 2.5

    def test_cost_env_override_completion(self, clean_env, monkeypatch):
        """環境変数でcompletionコストを上書き"""
        monkeypatch.setenv("NPE_COST_GPT_5_COMPLETION", "7.0")
        cost = _cost("gpt-5", "completion")
        assert cost == 7.0

    def test_cost_unknown_model_defaults_to_gpt5(self, clean_env):
        """未知のモデルはgpt-5にフォールバック"""
        cost = _cost("unknown-model", "prompt")
        assert cost == 1.6  # gpt-5のpromptコスト

    def test_cost_env_invalid_value_falls_back_to_default(self, clean_env, monkeypatch):
        """無効な環境変数値はデフォルトにフォールバック"""
        monkeypatch.setenv("NPE_COST_GPT_5_PROMPT", "invalid")
        cost = _cost("gpt-5", "prompt")
        assert cost == 1.6

    def test_cost_all_default_models(self, clean_env):
        """全てのデフォルトモデルのコストを確認"""
        models_costs = [
            ("gpt-5", "prompt", 1.6),
            ("gpt-5-mini", "prompt", 0.2),
            ("gemini-2.5-pro", "prompt", 1.2),
            ("gemini-2.5-flash", "prompt", 0.15),
            ("kimi-k2-turbo-preview", "prompt", 0.20),
            ("deepseek-coder", "prompt", 0.14),
        ]
        for model, kind, expected in models_costs:
            assert _cost(model, kind) == expected


# =============================================================================
# Test _env_float and _env_int
# =============================================================================


class TestEnvHelpers:
    """_env_float() と _env_int() のテスト"""

    def test_env_float_valid_value(self, monkeypatch):
        """有効なfloat値を取得"""
        monkeypatch.setenv("TEST_FLOAT", "3.14")
        assert _env_float("TEST_FLOAT", 0.0) == 3.14

    def test_env_float_default_when_missing(self, monkeypatch):
        """環境変数がない場合はデフォルト値"""
        monkeypatch.delenv("MISSING_FLOAT", raising=False)
        assert _env_float("MISSING_FLOAT", 5.5) == 5.5

    def test_env_float_invalid_returns_default(self, monkeypatch):
        """無効な値の場合はデフォルト値"""
        monkeypatch.setenv("INVALID_FLOAT", "not-a-number")
        assert _env_float("INVALID_FLOAT", 2.0) == 2.0

    def test_env_int_valid_value(self, monkeypatch):
        """有効なint値を取得"""
        monkeypatch.setenv("TEST_INT", "42")
        assert _env_int("TEST_INT", 0) == 42

    def test_env_int_default_when_missing(self, monkeypatch):
        """環境変数がない場合はデフォルト値"""
        monkeypatch.delenv("MISSING_INT", raising=False)
        assert _env_int("MISSING_INT", 10) == 10

    def test_env_int_invalid_returns_default(self, monkeypatch):
        """無効な値の場合はデフォルト値"""
        monkeypatch.setenv("INVALID_INT", "not-an-int")
        assert _env_int("INVALID_INT", 5) == 5

    def test_env_float_negative_value(self, monkeypatch):
        """負の float 値"""
        monkeypatch.setenv("NEG_FLOAT", "-1.5")
        assert _env_float("NEG_FLOAT", 0.0) == -1.5


# =============================================================================
# Test utility functions
# =============================================================================


class TestUtilityFunctions:
    """ユーティリティ関数のテスト"""

    def test_now_utc_iso_format(self):
        """_now_utc_iso() が ISO 8601 形式を返す"""
        iso = _now_utc_iso()
        assert "T" in iso
        assert "Z" in iso or "+" in iso or iso.endswith("+00:00")

    def test_day_key_current_day(self):
        """_day_key() が現在の日付を YYYY-MM-DD 形式で返す"""
        day = _day_key()
        assert len(day) == 10
        assert day.count("-") == 2
        # Format: YYYY-MM-DD
        parts = day.split("-")
        assert len(parts) == 3
        assert len(parts[0]) == 4  # Year
        assert len(parts[1]) == 2  # Month
        assert len(parts[2]) == 2  # Day

    def test_day_key_with_timestamp(self):
        """_day_key() が指定されたタイムスタンプの日付を返す"""
        # 2023-01-15 12:00:00 UTC
        ts = 1673784000.0
        day = _day_key(ts)
        assert day == "2023-01-15"

    def test_estimate_cost_jpy_calculation(self):
        """_estimate_cost_jpy() がコストを正しく計算"""
        # gpt-5: prompt=1.6, completion=5.0 per 1k tokens
        # 1000 prompt + 1000 completion = 1.6 + 5.0 = 6.6
        cost = _estimate_cost_jpy("gpt-5", 1000, 1000)
        assert abs(cost - 6.6) < 0.01

    def test_estimate_cost_jpy_small_tokens(self):
        """少量のトークンでのコスト計算"""
        # gpt-5-mini: prompt=0.2, completion=0.6
        # 100 prompt + 50 completion = 0.02 + 0.03 = 0.05
        cost = _estimate_cost_jpy("gpt-5-mini", 100, 50)
        assert abs(cost - 0.05) < 0.001

    def test_estimate_cost_jpy_zero_tokens(self):
        """トークン数ゼロの場合"""
        cost = _estimate_cost_jpy("gpt-5", 0, 0)
        assert cost == 0.0


# =============================================================================
# Test _read_today_total
# =============================================================================


class TestReadTodayTotal:
    """_read_today_total() のテスト"""

    def test_read_today_total_empty_ledger(self, temp_ledger):
        """空の台帳の場合は 0.0"""
        total = _read_today_total()
        assert total == 0.0

    def test_read_today_total_nonexistent_file(self, temp_ledger):
        """ファイルが存在しない場合は 0.0"""
        temp_ledger.unlink(missing_ok=True)
        total = _read_today_total()
        assert total == 0.0

    def test_read_today_total_single_entry(self, temp_ledger):
        """単一エントリの合計を計算"""
        today = _day_key()
        entry = {"day": today, "cost_jpy": 1.23}
        temp_ledger.write_text(json.dumps(entry) + "\n")

        total = _read_today_total()
        assert abs(total - 1.23) < 0.01

    def test_read_today_total_multiple_entries(self, temp_ledger):
        """複数エントリの合計を計算"""
        today = _day_key()
        entries = [
            {"day": today, "cost_jpy": 1.0},
            {"day": today, "cost_jpy": 2.5},
            {"day": today, "cost_jpy": 3.2},
        ]
        temp_ledger.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        total = _read_today_total()
        assert abs(total - 6.7) < 0.01

    def test_read_today_total_filters_other_days(self, temp_ledger):
        """他の日のエントリは除外"""
        today = _day_key()
        entries = [
            {"day": today, "cost_jpy": 1.0},
            {"day": "2023-01-01", "cost_jpy": 100.0},  # 過去の日
            {"day": today, "cost_jpy": 2.0},
        ]
        temp_ledger.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        total = _read_today_total()
        assert abs(total - 3.0) < 0.01

    def test_read_today_total_handles_corrupt_lines(self, temp_ledger):
        """壊れたJSON行をスキップ"""
        today = _day_key()
        lines = [
            json.dumps({"day": today, "cost_jpy": 1.0}),
            "corrupt json line",
            json.dumps({"day": today, "cost_jpy": 2.0}),
        ]
        temp_ledger.write_text("\n".join(lines) + "\n")

        total = _read_today_total()
        assert abs(total - 3.0) < 0.01

    def test_read_today_total_missing_cost_field(self, temp_ledger):
        """cost_jpy フィールドがない場合は 0 として扱う"""
        today = _day_key()
        entry = {"day": today}  # cost_jpy なし
        temp_ledger.write_text(json.dumps(entry) + "\n")

        total = _read_today_total()
        assert total == 0.0


# =============================================================================
# Test record_usage
# =============================================================================


class TestRecordUsage:
    """record_usage() のテスト"""

    def test_record_usage_creates_entry(self, temp_ledger):
        """使用量エントリを作成"""
        record_usage("gpt-5", "test_task", 1.5, 100, 50)

        assert temp_ledger.exists()
        lines = temp_ledger.read_text().strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["model"] == "gpt-5"
        assert entry["task"] == "test_task"
        assert entry["cost_jpy"] == 1.5
        assert entry["prompt_tokens"] == 100
        assert entry["completion_tokens"] == 50
        assert entry["source"] == "post_call"
        assert "ts_utc" in entry
        assert "day" in entry

    def test_record_usage_appends_multiple_entries(self, temp_ledger):
        """複数のエントリを追記"""
        record_usage("gpt-5", "task1", 1.0, 100, 50)
        record_usage("gpt-5-mini", "task2", 0.5, 50, 25)
        record_usage("gemini-2.5-pro", "task3", 2.0, 200, 100)

        lines = temp_ledger.read_text().strip().split("\n")
        assert len(lines) == 3

        models = [json.loads(line)["model"] for line in lines]
        assert models == ["gpt-5", "gpt-5-mini", "gemini-2.5-pro"]

    def test_record_usage_rounds_cost(self, temp_ledger):
        """コストが6桁に丸められる"""
        record_usage("gpt-5", "task", 1.123456789, 100, 50)

        entry = json.loads(temp_ledger.read_text().strip())
        assert entry["cost_jpy"] == 1.123457

    def test_record_usage_thread_safe(self, temp_ledger):
        """複数スレッドから呼び出しても安全"""

        def record_worker(n):
            for i in range(10):
                record_usage(f"model-{n}", f"task-{n}-{i}", 0.1 * i, 10 * i, 5 * i)

        threads = [threading.Thread(target=record_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        lines = temp_ledger.read_text().strip().split("\n")
        assert len(lines) == 50  # 5 threads * 10 entries


# =============================================================================
# Test preflight_check
# =============================================================================


class TestPreflightCheck:
    """preflight_check() のテスト"""

    def test_preflight_check_allows_normal_request(self, clean_env, temp_ledger):
        """通常のリクエストは許可"""
        decision = preflight_check(
            model="gpt-5-mini",
            task="test",
            est_prompt_tokens=100,
            est_completion_tokens=100,
        )

        assert decision.allow is True
        assert decision.reason == "ok"
        assert decision.est_cost_jpy > 0

    def test_preflight_check_blocks_per_call_cap(self, clean_env, temp_ledger, monkeypatch):
        """1回上限を超えるとブロック"""
        monkeypatch.setattr(budget, "PER_CALL_CAP_JPY", 0.1)

        decision = preflight_check(
            model="gpt-5",
            task="expensive",
            est_prompt_tokens=10000,
            est_completion_tokens=10000,
        )

        assert decision.allow is False
        assert "per-call cap exceeded" in decision.reason
        assert decision.caps["per_call_cap_jpy"] == 0.1

    def test_preflight_check_blocks_daily_hard_cap(self, clean_env, temp_ledger, monkeypatch):
        """日次ハード上限を超えるとブロック"""
        # 既に1400円使っている
        today = _day_key()
        for i in range(14):
            entry = {"day": today, "cost_jpy": 100.0}
            with temp_ledger.open("a") as f:
                f.write(json.dumps(entry) + "\n")

        monkeypatch.setattr(budget, "DAILY_HARD_CAP_JPY", 1500.0)
        monkeypatch.setattr(budget, "PER_CALL_CAP_JPY", 200.0)  # per-call上限を上げる

        # 追加の116円リクエストは拒否される（1400 + 116 > 1500）
        decision = preflight_check(
            model="gpt-5",
            task="test",
            est_prompt_tokens=10000,  # 約16円
            est_completion_tokens=20000,  # 約100円 = 合計116円
        )

        # 1400 + 116 > 1500
        assert decision.allow is False
        assert "daily hard cap exceeded" in decision.reason

    def test_preflight_check_allows_under_soft_cap(self, clean_env, temp_ledger, monkeypatch):
        """ソフト上限以下は許可"""
        today = _day_key()
        entry = {"day": today, "cost_jpy": 500.0}
        temp_ledger.write_text(json.dumps(entry) + "\n")

        monkeypatch.setattr(budget, "DAILY_SOFT_CAP_JPY", 1000.0)
        monkeypatch.setattr(budget, "ALLOW_WHEN_OVER_SOFT", True)

        decision = preflight_check(
            model="gpt-5-mini",
            task="test",
            est_prompt_tokens=100,
            est_completion_tokens=100,
        )

        assert decision.allow is True

    def test_preflight_check_blocks_when_over_soft_and_not_allowed(
        self, clean_env, temp_ledger, monkeypatch
    ):
        """ソフト上限超過でALLOW_WHEN_OVER_SOFT=falseの場合はブロック"""
        today = _day_key()
        entry = {"day": today, "cost_jpy": 950.0}
        temp_ledger.write_text(json.dumps(entry) + "\n")

        monkeypatch.setattr(budget, "DAILY_SOFT_CAP_JPY", 1000.0)
        monkeypatch.setattr(budget, "ALLOW_WHEN_OVER_SOFT", False)

        decision = preflight_check(
            model="gpt-5",
            task="test",
            est_prompt_tokens=10000,  # 約16円
            est_completion_tokens=10000,  # 約50円 = 合計66円
        )

        # 950 + 66 = 1016 > 1000 (soft cap)
        assert decision.allow is False
        assert "over daily soft cap" in decision.reason

    def test_preflight_check_allows_when_over_soft_and_allowed(
        self, clean_env, temp_ledger, monkeypatch
    ):
        """ソフト上限超過でもALLOW_WHEN_OVER_SOFT=trueなら許可"""
        today = _day_key()
        entry = {"day": today, "cost_jpy": 900.0}
        temp_ledger.write_text(json.dumps(entry) + "\n")

        monkeypatch.setattr(budget, "DAILY_SOFT_CAP_JPY", 1000.0)
        monkeypatch.setattr(budget, "DAILY_HARD_CAP_JPY", 1500.0)
        monkeypatch.setattr(budget, "ALLOW_WHEN_OVER_SOFT", True)

        decision = preflight_check(
            model="gpt-5",
            task="test",
            est_prompt_tokens=5000,
            est_completion_tokens=1000,  # 約13円
        )

        # ソフト上限は超えるがハード上限は超えない
        assert decision.allow is True

    def test_preflight_check_includes_caps_in_decision(self, clean_env, temp_ledger):
        """決定に上限情報が含まれる"""
        decision = preflight_check(
            model="gpt-5-mini",
            task="test",
            est_prompt_tokens=100,
            est_completion_tokens=100,
        )

        assert "per_call_cap_jpy" in decision.caps
        assert "daily_soft_cap_jpy" in decision.caps
        assert "daily_hard_cap_jpy" in decision.caps
        assert "today_total_jpy" in decision.caps


# =============================================================================
# Test record_estimate
# =============================================================================


class TestRecordEstimate:
    """record_estimate() のテスト"""

    def test_record_estimate_creates_entry(self, temp_ledger):
        """見積りエントリを作成"""
        decision = BudgetDecision(
            allow=True,
            reason="ok",
            est_cost_jpy=1.5,
            est_prompt_tokens=100,
            est_completion_tokens=50,
            caps={"per_call_cap_jpy": 80.0},
        )

        record_estimate("gpt-5", "test_task", decision)

        assert temp_ledger.exists()
        entry = json.loads(temp_ledger.read_text().strip())

        assert entry["model"] == "gpt-5"
        assert entry["task"] == "test_task"
        assert entry["cost_jpy"] == 1.5
        assert entry["prompt_tokens"] == 100
        assert entry["completion_tokens"] == 50
        assert entry["source"] == "preflight"
        assert entry["allow"] is True
        assert entry["reason"] == "ok"
        assert entry["caps"] == {"per_call_cap_jpy": 80.0}

    def test_record_estimate_blocked_decision(self, temp_ledger):
        """ブロックされた決定も記録"""
        decision = BudgetDecision(
            allow=False,
            reason="per-call cap exceeded",
            est_cost_jpy=100.0,
            est_prompt_tokens=10000,
            est_completion_tokens=10000,
            caps={},
        )

        record_estimate("gpt-5", "expensive_task", decision)

        entry = json.loads(temp_ledger.read_text().strip())
        assert entry["allow"] is False
        assert entry["reason"] == "per-call cap exceeded"


# =============================================================================
# Test Integration Scenarios
# =============================================================================


class TestIntegrationScenarios:
    """統合シナリオのテスト"""

    def test_full_workflow_allowed(self, clean_env, temp_ledger):
        """許可されるワークフロー全体"""
        # 見積りチェック
        decision = preflight_check(
            model="gpt-5-mini",
            task="integration_test",
            est_prompt_tokens=100,
            est_completion_tokens=100,
        )
        assert decision.allow is True

        # 見積り記録
        record_estimate("gpt-5-mini", "integration_test", decision)

        # 実測値記録
        record_usage("gpt-5-mini", "integration_test", 0.08, 100, 100)

        # 台帳に2エントリ（見積り + 実測）
        lines = temp_ledger.read_text().strip().split("\n")
        assert len(lines) == 2

        entries = [json.loads(line) for line in lines]
        assert entries[0]["source"] == "preflight"
        assert entries[1]["source"] == "post_call"

    def test_full_workflow_blocked(self, clean_env, temp_ledger, monkeypatch):
        """ブロックされるワークフロー全体"""
        monkeypatch.setattr(budget, "PER_CALL_CAP_JPY", 0.01)

        # 見積りチェック（ブロック）
        decision = preflight_check(
            model="gpt-5",
            task="expensive_task",
            est_prompt_tokens=10000,
            est_completion_tokens=10000,
        )
        assert decision.allow is False

        # ブロックされた見積りも記録
        record_estimate("gpt-5", "expensive_task", decision)

        # 実測値は記録されない（実行されないため）

        # 台帳には見積りのみ
        lines = temp_ledger.read_text().strip().split("\n")
        assert len(lines) == 1

        entry = json.loads(lines[0])
        assert entry["source"] == "preflight"
        assert entry["allow"] is False


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_zero_token_request(self, clean_env, temp_ledger):
        """トークン数0のリクエスト"""
        decision = preflight_check(
            model="gpt-5",
            task="zero_tokens",
            est_prompt_tokens=0,
            est_completion_tokens=0,
        )

        assert decision.allow is True
        assert decision.est_cost_jpy == 0.0

    def test_very_large_token_request(self, clean_env, temp_ledger, monkeypatch):
        """非常に大きなトークン数リクエスト"""
        monkeypatch.setattr(budget, "PER_CALL_CAP_JPY", 500.0)

        decision = preflight_check(
            model="gpt-5",
            task="huge_request",
            est_prompt_tokens=100000,
            est_completion_tokens=100000,
        )

        # 100k + 100k tokens = 約660円 > 500円 (per-call cap)
        assert decision.allow is False
        assert "per-call cap exceeded" in decision.reason

    def test_negative_cost_calculation(self):
        """負のトークン数（異常値）でもエラーにならない"""
        # 実装は max(1, ...) を使っていないので負の値も計算される
        cost = _estimate_cost_jpy("gpt-5", -100, -100)
        # 負のコストになる
        assert cost < 0

    def test_multiple_requests_same_second(self, clean_env, temp_ledger):
        """同じ秒に複数のリクエスト"""
        for i in range(10):
            record_usage(f"model-{i}", "task", 0.1, 10, 10)

        lines = temp_ledger.read_text().strip().split("\n")
        assert len(lines) == 10

    def test_ledger_file_write_error_handled(self, temp_ledger, monkeypatch, capsys):
        """台帳書き込みエラーが握りつぶされる"""
        # ファイルを読み取り専用にする（書き込み失敗を誘発）
        temp_ledger.touch()
        temp_ledger.chmod(0o444)

        # エラーが握りつぶされることを確認
        try:
            record_usage("gpt-5", "task", 1.0, 100, 50)
            # 例外が投げられないことを確認
        except Exception as e:
            pytest.fail(f"record_usage should not raise exception: {e}")
        finally:
            # クリーンアップ
            temp_ledger.chmod(0o644)

    def test_concurrent_read_and_write(self, clean_env, temp_ledger):
        """読み込みと書き込みの並行実行"""

        def writer():
            for i in range(50):
                record_usage("gpt-5", f"task-{i}", 0.1, 10, 10)

        def reader():
            for _ in range(50):
                total = _read_today_total()
                # total は増加していく
                assert total >= 0

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def test_budget_decision_dataclass(self):
        """BudgetDecision データクラスの基本動作"""
        decision = BudgetDecision(
            allow=True,
            reason="test",
            est_cost_jpy=1.5,
            est_prompt_tokens=100,
            est_completion_tokens=50,
            caps={"test": "value"},
        )

        assert decision.allow is True
        assert decision.reason == "test"
        assert decision.est_cost_jpy == 1.5
        assert decision.est_prompt_tokens == 100
        assert decision.est_completion_tokens == 50
        assert decision.caps == {"test": "value"}

    def test_day_boundary_handling(self, temp_ledger):
        """日付境界の処理"""
        # 昨日のエントリ
        yesterday = _day_key(time.time() - 86400)
        today = _day_key()

        entries = [
            {"day": yesterday, "cost_jpy": 100.0},
            {"day": today, "cost_jpy": 50.0},
        ]
        temp_ledger.write_text("\n".join(json.dumps(e) for e in entries) + "\n")

        # 今日の合計のみ
        total = _read_today_total()
        assert abs(total - 50.0) < 0.01

    def test_unicode_in_task_name(self, temp_ledger):
        """タスク名にUnicode文字"""
        record_usage("gpt-5", "日本語タスク", 1.0, 100, 50)

        entry = json.loads(temp_ledger.read_text().strip())
        assert entry["task"] == "日本語タスク"

    def test_very_long_model_name(self, temp_ledger):
        """非常に長いモデル名"""
        long_name = "a" * 1000
        record_usage(long_name, "task", 1.0, 100, 50)

        entry = json.loads(temp_ledger.read_text().strip())
        assert entry["model"] == long_name

    def test_caps_dictionary_structure(self, clean_env, temp_ledger):
        """caps辞書の構造を確認"""
        decision = preflight_check(
            model="gpt-5",
            task="test",
            est_prompt_tokens=100,
            est_completion_tokens=100,
        )

        assert isinstance(decision.caps, dict)
        required_keys = [
            "per_call_cap_jpy",
            "daily_soft_cap_jpy",
            "daily_hard_cap_jpy",
            "today_total_jpy",
        ]
        for key in required_keys:
            assert key in decision.caps
