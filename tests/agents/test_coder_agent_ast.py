from nexuscore.agents.coder_agent import CoderAgent


def test_coder_agent_ast_retry(mocker):
    agent = CoderAgent()
    # 1回目は構文エラー、2回目で修正される想定
    mocker.patch.object(
        agent,
        "execute_llm_task",
        side_effect=["def bad(:\n", "print('ok')"],
    )
    result = agent.implement_code("do something", "pass")
    assert result == "print('ok')"
    assert agent.execute_llm_task.call_count == 2
