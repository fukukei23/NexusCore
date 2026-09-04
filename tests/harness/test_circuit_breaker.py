"""Task 13: circuit_breaker.py（CLOSED→OPEN→HALF_OPEN）

plan Step 1 + MLR前提の補強テスト。
※ plan本文のtest_half_open_probe_success_recoversはcooldown既定300秒のままだと
  allow_probe()が即Trueにならず通らない（windowとcooldownの混同）→
  本テストスイートではcooldown_seconds=0を明示渡ししてクールダウン経過をシミュレート。
"""
import datetime as dt

from nexuscore.harness.circuit_breaker import CircuitBreaker, State


class FakeClock:
    """決定論的テスト用クロック（_now注入・cooldown経過をsleep無しでシミュレート）"""

    def __init__(self):
        self.t = dt.datetime(2026, 9, 5, tzinfo=dt.UTC)

    def __call__(self) -> dt.datetime:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += dt.timedelta(seconds=seconds)


def test_closed_to_open_on_3_429_in_window():
    cb = CircuitBreaker(provider="openai", window_seconds=60, threshold=3)
    for _ in range(3):
        cb.record_failure(is_429=True)
    assert cb.state == State.OPEN


def test_open_rejects_requests_until_cooldown():
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=1, cooldown_seconds=300)
    cb.record_failure(is_429=True)
    assert cb.state == State.OPEN
    assert cb.allow_request() is False
    cb.record_failure(is_429=True)  # OPEN中の追加失敗でも状態は変化しない
    assert cb.state == State.OPEN


def test_open_transitions_to_half_open_after_cooldown():
    clock = FakeClock()
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=1,
                        cooldown_seconds=300, _now=clock)
    cb.record_failure(is_429=True)
    assert cb.state == State.OPEN
    clock.advance(300)
    assert cb.state == State.HALF_OPEN  # cooldown経過→遷移
    assert cb.allow_request() is True  # HALF_OPENでは通常リクエスト許可


def test_half_open_probe_success_recovers():
    clock = FakeClock()
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=1,
                        cooldown_seconds=300, probe_required=2, _now=clock)
    cb.record_failure(is_429=True)
    clock.advance(300)
    assert cb.allow_probe() is True  # HALF_OPEN遷移済み→プローブ許可
    cb.record_probe_success()
    assert cb.state == State.HALF_OPEN  # 1/2では未回復
    cb.record_probe_success()
    assert cb.state == State.CLOSED  # 2/2で回復


def test_probe_failure_reopens():
    clock = FakeClock()
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=1,
                        cooldown_seconds=300, _now=clock)
    cb.record_failure(is_429=True)
    clock.advance(300)
    assert cb.allow_probe() is True
    cb.record_probe_failure()
    assert cb.state == State.OPEN  # プローブ失敗→OPEN復帰・opened_atも更新


def test_non_429_failure_ignored_when_not_closed():
    # spec: 連続429が主トリガ・非CLOSED時の非429失敗は状態に影響しない
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=1, cooldown_seconds=300)
    cb.record_failure(is_429=True)
    opened_at_before = cb.export_state()["breaker_opened_at"]
    cb.record_failure(is_429=False)
    assert cb.state == State.OPEN
    assert cb.export_state()["breaker_opened_at"] == opened_at_before


def test_export_state_matches_run_state_fields():
    # round7修正条項（Task 12側）: breaker_opened_at/probe_attempts/probe_resultsを
    # state経由で判定できるようexportする
    cb = CircuitBreaker(provider="openai", window_seconds=0, threshold=1, cooldown_seconds=300)
    cb.record_failure(is_429=True)
    snap = cb.export_state()
    assert snap["breaker_state"] == "OPEN"
    assert snap["provider"] == "openai"
    assert snap["breaker_opened_at"] is not None and snap["breaker_opened_at"].endswith("Z")
    assert snap["probe_attempts"] == 0
    assert snap["probe_results"] == []


# ---- MLR Task13レビュー採用分の検証テスト（2026-09-05） ----

def test_record_probe_failure_is_guarded_outside_half_open():
    """採用: CLOSED中の誤record_probe_failureで強制OPENしない（MiniMax+Gemini指摘）"""
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=3, cooldown_seconds=300)
    cb.record_probe_failure()  # CLOSED中の誤呼び
    assert cb.state == State.CLOSED


def test_cooldown_boundary_exact_second_transitions():
    """採用: 境界値テスト（cooldown-1秒はOPEN・ちょうどcooldown秒でHALF_OPEN）"""
    clock = FakeClock()
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=1,
                        cooldown_seconds=300, _now=clock)
    cb.record_failure(is_429=True)
    clock.advance(299.9)
    assert cb.state == State.OPEN  # 直前はまだOPEN
    clock.advance(0.1)
    assert cb.state == State.HALF_OPEN  # ちょうど300秒で遷移（>=判定）


def test_probe_attempts_counts_both_success_and_failure():
    """採用: probe_attemptsは成功・失敗の両方で加算（OR指摘・export整合）"""
    clock = FakeClock()
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=1,
                        cooldown_seconds=300, _now=clock)
    cb.record_failure(is_429=True)
    clock.advance(300)
    assert cb.allow_probe() is True
    cb.record_probe_failure()
    snap = cb.export_state()
    assert snap["probe_attempts"] == 1
    assert snap["probe_results"] == []
