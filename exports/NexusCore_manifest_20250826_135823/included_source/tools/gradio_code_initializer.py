# src/gradio_code_initializer.py
import gradio as gr
import openai
import os
from dotenv import load_dotenv
from file_creator import create_code_file

# .env から APIキーを読み込む
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_code_from_prompt(prompt: str, filename: str):
    if not filename.endswith(".py"):
        filename += ".py"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "あなたはPythonコードの専門家です。正確で読みやすいコードを出力してください。"},
                {"role": "user", "content": prompt}
            ]
        )
        code = response["choices"][0]["message"]["content"]
        file_path = create_code_file(filename, code)
        return f"✅ ファイル作成完了: {file_path}\n\n---\n{code}"
    except Exception as e:
        return f"❌ エラー: {str(e)}"

# Gradio UI の定義
demo = gr.Interface(
    fn=generate_code_from_prompt,
    inputs=[
        gr.Textbox(label="📝 作ってほしいコードの内容（自然言語でOK）", placeholder="例：PythonでFizzBuzzを書く", lines=4),
        gr.Textbox(label="💾 保存するファイル名（.pyは不要）", placeholder="例：fizzbuzz")
    ],
    outputs=gr.Textbox(label="📄 結果とコード", lines=20),
    title="✨ コード初期化自動生成ツール",
    description="指示を入力すると、コードをGPTで生成し、自動的にファイルとして保存します。"
)

if __name__ == "__main__":
    demo.launch()
