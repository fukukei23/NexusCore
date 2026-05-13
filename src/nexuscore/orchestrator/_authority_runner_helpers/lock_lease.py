from __future__ import annotations

import threading
from typing import Any

from ..run_lock import refresh_run_lock, release_run_lock, try_acquire_run_lock


class RunLockLease:
    """
    Context manager for holding a run lock during execution (Mode B).

    Acquires lock on enter, starts a background refresh loop, and releases on exit.
    If refresh fails, sets a flag that can be checked to trigger safe shutdown.
    """

    def __init__(self, run_id: str, refresh_interval_seconds: float | None = None):
        self.run_id = run_id
        self.refresh_interval = refresh_interval_seconds
        if self.refresh_interval is None:
            from ..run_lock import _get_lock_refresh_seconds

            self.refresh_interval = float(_get_lock_refresh_seconds())
        self._lock_acquired = False
        self._refresh_thread: threading.Thread | None = None
        self._stop_refresh = threading.Event()
        self._refresh_failed = threading.Event()
        self._refresh_failure_reason: str | None = None
        self._refresh_failure_details: dict[str, Any] | None = None

    def __enter__(self) -> RunLockLease:
        ok, reason = try_acquire_run_lock(self.run_id)
        if not ok:
            raise RuntimeError(f"Failed to acquire lock for {self.run_id}: {reason}")

        self._lock_acquired = True
        self._stop_refresh.clear()
        self._refresh_failed.clear()
        self._refresh_failure_reason = None
        self._refresh_failure_details = None

        self._refresh_thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._refresh_thread.start()

        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._stop_refresh.set()
        if self._refresh_thread is not None:
            self._refresh_thread.join(timeout=(self.refresh_interval or 0) * 2)

        if self._lock_acquired:
            release_run_lock(self.run_id)
            self._lock_acquired = False

    def _refresh_loop(self) -> None:
        while not self._stop_refresh.is_set():
            if self._stop_refresh.wait(timeout=self.refresh_interval):
                break

            ok, reason, details = refresh_run_lock(self.run_id)
            if not ok:
                self._refresh_failure_reason = reason
                self._refresh_failure_details = details
                self._refresh_failed.set()
                break

    def is_refresh_failed(self) -> bool:
        return self._refresh_failed.is_set()

    def get_refresh_failure(self) -> tuple[str | None, dict[str, Any] | None]:
        return self._refresh_failure_reason, self._refresh_failure_details
