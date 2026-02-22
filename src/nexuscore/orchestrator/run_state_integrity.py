"""
run_state_integrity.py

CR-022 (Integrity / Tamper Detection Contract) + CR-NEXUS-026: HMAC-SHA256 implementation.

RunState integrity verification using HMAC-SHA256 signatures.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import UTC, datetime
from typing import Any


def _get_hmac_secret() -> bytes:
    """
    Get HMAC secret from environment variable.

    Raises RuntimeError if not set (silent fallback is forbidden).
    """
    secret = os.getenv("NEXUSCORE_RUNSTATE_HMAC_SECRET")
    if not secret:
        raise RuntimeError(
            "NEXUSCORE_RUNSTATE_HMAC_SECRET environment variable must be set for RunState integrity verification"
        )
    return secret.encode("utf-8")


def _canonical_json(data: dict[str, Any]) -> bytes:
    """
    Generate canonical JSON representation (excluding integrity field).

    The integrity field itself is excluded from signing to avoid circular dependency.
    """
    # Exclude integrity field for signing
    signing_data = {k: v for k, v in data.items() if k != "integrity"}
    # Canonical JSON: sorted keys, no extra whitespace
    return json.dumps(
        signing_data, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


def sign_run_state(state: dict[str, Any]) -> dict[str, Any]:
    """
    Sign a RunState dictionary using HMAC-SHA256.

    Adds an 'integrity' field to the state containing:
    - algorithm: "HMAC-SHA256"
    - key_id: "default" (for future key rotation support)
    - signature: hex-encoded HMAC-SHA256 signature
    - signed_at: ISO8601 timestamp

    Args:
        state: RunState dictionary (must not already have 'integrity' field, or it will be replaced)

    Returns:
        RunState dictionary with 'integrity' field added

    Raises:
        RuntimeError: If NEXUSCORE_RUNSTATE_HMAC_SECRET is not set
    """
    secret = _get_hmac_secret()
    canonical = _canonical_json(state)

    # Compute HMAC-SHA256
    signature = hmac.new(secret, canonical, hashlib.sha256).hexdigest()

    # Build integrity block

    signed_at = datetime.now(UTC).isoformat()
    integrity_block: dict[str, Any] = {
        "algorithm": "HMAC-SHA256",
        "key_id": "default",
        "signature": signature,
        "signed_at": signed_at,
    }

    # Add integrity to state (create copy to avoid mutating input)
    signed_state = dict(state)
    signed_state["integrity"] = integrity_block

    return signed_state


def verify_integrity(state: dict[str, Any]) -> tuple[bool, str | None, str | None]:
    """
    Verify integrity of untrusted RunState using HMAC-SHA256.

    Args:
        state: RunState dictionary (expected to have 'integrity' field)

    Returns:
        (ok, code, message)
        - ok=True, code=None, message=None when verification succeeds
        - ok=False, code="STATE_INTEGRITY_MISSING" when integrity field is missing
        - ok=False, code="STATE_INTEGRITY_VIOLATION" when signature does not match
        - ok=False, code="STATE_INTEGRITY_ERROR" for other errors

    Raises:
        RuntimeError: If NEXUSCORE_RUNSTATE_HMAC_SECRET is not set
    """
    # Check if integrity field exists
    integrity = state.get("integrity")
    if not integrity or not isinstance(integrity, dict):
        return False, "STATE_INTEGRITY_MISSING", "RunState missing integrity field"

    # Verify algorithm
    algorithm = integrity.get("algorithm")
    if algorithm != "HMAC-SHA256":
        return False, "STATE_INTEGRITY_ERROR", f"Unsupported integrity algorithm: {algorithm}"

    # Get expected signature
    expected_signature = integrity.get("signature")
    if not isinstance(expected_signature, str):
        return False, "STATE_INTEGRITY_ERROR", "Invalid signature format in integrity field"

    try:
        secret = _get_hmac_secret()
        canonical = _canonical_json(state)

        # Compute HMAC-SHA256
        computed_signature = hmac.new(secret, canonical, hashlib.sha256).hexdigest()

        # Compare signatures using constant-time comparison
        if not hmac.compare_digest(computed_signature, expected_signature):
            return (
                False,
                "STATE_INTEGRITY_VIOLATION",
                "RunState signature verification failed (possible tampering)",
            )

        return True, None, None

    except RuntimeError:
        # Secret not set - propagate
        raise
    except Exception as e:
        return False, "STATE_INTEGRITY_ERROR", f"Integrity verification error: {str(e)}"
