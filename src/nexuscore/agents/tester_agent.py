# -----------------------------------------------------------------------------
# FILE:         src/nexuscore/agents/tester_agent.py
# DATE:         2025-11-02 20:30 (JST)
# REGISTRY:     nexuscore.agents.TesterAgent
# -----------------------------------------------------------------------------
# USAGE (使用方法):
# このエージェントは、AIマルチエージェントシステム（MAS）内で「品質保証(QA)」の
# 役割を担います。
# 1. DeveloperAgentがコードを実装した後、このエージェントが呼び出され、
#    `generate_tests_and_testimony` を使用してそのコードに対するテストを生成します。
# 2. PlannerAgentが実装計画を立てた後、このエージェントが呼び出され、
#    `generate_tests_from_plan` を使用して実装前のテスト（TDD）を生成します。
#
# OPERATION (操作対象ソフトウェア):
# このエージェントが生成する `test_code` は、Pythonのテストフレームワーク
# `pytest` によって実行されることを前提としています。
# 実行環境には `pytest` がインストールされている必要があります。
# (例: `pip install pytest`)
# -----------------------------------------------------------------------------

import json
import logging
# (ご提案 #2) 相対インポートから絶対インポートへ修正
# これにより、異なるディレクトリ階層からの呼び出し時も安定します。
from nexuscore.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class TesterAgent(BaseAgent):
    """
    品質保証（QA）エンジニアとして機能するエージェント。
    コードや実装計画に基づき、pytest形式のテストコードと設計証言を生成します。
    """
    
    # SYSTEM_PROMPTはBaseAgentに渡され、LLM呼び出し時のペルソナとして機能します。
    SYSTEM_PROMPT = """
あなたは、細部まで見逃さない、経験豊富な品質保証（QA）エンジニアです。
専門はpytestを用いた自動テストの作成です。
あなたの仕事は、与えられたPythonコードや実装計画に対して、その正しさを証明するための
高品質なテストコードと、そのテスト設計に関する「証言」を生成することです。
"""

    def generate_tests_and_testimony(self, code_to_test: str) -> str:
        """
        既存のコード文字列を基に、テストコードと証言を生成する。
        (ご提案 #1 に基づき、LLM呼び出しを execute_llm_task に修正)
        
        Args:
            code_to_test (str): テスト対象のPythonコード（文字列）。
            
        Returns:
            str: 'test_code' と 'testimony' をキーに持つJSON文字列。
                 失敗した場合はエラー情報を含むJSON文字列。
        """
        prompt = f"""
# テスト対象コード (Code to Test)
```python
{code_to_test}
```
# あなたへの指示 (Your Instructions)
上記のコードに対して、pytest形式のユニットテストと、そのテスト設計に関する「証言」を生成してください。

# 出力要件 (Output Requirements)
- テストコードは、正常系、異常系、そして考えうるエッジケースを網羅してください。
- 「証言」には、どのようなテストケースを、どのような意図で設計したかを簡潔に記述してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        # (ご提案 #1) _call_llm から execute_llm_task に置き換え
        # BaseAgentのSYSTEM_PROMPTハンドリング機能を利用します。
        return self.execute_llm_task(prompt, as_json=True)

    def generate_tests_from_plan(self, plan: dict, module_to_import: str) -> str:
        """
        実装計画（JSON）を基に、テストコードと証言を生成する（TDDアプローチ）。
        (統合的改善提案: こちらのメソッドも execute_llm_task に修正)
        
        Args:
            plan (dict): PlannerAgentによって生成された実装計画。
            module_to_import (str): テスト対象の関数をインポートするための
                                     モジュール名 (例: 'src.utils.file_io')
            
        Returns:
            str: 'test_code' と 'testimony' をキーに持つJSON文字列。
                 失敗した場合はエラー情報を含むJSON文字列。
        """
        try:
            plan_str = json.dumps(plan, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"[TesterAgent] Failed to serialize plan: {e}")
            plan_str = str(plan) # シリアライズ失敗時はそのまま文字列化

        prompt = f"""
# 実装計画 (Implementation Plan)
```json
{plan_str}
```
# あなたへの指示 (Your Instructions)
上記のJSON形式の実装計画に記述された全ての関数に対する、pytest形式のユニットテストとそのテスト設計に関する「証言」を生成してください。

# 重要：テスト対象のインポート (Critical: Import Target)
テスト対象の関数は、必ず `{module_to_import}` モジュールからインポートしてください。
例: `from {module_to_import} import function_name`

# 出力要件 (Output Requirements)
- テストコードは、計画に記述された仕様（引数、返り値、振る舞い）を完全に満たすことを検証してください。
- 正常系、異常系、エッジケースを網羅し、高品質なテストを作成してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        # (統合的改善提案) _call_llm から execute_llm_task に置き換え
        return self.execute_llm_task(prompt, as_json=True)

# -----------------------------------------------------------------------------
# END OF FILE: src/nexuscore/agents/tester_agent.py
# -----------------------------------------------------------------------------

