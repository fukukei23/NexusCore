"""Task 13: ブレーカMVP（CLOSED/OPEN/HALF_OPEN・プロバイダ単位）

spec §5 MVP + round7修正条項（BACKOFF_MAX=300秒の意味を明示）:
- **cooldown_seconds（既定300秒=BACKOFF_MAX）は「OPEN→HALF_OPEN遷移までの待ち」**
- Retry-After未指定時の指数バックオフ（base 2.0秒・full jitter）は**本クラスの管轄外**
  （LLM呼出側のリトライ層・Task 5-7 Mixin / Task 14ループの責務）
- breaker_opened_at/probe_attempts/probe_resultsはexport_state()でRunStateと結線
  （round7修正条項: breaker復帰判定をstate経由で可能に）

※ plan本文テストの既知不整合: planのtest_half_open_probe_success_recoversは
  cooldown既定300秒のままだとallow_probe()が即Trueにならず通らない
  （「window=0ですぐ遷移」はcooldownとwindowの混同）→ テスト側でcooldown_seconds=0を
  明示渡しして経過をシミュレート（plan改訂はしない・本docstringに記録）。
"""
from __future__ import annotations

import datetime as dt
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

# spec §10: バックオフ既定値
BACKOFF_BASE = 2.0  # Retry-After未指定時の指数バックオフ基準秒（本クラス管轄外・リトライ層用）
BACKOFF_MAX = 300.0  # cooldown_seconds既定=HALF_OPEN遷移までの待ち（round7修正条項）


class State(StrEnum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreaker:
    """プロバイダ単位ブレーカ（60秒窓内threshold回のfailureでOPEN・cooldown後にプローブ）

    Task 14のループは allow_request() / allow_probe() / record_failure() /
    export_state() を使用する（state.valueをRunState.breaker_stateへ書込）。
    """

    provider: str
    window_seconds: int = 60
    cooldown_seconds: float = BACKOFF_MAX
    threshold: int = 3  # 窓内failure到達でOPEN
    probe_required: int = 2  # M=2固定（M/NのN側はMVPは2で固定）
    _now: Callable[[], dt.datetime] = field(
        default=lambda: dt.datetime.now(dt.UTC), repr=False, compare=False
    )

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self._failures: list[dt.datetime] = []
        self._state = State.CLOSED
        self._opened_at: dt.datetime | None = None
        self._probe_results: list[bool] = []
        self._probe_attempts = 0

    @property
    def state(self) -> State:
        with self._lock:
            self._maybe_transition()
            return self._state

    def allow_request(self) -> bool:
        with self._lock:
            self._maybe_transition()
            return self._state in (State.CLOSED, State.HALF_OPEN)

    def allow_probe(self) -> bool:
        with self._lock:
            self._maybe_transition()
            return self._state == State.HALF_OPEN

    def record_failure(self, *, is_429: bool) -> None:
        """失敗を記録する（threading.Lock直列化によりスレッドセーフ）

        Args:
            is_429: True=429系（レート制限）・False=その他（5xx/timeout等）。
                非CLOSED時の非429は状態遷移にも記録にも影響しない。
                CLOSED時は非429も窓カウントに含む（plan定義どおり）。
        """
        with self._lock:
            if not is_429 and self._state != State.CLOSED:
                return  # 非429は非CLOSED時の状態遷移に影響しない（spec: 連続429が主トリガ）
            now = self._now()
            self._failures.append(now)
            self._trim(now)
            if self._state == State.HALF_OPEN:
                # プローブ失敗相当→即OPEN復帰
                self._state = State.OPEN
                self._opened_at = now
                self._probe_results.clear()
                return
            # _trim直後なので self._failures が現在の窓内集合（MLR採用: 二重フィルタ排除）
            if len(self._failures) >= self.threshold:
                self._state = State.OPEN
                self._opened_at = now

    def record_probe_success(self) -> None:
        with self._lock:
            if self._state in (State.CLOSED, State.OPEN):
                return  # CLOSEDは記録不要・OPENはプローブ許可前
            self._probe_attempts += 1
            self._probe_results.append(True)
            if len(self._probe_results) >= self.probe_required:
                self._state = State.CLOSED
                self._failures.clear()
                self._probe_results.clear()
                self._opened_at = None

    def record_probe_failure(self) -> None:
        """プローブ失敗→OPEN復帰（MLR採用: HALF_OPEN以外の呼び出しは無視=誤用ガード・
        probe_attemptsは成功/失敗両方で加算）"""
        with self._lock:
            if self._state != State.HALF_OPEN:
                return  # CLOSED/OPEN中の誤呼びで強制OPENしない
            self._probe_attempts += 1
            self._state = State.OPEN
            self._opened_at = self._now()
            self._probe_results.clear()

    def export_state(self) -> dict:
        """RunState（Task 12）との結線用スナップショット（round7修正条項）"""
        with self._lock:
            self._maybe_transition()
            return {
                "breaker_state": self._state.value,
                "provider": self.provider,
                "breaker_opened_at": (
                    self._opened_at.isoformat().replace("+00:00", "Z")
                    if self._opened_at else None
                ),
                "probe_attempts": self._probe_attempts,
                "probe_results": list(self._probe_results),
            }

    def _trim(self, now: dt.datetime) -> None:
        self._failures = [
            f for f in self._failures
            if (now - f).total_seconds() <= self.window_seconds
        ]

    def _maybe_transition(self) -> None:
        if self._state == State.OPEN and self._opened_at is not None:
            elapsed = (self._now() - self._opened_at).total_seconds()
            if elapsed >= self.cooldown_seconds:
                self._state = State.HALF_OPEN
                self._probe_results.clear()
                self._probe_attempts = 0
