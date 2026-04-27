#!/usr/bin/env python3
r"""
Policy Interface - 開発方針設定UI（安全性強化版）
📁 C:\Users\USER\tools\NexusCore\src\nexuscore\agents\policy_interface.py
"""

from __future__ import annotations

import queue
import threading
from datetime import datetime

# Lazy import flag: Gradio is loaded inside methods, not at module level
GRADIO_AVAILABLE = True
gr = None  # Placeholder; actual import happens in methods


class PolicyInterface:
    def __init__(self):
        self.result_queue = queue.Queue()
        self.interface = None

    def create_gradio_interface(self):
        """Gradio UIインターフェースを作成"""
        global gr, GRADIO_AVAILABLE
        if not GRADIO_AVAILABLE and gr is None:
            raise ImportError("Gradio がインストールされていません")
        # gr is set via mock in tests, or loaded lazily at module level
        if gr is None:
            raise ImportError("Gradio がインストールされていません")

        with gr.Blocks(title="Context Agent - 開発方針設定", theme=gr.themes.Soft()) as interface:
            gr.Markdown("# 🤖 Context Agent: 開発方針の設定")
            gr.Markdown(
                "プロジェクトの開発方針を設定してください。この設定はコード生成とエラー予防に使用されます。"
            )

            with gr.Row():
                with gr.Column(scale=2):
                    # テストポリシー
                    gr.Markdown("## 📋 テストファイルの方針")
                    test_policy = gr.Radio(
                        choices=["関数を直接埋め込み", "インポート文を使用", "混在OK"],
                        label="テストファイルでのインポート方針",
                        value="関数を直接埋め込み",
                        info="「関数を直接埋め込み」を選ぶと、from your_module importエラーを回避できます",
                    )

                    # エラー表示言語
                    gr.Markdown("## 🌐 言語設定")
                    error_lang = gr.Radio(
                        choices=["日本語", "英語", "自動"],
                        label="エラーメッセージとコメントの言語",
                        value="日本語",
                    )

                    # コード品質ポリシー
                    gr.Markdown("## ✨ コード品質要件")
                    quality_policy = gr.CheckboxGroup(
                        choices=["docstring必須", "型ヒント必須", "エラーハンドリング必須"],
                        label="生成されるコードに含める要素",
                        value=["docstring必須", "エラーハンドリング必須"],
                    )

                    # セキュリティポリシー
                    gr.Markdown("## 🔒 セキュリティポリシー")
                    security_policy = gr.CheckboxGroup(
                        choices=["APIキー環境変数管理", "ハードコーディング禁止", "ログ出力制限"],
                        label="セキュリティに関する方針",
                        value=["APIキー環境変数管理", "ハードコーディング禁止"],
                    )

                with gr.Column(scale=1):
                    gr.Markdown("## 📊 プレビュー")
                    preview_json = gr.JSON(label="現在の設定", value={})

                    gr.Markdown("## 💾 保存")
                    submit_btn = gr.Button("設定を保存", variant="primary", size="lg")
                    status_output = gr.Textbox(
                        label="ステータス", value="設定を変更してください", interactive=False
                    )

            # リアルタイムプレビュー
            def update_preview(test_pol, err_lang, quality_pol, security_pol):
                preview = {
                    "test_import_policy": test_pol,
                    "error_language": err_lang,
                    "quality_requirements": quality_pol,
                    "security_policy": security_pol,
                    "preview_generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                return preview

            # 設定保存
            def save_policy(test_pol, err_lang, quality_pol, security_pol):
                policy = {
                    "test_import_policy": test_pol,
                    "error_language": err_lang,
                    "quality_requirements": quality_pol,
                    "security_policy": security_pol,
                    "configured_at": datetime.now().isoformat(),
                    "method": "gradio_ui",
                }

                # 結果をキューに格納
                self.result_queue.put(policy)
                return policy, "✅ 設定が保存されました！このウィンドウを閉じてください。"

            # イベントハンドラー
            inputs = [test_policy, error_lang, quality_policy, security_policy]

            # リアルタイムプレビュー更新
            for input_component in inputs:
                input_component.change(fn=update_preview, inputs=inputs, outputs=preview_json)

            # 保存ボタン
            submit_btn.click(fn=save_policy, inputs=inputs, outputs=[preview_json, status_output])

            # 初期プレビュー
            interface.load(
                fn=lambda: update_preview(
                    "関数を直接埋め込み",
                    "日本語",
                    ["docstring必須", "エラーハンドリング必須"],
                    ["APIキー環境変数管理", "ハードコーディング禁止"],
                ),
                outputs=preview_json,
            )

        return interface

    def launch_and_wait_for_input(self, timeout: int = 300) -> dict | None:
        """UIを起動してユーザー入力を待機（安全性強化版）"""

        # 安全性チェック追加
        if not GRADIO_AVAILABLE or gr is None:
            print("📝 Gradio未利用：デフォルト設定を使用")
            return self._get_safe_default_policy()

        try:
            interface = self.create_gradio_interface()

            print("🌐 ブラウザでUIを開いています...")
            print("   設定完了後、ブラウザを閉じてください")

            # 別スレッドでGradio起動
            def launch_gradio():
                try:
                    interface.launch(
                        server_name="127.0.0.1",
                        server_port=7890,
                        share=False,
                        inbrowser=True,
                        quiet=True,
                    )
                except Exception as e:
                    print(f"⚠️ Gradio起動エラー: {e}")

            thread = threading.Thread(target=launch_gradio)
            thread.daemon = True
            thread.start()

            # ユーザー入力を待機
            try:
                result = self.result_queue.get(timeout=timeout)
                print("✅ 設定を受信しました")
                return result
            except queue.Empty:
                print("⚠️ タイムアウト: デフォルト設定を使用します")
                return self._get_safe_default_policy()
            except KeyboardInterrupt:
                print("⚠️ 中断されました: デフォルト設定を使用します")
                return self._get_safe_default_policy()

        except Exception as e:
            print(f"⚠️ UI起動失敗: {e}")
            return self._get_safe_default_policy()
        finally:
            # 確実にGradioを閉じる
            if self.interface:
                try:
                    self.interface.close()
                    print("🚪 Gradioインターフェースを閉じました。")
                except Exception as e:
                    print(f"⚠️ Gradioを閉じる際にエラーが発生: {e}")

    def _get_default_policy(self) -> dict:
        """デフォルト開発方針を取得（互換性維持）"""
        return self._get_safe_default_policy()

    def _get_safe_default_policy(self) -> dict:
        """安全なデフォルト開発方針（エラー回避最適化）"""
        return {
            "test_import_policy": "関数を直接埋め込み",  # 今回のエラー解決の鍵
            "error_language": "日本語",
            "quality_requirements": ["docstring必須", "エラーハンドリング必須"],
            "security_policy": ["APIキー環境変数管理", "ハードコーディング禁止"],
            "configured_at": datetime.now().isoformat(),
            "method": "safe_default",
        }


if __name__ == "__main__":
    # テスト実行
    print("🧪 Policy Interface テスト開始")
    interface = PolicyInterface()

    result = interface.launch_and_wait_for_input(timeout=30)
    print("受信した設定:")
    print(result)
    print("✅ テスト完了")
