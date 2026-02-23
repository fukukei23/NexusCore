"""
webapp/orchestrator_helper.py の高品質なテスト

注意: このテストファイルは Flask レガシー前提です。
CR-FASTAPI-010 で Flask API が削除されたため、このテストファイルは skip されます。
FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください。
"""

import pytest

# CR-FASTAPI-010: Flask レガシー前提のテストは削除済み
# FastAPI 側のテストは tests/api/test_fastapi_*.py を参照してください
pytest.skip(
    "Flask legacy orchestrator_helper tests have been removed in CR-FASTAPI-010. "
    "Use FastAPI tests in tests/api/test_fastapi_*.py instead.",
    allow_module_level=True,
)


class TestCreateOrchestratorInstance:
    """create_orchestrator_instance() のテスト"""

    def test_create_orchestrator_instance_returns_orchestrator(self, tmp_path):
        """create_orchestrator_instance() が Orchestrator インスタンスを返す"""
        from nexuscore.webapp.orchestrator_helper import create_orchestrator_instance

        project_path = str(tmp_path)

        with patch("nexuscore.webapp.orchestrator_helper.assemble_agent_team") as mock_team:
            with patch("nexuscore.webapp.orchestrator_helper.Orchestrator") as MockOrchestrator:
                mock_team.return_value = {"requirement_agent": Mock()}
                mock_orchestrator = Mock()
                MockOrchestrator.return_value = mock_orchestrator

                result = create_orchestrator_instance(
                    project_path=project_path,
                    autonomy_level=1,
                )

                assert result == mock_orchestrator
                MockOrchestrator.assert_called_once()

    def test_create_orchestrator_instance_with_default_autonomy_level(self, tmp_path):
        """create_orchestrator_instance() がデフォルトの autonomy_level=1 を使用"""
        from nexuscore.webapp.orchestrator_helper import create_orchestrator_instance

        project_path = str(tmp_path)

        with patch("nexuscore.webapp.orchestrator_helper.assemble_agent_team") as mock_team:
            with patch("nexuscore.webapp.orchestrator_helper.Orchestrator") as MockOrchestrator:
                mock_team.return_value = {}
                mock_orchestrator = Mock()
                MockOrchestrator.return_value = mock_orchestrator

                create_orchestrator_instance(project_path=project_path)

                # constitution に autonomy_level=1 が含まれる
                call_kwargs = MockOrchestrator.call_args[1]
                assert call_kwargs["constitution"]["automation_policy"]["autonomy_level"] == 1

    def test_create_orchestrator_instance_with_custom_autonomy_level(self, tmp_path):
        """create_orchestrator_instance() がカスタムの autonomy_level を使用"""
        from nexuscore.webapp.orchestrator_helper import create_orchestrator_instance

        project_path = str(tmp_path)

        with patch("nexuscore.webapp.orchestrator_helper.assemble_agent_team") as mock_team:
            with patch("nexuscore.webapp.orchestrator_helper.Orchestrator") as MockOrchestrator:
                mock_team.return_value = {}
                mock_orchestrator = Mock()
                MockOrchestrator.return_value = mock_orchestrator

                create_orchestrator_instance(
                    project_path=project_path,
                    autonomy_level=2,
                )

                # constitution に autonomy_level=2 が含まれる
                call_kwargs = MockOrchestrator.call_args[1]
                assert call_kwargs["constitution"]["automation_policy"]["autonomy_level"] == 2

    def test_create_orchestrator_instance_generates_session_id(self, tmp_path):
        """create_orchestrator_instance() が session_id を自動生成"""
        from nexuscore.webapp.orchestrator_helper import create_orchestrator_instance

        project_path = str(tmp_path)

        with patch("nexuscore.webapp.orchestrator_helper.assemble_agent_team") as mock_team:
            with patch("nexuscore.webapp.orchestrator_helper.Orchestrator") as MockOrchestrator:
                with patch(
                    "nexuscore.webapp.orchestrator_helper.SessionController"
                ) as MockSessionController:
                    mock_team.return_value = {}
                    mock_orchestrator = Mock()
                    MockOrchestrator.return_value = mock_orchestrator
                    mock_session_controller = Mock()
                    MockSessionController.return_value = mock_session_controller

                    create_orchestrator_instance(project_path=project_path)

                    # SessionController が session_id を受け取る
                    MockSessionController.assert_called_once()
                    call_kwargs = MockSessionController.call_args[1]
                    assert "session_id" in call_kwargs
                    # session_id は32文字の16進数（uuid4().hex）
                    session_id = call_kwargs["session_id"]
                    assert len(session_id) == 32
                    assert all(c in "0123456789abcdef" for c in session_id)

    def test_create_orchestrator_instance_uses_provided_session_id(self, tmp_path):
        """create_orchestrator_instance() が提供された session_id を使用"""
        from nexuscore.webapp.orchestrator_helper import create_orchestrator_instance

        project_path = str(tmp_path)
        custom_session_id = "custom-session-123"

        with patch("nexuscore.webapp.orchestrator_helper.assemble_agent_team") as mock_team:
            with patch("nexuscore.webapp.orchestrator_helper.Orchestrator") as MockOrchestrator:
                with patch(
                    "nexuscore.webapp.orchestrator_helper.SessionController"
                ) as MockSessionController:
                    mock_team.return_value = {}
                    mock_orchestrator = Mock()
                    MockOrchestrator.return_value = mock_orchestrator
                    mock_session_controller = Mock()
                    MockSessionController.return_value = mock_session_controller

                    create_orchestrator_instance(
                        project_path=project_path,
                        session_id=custom_session_id,
                    )

                    # 提供された session_id が使用される
                    call_kwargs = MockSessionController.call_args[1]
                    assert call_kwargs["session_id"] == custom_session_id

    def test_create_orchestrator_instance_creates_session_controller(self, tmp_path):
        """create_orchestrator_instance() が SessionController を作成"""
        from nexuscore.webapp.orchestrator_helper import create_orchestrator_instance

        project_path = str(tmp_path)

        with patch("nexuscore.webapp.orchestrator_helper.assemble_agent_team") as mock_team:
            with patch("nexuscore.webapp.orchestrator_helper.Orchestrator") as MockOrchestrator:
                with patch(
                    "nexuscore.webapp.orchestrator_helper.SessionController"
                ) as MockSessionController:
                    mock_team.return_value = {}
                    mock_orchestrator = Mock()
                    MockOrchestrator.return_value = mock_orchestrator
                    mock_session_controller = Mock()
                    MockSessionController.return_value = mock_session_controller

                    create_orchestrator_instance(project_path=project_path)

                    # SessionController が正しいパスで作成される
                    MockSessionController.assert_called_once()
                    call_kwargs = MockSessionController.call_args[1]
                    expected_session_dir = os.path.join(project_path, ".nexus", "sessions")
                    assert call_kwargs["root_dir"] == expected_session_dir

    def test_create_orchestrator_instance_assembles_agent_team(self, tmp_path):
        """create_orchestrator_instance() がエージェントチームを組み立て"""
        from nexuscore.webapp.orchestrator_helper import create_orchestrator_instance

        project_path = str(tmp_path)

        with patch("nexuscore.webapp.orchestrator_helper.assemble_agent_team") as mock_team:
            with patch("nexuscore.webapp.orchestrator_helper.Orchestrator") as MockOrchestrator:
                mock_agents = {
                    "requirement_agent": Mock(),
                    "architect_agent": Mock(),
                }
                mock_team.return_value = mock_agents
                mock_orchestrator = Mock()
                MockOrchestrator.return_value = mock_orchestrator

                create_orchestrator_instance(project_path=project_path)

                # assemble_agent_team が呼ばれる
                mock_team.assert_called_once_with(project_path=project_path)

                # エージェントが Orchestrator に渡される
                call_kwargs = MockOrchestrator.call_args[1]
                assert call_kwargs["requirement_agent"] == mock_agents["requirement_agent"]
                assert call_kwargs["architect_agent"] == mock_agents["architect_agent"]

    def test_create_orchestrator_instance_handles_config_error(self, tmp_path):
        """create_orchestrator_instance() が AppConfig エラーを処理"""
        from nexuscore.webapp.orchestrator_helper import create_orchestrator_instance

        project_path = str(tmp_path)

        with patch("nexuscore.webapp.orchestrator_helper.assemble_agent_team") as mock_team:
            with patch("nexuscore.webapp.orchestrator_helper.Orchestrator") as MockOrchestrator:
                with patch("nexuscore.webapp.orchestrator_helper.AppConfig") as MockAppConfig:
                    mock_team.return_value = {}
                    mock_orchestrator = Mock()
                    MockOrchestrator.return_value = mock_orchestrator

                    # AppConfig がエラーを投げる
                    MockAppConfig.BASELINE_AUTOMATION_POLICY.get.side_effect = Exception(
                        "Config error"
                    )

                    # エラーを無視してデフォルト値で進む
                    result = create_orchestrator_instance(project_path=project_path)

                    assert result == mock_orchestrator

    def test_create_orchestrator_instance_passes_project_path_to_orchestrator(self, tmp_path):
        """create_orchestrator_instance() が project_path を Orchestrator に渡す"""
        from nexuscore.webapp.orchestrator_helper import create_orchestrator_instance

        project_path = str(tmp_path)

        with patch("nexuscore.webapp.orchestrator_helper.assemble_agent_team") as mock_team:
            with patch("nexuscore.webapp.orchestrator_helper.Orchestrator") as MockOrchestrator:
                mock_team.return_value = {}
                mock_orchestrator = Mock()
                MockOrchestrator.return_value = mock_orchestrator

                create_orchestrator_instance(project_path=project_path)

                # project_path が Orchestrator に渡される
                call_kwargs = MockOrchestrator.call_args[1]
                assert call_kwargs["project_path"] == project_path


class TestRunOrchestratorSync:
    """run_orchestrator_sync() のテスト"""

    def test_run_orchestrator_sync_creates_orchestrator(self, tmp_path):
        """run_orchestrator_sync() が Orchestrator インスタンスを作成"""
        from nexuscore.webapp.orchestrator_helper import run_orchestrator_sync

        project_path = str(tmp_path)

        with patch(
            "nexuscore.webapp.orchestrator_helper.create_orchestrator_instance"
        ) as mock_create:
            mock_orchestrator = Mock()
            mock_orchestrator.run_full_project = Mock()
            mock_create.return_value = mock_orchestrator

            run_orchestrator_sync(
                project_path=project_path,
                user_requirement="Fix bugs",
            )

            # create_orchestrator_instance が呼ばれる
            mock_create.assert_called_once_with(
                project_path=project_path,
                autonomy_level=1,
            )

    def test_run_orchestrator_sync_with_custom_autonomy_level(self, tmp_path):
        """run_orchestrator_sync() がカスタムの autonomy_level を使用"""
        from nexuscore.webapp.orchestrator_helper import run_orchestrator_sync

        project_path = str(tmp_path)

        with patch(
            "nexuscore.webapp.orchestrator_helper.create_orchestrator_instance"
        ) as mock_create:
            mock_orchestrator = Mock()
            mock_orchestrator.run_full_project = Mock()
            mock_create.return_value = mock_orchestrator

            run_orchestrator_sync(
                project_path=project_path,
                user_requirement="Fix bugs",
                autonomy_level=2,
            )

            # autonomy_level=2 で呼ばれる
            mock_create.assert_called_once_with(
                project_path=project_path,
                autonomy_level=2,
            )

    def test_run_orchestrator_sync_calls_run_full_project(self, tmp_path):
        """run_orchestrator_sync() が run_full_project を呼ぶ"""
        from nexuscore.webapp.orchestrator_helper import run_orchestrator_sync

        project_path = str(tmp_path)

        with patch(
            "nexuscore.webapp.orchestrator_helper.create_orchestrator_instance"
        ) as mock_create:
            mock_orchestrator = Mock()
            mock_orchestrator.run_full_project = Mock()
            mock_create.return_value = mock_orchestrator

            run_orchestrator_sync(
                project_path=project_path,
                user_requirement="Fix bugs",
            )

            # run_full_project が呼ばれる
            mock_orchestrator.run_full_project.assert_called_once()

    def test_run_orchestrator_sync_passes_parameters_to_run_full_project(self, tmp_path):
        """run_orchestrator_sync() がパラメータを run_full_project に渡す"""
        from nexuscore.webapp.orchestrator_helper import run_orchestrator_sync

        project_path = str(tmp_path)

        with patch(
            "nexuscore.webapp.orchestrator_helper.create_orchestrator_instance"
        ) as mock_create:
            mock_orchestrator = Mock()
            mock_orchestrator.run_full_project = Mock()
            mock_create.return_value = mock_orchestrator

            run_orchestrator_sync(
                project_path=project_path,
                user_requirement="Fix all bugs",
                run_db_id=123,
                autonomy_level=2,
                language="en",
                fast_lane=True,
            )

            # すべてのパラメータが渡される
            mock_orchestrator.run_full_project.assert_called_once_with(
                user_requirement="Fix all bugs",
                language="en",
                fast_lane=True,
                run_db_id=123,
            )

    def test_run_orchestrator_sync_with_default_parameters(self, tmp_path):
        """run_orchestrator_sync() がデフォルトパラメータを使用"""
        from nexuscore.webapp.orchestrator_helper import run_orchestrator_sync

        project_path = str(tmp_path)

        with patch(
            "nexuscore.webapp.orchestrator_helper.create_orchestrator_instance"
        ) as mock_create:
            mock_orchestrator = Mock()
            mock_orchestrator.run_full_project = Mock()
            mock_create.return_value = mock_orchestrator

            run_orchestrator_sync(
                project_path=project_path,
                user_requirement="Fix bugs",
            )

            # デフォルト値が使用される
            call_kwargs = mock_orchestrator.run_full_project.call_args[1]
            assert call_kwargs["language"] == "ja"
            assert call_kwargs["fast_lane"] is False
            assert call_kwargs["run_db_id"] is None

    def test_run_orchestrator_sync_propagates_exception(self, tmp_path):
        """run_orchestrator_sync() がエラーを伝播する"""
        from nexuscore.webapp.orchestrator_helper import run_orchestrator_sync

        project_path = str(tmp_path)

        with patch(
            "nexuscore.webapp.orchestrator_helper.create_orchestrator_instance"
        ) as mock_create:
            mock_orchestrator = Mock()
            mock_orchestrator.run_full_project.side_effect = Exception("Orchestrator error")
            mock_create.return_value = mock_orchestrator

            # エラーが伝播する
            with pytest.raises(Exception, match="Orchestrator error"):
                run_orchestrator_sync(
                    project_path=project_path,
                    user_requirement="Fix bugs",
                )
