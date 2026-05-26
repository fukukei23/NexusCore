from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class SessionState:
    """セッションの現在状態を表すシンプルなデータクラス。"""

    session_id: str
    status: str  # "running" | "paused" | "stopped"
    last_phase: str  # 例: "requirement", "planning", "coding", ...
    last_updated: float  # Unix time
    metadata: dict[str, Any]


class SessionController:
    """
    NexusCore のセッションライフサイクルを管理するクラス。

    役割:
      - 外部 UI/CLI/HTTP からの「中断/再開」指示を control.json 経由で受け取る。
      - Orchestrator などの長時間処理からは、`checkpoint()` と `should_stop()` を呼ぶだけでよい。
      - 「ここまでで一旦保存して」に相当する状態を `state.json` に常に保存しておく。
    """

    def __init__(self, session_id: str, root_dir: str = ".nexus/sessions") -> None:
        self.session_id = session_id
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)

        self.control_file = self.root / f"{session_id}.control.json"
        self.state_file = self.root / f"{session_id}.state.json"
        # Optional: runner-injected phase gating (external control).
        # Default empty keeps existing behavior unchanged.
        self.stop_before_phases: list[str] = []

    # ---------------------------------------------------------------------
    # 外部（Chat UI / CLI / Web API）から呼び出すことを想定したメソッド
    # ---------------------------------------------------------------------
    def request_stop(self) -> None:
        """セッションに対して「ここで止めて」の指示を出す。"""
        self._write_control({"command": "stop"})

    def request_pause(self) -> None:
        """将来の発展用。「一時停止」を表現したい場合に利用可能。"""
        self._write_control({"command": "pause"})

    def request_continue(self) -> None:
        """セッションに対して「続けて」の指示を出す。"""
        self._write_control({"command": "continue"})

    # ---------------------------------------------------------------------
    # Orchestrator / Self-Healing Service など内部から利用するメソッド
    # ---------------------------------------------------------------------
    def should_stop(self) -> bool:
        """
        現在の control.json を読み、stop/pause 指示が出ていれば True を返す。
        Orchestrator 側ではフェーズの境目でこれを呼び出して中断判定に使う。
        """
        cmd = self._read_control()
        return cmd.get("command") in ("stop", "pause")

    def set_stop_before_phases(self, phases: list[str]) -> None:
        """
        Set phase-gating stop policy (runner-side external control).

        This does NOT interpret phases; it merely stores them so callers can
        enforce a consistent stop policy at phase boundaries.
        """
        self.stop_before_phases = list(phases)
        # Keep it observable for external tools without changing the command semantics.
        try:
            cmd = self._read_control()
            cmd["stop_before_phases"] = list(phases)
            self._write_control(cmd)
        except (OSError, json.JSONDecodeError):
            pass

    def checkpoint(self, phase: str, metadata: dict[str, Any] | None = None) -> None:
        """
        現在のフェーズとメタデータを state.json に保存する。

        例:
            controller.checkpoint(
                phase="after_planning",
                metadata={"plan_summary": "..."}
            )
        """
        state = SessionState(
            session_id=self.session_id,
            status="running",
            last_phase=phase,
            last_updated=time.time(),
            metadata=metadata or {},
        )
        self._write_state(asdict(state))

    # ---------------------------------------------------------------------
    # 内部ユーティリティ (ファイル I/O)
    # ---------------------------------------------------------------------
    def _write_control(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.control_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _read_control(self) -> dict[str, Any]:
        if not self.control_file.exists():
            return {}
        try:
            with self.control_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            # 破損していても全システムを止めない
            return {}

    def _read_state(self) -> dict[str, Any]:
        if not self.state_file.exists():
            return {}
        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_state(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
