# --- FILE: src/ai_assistant.py ---
# GPTへの問い合わせと応答解析を担うモジュール
# ==============================================================================
import re
from openai import OpenAI

class AIAssistant:
    """AIアシスタント機能を提供するクラス"""
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("OpenAI APIキーが設定されていません。")
        self.client = OpenAI(api_key=api_key)

    def _call_gpt(self, prompt: str, model: str = "gpt-4-turbo") -> str:
        """GPT APIを呼び出すプライベートメソッド"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"GPT API Error: {e}")
            return f"APIエラー: {e}"

    def _parse_response(self, text: str) -> dict:
        """GPTの応答をコードと要約に分割する"""
        code_match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        code = code_match.group(1).strip() if code_match else ""
        
        summary_match = re.search(r"【修正理由・要約】\n(.*?)(?:\n---|$)", text, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else "要約がありません。"
        
        return {"code": code, "summary": summary}

    def generate_fix(self, target_file: str, current_code: str, test_code: str, test_results: str, user_instruction: str) -> dict:
        """
        テスト失敗を修正するためのプロンプトを生成し、GPTに問い合わせる
        """
        prompt = f"""
あなたは、テストの失敗を自動で修正するエキスパートPython開発者です。

【前提】
- 修正対象ファイル: `{target_file}`
- テストファイル: `test_sample.py`
- 直近のテスト実行結果: 
```
{test_results}
```
- ユーザーからの追加指示: {user_instruction if user_instruction else "特にありません。テストが通るように修正してください。"}

【現在のコード】
`{target_file}`:
```python
{current_code}
```test_sample.py`:
```python
{test_code}
```

【タスク】
1.  上記情報をもとに、`{target_file}` の修正版コードを提案してください。
2.  修正内容の要約と、なぜその修正が必要かを簡潔に説明してください。
3.  出力は、必ず以下の【出力フォーマット】に従ってください。説明文とコードは厳密に分けてください。

【出力フォーマット】
---
【修正理由・要約】
ここに、主な修正点、修正が必要な理由などを簡潔に記述してください。

---
【修正版コード】
```python
ここに修正後の完全なPythonコードのみを記述してください。
```
---
"""
        response_text = self._call_gpt(prompt)
        return self._parse_response(response_text)

