from .base_agent import BaseAgent


class ArchitectAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、ベストプラクティスに精通したシニアソフトウェアアーキテクトです。
ユーザーの高レベルな要求を解釈し、堅牢でスケーラブルなプロジェクトの完全なファイル構造と、
各ファイルのスケルトンコード（骨格）、そして依存関係を定義するJSONを出力してください。
"""

    def __init__(self):
        """
        ArchitectAgentを初期化する。
        新しいBaseAgentの__init__を呼び出すことで、LLMRouterが自動的にセットアップされる。
        """
        super().__init__()

    def design_project_structure(self, user_requirement: str) -> str:
        prompt = f"""
以下のユーザー要求を満たすための、完全なプロジェクト構造を設計してください。

# ユーザー要求
{user_requirement}

# 出力要件
- ルートは単一の `project` オブジェクトとします。
- ファイル構造は `files` 配列で、ネストされたオブジェクトとして表現してください。
- 各ファイルオブジェクトは `name` (ディレクトリを含むフルパス), `type` ('folder' or 'file'), `content` (スケルトンコード) のキーを持つ必要があります。
- `content`には、クラス定義、関数シグネチャ、主要なロジックをTODOコメントとして記述してください。
- 必要なライブラリは `requirements.txt` に含めてください。
- 必ずJSON形式で出力してください。

# JSON出力例
{{
  "project": {{
    "files": [
      {{
        "name": "app/",
        "type": "folder",
        "content": ""
      }},
      {{
        "name": "app/main.py",
        "type": "file",
        "content": "# TODO: Flask app initialization\\n\\ndef main():\\n    pass"
      }},
      {{
        "name": "requirements.txt",
        "type": "file",
        "content": "flask\\nsqlalchemy"
      }}
    ]
  }}
}}
"""
        return self.execute_llm_task(prompt, as_json=True)

    def design_architecture(self, specs: dict, plan: dict) -> dict:
        """要件仕様と実装計画から、コーダーに注入する設計方針(design_directive)を生成する。

        ファイル構成そのものはplanner(target_files)の責務・本メソッドはコード設計方針のみ扱う
        （spec §3-1 line47の責務分離）。
        """
        import json

        prompt = f"""
以下の要件仕様と実装計画に基づき、実装時に守るべき設計方針を簡潔に述べてください。

# 要件仕様
{json.dumps(specs, ensure_ascii=False)}

# 実装計画
{json.dumps(plan, ensure_ascii=False)}

# 出力要件
- 必ずJSON形式: {{"design_directive": "<設計方針の説明文>"}}
- design_directiveは、レイヤー分け・命名規則・エラーハンドリング方針など、コーダーが実装時に直接従える具体的な指示にすること。
"""
        raw = self.execute_llm_task(prompt, as_json=True)
        if not raw or not str(raw).strip():
            return {"design_directive": ""}

        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            return {"design_directive": str(raw).strip()}

        if isinstance(parsed, dict) and "design_directive" in parsed:
            return {"design_directive": str(parsed["design_directive"])}
        return {"design_directive": str(parsed)}
