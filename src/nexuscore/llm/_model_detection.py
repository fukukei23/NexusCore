from __future__ import annotations

import logging
import os
from typing import Any


from nexuscore.llm.runtime import HTTP_CLIENT_FACTORY


def detect_available_models(logger: logging.Logger) -> dict[str, list[Any]]:
    """Detect available models from OpenAI and Gemini APIs."""
    detected: dict[str, list[Any]] = {"openai": [], "gemini": []}

    # OpenAI model detection
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and HTTP_CLIENT_FACTORY.available:
        try:
            session = HTTP_CLIENT_FACTORY.create_session()
            if session:
                url = "https://api.openai.com/v1/models"
                headers = {"Authorization": f"Bearer {openai_key}"}
                resp = session.get(url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    all_models = [m["id"] for m in data.get("data", [])]
                    chat_compatible = [
                        m
                        for m in all_models
                        if not m.endswith("-codex") and not m.endswith("-instruct")
                    ]
                    detected["openai"] = chat_compatible
                    logger.info(
                        "[Model Detection] OpenAI: Found %d total models, %d chat-compatible",
                        len(all_models),
                        len(chat_compatible),
                    )
                    if chat_compatible:
                        logger.debug(
                            "[Model Detection] OpenAI chat-compatible (first 10): %s",
                            chat_compatible[:10],
                        )
        except (OSError, ConnectionError, ValueError, RuntimeError) as e:
            logger.warning(
                "[Model Detection] OpenAI models.list failed: %s. Using static defaults.", e
            )

    # Gemini model detection
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and HTTP_CLIENT_FACTORY.available:
        try:
            session = HTTP_CLIENT_FACTORY.create_session()
            if session:
                url = "https://generativelanguage.googleapis.com/v1beta/models"
                params = {"key": gemini_key}
                resp = session.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        name = m.get("name", "")
                        methods = m.get("supportedGenerationMethods", [])
                        if "generateContent" in methods and name.startswith("models/"):
                            detected["gemini"].append(name.replace("models/", ""))
                    logger.info(
                        "[Model Detection] Gemini: Found %d generateContent-compatible models",
                        len(detected["gemini"]),
                    )
                elif resp.status_code == 403:
                    logger.warning(
                        "[Model Detection] Gemini API returned 403. Gemini disabled for this run."
                    )
                else:
                    logger.warning(
                        "[Model Detection] Gemini API returned status %d. Using static defaults.",
                        resp.status_code,
                    )
        except (OSError, ConnectionError, ValueError, RuntimeError) as e:
            logger.warning(
                "[Model Detection] Gemini models.list failed: %s. Using static defaults.", e
            )

    return detected


def _find_available_model(candidates: list[str], available: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in available:
            return candidate
    return None


def apply_detected_models(
    detected: dict[str, list[str]],
    task_model_map: dict[str, Any],
    logger: logging.Logger,
) -> None:
    """Update task_model_map based on detected available models."""
    openai_models = detected.get("openai", [])
    gemini_models = detected.get("gemini", [])

    openai_chat_candidates = [
        "gpt-5.2-chat-latest",
        "gpt-5.1-chat-latest",
        "gpt-5-chat-latest",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]
    openai_codex_candidates = ["gpt-4o"]
    openai_mini_candidates = ["gpt-5-mini", "gpt-5.1-mini", "gpt-4o-mini", "gpt-3.5-turbo"]

    chat_model = _find_available_model(openai_chat_candidates, openai_models) or "gpt-4o"
    codex_model = _find_available_model(openai_codex_candidates, openai_models) or chat_model
    mini_model = _find_available_model(openai_mini_candidates, openai_models) or "gpt-4o-mini"

    gemini_model = None
    if gemini_models:
        for candidate in ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-1.5-pro"]:
            if candidate in gemini_models:
                gemini_model = f"google:{candidate}"
                break

    def _prefix(model: str) -> str:
        return model if model.startswith("openai:") else f"openai:{model}"

    updates: dict[str, Any] = {}

    if chat_model:
        for task in [
            "general", "requirement", "requirement_elicit", "plan_generate",
            "planning", "code_review", "review", "testing", "test",
        ]:
            if task in task_model_map and isinstance(task_model_map[task], dict):
                updates[task] = {**task_model_map[task], "primary": _prefix(chat_model)}

    if codex_model:
        for task in ["code_generate", "test_generate", "debug", "code_refactor"]:
            if task in task_model_map and isinstance(task_model_map[task], dict):
                updates[task] = {**task_model_map[task], "primary": _prefix(codex_model)}
                logger.debug(
                    "[Model Detection] %s will use %s (chat-compatible)", task, _prefix(codex_model)
                )

    if mini_model and "routing_classify" in task_model_map:
        current = task_model_map["routing_classify"]
        if isinstance(current, dict):
            updates["routing_classify"] = {**current, "primary": _prefix(mini_model)}

    if gemini_model:
        for task in ["analytical", "plan_generate", "catalog_enrich", "scraping_analyze"]:
            if task in task_model_map and isinstance(task_model_map[task], dict):
                updates[task] = {**task_model_map[task], "primary": gemini_model}

    for task, new_config in updates.items():
        task_model_map[task] = new_config
        logger.info("[Model Detection] Updated %s: %s", task, new_config.get("primary"))

    if updates:
        logger.info(
            "[Model Detection] Updated %d task model mappings based on detected models",
            len(updates),
        )
    else:
        logger.info("[Model Detection] No model mappings updated (using static defaults)")
