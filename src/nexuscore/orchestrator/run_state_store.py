from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .run_state_integrity import sign_run_state


def _now_iso8601() -> str:
    return datetime.now(UTC).isoformat()


def _root_dir() -> Path:
    override = os.getenv("NEXUSCORE_RUN_STATE_DIR")
    if override:
        return Path(override)
    return Path("var") / "run_state"


def _state_path(run_id: str) -> Path:
    return _root_dir() / f"{run_id}.json"


def save_state(state: dict[str, Any]) -> None:
    """
    Save run state to JSON file. `state` must contain at least `run_id`.

    The state is signed using HMAC-SHA256 before saving (CR-NEXUS-026).
    """
    run_id = state.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("state.run_id must be a non-empty string")

    root = _root_dir()
    root.mkdir(parents=True, exist_ok=True)

    data = dict(state)
    data.setdefault("updated_at", _now_iso8601())

    # Sign state before saving (CR-NEXUS-026)
    signed_data = sign_run_state(data)

    path = _state_path(run_id)
    path.write_text(json.dumps(signed_data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state(run_id: str) -> dict[str, Any]:
    """
    Load run state from JSON file.
    """
    path = _state_path(run_id)
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def update_state(run_id_or_state: str | dict[str, Any], **patch: Any) -> dict[str, Any]:
    """
    Read-Modify-Write update (keeps unknown fields).

    Backwards compatible API:
    - update_state(run_id: str, **patch)
    - update_state(state: dict)  # full-state style update (RMW merge)
    """
    if isinstance(run_id_or_state, dict):
        incoming = dict(run_id_or_state)
        run_id = incoming.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("state.run_id must be a non-empty string")

        # RMW merge: preserve unknown fields from storage, then overlay incoming.
        base = load_state(run_id)
        merged = dict(base)
        merged.update(incoming)
        merged.update(patch)
        merged["run_id"] = run_id
        merged["updated_at"] = _now_iso8601()
        save_state(merged)
        return merged

    run_id = run_id_or_state
    # RMW merge: preserve unknown fields by patching loaded state.
    base = load_state(run_id)
    merged = dict(base)
    merged.update(patch)
    merged["run_id"] = run_id
    merged["updated_at"] = _now_iso8601()
    save_state(merged)
    return merged
