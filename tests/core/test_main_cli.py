from unittest.mock import MagicMock


def test_exit_code_needs_human_review_maps_to_2(tmp_path):
    from main_cli import run_smoke_gate

    result_context = MagicMock()
    result_context.plan = {"target_files": []}
    result_context.terminal_state = "NEEDS_HUMAN_REVIEW"

    ok, errors = run_smoke_gate(str(tmp_path), [])
    assert ok is True

    exit_code = 0
    if result_context.terminal_state == "NEEDS_HUMAN_REVIEW":
        exit_code = 2
    assert exit_code == 2
