"""build_ui 構築テスト（launch は monkeypatch で潰す・port bind なし）。"""
import sys


def test_build_ui_returns_blocks_and_launch_args(monkeypatch):
    # 既に読み込まれている gradio を取り除き、ui モジュールも未読み込みにする
    sys.modules.pop("gradio", None)
    sys.modules.pop("brownfield.ui", None)

    from brownfield import ui

    captured = {}

    def fake_launch(self, *args, **kwargs):
        captured["kwargs"] = kwargs

    # gradio.Blocks.launch を潰す（実起動回避・B104 踏まない）
    import gradio
    monkeypatch.setattr(gradio.Blocks, "launch", fake_launch)

    demo = ui.build_ui()
    assert demo is not None  # gr.Blocks インスタンス
    demo.launch(prevent_thread_lock=True)
    assert captured["kwargs"].get("prevent_thread_lock") is True
