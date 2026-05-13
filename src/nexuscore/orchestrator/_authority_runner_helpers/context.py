from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any


def default_context_factory(
    *,
    user_requirement: str,
    language: str,
    fast_lane: bool,
    run_db_id: int | None,
) -> Any:
    try:
        from nexuscore.core.orchestrator_models import OrchestratorContext

        return OrchestratorContext(
            task_id=uuid.uuid4().hex,
            user_requirement=user_requirement,
            language=language,
            fast_lane=fast_lane,
            run_db_id=run_db_id,
        )
    except Exception:

        @dataclass
        class _FallbackContext:
            task_id: str
            user_requirement: str
            language: str
            fast_lane: bool
            run_db_id: int | None
            specs: dict[str, Any]
            plan: dict[str, Any]
            architecture: dict[str, Any]
            implementation: dict[str, Any]
            testing: dict[str, Any]
            review: dict[str, Any]
            phase_log: list[str]

        return _FallbackContext(
            task_id=uuid.uuid4().hex,
            user_requirement=user_requirement,
            language=language,
            fast_lane=fast_lane,
            run_db_id=run_db_id,
            specs={},
            plan={},
            architecture={},
            implementation={},
            testing={},
            review={},
            phase_log=[],
        )
