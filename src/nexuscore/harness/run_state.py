"""Task 12: 原子的状態保存・破損時quarantine・ファイルロック (spec §5/§10)

round7修正条項を反映:
- save戻り値=Success/PartialFailure（Task 14のloopがabort判断に使う）
- 起動時scanで*.tmpを発見→同一run_idのチェックサム+本体があれば本体採用・なければquarantine化
- RunStateにbreaker_opened_at/probe_attempts/probe_resultsを追加（breaker復帰判定をstate経由で行う）

ロックはspec §10: fcntl.flock固定・Linux/WSL前提（Windows対応はPhase 5以降）。
"""
from __future__ import annotations

import dataclasses
import datetime as dt
import fcntl
import hashlib
import json
import os
import time
from enum import Enum
from pathlib import Path

DEFAULT_PATH = Path(os.getenv("NEXUSCORE_RUN_STATE_PATH",
                              "artifacts/harness/run_state.json"))


class SaveResult(Enum):
    """save()の戻り値・Task 14のloopがPartialFailureでabort判断する"""
    SUCCESS = "success"
    PARTIAL_FAILURE = "partial_failure"


@dataclasses.dataclass
class RunState:
    loop_steps: int = 0
    tokens_used: int = 0
    breaker_state: str = "CLOSED"
    provider: str = ""
    in_flight_tool: str | None = None
    abort_reason: str | None = None
    # round7修正条項: breaker復帰判定をstate経由で行うため拡張
    breaker_opened_at: str | None = None
    probe_attempts: int = 0
    probe_results: list[bool] = dataclasses.field(default_factory=list)
    schema_version: int = 1
    updated_at: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class RunStateStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, state: RunState) -> SaveResult:
        state.updated_at = dt.datetime.utcnow().isoformat() + "Z"
        data = state.to_dict()
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
        checksum = hashlib.sha256(payload.encode()).hexdigest()
        record = {"data": data, "checksum": checksum, "schema_version": 1}
        body = json.dumps(record, ensure_ascii=False, sort_keys=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        try:
            with open(lock, "w") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    with open(tmp, "w") as tf:
                        tf.write(body)
                        tf.flush()
                        os.fsync(tf.fileno())
                    os.replace(tmp, self.path)
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
            (self.path.parent / (self.path.name + ".sha256")).write_text(checksum)
            return SaveResult.SUCCESS
        except OSError:
            return SaveResult.PARTIAL_FAILURE  # round7修正条項

    def load_or_quarantine(self) -> tuple[RunState | None, str | None]:
        """round7修正条項のorphan temp検出を起動時scanとして統合"""
        if not self.path.exists():
            # orphan temp: 本体なし → *.tmpをquarantine化
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            if tmp.exists():
                qn = self.path.parent / f"quarantine-{int(time.time())}.tmp"
                tmp.rename(qn)
            return None, None
        try:
            record = json.loads(self.path.read_text())
            ck_path = self.path.parent / (self.path.name + ".sha256")
            expected = ck_path.read_text().strip() if ck_path.exists() else None
            if expected and expected != record.get("checksum"):
                raise ValueError("checksum mismatch")
            state = RunState(**record["data"])
            # 本体採用成功 → orphan tempが残っていればquarantine（本体が正）
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            if tmp.exists():
                qn = self.path.parent / f"quarantine-{int(time.time())}.tmp"
                tmp.rename(qn)
            return state, None
        except Exception as e:
            qn = self.path.parent / f"quarantine-{int(time.time())}.json"
            self.path.rename(qn)
            return None, str(e)
