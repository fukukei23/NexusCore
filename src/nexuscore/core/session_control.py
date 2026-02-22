"""
session_control.py

NexusCore の長時間タスク（Orchestrator など）に対して、
「中断」「一旦保存」「再開」といったセッション操作を提供する制御レイヤ。

設計方針:
- 各セッションは session_id で識別する。
- `.nexus/sessions/{session_id}.control.json` を通じて外部から stop/pause/continue を指示。
- `.nexus/sessions/{session_id}.state.json` に現在のフェーズやメタデータをチェックポイントとして保存。
- Orchestrator 側は、フェーズの境目ごとに `checkpoint()` と `should_stop()` を呼ぶだけでよい。
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class SessionState:
    """セッションの現在状態を表すシンプルなデータクラス。"""
    session_id: str
    status: str          # "running" | "paused" | "stopped"
    last_phase: str      # 例: "requirement", "planning", "coding", ...
    last_updated: float  # Unix time
    metadata: Dict[str, Any]


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
        except Exception:
            pass

    def checkpoint(self, phase: str, metadata: Optional[Dict[str, Any]] = None) -> None:
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
    def _write_control(self, data: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.control_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _read_control(self) -> Dict[str, Any]:
        if not self.control_file.exists():
            return {}
        try:
            with self.control_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            # 破損していても全システムを止めない
            return {}

    def _read_state(self) -> Dict[str, Any]:
        if not self.state_file.exists():
            return {}
        try:
            with self.state_file.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _write_state(self, data: Dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        with self.state_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

