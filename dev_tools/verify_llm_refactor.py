#!/usr/bin/env python3
"""
Quick verification script for LLM routing refactor.
Tests that imports work and basic structures are correct.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

try:
    from nexuscore.llm.routing_policy import (
        TASK_MODEL_MAP_DEFAULT,
        LEGACY_TO_TASK,
        model_family,
        split_provider,
    )
    from nexuscore.llm.task_model_map import (
        TASK_MODEL_CONFIGS,
        build_task_model_map_dict,
    )
    from nexuscore.llm.llm_profiles import PROFILE_REGISTRY, profile_to_model_name

    print("✓ All imports successful")

    # Check TASK_MODEL_MAP_DEFAULT structure
    assert "general" in TASK_MODEL_MAP_DEFAULT, "Missing 'general' task"
    assert "primary" in TASK_MODEL_MAP_DEFAULT["general"], "Missing 'primary' key"
    print("✓ TASK_MODEL_MAP_DEFAULT structure valid")

    # Check LEGACY_TO_TASK
    assert LEGACY_TO_TASK["qa"] == "testing", "LEGACY_TO_TASK['qa'] mismatch"
    assert "testing" in TASK_MODEL_CONFIGS, "Missing 'testing' alias in TASK_MODEL_CONFIGS"
    print("✓ LEGACY_TO_TASK mappings valid")

    # Check that build_task_model_map_dict produces same structure
    rebuilt = build_task_model_map_dict()
    assert "general" in rebuilt, "Rebuilt map missing 'general'"
    assert rebuilt["general"]["primary"], "Rebuilt map missing primary"
    print("✓ build_task_model_map_dict() works correctly")

    # Check profile registry
    assert "gpt5_codex" in PROFILE_REGISTRY, "Missing gpt5_codex profile"
    model_name = profile_to_model_name("gpt5_codex")
    assert ":" in model_name, f"Invalid model name format: {model_name}"
    print("✓ LLM profiles work correctly")

    # Check model_family
    assert model_family("openai:gpt-5") == "openai"
    assert model_family("google:gemini-2.5-flash") == "gemini"
    print("✓ model_family() works correctly")

    print("\n✅ All verifications passed!")
    sys.exit(0)

except Exception as e:
    print(f"\n❌ Verification failed: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

