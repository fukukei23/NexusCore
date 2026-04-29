#!/usr/bin/env python3
r"""
Streamlit風コード生成・テストタブ（MiniMax移行版）- v3.0

機能:
- MiniMax API経由のHTTP呼び出し（openai SDK依存なし）
- Context Agent による自動エラー予防
- 完全版 + Simple版のフォールバック対応
- 日本語対応
"""
import asyncio
import importlib.util
import logging
import os
import subprocess
import sys
from datetime import datetime

import gradio as gr
from dotenv import load_dotenv

from nexuscore.gradio_app.llm_helper import call_llm_messages

# ===== 1. 設定とロギングの初期化 =====

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")
MINIMAX_MODEL = os.getenv("MINIMAX_MODEL", "MiniMax-M2.7")
MAX_TOKENS = 4000

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

logger.info("==================================================")
logger.info("🚀 アプリケーション起動: MiniMax移行版 (v3.0)")
logger.info("==================================================")


# ===== 2. APIキー読み込み =====


def load_api_key() -> tuple[str | None, str]:
    """階層的にAPIキーを読み込む。優先順位: 1. 環境変数 -> 2. .envファイル"""
    logger.info("🔑 APIキーの探索を開始します...")

    logger.info("  [1/2] 環境変数をチェック中...")
    api_key = os.getenv("MINIMAX_API_KEY")
    if api_key:
        logger.info(f"    ✅ 環境変数からAPIキーを発見しました (キーの末尾: ...{api_key[-4:]})。")
        return api_key, "環境変数 (Environment Variable)"

    logger.info("  [2/2] .env ファイルをチェック中...")
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        dotenv_path = os.path.join(project_root, ".env")
        if os.path.exists(dotenv_path):
            logger.info(f"    .env ファイルを発見: {dotenv_path}")
            load_dotenv(dotenv_path=dotenv_path)
            api_key = os.getenv("MINIMAX_API_KEY")
            if api_key:
                logger.info(f"    ✅ .env ファイルからAPIキーを発見しました。")
                return api_key, ".env ファイル"
        else:
            logger.info("    .env ファイルは見つかりませんでした。")
    except Exception as e:
        logger.warning(f"    .envファイルの読み込み中にエラーが発生しました: {e}")

    logger.error("❌ 全ての場所で有効なMiniMax APIキーが見つかりませんでした。")
    return None, "見つかりません"


# APIキーをグローバルで読み込む
MINIMAX_API_KEY, API_KEY_SOURCE = load_api_key()

# --- Context Agent 統合システム ---
logger.info("🔗 Context Agent統合システム初期化中...")
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_file_dir, "../..")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

context_agent = None
rules = {"embed_functions_in_tests": True}
agent_type = "基本版"

logger.info("🔍 Context Agent検索中...")
try:
    from nexuscore.analyzer.context_agent import ContextAgent

    context_agent = ContextAgent()
    rules = context_agent.get_error_prevention_rules()
    agent_type = "完全版"
    logger.info("✅ 完全版Context Agent統合完了")
except Exception as e:
    logger.warning(f"完全版Context Agent失敗: {e}, Simple版にフォールバックします。")
    try:
        from simple_context_agent import SimpleContextAgent

        context_agent = SimpleContextAgent()
        rules = context_agent.get_error_prevention_rules()
        agent_type = "Simple版"
        logger.info("✅ Simple Context Agent フォールバック成功")
    except Exception as e2:
        logger.error(f"Simple Context Agent も失敗: {e2}")
        logger.warning("📝 基本エラー予防機能で継続します。")

logger.info(f"🔗 Context Agent統合状況: [エージェント: {agent_type}]")


# ===== 3. MiniMax API連携 =====


async def call_gpt_async(prompt: str, temperature: float = 0.1) -> str:
    """非同期版 LLM呼び出し（llm_helper経由）"""
    try:
        logger.info("LLM呼び出し開始 (llm_helper経由)")
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            None,
            lambda: call_llm_messages(
                [
                    {"role": "system", "content": "あなたは優秀なPythonプログラマーです。Context Agentの推奨事項に従い、高品質なコードを生成してください。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=temperature,
            ),
        )
        logger.info("LLM呼び出し成功")
        return result

    except Exception as e:
        logger.error(f"LLM エラー: {e}", exc_info=True)
        return f"❌ LLM エラー: {e}"


def extract_code_from_response(response: str) -> str:
    """レスポンスからコードブロックを抽出"""
    py_start_tag = "```python"
    start_index = response.find(py_start_tag)
    if start_index != -1:
        code_start = start_index + len(py_start_tag)
        end_index = response.find("```", code_start)
        if end_index != -1:
            return response[code_start:end_index].strip()

    start_tag = "```"
    start_index = response.find(start_tag)
    if start_index != -1:
        code_start = start_index + len(start_tag)
        end_index = response.find("```", code_start)
        if end_index != -1:
            return response[code_start:end_index].strip()

    return response.strip()


# ===== 4. ビジネスロジック（非同期関数） =====


async def generate_code_with_context_awareness(prompt: str, progress=gr.Progress(track_tqdm=True)):
    if not prompt.strip():
        logger.warning("コード生成プロンプトが空です。")
        return "# プロンプトが空です", ""
    logger.info(f"コード生成開始: Context Agent({agent_type})使用")
    progress(0, desc="プロンプト分析中...")
    enhanced_prompt = prompt
    if rules.get("require_docstring"):
        enhanced_prompt += "\n- 関数には詳細なdocstringを含めてください。"
    if rules.get("require_error_handling"):
        enhanced_prompt += "\n- 適切なエラーハンドリング（try-except）を実装してください。"
    progress(0.5, desc="MiniMaxにコード生成を依頼中...")
    llm_response = await call_gpt_async(enhanced_prompt, temperature=0.1)
    progress(1.0, desc="生成完了")
    extracted_code = extract_code_from_response(llm_response)
    return extracted_code, extracted_code


async def generate_tests_with_context_prevention(code: str, progress=gr.Progress(track_tqdm=True)):
    if not code.strip():
        logger.warning("テスト生成対象のコードがありません。")
        return "# テスト対象のコードがありません", ""
    logger.info(f"テスト生成開始: Context Agent({agent_type})エラー予防システム")
    progress(0, desc="テスト戦略を立案中...")
    test_prompt = f"""以下のPythonコードに対するpytest形式のテストコードを生成してください：
```python
{code}
```
🔥 重要な要件（Context Agentエラー予防システム）:
- `from your_module import ...` のような相対インポートは絶対に禁止します。
- テスト対象の関数やクラスは、テストファイル内に直接定義（コピー）してください。
- `pytest` 以外のライブラリはインポートしないでください。
- 正常系と異常系（エラーケース）の両方を網羅するテストを作成してください。
- すべてのコメントとdocstringは日本語で記述してください。
"""
    progress(0.5, desc="MiniMaxにテストコード生成を依頼中...")
    llm_response = await call_gpt_async(test_prompt, temperature=0.2)
    logger.info("テスト生成完了。インポート検証実施。")
    result = extract_code_from_response(llm_response)
    if "from your_module import" in result:
        logger.error("`from your_module import` パターンを検出！自動修正します。")
        result = result.replace("from your_module import", "# from your_module import  # Context Agent により削除")
    progress(1.0, desc="生成完了")
    return result, result


def run_tests_safely_sync(test_code: str) -> str:
    if not test_code.strip():
        return "実行するテストコードがありません。"
    logger.info("テスト実行開始: Context Agent安全モード")
    test_file = f"./temp_context_test_{datetime.now().strftime('%Y%m%d%H%M%S')}.py"
    try:
        with open(test_file, "w", encoding="utf-8") as f:
            f.write(test_code)
        logger.info(f"テストファイル作成: {test_file}")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            capture_output=True, text=True, encoding="utf-8", timeout=30,
        )
        output = result.stdout + "\n" + result.stderr
        if result.returncode == 0:
            logger.info("テスト実行成功")
            return f"🎉 テスト正常終了\n\n{output}"
        else:
            logger.warning(f"テスト実行で問題発生 (コード: {result.returncode})")
            return f"⚠️ テストで問題が発生しました:\n\n{output}"
    except Exception as e:
        logger.error(f"テスト実行中に致命的なエラー: {e}", exc_info=True)
        return f"❌ テスト実行エラー: {e}"
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)
            logger.info(f"テンポラリファイル削除: {test_file}")


async def run_tests_safely(test_code: str):
    logger.info("テスト実行プロセスをバックグラウンドで開始します。")
    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, run_tests_safely_sync, test_code)
    return result


async def generate_code_review(code: str, progress=gr.Progress(track_tqdm=True)):
    if not code.strip():
        return "レビュー対象のコードがありません。"
    logger.info("コードレビュー生成開始")
    progress(0.5, desc="MiniMaxにレビューを依頼中...")
    review_prompt = f"""以下のPythonコードをレビューしてください：
```python
{code}
```
Context Agent品質基準に基づき、以下の観点で具体的かつ建設的なフィードバックを日本語で提供してください：
1. **コード品質**: 可読性、保守性、DRY原則
2. **パフォーマンス**: 非効率な処理がないか
3. **セキュリティ**: 潜在的な脆弱性
4. **ベストプラクティス**: PEP8準拠、Pythonicな書き方
"""
    result = await call_gpt_async(review_prompt, temperature=0.3)
    progress(1.0, desc="レビュー完了")
    return f"🔍 Context Agent統合レビュー結果:\n\n{result}"


async def generate_improvement_suggestions(code: str, progress=gr.Progress(track_tqdm=True)):
    if not code.strip():
        return "改善対象のコードがありません。"
    logger.info("改善提案の生成開始")
    progress(0.5, desc="MiniMaxに改善案を依頼中...")
    improvement_prompt = f"""以下のPythonコードの改善版を提案してください：
```python
{code}
```
Context Agent最適化要件に基づき、以下の点を改善したコードを ` ```python` ブロックで提供し、変更点を解説してください：
1. **可読性の向上**
2. **パフォーマンスの最適化**
3. **エラーハンドリングの強化**
4. **セキュリティの向上**
"""
    result = await call_gpt_async(improvement_prompt, temperature=0.2)
    progress(1.0, desc="改善案の生成完了")
    return f"💡 Context Agent統合改善提案:\n\n{result}"


# ===== 5. Gradio UI構築 =====


def create_streamlit_migrated_tab():
    """Context Agent完全統合版 Streamlit風タブ"""
    with gr.Blocks(
        title="🤖 コード生成 & テストタブ（MiniMax版）", theme=gr.themes.Soft()
    ) as interface:

        code_state = gr.State(value="")
        test_code_state = gr.State(value="")

        gr.Markdown(
            f"""
        # 🤖 コード生成 & テストタブ（MiniMax移行版 - v3.0）
        **✅ Context Agent:** `{agent_type}` | **🛡️ エラー予防:** `有効` | **🔑 APIキー:** `{'✅ ' + API_KEY_SOURCE if MINIMAX_API_KEY else '❌ 未設定'}`
        """
        )

        with gr.Tabs():
            with gr.TabItem("① コード生成", id="tab_code"):
                with gr.Row():
                    with gr.Column(scale=2):
                        code_prompt = gr.Textbox(
                            label="プロンプト", placeholder="例: 2つの数を足す関数を作って", lines=5
                        )
                        generate_btn = gr.Button("🔧 コード生成 (非同期)", variant="primary", size="lg")
                    with gr.Column(scale=3):
                        generated_code = gr.Code(
                            label="生成されたコード", language="python", lines=20
                        )

            with gr.TabItem("② テスト生成・実行", id="tab_test"):
                with gr.Row():
                    with gr.Column(scale=2):
                        test_generate_btn = gr.Button(
                            "📊 テスト生成 (非同期)", variant="secondary", size="lg"
                        )
                        test_run_btn = gr.Button(
                            "▶️ テスト実行 (非同期)", variant="primary", size="lg"
                        )
                    with gr.Column(scale=3):
                        generated_tests = gr.Code(
                            label="生成されたテストコード", language="python", lines=12
                        )
                        test_results = gr.Textbox(label="テスト結果", lines=10, max_lines=15)

            with gr.TabItem("③ コードレビュー", id="tab_review"):
                with gr.Row():
                    with gr.Column(scale=2):
                        review_btn = gr.Button(
                            "📋 レビュー生成 (非同期)", variant="secondary", size="lg"
                        )
                    with gr.Column(scale=3):
                        review_results = gr.Textbox(label="レビュー結果", lines=22, max_lines=30)

            with gr.TabItem("④ 修正案", id="tab_improve"):
                with gr.Row():
                    with gr.Column(scale=2):
                        improve_btn = gr.Button(
                            "💡 修正案表示 (非同期)", variant="secondary", size="lg"
                        )
                    with gr.Column(scale=3):
                        improvement_results = gr.Code(
                            label="AIによる修正提案コード", language="python", lines=22
                        )

        # --- イベントハンドラー ---
        generate_btn.click(
            fn=generate_code_with_context_awareness,
            inputs=code_prompt,
            outputs=[generated_code, code_state],
        )
        test_generate_btn.click(
            fn=generate_tests_with_context_prevention,
            inputs=code_state,
            outputs=[generated_tests, test_code_state],
        )
        test_run_btn.click(fn=run_tests_safely, inputs=test_code_state, outputs=test_results)
        review_btn.click(fn=generate_code_review, inputs=code_state, outputs=review_results)
        improve_btn.click(
            fn=generate_improvement_suggestions, inputs=code_state, outputs=improvement_results
        )

    return interface


def tab_streamlit_port():
    """メイン関数：Context Agent統合版タブを返す"""
    logger.info("Gradioタブの初期化を開始します。")
    return create_streamlit_migrated_tab()


# ===== 6. アプリケーション起動 =====
if __name__ == "__main__":
    logger.info("アプリケーションのメインブロックを実行します。")

    if not MINIMAX_API_KEY:
        logger.critical(
            "APIキーが設定されていません。環境変数、.envを確認してください。"
        )

    app = tab_streamlit_port()

    logger.info("Gradioアプリケーションを起動します... [http://127.0.0.1:7860](http://127.0.0.1:7860)")
    app.launch()
