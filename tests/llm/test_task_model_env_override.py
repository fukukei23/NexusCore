"""壁3: タスク単位のLLBプロファイルenv上書きのテスト（nexuscore-bench Phase 0）.

NEXUS_TASK_MODEL_<TASK> がタスク単位・NEXUS_TASK_MODEL_<CATEGORY> より優先。
未設定なら既存挙動完全不変（後方互換）。
"""
import os
from unittest.mock import patch

from src.nexuscore.llm.task_model_map import _resolve_primary


class TestTaskLevelEnvOverride:
    def test_task_env_overrides_default(self) -> None:
        with patch.dict(os.environ, {"NEXUS_TASK_MODEL_DEBUG": "gemini_secondary"}):
            assert _resolve_primary("debug", "glm_default") == "gemini_secondary"

    def test_task_env_overrides_category_env(self) -> None:
        with patch.dict(os.environ, {
            "NEXUS_TASK_MODEL_DEBUG": "gemini_secondary",
            "NEXUS_TASK_MODEL_CODING": "minimax_default",
        }):
            # タスク単位がカテゴリ単位に優先
            assert _resolve_primary("debug", "glm_default") == "gemini_secondary"

    def test_unset_keeps_default(self) -> None:
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("NEXUS_TASK_MODEL")}
        with patch.dict(os.environ, env, clear=True):
            assert _resolve_primary("debug", "glm_default") == "glm_default"

    def test_unknown_profile_falls_back(self) -> None:
        with patch.dict(os.environ, {"NEXUS_TASK_MODEL_DEBUG": "no-such-profile"}):
            # 未知profile IDは既定へフォールバック（クラッシュしない）
            assert _resolve_primary("debug", "glm_default") == "glm_default"

    def test_unrelated_task_unaffected(self) -> None:
        with patch.dict(os.environ, {"NEXUS_TASK_MODEL_DEBUG": "gemini_secondary"}):
            # 他タスク(code_generate)は影響を受けない
            assert _resolve_primary("code_generate", "glm_default") == "glm_default"
