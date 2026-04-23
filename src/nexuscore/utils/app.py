# ✅ app.py（Flask + Gradio 並行起動）
import threading

from flask import Flask
from routes_ai_repair import bp as repair_bp

app = Flask(__name__)
app.register_blueprint(repair_bp)

# Gradio 並行起動（非ブロッキング・lazy import）
def _launch_gradio():
    try:
        from gradio_ui import gradio_launch
        gradio_launch()
    except ImportError:
        pass

threading.Thread(target=_launch_gradio, daemon=True).start()

if __name__ == "__main__":
    app.run(debug=True)
