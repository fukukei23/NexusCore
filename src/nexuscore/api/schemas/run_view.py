"""
RunView schemas for CR-NEXUS-028.

RunView projection models for API responses (RunState is not exposed directly).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExplainabilityModel(BaseModel):
    """Explainability projection model."""

    what: str = Field(..., description="What happened")
    why: str = Field(..., description="Why it happened (error code or reason)")
    next_action: str = Field(..., description="What to do next")
    details: dict[str, Any] | None = Field(None, description="Additional details")

    class Config:
        json_schema_extra = {
            "example": {
                "what": "Resume failed: invalid RunState schema",
                "why": "SCHEMA_INVALID",
                "next_action": "Fix RunState or abort and start a new run",
                "details": None,
            }
        }


class RunViewResponse(BaseModel):
    """RunView projection for API responses."""

    run_id: str = Field(..., description="Run ID")
    status: str = Field(
        ..., description="Run status (RUNNING, PAUSED, COMPLETED, CONFLICT, FAILED, ABORTED)"
    )
    phase: str | None = Field(None, description="Current phase (if paused)")
    authority_level: str | None = Field(
        None, description="Authority level (human, partial, full)"
    )
    updated_at: str | None = Field(None, description="Last update timestamp (ISO8601)")
    explainability: ExplainabilityModel | None = Field(
        None,
        description="Explainability details (required for CONFLICT, FAILED, ABORTED)",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "run_id": "abc123def456",
                "status": "PAUSED",
                "phase": "implementation",
                "authority_level": "partial",
                "updated_at": "2025-01-01T00:00:00+00:00",
                "explainability": None,
            }
        }


class RunCreateRequest(BaseModel):
    """Request model for creating a new run."""

    requirement: str = Field(..., description="User requirement")
    authority_level: str | None = Field(
        None, description="Authority level (human, partial, full)"
    )
    language: str = Field("ja", description="Language (ja, en)")

    class Config:
        json_schema_extra = {
            "example": {
                "requirement": "Create a simple CRM application",
                "authority_level": "partial",
                "language": "ja",
            }
        }
