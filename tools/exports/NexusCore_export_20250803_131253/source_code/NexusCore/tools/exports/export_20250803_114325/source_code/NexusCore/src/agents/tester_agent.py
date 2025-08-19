# C:\Users\USER\tools\OpenCodeInterpreter\src\agents\tester_agent.py

import json
from .base_agent import BaseAgent

class TesterAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、細部まで見逃さない、経験豊富な品質保証（QA）エンジニアです。
専門はpytestを用いた自動テストの作成です。
あなたの仕事は、与えられたPythonコードや実装計画に対して、その正しさを証明するための
高品質なテストコードと、そのテスト設計に関する「証言」を生成することです。
"""

    def generate_tests_and_testimony(self, code_to_test: str) -> str:
        """【旧メソッド】コードを基にテストを生成する"""
        prompt = f"""
# テスト対象コード
```python
{code_to_test}
```
# あなたへの指示
上記のコードに対して、pytest形式のユニットテストと、そのテスト設計に関する「証言」を生成してください。
# 出力要件
- テストコードは、正常系、異常系、そして考えうるエッジケースを網羅してください。
- 「証言」には、どのようなテストケースを、どのような意図で設計したかを簡潔に記述してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)

    # ★★★★★ ここが最重要修正点 (2/2) ★★★★★
    # メソッドの定義に module_to_import を追加し、プロンプト内でそれを使用します。
    def generate_tests_from_plan(self, plan: dict, module_to_import: str) -> str:
        """実装計画を基に、テストコードと証言を生成する"""
        plan_str = json.dumps(plan, indent=2, ensure_ascii=False)
        prompt = f"""
# 実装計画
```json
{plan_str}
```
# あなたへの指示
上記のJSON形式の実装計画に記述された全ての関数に対する、pytest形式のユニットテストとそのテスト設計に関する「証言」を生成してください。

# 重要：テスト対象のインポート
テスト対象の関数は、必ず `{module_to_import}` モジュールからインポートしてください。
例: `from {module_to_import} import function_name`

# 出力要件
- テストコードは、計画に記述された仕様（引数、返り値、振る舞い）を完全に満たすことを検証してください。
- 正常系、異常系、エッジケースを網羅し、高品質なテストを作成してください。
- 必ず以下のキーを持つJSON形式で出力してください: `test_code`, `testimony`
"""
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)
