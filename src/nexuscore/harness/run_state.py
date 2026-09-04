"""Task 12: 原子的状態保存・破損時quarantine・ファイルロック (spec §5/§10)

round7修正条項を反映:
- save戻り値=Success/PartialFailure（Task 14のloopがabort判断に使う）
- 起動時scanで*.tmpを発見→同一run_idのチェックサム+本体があれば本体採用・なければquarantine化
- RunStateにbreaker_opened_at/probe_attempts/probe_resultsを追加（breaker復帰判定をstate経由で行う）

MLR Task12レビュー採用7件（2026-09-04）:
- load_or_quarantineも同一ロックで保護（save/ load並走競合対策）
- .sha256書込をロック内へ移動（解放後書込のレース窓解消）
- quarantine名にpid+uuid接尾辞（同一秒衝突対策）
- save失敗時のtmp残骸cleanup
- schema_version検証（不一致=破損扱いquarantine）+except例外の絞り込み
- os.replace後のディレクトリfsync（クラッシュ耐性）
- utcnow→now(timezone.utc)

ロックはspec §10: fcntl.flock固定・Linux/WSL前提（Windows対応はPhase 5以降）。
flockはプロセス死亡時にカーネルが自動解放するためstale lockデッドロックは発生しない。
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
from uuid import uuid4

DEFAULT_PATH = Path(os.getenv("NEXUSCORE_RUN_STATE_PATH",
                              "artifacts/harness/run_state.json"))

SCHEMA_VERSION = 1


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
    schema_version: int = SCHEMA_VERSION
    updated_at: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


class RunStateStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def _lock_path(self) -> Path:
        return self.path.with_suffix(self.path.suffix + ".lock")

    @property
    def _tmp_path(self) -> Path:
        return self.path.with_suffix(self.path.suffix + ".tmp")

    @property
    def _checksum_path(self) -> Path:
        return self.path.parent / (self.path.name + ".sha256")

    def _quarantine_name(self, suffix: str) -> Path:
        """一意名（同一秒の複数quarantineで上書きしない・MLR採用#3）"""
        return self.path.parent / (
            f"quarantine-{int(time.time())}-{os.getpid()}-{uuid4().hex[:8]}{suffix}"
        )

    def _fsync_dir(self) -> None:
        """os.replace後のディレクトリfsync（rename永続化・MLR採用#6）"""
        dir_fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)

    def save(self, state: RunState) -> SaveResult:
        state.updated_at = (
            dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")
        )
        data = state.to_dict()
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
        checksum = hashlib.sha256(payload.encode()).hexdigest()
        record = {"data": data, "checksum": checksum, "schema_version": SCHEMA_VERSION}
        body = json.dumps(record, ensure_ascii=False, sort_keys=True)
        try:
            with open(self._lock_path, "w") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    with open(self._tmp_path, "w") as tf:
                        tf.write(body)
                        tf.flush()
                        os.fsync(tf.fileno())
                    os.replace(self._tmp_path, self.path)
                    self._fsync_dir()
                    # checksum書込もロック内（MLR採用#2・解放後書込のレース窓対策）
                    self._checksum_path.write_text(checksum)
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
            return SaveResult.SUCCESS
        except OSError:
            # tmp残骸cleanup（MLR採用#4・replace失敗時に孤立するのを防ぐ）
            try:
                self._tmp_path.unlink()
            except OSError:
                pass
            return SaveResult.PARTIAL_FAILURE  # round7修正条項

    def load_or_quarantine(self) -> tuple[RunState | None, str | None]:
        """破損時quarantine+orphan temp検出（MLR採用#1: 全経路を同一ロックで保護）"""
        if not self.path.exists() and not self._tmp_path.exists():
            return None, None
        try:
            with open(self._lock_path, "w") as lf:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                try:
                    return self._load_locked()
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        except (
            json.JSONDecodeError,
            ValueError,
            OSError,
            TypeError,
            KeyError,
        ) as e:
            # 破損→quarantine（spec §5 F2: 自動クリア禁止）
            # 未知キー/型不一致もTypeErrorでここに流れる（fail-safe隔離）
            self._quarantine(self.path, ".json")
            tmp = self._tmp_path
            if tmp.exists():
                self._quarantine(tmp, ".tmp")
            return None, str(e)

    def _load_locked(self) -> tuple[RunState | None, str | None]:
        """ロック保持中の読込本体（呼び出し側が例外をquarantineへ変換する）"""
        tmp = self._tmp_path
        if not self.path.exists():
            # orphan temp: 本体なし → *.tmpをquarantine化（採用はしない・修正条項どおり）
            if tmp.exists():
                self._quarantine(tmp, ".tmp")
            return None, None
        record = json.loads(self.path.read_text())
        if record.get("schema_version") != SCHEMA_VERSION:
            # MLR採用#5: 将来バージョン/破損値は読まず隔離
            raise ValueError(
                f"unsupported schema_version: {record.get('schema_version')!r}"
            )
        expected = None
        if self._checksum_path.exists():
            expected = self._checksum_path.read_text().strip()
        if expected and expected != record.get("checksum"):
            raise ValueError("checksum mismatch")
        state = RunState(**record["data"])
        # 本体採用成功 → orphan tempが残っていればquarantine（本体が正）
        if tmp.exists():
            self._quarantine(tmp, ".tmp")
        return state, None

    def _quarantine(self, src: Path, suffix: str) -> None:
        """rename隔離のみ（削除はしない・spec §5 F2）"""
        try:
            src.rename(self._quarantine_name(suffix))
        except OSError:
            pass  # 隔離失敗時も例外は握らない（load自体の応答を優先）
