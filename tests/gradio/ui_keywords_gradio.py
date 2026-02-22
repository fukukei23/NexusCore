"""
Gradio UI キーワード表

Gradio UI が壊れたときすぐ気づけるよう、全タブ・ボタン共通で UI キーワードを一元管理するモジュール。

各タブ・ボタンの重要な文字列（絵文字含む）をここに集約し、
UI ラベル変更時はこのファイルを修正するだけで対応可能にする。
"""

# Gradio メインタイトル
GRADIO_MAIN_TITLE = "NexusCore Unified UI"

# Gradio タブ名（実際の unified_gradio_ui.py のタブ名に合わせる）
GRADIO_TABS = [
    "📝 Code / Prompt",
    "🤖 AI Revision",
    "🧪 Test Runner",
    "📜 History & Diff",
]

# Gradio 主要ボタンラベル（実際の unified_gradio_ui.py のボタンラベルに合わせる）
GRADIO_BUTTON_LABELS = [
    "🔁 コード生成",  # Code / Prompt タブ
    "💾 コードを保存",  # Code / Prompt タブ
    "🔧 パッチ生成",  # AI Revision タブ
    "✅ パッチ適用",  # AI Revision タブ
    "▶️ テスト実行",  # Test Runner タブ
    "🚀 Self-Healing を実行",  # History & Diff タブ（Self-Healing Run 発火ボタン）
]
