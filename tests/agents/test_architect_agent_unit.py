from nexuscore.agents.architect_agent import ArchitectAgent


def test_design_project_structure_uses_execute_llm_task(mocker):
    mocker.patch("nexuscore.agents.architect_agent.BaseAgent.__init__", return_value=None)
    agent = ArchitectAgent()
    agent.logger = mocker.Mock()

    execute_mock = mocker.patch.object(ArchitectAgent, "execute_llm_task", return_value="{}")
    requirement = "構成管理システムを設計したい"

    result = agent.design_project_structure(requirement)

    assert result == "{}"
    execute_mock.assert_called_once()
    called_prompt = execute_mock.call_args[0][0]
    assert requirement in called_prompt
    assert execute_mock.call_args.kwargs["as_json"] is True
