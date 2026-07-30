"""NEXUS_TASK_MODEL_CODING/REVIEW/GENERAL env 上書きのテスト。

7-23監査④デッドキー是正: env の3キーで各カテゴリの primary を上書き可能にする。
値は profile ID（glm_default/gemini_secondary/minimax_default 等）を想定。
"""

from nexuscore.llm.task_model_map import build_task_model_map_dict

ENV_KEYS = (
    "NEXUS_TASK_MODEL_CODING",
    "NEXUS_TASK_MODEL_REVIEW",
    "NEXUS_TASK_MODEL_GENERAL",
)


def _clear_env(monkeypatch):
    for key in ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_coding_env_overrides_primary(monkeypatch):
    """NEXUS_TASK_MODEL_CODING 設定時、生成系タスクの primary が上書きされる。"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("NEXUS_TASK_MODEL_CODING", "minimax_default")
    result = build_task_model_map_dict()
    for task in ("code_generate", "code_refactor", "code_explain", "test_generate", "debug", "self_heal"):
        assert result[task]["primary"].startswith("minimax:"), f"{task} should be overridden to minimax"


def test_review_env_overrides_primary(monkeypatch):
    """NEXUS_TASK_MODEL_REVIEW 設定時、レビュー系タスクの primary が上書きされる。"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("NEXUS_TASK_MODEL_REVIEW", "glm_default")
    result = build_task_model_map_dict()
    for task in ("code_review", "architect", "arch_design", "plan_generate", "requirement", "policy_check", "postmortem_analyze"):
        assert result[task]["primary"].startswith("glm:"), f"{task} should be overridden to glm"


def test_general_env_overrides_primary(monkeypatch):
    """NEXUS_TASK_MODEL_GENERAL 設定時、分析/分類系タスクの primary が上書きされる。"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("NEXUS_TASK_MODEL_GENERAL", "glm_default")
    result = build_task_model_map_dict()
    for task in ("routing_classify", "knowledge_curate", "general", "chat_general", "analytical", "pricing_strategy"):
        assert result[task]["primary"].startswith("glm:"), f"{task} should be overridden to glm"


def test_no_env_keeps_default(monkeypatch):
    """env 未設定時は既存挙動を維持（既存テストとの互換）。"""
    _clear_env(monkeypatch)
    result = build_task_model_map_dict()
    # 既定: code_generate は GLM, code_review は Gemini, routing_classify は MiniMax
    assert result["code_generate"]["primary"].startswith("glm:")
    assert result["routing_classify"]["primary"].startswith("minimax:")
    review_primary = result["code_review"]["primary"]
    assert "gemini" in review_primary or "google" in review_primary, "code_review default should be Gemini"


def test_alias_inherits_category(monkeypatch):
    """alias（testing 等）は target と同カテゴリとして上書きされる。"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("NEXUS_TASK_MODEL_CODING", "minimax_default")
    result = build_task_model_map_dict()
    # testing は test_generate の alias → CODING系
    assert result["testing"]["primary"].startswith("minimax:"), "alias 'testing' should inherit coding category"


def test_invalid_profile_falls_back(monkeypatch):
    """未知の profile ID 値は警告＋既定フォールバック（移行安全性・クラッシュ回避）。"""
    _clear_env(monkeypatch)
    # _WARNED_BAD_ENV をリセット（他テストの汚れ除去）
    from nexuscore.llm import task_model_map as tmm
    tmm._WARNED_BAD_ENV.clear()
    monkeypatch.setenv("NEXUS_TASK_MODEL_CODING", "gpt-5")
    result = build_task_model_map_dict()
    # 既定 glm_default にフォールバック（ValueError で落とさない）
    assert result["code_generate"]["primary"].startswith("glm:")


def test_secondary_fallback_not_overridden(monkeypatch):
    """primary のみ上書きされ、secondary/fallback は既定維持。"""
    _clear_env(monkeypatch)
    monkeypatch.setenv("NEXUS_TASK_MODEL_CODING", "gemini_secondary")
    result = build_task_model_map_dict()
    # primary は上書きされるが、fallbacks に元の fallback が含まれる（既定動作維持）
    assert result["code_generate"]["primary"].startswith("gemini:") or "google" in result["code_generate"]["primary"]
    # fallbacks は非空
    assert result["code_generate"]["fallbacks"], "fallbacks should remain populated"
