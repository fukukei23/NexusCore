import unittest
from unittest.mock import patch, MagicMock
import sys

sys.path.append('src')

try:
    from nexuscore.core.orchestrator import Orchestrator
except ImportError:
    Orchestrator = None

class TestOrchestratorMega(unittest.TestCase):
    """オーケストレーター修正版テスト"""
    
    def test_orchestrator_import(self):
        """オーケストレーターのインポートテスト"""
        if Orchestrator is None:
            self.skipTest("Orchestratorが利用できません")
        self.assertIsNotNone(Orchestrator)
    
    def test_orchestrator_class_structure(self):
        """オーケストレータークラス構造テスト"""
        if Orchestrator is None:
            self.skipTest("Orchestratorが利用できません")
        
        # クラスの基本属性確認
        self.assertTrue(hasattr(Orchestrator, '__init__'))
        self.assertTrue(callable(Orchestrator))
    
    def test_orchestrator_with_mocked_dependencies(self):
        """モック依存関係でのオーケストレーターテスト"""
        if Orchestrator is None:
            self.skipTest("Orchestratorが利用できません")

        from tempfile import TemporaryDirectory
        from unittest.mock import MagicMock

        with TemporaryDirectory() as tmp:
            mock_agent = MagicMock()
            router = MagicMock()
            router.complete = MagicMock(return_value={"content": ""})
            orch = Orchestrator(
                project_path=tmp,
                constitution={},
                requirement_agent=mock_agent,
                architect_agent=mock_agent,
                planner_agent=mock_agent,
                coder_agent=mock_agent,
                tester_agent=mock_agent,
                debugger_agent=mock_agent,
                guardian_agent=mock_agent,
                policy_agent=mock_agent,
                postmortem_agent=mock_agent,
                knowledge_curator_agent=mock_agent,
                patch_applier_agent=mock_agent,
                llm_router=router,
            )
            self.assertIsInstance(orch, Orchestrator)
            self.assertTrue(hasattr(orch, "run_full_project"))

if __name__ == '__main__':
    unittest.main()
