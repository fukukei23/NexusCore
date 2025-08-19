# src/agents/planner_agent.py
import json
from .base_agent import BaseAgent

class PlannerAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、曖昧な要求を具体的な開発計画に落とし込む、優秀なプロダクトマネージャーです。
あなたの仕事は、ユーザーの要求を分析し、実装すべき機能の仕様（関数名、引数、返り値、基本的な振る舞い）を定義した、
明確で誤解のしようがない「実装計画」をJSON形式で出力することです。
"""

    def create_plan(self, user_requirement: str) -> str:
        prompt = f"""
# ユーザー要求
「{user_requirement}」

# あなたへの指示
上記のユーザー要求を、CoderAgentとTesterAgentの両方が参照する、
具体的な実装計画に変換してください。

# 出力要件
- `functions_to_implement` というキーを持つJSONオブジェクトを生成してください。
- その値は、実装すべき関数のリスト（配列）です。
- 各関数オブジェクトは、`name`, `description`, `args` (引数のリスト), `returns` (返り値の説明) のキーを持つ必要があります。
- 存在しない機能の幻覚（Hallucination）を避け、要求に忠実な計画のみを作成してください。

# JSON出力例
{{
  "functions_to_implement": [
    {{
      "name": "greet_user",
      "description": "ユーザー名を受け取り、挨拶メッセージを返す。",
      "args": [
        {{"name": "username", "type": "str", "description": "挨拶する相手のユーザー名"}}
      ],
      "returns": {{"type": "str", "description": "'Hello, [username]!' という形式の文字列"}}
    }}
  ]
}}
"""
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)
