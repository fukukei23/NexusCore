from __future__ import annotations

from typing import Any

import main_cli


class _Dummy:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass


class _DummyOrchestrator:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # keep a reference to constitution for potential inspection
        self.constitution = kwargs.get("constitution", {})

    def run_full_project(self, *args: Any, **kwargs: Any) -> None:
        raise AssertionError("run_full_project must not be called directly by main_cli in STEP2")


def _patch_main_cli_to_be_lightweight(monkeypatch: Any) -> None:
    # Avoid real logging/files/artifacts and heavy agent initialization in unit tests.
    monkeypatch.setattr(main_cli, "setup_logging", lambda verbose: None)
    monkeypatch.setattr(main_cli, "_save_codex_artifacts", lambda status_tag: None)
    monkeypatch.setattr(main_cli, "_prepare_local_knowledge_base", lambda project_path: None)
    monkeypatch.setattr(main_cli, "_load_guardian_credentials", lambda: ("k", "m"))

    monkeypatch.setattr(main_cli, "RequirementAgent", _Dummy)
    monkeypatch.setattr(main_cli, "ArchitectAgent", _Dummy)
    monkeypatch.setattr(main_cli, "PlannerAgent", _Dummy)
    monkeypatch.setattr(main_cli, "CoderAgent", _Dummy)
    monkeypatch.setattr(main_cli, "TesterAgent", _Dummy)
    monkeypatch.setattr(main_cli, "DebuggerAgent", _Dummy)
    monkeypatch.setattr(main_cli, "GuardianAgent", _Dummy)
    monkeypatch.setattr(main_cli, "PolicyAgent", _Dummy)
    monkeypatch.setattr(main_cli, "PostmortemAgent", _Dummy)
    monkeypatch.setattr(main_cli, "KnowledgeCuratorAgent", _Dummy)
    monkeypatch.setattr(main_cli, "PatchApplier", _Dummy)
    monkeypatch.setattr(main_cli, "LLMRouter", _Dummy)
    monkeypatch.setattr(main_cli, "Orchestrator", _DummyOrchestrator)


def test_cli_wires_authority_level_partial_to_runner(monkeypatch: Any, tmp_path: Any) -> None:
    _patch_main_cli_to_be_lightweight(monkeypatch)

    called: dict[str, Any] = {}

    def fake_run_with_authority(**kwargs: Any) -> None:
        called.update(kwargs)

    # Patch the runner function where main_cli imports from.
    import nexuscore.orchestrator.authority_runner as ar

    monkeypatch.setattr(ar, "run_with_authority", fake_run_with_authority)

    argv = [
        "Example requirement",
        "--project-path",
        str(tmp_path),
        "--authority-level",
        "partial",
    ]
    main_cli.run_cli(argv)

    assert called["authority_level"] == "partial"
    assert called["user_requirement"] == "Example requirement"
    assert called["language"] == "ja"


def test_cli_wires_authority_level_none_to_runner(monkeypatch: Any, tmp_path: Any) -> None:
    _patch_main_cli_to_be_lightweight(monkeypatch)

    called: dict[str, Any] = {}

    def fake_run_with_authority(**kwargs: Any) -> None:
        called.update(kwargs)

    import nexuscore.orchestrator.authority_runner as ar

    monkeypatch.setattr(ar, "run_with_authority", fake_run_with_authority)

    argv = [
        "Example requirement",
        "--project-path",
        str(tmp_path),
    ]
    main_cli.run_cli(argv)

    assert called["authority_level"] is None
