def gradio_launch():
    import gradio as gr
    import os
    from auto_cycle_manager import auto_repair_cycle

    def repair_code(code):
        fixed_code, output = auto_repair_cycle(code)
        return fixed_code, output

    with gr.Blocks() as demo:
        gr.Markdown("## 🔧 AI Pythonコード修復ツール（Gradio UI）")
        with gr.Row():
            code_input = gr.Textbox(label="🔍 修復対象のコード", lines=20, placeholder="ここにPythonコードを貼り付け")
            with gr.Column():
                run_button = gr.Button("🚀 修復実行")
                clear_button = gr.Button("🗑️ クリア")
        fixed_output = gr.Textbox(label="✅ 修正後コード", lines=20)
        result_output = gr.Textbox(label="🖥 実行出力", lines=10)

        run_button.click(fn=repair_code, inputs=code_input, outputs=[fixed_output, result_output])
        clear_button.click(fn=lambda: ("", "", ""), inputs=[], outputs=[code_input, fixed_output, result_output])

    demo.launch(share=False, inbrowser=True)
