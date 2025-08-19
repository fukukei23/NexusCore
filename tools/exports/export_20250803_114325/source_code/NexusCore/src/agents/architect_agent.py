# フォルダ: src/agents
# ファイル名: architect_agent.py
# メモ: 『アーキテクト・ファースト』アプローチの設計専門AI。
#      BaseAgentを継承して作ります。
# ==============================================================================
from .base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、ベストプラクティスに精通したシニアソフトウェアアーキテクトです。
ユーザーの高レベルな要求を解釈し、堅牢でスケーラブルなプロジェクトの完全なファイル構造と、
各ファイルのスケルトンコード（骨格）、そして依存関係を定義するJSONを出力してください。
"""

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
        # JSON形式の出力を期待するため、as_json=True を指定
        return self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)
