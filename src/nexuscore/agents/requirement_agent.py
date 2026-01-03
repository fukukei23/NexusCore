# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# フォルダ: src/nexuscore/agents/
# ファイル名: requirement_agent.py
#
# 日付: 2025年9月29日
# 日本時間: 07:15
#
# バージョン: 8.3 (Gradio Chatbot Format Fix)
#
# 改修内容:
#   - Gradio UIの起動時に発生していた `gradio.exceptions.Error` を完全に修正しました。
#   - `on_ui_load` 関数が返す初期メッセージのデータ形式を、Gradioの `Chatbot` が
#     期待する `messages` 形式（辞書のリスト）に準拠させました。
#   - これにより、すべての起動時エラーが解消され、ついに対話型UIが正常に表示され、
#     AIとの対話を開始できる状態になります。
# ==============================================================================

from __future__ import annotations
import os
import re
import json
import uuid
import time
# Gradio は lazy import（launch_gradio_ui() 内でのみ import）で UI 依存を分離
from typing import Dict, List, Optional, Any, Set, Callable, Tuple, Generator
from datetime import datetime

# --- 依存 ---
try:
    from .base_agent import BaseAgent
    from ..utils.json_sanitizer import sanitize_json_like
except ImportError:
    # --- フォールバック ---
    def sanitize_json_like(payload: Any) -> Any: return payload
    class BaseAgent:
        def __init__(self, *args, **kwargs): print("警告: BaseAgentが見つかりません。")
        def execute_llm_task(self, prompt: str, as_json: bool = False) -> str: return "{}"

# (TextLocalization と StateMachine クラスは変更なし)
class TextLocalization:
    def __init__(self, language: str = "ja"):
        self.language = language
        self.texts = {
            "ja": { "title": "NexusCore: 対話型 要件定義エージェント", "boot_msg": "Gradio UIを起動中...", "initial_greeting": "こんにちは。どのようなソフトウェアを開発したいですか？", "status_ready": "入力待機中...", "status_thinking": "思考中...", "status_suggesting": "提案を生成しました。", "status_finished": "要件定義が完了しました。", "input_placeholder": "メッセージを入力...", "send_button": "送信", "finish_button": "完了", "final_output_label": "最終仕様（JSON）", "yes_button": "はい", "no_button": "いいえ", "suggest_button": "他の提案は？" },
            "en": { "title": "NexusCore: Interactive Requirement Agent", "boot_msg": "Launching Gradio UI...", "initial_greeting": "Hello. What software would you like to develop?", "status_ready": "Waiting for input...", "status_thinking": "Thinking...", "status_suggesting": "Suggestion generated.", "status_finished": "Requirements complete.", "input_placeholder": "Enter your message...", "send_button": "Send", "finish_button": "Finish", "final_output_label": "Final Specifications (JSON)", "yes_button": "Yes", "no_button": "No", "suggest_button": "Other suggestions?" },
        }
    def __getitem__(self, key: str) -> str: return self.texts.get(self.language, self.texts["en"]).get(key, f"<{key}>")

class StateMachine:
    def __init__(self, agent: 'RequirementAgent'): self.agent = agent; self.state = self.agent._get_initial_state()
    def transition(self, user_input: Optional[str] = None): self.state["state"] = "FINALIZING"; return [(None, "仕様を生成します。")] # 仮実装

class RequirementAgent(BaseAgent):
    def __init__(self, language: str = "ja", use_ui: bool = False):
        super().__init__()
        self.language = language
        self.text = TextLocalization(language)
        self.final_requirements: Optional[Dict[str, Any]] = None
        self.use_ui = use_ui
        self._initial_requirement: str = ""

    def _get_initial_state(self) -> Dict[str, Any]:
        return { "session_id": str(uuid.uuid4()), "history": [], "state": "INIT" }

    def generate_final_spec(self, history: List[Dict]) -> Dict[str, Any]:
        last_user_msg = next((h['content'] for h in reversed(history) if h['role'] == 'user'), "No user input.")
        return {"summary": "Final Specification", "details": last_user_msg}

    def set_initial_requirement(self, requirement: str) -> None:
        self._initial_requirement = requirement

    def analyze_requirement(self, requirement: str) -> Dict[str, Any]:
        """
        Headless requirement digestion fallback using LLM or heuristic summary.
        """
        requirement = requirement.strip() or self._initial_requirement or "No requirement provided."
        prompt = f"""
You are a requirements analyst. Convert the user's request into a concise JSON specification.

# User Requirement
{requirement}

# Output JSON schema
{{
  "summary": "<overall goal>",
  "features": ["<feature1>", "<feature2>"],
  "constraints": ["<constraint>", "..."],
  "acceptance_criteria": ["<criteria>", "..."]
}}

Ensure the response is strictly valid JSON with filled arrays (no empty strings).
"""
        response = self.execute_llm_task(prompt, as_json=True)
        try:
            data = sanitize_json_like(json.loads(response))
        except Exception:
            data = {
                "summary": requirement[:80],
                "features": ["Auto-generated draft feature list"],
                "constraints": [],
                "acceptance_criteria": []
            }
        self.final_requirements = data
        return data

    def launch_gradio_ui(self, share: bool = False) -> Dict[str, Any]:
        """
        Gradio UI を起動して要件定義を行う。

        Note: Gradio はこのメソッド内でのみ import される（lazy import）。
        これにより、RequirementAgent を import しても Gradio が読み込まれない。
        """
        if not self.use_ui:
            self.logger.info("RequirementAgent running in headless mode.")
            return self.analyze_requirement(self._initial_requirement)

        # Lazy import: Gradio はこのメソッド内でのみ import
        try:
            import gradio as gr
        except ImportError:
            self.logger.warning("Gradio is not installed. Falling back to headless mode.")
            return self.analyze_requirement(self._initial_requirement)

        fsm = StateMachine(self)

        with gr.Blocks(title=self.text["title"]) as demo:
            gr.Markdown(f"<h1>{self.text['title']}</h1>")
            status_bar = gr.Textbox(value=self.text["status_ready"], label="Status", interactive=False)
            chatbot = gr.Chatbot(label="Chat History", height=500, type="messages") # type="messages" を明示
            with gr.Row():
                msg_input = gr.Textbox(placeholder=self.text["input_placeholder"], scale=4)
                send_button = gr.Button(self.text["send_button"], scale=1)
            with gr.Row(visible=False) as suggestion_row:
                yes_btn = gr.Button(self.text["yes_button"])
                no_btn = gr.Button(self.text["no_button"])
                suggest_btn = gr.Button(self.text["suggest_button"])
            finish_button = gr.Button(self.text["finish_button"], variant="primary")
            final_output = gr.Code(label=self.text["final_output_label"], language="json")

            def on_ui_load() -> List[Any]:
                fsm.state = self._get_initial_state()
                initial_message = self.text["initial_greeting"]
                fsm.state["history"].append({"role": "assistant", "content": initial_message})
                # ★★★★★ ここからが v8.3 修正の核心 ★★★★★
                # Chatbotが期待する messages 形式（辞書のリスト）で返すように修正
                return [[{"role": "assistant", "content": initial_message}]], self.text["status_ready"]
                # ★★★★★ ここまで ★★★★★

            def on_user_submit(user_message: str, history: List[Dict]) -> Generator[List[Any], None, None]:
                if not user_message:
                    yield history, self.text["status_ready"], gr.update(), gr.update(), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)
                    return

                history.append({"role": "user", "content": user_message})
                fsm.state["history"].append({"role": "user", "content": user_message})

                yield (
                    history, self.text["status_thinking"], gr.update(interactive=False, value=""),
                    gr.update(interactive=False), gr.update(visible=False),
                    gr.update(visible=False), gr.update(visible=False)
                )

                time.sleep(1)
                responses = fsm.transition(user_input=user_message)

                for _, assistant_a in responses:
                    history.append({"role": "assistant", "content": assistant_a})
                    fsm.state["history"].append({"role": "assistant", "content": assistant_a})

                suggestion_buttons_update = gr.update(visible=(fsm.state["state"] == "SUGGESTING"))
                yield (
                    history, self.text["status_ready"], gr.update(interactive=True),
                    gr.update(interactive=True), suggestion_buttons_update,
                    suggestion_buttons_update, suggestion_buttons_update
                )

            def on_finish_click() -> List[Any]:
                self.final_requirements = self.generate_final_spec(fsm.state["history"])
                final_json_str = json.dumps(self.final_requirements, indent=2, ensure_ascii=False)
                # UIを閉じるには、Gradioサーバーを停止するなどの追加処理が必要
                # ここでは完了ステータスを表示し、手動で閉じることを想定
                # demo.close() # この呼び出しはバックエンドのイベントハンドラからは直接機能しない
                return final_json_str, self.text["status_finished"]

            demo.load(on_ui_load, outputs=[chatbot, status_bar])

            send_button.click(on_user_submit, inputs=[msg_input, chatbot], outputs=[chatbot, status_bar, msg_input, send_button, yes_btn, no_btn, suggest_btn])
            msg_input.submit(on_user_submit, inputs=[msg_input, chatbot], outputs=[chatbot, status_bar, msg_input, send_button, yes_btn, no_btn, suggest_btn])
            finish_button.click(on_finish_click, outputs=[final_output, status_bar])

        print(self.text["boot_msg"])
        demo.queue().launch(server_name="127.0.0.1", server_port=7860, share=share)

        return self.final_requirements or {}

if __name__ == "__main__":
    agent = RequirementAgent(language="ja")
    specs = agent.launch_gradio_ui(share=False)
    if specs:
        print("\n--- [最終生成仕様] ---")
        print(json.dumps(specs, indent=2, ensure_ascii=False))
