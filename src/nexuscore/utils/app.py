# ✅ app.py（Flask + Gradio 並行起動）
import threading

from flask import Flask
from gradio_ui import gradio_launch  # Gradio UI 関数インポート
from routes_ai_repair import bp as repair_bp

app = Flask(__name__)
app.register_blueprint(repair_bp)

# Gradio 並行起動（非ブロッキング）
threading.Thread(target=gradio_launch, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True)
