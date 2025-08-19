# ==============================================================================
# フォルダ: src/nexuscore/agents/
# ファイル名: architect_agent.py (リファクタリング版)
# メモ: 新しいBaseAgentに準拠するようリファクタリング。
#      - __init__を明示的に呼び出すように変更。
#      - LLM呼び出しをexecute_llm_taskメソッドに統一。
# ==============================================================================
from .base_agent import BaseAgent

class ArchitectAgent(BaseAgent):
    SYSTEM_PROMPT = """
あなたは、ベストプラクティスに精通したシニアソフトウェアアーキテクトです。
ユーザーの高レベルな要求を解釈し、堅牢でスケーラブルなプロジェクトの完全なファイル構造と、
各ファイルのスケルトンコード（骨格）、そして依存関係を定義するJSONを出力してください。
"""
    # ★★★★★ ここからが最重要修正点 (1/2) ★★★★★
    def __init__(self):
        """
        ArchitectAgentを初期化する。
        新しいBaseAgentの__init__を呼び出すことで、LLMRouterが自動的にセットアップされる。
        """
        super().__init__()
    # ★★★★★ ここまで ★★★★★

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
        # ★★★★★ ここからが最重要修正点 (2/2) ★★★★★
        # 古い_call_llmから、新しいexecute_llm_taskメソッドに変更
        # これにより、このタスクに最適なLLMがLLMRouterによって自動で選択される
        return self.execute_llm_task(prompt, as_json=True)
        # ★★★★★ ここまで ★★★★★

# ==============================================================================
# フォルダ: src/nexuscore/agents/
# ファイル名: coder_agent.py (リファクタリング版)
# メモ: 新しいBaseAgentに準拠するようリファクタリング。
#      - __init__を明示的に呼び出すように変更。
#      - LLM呼び出しをexecute_llm_taskメソッドに統一。
# ==============================================================================
from .base_agent import BaseAgent

class CoderAgent(BaseAgent):
    SYSTEM_PROMPT = "あなたは、クリーンで効率的なコードを書くことを得意とする、世界クラスのPython開発者です。あなたの唯一の仕事は、与えられた指示に基づき、完全に動作するPythonコードを生成することです。"

    # ★★★★★ ここからが最重要修正点 (1/2) ★★★★★
    def __init__(self):
        """
        CoderAgentを初期化する。
        新しいBaseAgentの__init__を呼び出すことで、LLMRouterが自動的にセットアップされる。
        """
        super().__init__()
    # ★★★★★ ここまで ★★★★★

    def implement_code(self, task_description: str, existing_code: str) -> str:
        prompt = f"""
# 既存のコード
```python
{existing_code}
```

# あなたへの指示
上記の既存コードに対して、以下のタスクを実装してください。

## タスク内容
「{task_description}」

# 重要：
もしタスク内容に `[Orchestratorからの具体的指示]` や `[Guardianからのフィードバック]` が含まれている場合は、元のタスクよりも、そのフィードバックの内容を解決することを最優先してください。

# 絶対的な出力ルール
- **修正後の完全なPythonコードのみ**を出力してください。
- コードの前に前置きや言い訳、後に結びの言葉や要約など、**コード以外のテキストは一切含めないでください。**
- あなたの思考プロセスや解釈を、Pythonのコメント（`#`）以外でコードに含めてはなりません。
- 出力は、そのまま `.py` ファイルとして保存できる、純粋なPythonコードでなければなりません。
"""
        # ★★★★★ ここからが最重要修正点 (2/2) ★★★★★
        # 古い_call_llmから、新しいexecute_llm_taskメソッドに変更
        return self.execute_llm_task(prompt)
        # ★★★★★ ここまで ★★★★★
