from nexuscore.core.orchestrator_models import OrchestratorContext


def test_context_has_stage2_loop_fields_with_defaults():
    context = OrchestratorContext(task_id="t1", user_requirement="req")
    assert context.debug_retries == 0
    assert context.review_retries == 0
    assert context.terminal_state == "APPROVED"
    assert context.review_report == {}
