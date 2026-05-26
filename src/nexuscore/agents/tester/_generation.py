import json
import logging

logger = logging.getLogger(__name__)


def build_tests_and_testimony_prompt(code_to_test: str) -> str:
    return f"""
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


def build_tests_from_plan_prompt(plan: dict, module_to_import: str) -> str:
    try:
        plan_str = json.dumps(plan, indent=2, ensure_ascii=False)
    except (TypeError, ValueError):
        plan_str = str(plan)

    return f"""
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


def build_tests_from_requirement_prompt(requirement_summary: str) -> str:
    return f"""
# ユーザー要件 (Requirement)
{requirement_summary}

# あなたへの指示
上記の要件に対して、pytest で実行できる回帰テストと、それぞれのテストで検証する
観点の短い解説（testimony）を JSON で返してください。

# 出力形式
{{
  "test_code": "...pytest code...",
  "testimony": "...why these tests cover the requirement..."
}}

- test_code には pytest テストファイル全体を記述してください。
- 外部サービスへの依存がある場合は、スタブやフェイクを用いた形で表現してください。
"""


def extract_test_code_from_response(llm_response: str) -> str:
    try:
        data = json.loads(llm_response)
        if isinstance(data, dict) and "test_code" in data:
            return data["test_code"]
        if isinstance(data, str):
            return data
        return str(data)
    except json.JSONDecodeError:
        logger.warning("LLM response is not valid JSON. Using as-is.")
        return llm_response
