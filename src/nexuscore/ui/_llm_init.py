from __future__ import annotations

import logging
from pathlib import Path

from dotenv import load_dotenv

_load_path = Path.home() / ".secrets.env"
if _load_path.exists():
    load_dotenv(_load_path)

logger = logging.getLogger(__name__)

try:
    from nexuscore.llm.llm_router import LLMRouter

    _router = LLMRouter()
    HAS_LLM = True
except Exception as e:
    logging.getLogger(__name__).warning(f"LLMRouter init failed: {e}")
    _router = None
    HAS_LLM = False

try:
    from nexuscore.modules.whisper_handler import transcribe_audio

    HAS_WHISPER = True
except ImportError:
    HAS_WHISPER = False
    transcribe_audio = None

try:
    from nexuscore.agents.debugger_agent import DebuggerAgent
    from nexuscore.integration.github_pr_comment import load_run_markdown
    from nexuscore.services.self_healing_service import SelfHealingService

    HAS_SELF_HEALING = True
except ImportError:
    HAS_SELF_HEALING = False
    SelfHealingService = None
    DebuggerAgent = None
    load_run_markdown = None
