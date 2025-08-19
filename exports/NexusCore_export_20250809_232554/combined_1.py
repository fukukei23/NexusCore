
# === NexusCore/src\nexuscore\gradio_app\streamlit_migrated_tab.py ===
#!/usr/bin/env python3
r"""
Streamlit風コード生成・テストタブ（Context Agent完全統合版）- 最終版 v2.2

📁 C:\Users\USER\tools\NexusCore\src\nexuscore\gradio_app\streamlit_migrated_tab.py

機能:
- from your_module import エラーの根本解決
- Context Agent による自動エラー予防
- 完全版 + Simple版のフォールバック対応
- 日本語対応

最終版 v2.2 の改善点:
- [修正] APIキー読み込みプロセスを詳細にロギングし、UIにも表示するよう改善。
- [修正] Gradioのバージョン互換性問題を解決 (show_copy_button引数を削除)
- 階層的APIキー読み込み: 環境変数 > .env > secrets.py の順でキーを自動探索。
- 構造化ロギング、非同期処理、状態管理。
"""
import gradio as gr
import os
import sys
import subprocess
import json
import logging
import asyncio
import importlib.util
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from dotenv import load_dotenv

# ===== 1. 設定とロギングの初期化 =====

# --- グローバル設定 ---
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")
GPT_MODEL = "gpt-4o-mini"
MAX_TOKENS = 4000

# --- ロギング設定 ---
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(funcName)s] - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

logger.info("==================================================")
logger.info("🚀 アプリケーション起動: Context Agent統合システム (v2.2)")
logger.info("==================================================")


# ===== 2. APIキー読み込みとContext Agent統合 =====

def load_api_key() -> Tuple[Optional[str], str]:
    """
    階層的にAPIキーを読み込む。どのソースから読み込んだかの情報も返す。
    優先順位: 1. 環境変数 -> 2. .envファイル -> 3. secrets.py
    戻り値: (APIキー, 読み込み元)
    """
    logger.info("🔑 APIキーの探索を開始します...")

    # 1. 環境変数から直接読み込み
    logger.info("  [1/3] 環境変数をチェック中...")
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        logger.info(f"    ✅ 環境変数からAPIキーを発見しました (キーの末尾: ...{api_key[-4:]})。これを使用します。")
        return api_key, "環境変数 (Environment Variable)"

    # 2. .env ファイルから読み込み
    logger.info("  [2/3] .env ファイルをチェック中...")
    try:
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
        dotenv_path = os.path.join(project_root, '.env')
        if os.path.exists(dotenv_path):
            logger.info(f"    .env ファイルを発見: {dotenv_path}")
            load_dotenv(dotenv_path=dotenv_path)
            api_key = os.getenv("OPENAI_API_KEY_FROM_DOTENV") # .env専用の変数名で読み込み
            if not api_key: # 上記がなければ、標準名で試す
                 api_key = os.getenv("OPENAI_API_KEY")

            if api_key:
                logger.info(f"    ✅ .env ファイルからAPIキーを発見しました (キーの末尾: ...{api_key[-4:]})。これを使用します。")
                return api_key, ".env ファイル"
        else:
            logger.info("    .env ファイルは見つかりませんでした。")
    except Exception as e:
        logger.warning(f"    .envファイルの読み込み中にエラーが発生しました: {e}")


    # 3. secrets.py から読み込み
    logger.info("  [3/3] secrets.py をチェック中...")
    try:
        secrets_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config/secrets.py'))
        if os.path.exists(secrets_path):
            logger.info(f"    secrets.py ファイルを発見: {secrets_path}")
            spec = importlib.util.spec_from_file_location("secrets", secrets_path)
            secrets_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(secrets_module)
            api_key = getattr(secrets_module, 'OPENAI_API_KEY', getattr(secrets_module, 'API_KEY', None))
            if api_key:
                logger.info(f"    ✅ secrets.py からAPIキーを発見しました (キーの末尾: ...{api_key[-4:]})。これを使用します。")
                return api_key, "secrets.py"
    except Exception as e:
        logger.warning(f"    secrets.pyからのAPIキー読み込みに失敗しました: {e}")

    logger.error("❌ 全ての場所で有効なOpenAI APIキーが見つかりませんでした。")
    return None, "見つかりません"

# APIキーをグローバルで読み込む
OPENAI_API_KEY, API_KEY_SOURCE = load_api_key()

# --- Context Agent 統合システム ---
logger.info("🔗 Context Agent統合システム初期化中...")
# (Context Agentの初期化ロジックは変更なし)
current_file_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_file_dir, "../..")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

context_agent = None
rules = {"embed_functions_in_tests": True}
agent_type = "基本版"

logger.info("🔍 Context Agent検索中...")
try:
    from nexuscore.agents.context_agent import ContextAgent
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


# ===== 3. GPT API連携（非同期） =====
async def call_gpt_async(prompt: str, temperature: float = 0.1) -> str:
    """非同期版 OpenAI GPT API呼び出し（Context Agent対応）"""
    if not OPENAI_API_KEY:
        return "❌ エラー: OpenAI APIキーが設定されていません。"
    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        
        logger.info(f"GPT API呼び出し開始 (Model: {GPT_MODEL})")
        response = await client.chat.completions.create(
            model=GPT_MODEL,
            messages=[
                {"role": "system", "content": "あなたは優秀なPythonプログラマーです。Context Agentの推奨事項に従い、高品質なコードを生成してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=MAX_TOKENS
        )
        logger.info("GPT API呼び出し成功")
        return response.choices[0].message.content

    except ImportError:
        msg = "❌ エラー: `openai`ライブラリが見つかりません。`pip install --upgrade openai \"openai[http_x]\"`を実行してください。"
        logger.critical(msg)
        return msg
    except Exception as e:
        logger.error(f"GPT API エラー: {e}", exc_info=True)
        return f"❌ GPT API エラー: {e}"

def extract_code_from_response(response: str) -> str:
    """GPTレスポンスからコードブロックを抽出（堅牢版）"""
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
# (各関数の内部ロジックは変更なし)
async def generate_code_with_context_awareness(prompt: str, progress=gr.Progress(track_tqdm=True)):
    if not prompt.strip():
        logger.warning("コード生成プロンプトが空です。")
        return "# プロンプトが空です", ""
    logger.info(f"コード生成開始: Context Agent({agent_type})使用")
    progress(0, desc="プロンプト分析中...")
    enhanced_prompt = prompt
    if rules.get("require_docstring"): enhanced_prompt += "\n- 関数には詳細なdocstringを含めてください。"
    if rules.get("require_error_handling"): enhanced_prompt += "\n- 適切なエラーハンドリング（try-except）を実装してください。"
    progress(0.5, desc="GPTにコード生成を依頼中...")
    gpt_response = await call_gpt_async(enhanced_prompt, temperature=0.1)
    progress(1.0, desc="生成完了")
    extracted_code = extract_code_from_response(gpt_response)
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
    progress(0.5, desc="GPTにテストコード生成を依頼中...")
    gpt_response = await call_gpt_async(test_prompt, temperature=0.2)
    logger.info("テスト生成完了。インポート検証実施。")
    result = extract_code_from_response(gpt_response)
    if "from your_module import" in result:
        logger.error("`from your_module import` パターンを検出！自動修正します。")
        result = result.replace("from your_module import", "# from your_module import  # Context Agent により削除")
    progress(1.0, desc="生成完了")
    return result, result

def run_tests_safely_sync(test_code: str) -> str:
    if not test_code.strip(): return "実行するテストコードがありません。"
    logger.info("テスト実行開始: Context Agent安全モード")
    test_file = f"./temp_context_test_{datetime.now().strftime('%Y%m%d%H%M%S')}.py"
    try:
        with open(test_file, "w", encoding="utf-8") as f: f.write(test_code)
        logger.info(f"テストファイル作成: {test_file}")
        result = subprocess.run([sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"], capture_output=True, text=True, encoding='utf-8', timeout=30)
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
    if not code.strip(): return "レビュー対象のコードがありません。"
    logger.info("コードレビュー生成開始")
    progress(0.5, desc="GPTにレビューを依頼中...")
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
    if not code.strip(): return "改善対象のコードがありません。"
    logger.info("改善提案の生成開始")
    progress(0.5, desc="GPTに改善案を依頼中...")
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
    with gr.Blocks(title="🤖 コード生成 & テストタブ（Context Agent統合版）", theme=gr.themes.Soft()) as interface:
        
        code_state = gr.State(value="")
        test_code_state = gr.State(value="")

        gr.Markdown(f"""
        # 🤖 コード生成 & テストタブ（Context Agent統合版 - vFinal-2.2）
        **✅ Context Agent:** `{agent_type}` | **🛡️ エラー予防:** `有効` | **🔑 APIキー:** `{'✅ ' + API_KEY_SOURCE if OPENAI_API_KEY else '❌ 未設定'}`
        **✨ 新機能:** APIキー読み込みプロセスの詳細ロギング、UIでのソース表示
        """)

        with gr.Tabs():
            with gr.TabItem("① コード生成", id="tab_code"):
                with gr.Row():
                    with gr.Column(scale=2):
                        code_prompt = gr.Textbox(label="プロンプト", placeholder="例: 2つの数を足す関数を作って", lines=5)
                        generate_btn = gr.Button("🔧 コード生成 (非同期)", variant="primary", size="lg")
                    with gr.Column(scale=3):
                        generated_code = gr.Code(label="生成されたコード", language="python", lines=20)

            with gr.TabItem("② テスト生成・実行", id="tab_test"):
                with gr.Row():
                    with gr.Column(scale=2):
                        test_generate_btn = gr.Button("📊 テスト生成 (非同期)", variant="secondary", size="lg")
                        test_run_btn = gr.Button("▶️ テスト実行 (非同期)", variant="primary", size="lg")
                    with gr.Column(scale=3):
                        generated_tests = gr.Code(label="生成されたテストコード", language="python", lines=12)
                        test_results = gr.Textbox(label="テスト結果", lines=10, max_lines=15)
            
            with gr.TabItem("③ コードレビュー", id="tab_review"):
                with gr.Row():
                    with gr.Column(scale=2):
                         review_btn = gr.Button("📋 レビュー生成 (非同期)", variant="secondary", size="lg")
                    with gr.Column(scale=3):
                        review_results = gr.Textbox(label="レビュー結果", lines=22, max_lines=30)

            with gr.TabItem("④ 修正案", id="tab_improve"):
                with gr.Row():
                    with gr.Column(scale=2):
                        improve_btn = gr.Button("💡 修正案表示 (非同期)", variant="secondary", size="lg")
                    with gr.Column(scale=3):
                        improvement_results = gr.Code(label="AIによる修正提案コード", language="python", lines=22)
        
        # --- イベントハンドラー ---
        generate_btn.click(fn=generate_code_with_context_awareness, inputs=code_prompt, outputs=[generated_code, code_state])
        test_generate_btn.click(fn=generate_tests_with_context_prevention, inputs=code_state, outputs=[generated_tests, test_code_state])
        test_run_btn.click(fn=run_tests_safely, inputs=test_code_state, outputs=test_results)
        review_btn.click(fn=generate_code_review, inputs=code_state, outputs=review_results)
        improve_btn.click(fn=generate_improvement_suggestions, inputs=code_state, outputs=improvement_results)
        
    return interface

def tab_streamlit_port():
    """メイン関数：Context Agent統合版タブを返す"""
    logger.info("Gradioタブの初期化を開始します。")
    return create_streamlit_migrated_tab()

# ===== 6. アプリケーション起動 =====
if __name__ == "__main__":
    logger.info("アプリケーションのメインブロックを実行します。")
    
    if not OPENAI_API_KEY:
        logger.critical("APIキーが設定されていません。環境変数、.env、またはsecrets.pyを確認してください。")

    app = tab_streamlit_port()
    
    logger.info("Gradioアプリケーションを起動します... [http://127.0.0.1:7860](http://127.0.0.1:7860)")
    app.launch()

# === NexusCore/simple_context_agent.py ===
#!/usr/bin/env python3
r"""
Simple Context Agent - 安全版
フォルダ: C:/Users/USER/tools/NexusCore/simple_context_agent.py
目的: from your_module import エラーを確実に解決
"""

import os
import json
from typing import Dict
from datetime import datetime

class SimpleContextAgent:
    def __init__(self, project_root: str = None):
        self.project_root = project_root or os.getcwd()
        self.context_cache_file = os.path.join(self.project_root, ".nexus_context.json")
        print(f"🔍 プロジェクトルート: {self.project_root}")
        
        # キャッシュがあれば読み込み、なければ作成
        if os.path.exists(self.context_cache_file):
            self.context = self.load_context()
        else:
            self.context = self.create_context()
            self.save_context()
    
    def create_context(self) -> Dict:
        """安全なコンテキスト作成"""
        print("🔍 コンテキストを作成中...")
        
        context = {
            "tech_stack": {
                "frameworks": self._safe_detect_frameworks(),
                "python_version": "3.11+"
            },
            "file_structure": {
                "has_src_dir": os.path.exists(os.path.join(self.project_root, "src")),
                "has_tests_dir": os.path.exists(os.path.join(self.project_root, "tests")),
                "has_venv": os.path.exists(os.path.join(self.project_root, "venv"))
            },
            "dependencies": {
                "external": ["gradio", "openai", "pytest"],
                "internal": ["nexuscore"]
            },
            "environment": {
                "platform": os.name,
                "env_file_exists": os.path.exists(os.path.join(self.project_root, ".env")),
                "in_venv": os.getenv("VIRTUAL_ENV") is not None
            },
            "dev_policy": {
                "test_import_policy": "関数を直接埋め込み",
                "error_language": "日本語",
                "quality_requirements": ["docstring必須", "エラーハンドリング必須"],
                "security_policy": ["APIキー環境変数管理", "ハードコーディング禁止"],
                "configured_at": datetime.now().isoformat()
            },
            "last_updated": datetime.now().isoformat(),
            "version": "1.0-safe"
        }
        
        print("✅ コンテキスト作成完了")
        return context
    
    def _safe_detect_frameworks(self) -> list:
        """安全なフレームワーク検出"""
        frameworks = []
        req_file = os.path.join(self.project_root, "requirements.txt")
        
        if os.path.exists(req_file):
            try:
                with open(req_file, 'r', encoding='utf-8') as f:
                    content = f.read().lower()
                    if 'gradio' in content:
                        frameworks.append('gradio')
                    if 'openai' in content:
                        frameworks.append('openai')
                    if 'pytest' in content:
                        frameworks.append('pytest')
                    if 'streamlit' in content:
                        frameworks.append('streamlit')
            except Exception:
                frameworks = ['gradio', 'openai']
        
        return frameworks
    
    def load_context(self) -> Dict:
        """コンテキスト読み込み"""
        try:
            with open(self.context_cache_file, 'r', encoding='utf-8') as f:
                context = json.load(f)
                print(f"✅ キャッシュ読み込み: {self.context_cache_file}")
                return context
        except Exception as e:
            print(f"⚠️ キャッシュ読み込み失敗: {e}")
            return self.create_context()
    
    def save_context(self):
        """コンテキスト保存"""
        try:
            with open(self.context_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.context, f, indent=2, ensure_ascii=False)
            print(f"✅ コンテキスト保存: {self.context_cache_file}")
        except Exception as e:
            print(f"❌ 保存エラー: {e}")
    
    def get_error_prevention_rules(self) -> Dict:
        """エラー予防ルール（今回のエラー解決）"""
        return {
            "embed_functions_in_tests": True,
            "use_japanese_errors": True,
            "require_docstring": True,
            "require_error_handling": True,
            "use_env_vars": True,
            "test_policy": "関数を直接埋め込み"
        }
    
    def generate_enhanced_test_prompt(self, source_code: str) -> str:
        """エラー回避版テスト生成プロンプト"""
        return f"""以下のPythonコードに対するpytest形式のテストコードを生成してください：

{source_code}

重要な要件:
- インポート文は一切使用しない
- テスト対象の関数定義もテストファイルに含める
- 完全に自己完結したテストファイルとして作成
- pytest形式でテストを作成
- 正常系と異常系の両方をテスト
- 日本語でコメントを記述

`````` で終わるコードブロック形式で出力してください。"""

if __name__ == "__main__":
    print("🚀 SimpleContextAgent 開始")
    print("📁 実行場所: C:/Users/USER/tools/NexusCore/simple_context_agent.py")
    
    # 基本動作テスト
    agent = SimpleContextAgent()
    
    print("\n📊 コンテキスト:")
    print(json.dumps(agent.context, indent=2, ensure_ascii=False))
    
    print("\n🛡️ エラー予防ルール:")
    rules = agent.get_error_prevention_rules()
    for rule, value in rules.items():
        print(f"  {rule}: {value}")
    
    # テスト生成のデモ
    print("\n🧪 修正されたテスト生成プロンプト例:")
    sample_code = "def add(a, b): return a + b"
    enhanced_prompt = agent.generate_enhanced_test_prompt(sample_code)
    print(enhanced_prompt[:200] + "...")
    
    print("\n✅ SimpleContextAgent 完了！")
    print("💡 これで from your_module import エラーは解決されます。")

# === NexusCore/openenv\Lib\site-packages\nltk\app\chartparser_app.py ===
# Natural Language Toolkit: Chart Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Jean Mark Gawron <gawron@mail.sdsu.edu>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring chart parsing.

Chart parsing is a flexible parsing algorithm that uses a data
structure called a "chart" to record hypotheses about syntactic
constituents.  Each hypothesis is represented by a single "edge" on
the chart.  A set of "chart rules" determine when new edges can be
added to the chart.  This set of rules controls the overall behavior
of the parser (e.g. whether it parses top-down or bottom-up).

The chart parsing tool demonstrates the process of parsing a single
sentence, with a given grammar and lexicon.  Its display is divided
into three sections: the bottom section displays the chart; the middle
section displays the sentence; and the top section displays the
partial syntax tree corresponding to the selected edge.  Buttons along
the bottom of the window are used to control the execution of the
algorithm.

The chart parsing tool allows for flexible control of the parsing
algorithm.  At each step of the algorithm, you can select which rule
or strategy you wish to apply.  This allows you to experiment with
mixing different strategies (e.g. top-down and bottom-up).  You can
exercise fine-grained control over the algorithm by selecting which
edge you wish to apply a rule to.
"""

# At some point, we should rewrite this tool to use the new canvas
# widget system.


import os.path
import pickle
from tkinter import (
    Button,
    Canvas,
    Checkbutton,
    Frame,
    IntVar,
    Label,
    Menu,
    Scrollbar,
    Tk,
    Toplevel,
)
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.font import Font
from tkinter.messagebox import showerror, showinfo

from nltk.draw import CFGEditor, TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import (
    CanvasFrame,
    ColorizedList,
    EntryDialog,
    MutableOptionMenu,
    ShowText,
    SymbolWidget,
)
from nltk.grammar import CFG, Nonterminal
from nltk.parse.chart import (
    BottomUpPredictCombineRule,
    BottomUpPredictRule,
    Chart,
    LeafEdge,
    LeafInitRule,
    SingleEdgeFundamentalRule,
    SteppingChartParser,
    TopDownInitRule,
    TopDownPredictRule,
    TreeEdge,
)
from nltk.tree import Tree
from nltk.util import in_idle

# Known bug: ChartView doesn't handle edges generated by epsilon
# productions (e.g., [Production: PP -> ]) very well.

#######################################################################
# Edge List
#######################################################################


class EdgeList(ColorizedList):
    ARROW = SymbolWidget.SYMBOLS["rightarrow"]

    def _init_colortags(self, textwidget, options):
        textwidget.tag_config("terminal", foreground="#006000")
        textwidget.tag_config("arrow", font="symbol", underline="0")
        textwidget.tag_config("dot", foreground="#000000")
        textwidget.tag_config(
            "nonterminal", foreground="blue", font=("helvetica", -12, "bold")
        )

    def _item_repr(self, item):
        contents = []
        contents.append(("%s\t" % item.lhs(), "nonterminal"))
        contents.append((self.ARROW, "arrow"))
        for i, elt in enumerate(item.rhs()):
            if i == item.dot():
                contents.append((" *", "dot"))
            if isinstance(elt, Nonterminal):
                contents.append((" %s" % elt.symbol(), "nonterminal"))
            else:
                contents.append((" %r" % elt, "terminal"))
        if item.is_complete():
            contents.append((" *", "dot"))
        return contents


#######################################################################
# Chart Matrix View
#######################################################################


class ChartMatrixView:
    """
    A view of a chart that displays the contents of the corresponding matrix.
    """

    def __init__(
        self, parent, chart, toplevel=True, title="Chart Matrix", show_numedges=False
    ):
        self._chart = chart
        self._cells = []
        self._marks = []

        self._selected_cell = None

        if toplevel:
            self._root = Toplevel(parent)
            self._root.title(title)
            self._root.bind("<Control-q>", self.destroy)
            self._init_quit(self._root)
        else:
            self._root = Frame(parent)

        self._init_matrix(self._root)
        self._init_list(self._root)
        if show_numedges:
            self._init_numedges(self._root)
        else:
            self._numedges_label = None

        self._callbacks = {}

        self._num_edges = 0

        self.draw()

    def _init_quit(self, root):
        quit = Button(root, text="Quit", command=self.destroy)
        quit.pack(side="bottom", expand=0, fill="none")

    def _init_matrix(self, root):
        cframe = Frame(root, border=2, relief="sunken")
        cframe.pack(expand=0, fill="none", padx=1, pady=3, side="top")
        self._canvas = Canvas(cframe, width=200, height=200, background="white")
        self._canvas.pack(expand=0, fill="none")

    def _init_numedges(self, root):
        self._numedges_label = Label(root, text="0 edges")
        self._numedges_label.pack(expand=0, fill="none", side="top")

    def _init_list(self, root):
        self._list = EdgeList(root, [], width=20, height=5)
        self._list.pack(side="top", expand=1, fill="both", pady=3)

        def cb(edge, self=self):
            self._fire_callbacks("select", edge)

        self._list.add_callback("select", cb)
        self._list.focus()

    def destroy(self, *e):
        if self._root is None:
            return
        try:
            self._root.destroy()
        except:
            pass
        self._root = None

    def set_chart(self, chart):
        if chart is not self._chart:
            self._chart = chart
            self._num_edges = 0
            self.draw()

    def update(self):
        if self._root is None:
            return

        # Count the edges in each cell
        N = len(self._cells)
        cell_edges = [[0 for i in range(N)] for j in range(N)]
        for edge in self._chart:
            cell_edges[edge.start()][edge.end()] += 1

        # Color the cells correspondingly.
        for i in range(N):
            for j in range(i, N):
                if cell_edges[i][j] == 0:
                    color = "gray20"
                else:
                    color = "#00{:02x}{:02x}".format(
                        min(255, 50 + 128 * cell_edges[i][j] / 10),
                        max(0, 128 - 128 * cell_edges[i][j] / 10),
                    )
                cell_tag = self._cells[i][j]
                self._canvas.itemconfig(cell_tag, fill=color)
                if (i, j) == self._selected_cell:
                    self._canvas.itemconfig(cell_tag, outline="#00ffff", width=3)
                    self._canvas.tag_raise(cell_tag)
                else:
                    self._canvas.itemconfig(cell_tag, outline="black", width=1)

        # Update the edge list.
        edges = list(self._chart.select(span=self._selected_cell))
        self._list.set(edges)

        # Update our edge count.
        self._num_edges = self._chart.num_edges()
        if self._numedges_label is not None:
            self._numedges_label["text"] = "%d edges" % self._num_edges

    def activate(self):
        self._canvas.itemconfig("inactivebox", state="hidden")
        self.update()

    def inactivate(self):
        self._canvas.itemconfig("inactivebox", state="normal")
        self.update()

    def add_callback(self, event, func):
        self._callbacks.setdefault(event, {})[func] = 1

    def remove_callback(self, event, func=None):
        if func is None:
            del self._callbacks[event]
        else:
            try:
                del self._callbacks[event][func]
            except:
                pass

    def _fire_callbacks(self, event, *args):
        if event not in self._callbacks:
            return
        for cb_func in list(self._callbacks[event].keys()):
            cb_func(*args)

    def select_cell(self, i, j):
        if self._root is None:
            return

        # If the cell is already selected (and the chart contents
        # haven't changed), then do nothing.
        if (i, j) == self._selected_cell and self._chart.num_edges() == self._num_edges:
            return

        self._selected_cell = (i, j)
        self.update()

        # Fire the callback.
        self._fire_callbacks("select_cell", i, j)

    def deselect_cell(self):
        if self._root is None:
            return
        self._selected_cell = None
        self._list.set([])
        self.update()

    def _click_cell(self, i, j):
        if self._selected_cell == (i, j):
            self.deselect_cell()
        else:
            self.select_cell(i, j)

    def view_edge(self, edge):
        self.select_cell(*edge.span())
        self._list.view(edge)

    def mark_edge(self, edge):
        if self._root is None:
            return
        self.select_cell(*edge.span())
        self._list.mark(edge)

    def unmark_edge(self, edge=None):
        if self._root is None:
            return
        self._list.unmark(edge)

    def markonly_edge(self, edge):
        if self._root is None:
            return
        self.select_cell(*edge.span())
        self._list.markonly(edge)

    def draw(self):
        if self._root is None:
            return
        LEFT_MARGIN = BOT_MARGIN = 15
        TOP_MARGIN = 5
        c = self._canvas
        c.delete("all")
        N = self._chart.num_leaves() + 1
        dx = (int(c["width"]) - LEFT_MARGIN) / N
        dy = (int(c["height"]) - TOP_MARGIN - BOT_MARGIN) / N

        c.delete("all")

        # Labels and dotted lines
        for i in range(N):
            c.create_text(
                LEFT_MARGIN - 2, i * dy + dy / 2 + TOP_MARGIN, text=repr(i), anchor="e"
            )
            c.create_text(
                i * dx + dx / 2 + LEFT_MARGIN,
                N * dy + TOP_MARGIN + 1,
                text=repr(i),
                anchor="n",
            )
            c.create_line(
                LEFT_MARGIN,
                dy * (i + 1) + TOP_MARGIN,
                dx * N + LEFT_MARGIN,
                dy * (i + 1) + TOP_MARGIN,
                dash=".",
            )
            c.create_line(
                dx * i + LEFT_MARGIN,
                TOP_MARGIN,
                dx * i + LEFT_MARGIN,
                dy * N + TOP_MARGIN,
                dash=".",
            )

        # A box around the whole thing
        c.create_rectangle(
            LEFT_MARGIN, TOP_MARGIN, LEFT_MARGIN + dx * N, dy * N + TOP_MARGIN, width=2
        )

        # Cells
        self._cells = [[None for i in range(N)] for j in range(N)]
        for i in range(N):
            for j in range(i, N):
                t = c.create_rectangle(
                    j * dx + LEFT_MARGIN,
                    i * dy + TOP_MARGIN,
                    (j + 1) * dx + LEFT_MARGIN,
                    (i + 1) * dy + TOP_MARGIN,
                    fill="gray20",
                )
                self._cells[i][j] = t

                def cb(event, self=self, i=i, j=j):
                    self._click_cell(i, j)

                c.tag_bind(t, "<Button-1>", cb)

        # Inactive box
        xmax, ymax = int(c["width"]), int(c["height"])
        t = c.create_rectangle(
            -100,
            -100,
            xmax + 100,
            ymax + 100,
            fill="gray50",
            state="hidden",
            tag="inactivebox",
        )
        c.tag_lower(t)

        # Update the cells.
        self.update()

    def pack(self, *args, **kwargs):
        self._root.pack(*args, **kwargs)


#######################################################################
# Chart Results View
#######################################################################


class ChartResultsView:
    def __init__(self, parent, chart, grammar, toplevel=True):
        self._chart = chart
        self._grammar = grammar
        self._trees = []
        self._y = 10
        self._treewidgets = []
        self._selection = None
        self._selectbox = None

        if toplevel:
            self._root = Toplevel(parent)
            self._root.title("Chart Parser Application: Results")
            self._root.bind("<Control-q>", self.destroy)
        else:
            self._root = Frame(parent)

        # Buttons
        if toplevel:
            buttons = Frame(self._root)
            buttons.pack(side="bottom", expand=0, fill="x")
            Button(buttons, text="Quit", command=self.destroy).pack(side="right")
            Button(buttons, text="Print All", command=self.print_all).pack(side="left")
            Button(buttons, text="Print Selection", command=self.print_selection).pack(
                side="left"
            )

        # Canvas frame.
        self._cframe = CanvasFrame(self._root, closeenough=20)
        self._cframe.pack(side="top", expand=1, fill="both")

        # Initial update
        self.update()

    def update(self, edge=None):
        if self._root is None:
            return
        # If the edge isn't a parse edge, do nothing.
        if edge is not None:
            if edge.lhs() != self._grammar.start():
                return
            if edge.span() != (0, self._chart.num_leaves()):
                return

        for parse in self._chart.parses(self._grammar.start()):
            if parse not in self._trees:
                self._add(parse)

    def _add(self, parse):
        # Add it to self._trees.
        self._trees.append(parse)

        # Create a widget for it.
        c = self._cframe.canvas()
        treewidget = tree_to_treesegment(c, parse)

        # Add it to the canvas frame.
        self._treewidgets.append(treewidget)
        self._cframe.add_widget(treewidget, 10, self._y)

        # Register callbacks.
        treewidget.bind_click(self._click)

        # Update y.
        self._y = treewidget.bbox()[3] + 10

    def _click(self, widget):
        c = self._cframe.canvas()
        if self._selection is not None:
            c.delete(self._selectbox)
        self._selection = widget
        (x1, y1, x2, y2) = widget.bbox()
        self._selectbox = c.create_rectangle(x1, y1, x2, y2, width=2, outline="#088")

    def _color(self, treewidget, color):
        treewidget.label()["color"] = color
        for child in treewidget.subtrees():
            if isinstance(child, TreeSegmentWidget):
                self._color(child, color)
            else:
                child["color"] = color

    def print_all(self, *e):
        if self._root is None:
            return
        self._cframe.print_to_file()

    def print_selection(self, *e):
        if self._root is None:
            return
        if self._selection is None:
            showerror("Print Error", "No tree selected")
        else:
            c = self._cframe.canvas()
            for widget in self._treewidgets:
                if widget is not self._selection:
                    self._cframe.destroy_widget(widget)
            c.delete(self._selectbox)
            (x1, y1, x2, y2) = self._selection.bbox()
            self._selection.move(10 - x1, 10 - y1)
            c["scrollregion"] = f"0 0 {x2 - x1 + 20} {y2 - y1 + 20}"
            self._cframe.print_to_file()

            # Restore our state.
            self._treewidgets = [self._selection]
            self.clear()
            self.update()

    def clear(self):
        if self._root is None:
            return
        for treewidget in self._treewidgets:
            self._cframe.destroy_widget(treewidget)
        self._trees = []
        self._treewidgets = []
        if self._selection is not None:
            self._cframe.canvas().delete(self._selectbox)
        self._selection = None
        self._y = 10

    def set_chart(self, chart):
        self.clear()
        self._chart = chart
        self.update()

    def set_grammar(self, grammar):
        self.clear()
        self._grammar = grammar
        self.update()

    def destroy(self, *e):
        if self._root is None:
            return
        try:
            self._root.destroy()
        except:
            pass
        self._root = None

    def pack(self, *args, **kwargs):
        self._root.pack(*args, **kwargs)


#######################################################################
# Chart Comparer
#######################################################################


class ChartComparer:
    """

    :ivar _root: The root window

    :ivar _charts: A dictionary mapping names to charts.  When
        charts are loaded, they are added to this dictionary.

    :ivar _left_chart: The left ``Chart``.
    :ivar _left_name: The name ``_left_chart`` (derived from filename)
    :ivar _left_matrix: The ``ChartMatrixView`` for ``_left_chart``
    :ivar _left_selector: The drop-down ``MutableOptionsMenu`` used
          to select ``_left_chart``.

    :ivar _right_chart: The right ``Chart``.
    :ivar _right_name: The name ``_right_chart`` (derived from filename)
    :ivar _right_matrix: The ``ChartMatrixView`` for ``_right_chart``
    :ivar _right_selector: The drop-down ``MutableOptionsMenu`` used
          to select ``_right_chart``.

    :ivar _out_chart: The out ``Chart``.
    :ivar _out_name: The name ``_out_chart`` (derived from filename)
    :ivar _out_matrix: The ``ChartMatrixView`` for ``_out_chart``
    :ivar _out_label: The label for ``_out_chart``.

    :ivar _op_label: A Label containing the most recent operation.
    """

    _OPSYMBOL = {
        "-": "-",
        "and": SymbolWidget.SYMBOLS["intersection"],
        "or": SymbolWidget.SYMBOLS["union"],
    }

    def __init__(self, *chart_filenames):
        # This chart is displayed when we don't have a value (eg
        # before any chart is loaded).
        faketok = [""] * 8
        self._emptychart = Chart(faketok)

        # The left & right charts start out empty.
        self._left_name = "None"
        self._right_name = "None"
        self._left_chart = self._emptychart
        self._right_chart = self._emptychart

        # The charts that have been loaded.
        self._charts = {"None": self._emptychart}

        # The output chart.
        self._out_chart = self._emptychart

        # The most recent operation
        self._operator = None

        # Set up the root window.
        self._root = Tk()
        self._root.title("Chart Comparison")
        self._root.bind("<Control-q>", self.destroy)
        self._root.bind("<Control-x>", self.destroy)

        # Initialize all widgets, etc.
        self._init_menubar(self._root)
        self._init_chartviews(self._root)
        self._init_divider(self._root)
        self._init_buttons(self._root)
        self._init_bindings(self._root)

        # Load any specified charts.
        for filename in chart_filenames:
            self.load_chart(filename)

    def destroy(self, *e):
        if self._root is None:
            return
        try:
            self._root.destroy()
        except:
            pass
        self._root = None

    def mainloop(self, *args, **kwargs):
        return
        self._root.mainloop(*args, **kwargs)

    # ////////////////////////////////////////////////////////////
    # Initialization
    # ////////////////////////////////////////////////////////////

    def _init_menubar(self, root):
        menubar = Menu(root)

        # File menu
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Load Chart",
            accelerator="Ctrl-o",
            underline=0,
            command=self.load_chart_dialog,
        )
        filemenu.add_command(
            label="Save Output",
            accelerator="Ctrl-s",
            underline=0,
            command=self.save_chart_dialog,
        )
        filemenu.add_separator()
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        # Compare menu
        opmenu = Menu(menubar, tearoff=0)
        opmenu.add_command(
            label="Intersection", command=self._intersection, accelerator="+"
        )
        opmenu.add_command(label="Union", command=self._union, accelerator="*")
        opmenu.add_command(
            label="Difference", command=self._difference, accelerator="-"
        )
        opmenu.add_separator()
        opmenu.add_command(label="Swap Charts", command=self._swapcharts)
        menubar.add_cascade(label="Compare", underline=0, menu=opmenu)

        # Add the menu
        self._root.config(menu=menubar)

    def _init_divider(self, root):
        divider = Frame(root, border=2, relief="sunken")
        divider.pack(side="top", fill="x", ipady=2)

    def _init_chartviews(self, root):
        opfont = ("symbol", -36)  # Font for operator.
        eqfont = ("helvetica", -36)  # Font for equals sign.

        frame = Frame(root, background="#c0c0c0")
        frame.pack(side="top", expand=1, fill="both")

        # The left matrix.
        cv1_frame = Frame(frame, border=3, relief="groove")
        cv1_frame.pack(side="left", padx=8, pady=7, expand=1, fill="both")
        self._left_selector = MutableOptionMenu(
            cv1_frame, list(self._charts.keys()), command=self._select_left
        )
        self._left_selector.pack(side="top", pady=5, fill="x")
        self._left_matrix = ChartMatrixView(
            cv1_frame, self._emptychart, toplevel=False, show_numedges=True
        )
        self._left_matrix.pack(side="bottom", padx=5, pady=5, expand=1, fill="both")
        self._left_matrix.add_callback("select", self.select_edge)
        self._left_matrix.add_callback("select_cell", self.select_cell)
        self._left_matrix.inactivate()

        # The operator.
        self._op_label = Label(
            frame, text=" ", width=3, background="#c0c0c0", font=opfont
        )
        self._op_label.pack(side="left", padx=5, pady=5)

        # The right matrix.
        cv2_frame = Frame(frame, border=3, relief="groove")
        cv2_frame.pack(side="left", padx=8, pady=7, expand=1, fill="both")
        self._right_selector = MutableOptionMenu(
            cv2_frame, list(self._charts.keys()), command=self._select_right
        )
        self._right_selector.pack(side="top", pady=5, fill="x")
        self._right_matrix = ChartMatrixView(
            cv2_frame, self._emptychart, toplevel=False, show_numedges=True
        )
        self._right_matrix.pack(side="bottom", padx=5, pady=5, expand=1, fill="both")
        self._right_matrix.add_callback("select", self.select_edge)
        self._right_matrix.add_callback("select_cell", self.select_cell)
        self._right_matrix.inactivate()

        # The equals sign
        Label(frame, text="=", width=3, background="#c0c0c0", font=eqfont).pack(
            side="left", padx=5, pady=5
        )

        # The output matrix.
        out_frame = Frame(frame, border=3, relief="groove")
        out_frame.pack(side="left", padx=8, pady=7, expand=1, fill="both")
        self._out_label = Label(out_frame, text="Output")
        self._out_label.pack(side="top", pady=9)
        self._out_matrix = ChartMatrixView(
            out_frame, self._emptychart, toplevel=False, show_numedges=True
        )
        self._out_matrix.pack(side="bottom", padx=5, pady=5, expand=1, fill="both")
        self._out_matrix.add_callback("select", self.select_edge)
        self._out_matrix.add_callback("select_cell", self.select_cell)
        self._out_matrix.inactivate()

    def _init_buttons(self, root):
        buttons = Frame(root)
        buttons.pack(side="bottom", pady=5, fill="x", expand=0)
        Button(buttons, text="Intersection", command=self._intersection).pack(
            side="left"
        )
        Button(buttons, text="Union", command=self._union).pack(side="left")
        Button(buttons, text="Difference", command=self._difference).pack(side="left")
        Frame(buttons, width=20).pack(side="left")
        Button(buttons, text="Swap Charts", command=self._swapcharts).pack(side="left")

        Button(buttons, text="Detach Output", command=self._detach_out).pack(
            side="right"
        )

    def _init_bindings(self, root):
        # root.bind('<Control-s>', self.save_chart)
        root.bind("<Control-o>", self.load_chart_dialog)
        # root.bind('<Control-r>', self.reset)

    # ////////////////////////////////////////////////////////////
    # Input Handling
    # ////////////////////////////////////////////////////////////

    def _select_left(self, name):
        self._left_name = name
        self._left_chart = self._charts[name]
        self._left_matrix.set_chart(self._left_chart)
        if name == "None":
            self._left_matrix.inactivate()
        self._apply_op()

    def _select_right(self, name):
        self._right_name = name
        self._right_chart = self._charts[name]
        self._right_matrix.set_chart(self._right_chart)
        if name == "None":
            self._right_matrix.inactivate()
        self._apply_op()

    def _apply_op(self):
        if self._operator == "-":
            self._difference()
        elif self._operator == "or":
            self._union()
        elif self._operator == "and":
            self._intersection()

    # ////////////////////////////////////////////////////////////
    # File
    # ////////////////////////////////////////////////////////////
    CHART_FILE_TYPES = [("Pickle file", ".pickle"), ("All files", "*")]

    def save_chart_dialog(self, *args):
        filename = asksaveasfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            with open(filename, "wb") as outfile:
                pickle.dump(self._out_chart, outfile)
        except Exception as e:
            showerror("Error Saving Chart", f"Unable to open file: {filename!r}\n{e}")

    def load_chart_dialog(self, *args):
        filename = askopenfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            self.load_chart(filename)
        except Exception as e:
            showerror("Error Loading Chart", f"Unable to open file: {filename!r}\n{e}")

    def load_chart(self, filename):
        with open(filename, "rb") as infile:
            chart = pickle.load(infile)
        name = os.path.basename(filename)
        if name.endswith(".pickle"):
            name = name[:-7]
        if name.endswith(".chart"):
            name = name[:-6]
        self._charts[name] = chart
        self._left_selector.add(name)
        self._right_selector.add(name)

        # If either left_matrix or right_matrix is empty, then
        # display the new chart.
        if self._left_chart is self._emptychart:
            self._left_selector.set(name)
        elif self._right_chart is self._emptychart:
            self._right_selector.set(name)

    def _update_chartviews(self):
        self._left_matrix.update()
        self._right_matrix.update()
        self._out_matrix.update()

    # ////////////////////////////////////////////////////////////
    # Selection
    # ////////////////////////////////////////////////////////////

    def select_edge(self, edge):
        if edge in self._left_chart:
            self._left_matrix.markonly_edge(edge)
        else:
            self._left_matrix.unmark_edge()
        if edge in self._right_chart:
            self._right_matrix.markonly_edge(edge)
        else:
            self._right_matrix.unmark_edge()
        if edge in self._out_chart:
            self._out_matrix.markonly_edge(edge)
        else:
            self._out_matrix.unmark_edge()

    def select_cell(self, i, j):
        self._left_matrix.select_cell(i, j)
        self._right_matrix.select_cell(i, j)
        self._out_matrix.select_cell(i, j)

    # ////////////////////////////////////////////////////////////
    # Operations
    # ////////////////////////////////////////////////////////////

    def _difference(self):
        if not self._checkcompat():
            return

        out_chart = Chart(self._left_chart.tokens())
        for edge in self._left_chart:
            if edge not in self._right_chart:
                out_chart.insert(edge, [])

        self._update("-", out_chart)

    def _intersection(self):
        if not self._checkcompat():
            return

        out_chart = Chart(self._left_chart.tokens())
        for edge in self._left_chart:
            if edge in self._right_chart:
                out_chart.insert(edge, [])

        self._update("and", out_chart)

    def _union(self):
        if not self._checkcompat():
            return

        out_chart = Chart(self._left_chart.tokens())
        for edge in self._left_chart:
            out_chart.insert(edge, [])
        for edge in self._right_chart:
            out_chart.insert(edge, [])

        self._update("or", out_chart)

    def _swapcharts(self):
        left, right = self._left_name, self._right_name
        self._left_selector.set(right)
        self._right_selector.set(left)

    def _checkcompat(self):
        if (
            self._left_chart.tokens() != self._right_chart.tokens()
            or self._left_chart.property_names() != self._right_chart.property_names()
            or self._left_chart == self._emptychart
            or self._right_chart == self._emptychart
        ):
            # Clear & inactivate the output chart.
            self._out_chart = self._emptychart
            self._out_matrix.set_chart(self._out_chart)
            self._out_matrix.inactivate()
            self._out_label["text"] = "Output"
            # Issue some other warning?
            return False
        else:
            return True

    def _update(self, operator, out_chart):
        self._operator = operator
        self._op_label["text"] = self._OPSYMBOL[operator]
        self._out_chart = out_chart
        self._out_matrix.set_chart(out_chart)
        self._out_label["text"] = "{} {} {}".format(
            self._left_name,
            self._operator,
            self._right_name,
        )

    def _clear_out_chart(self):
        self._out_chart = self._emptychart
        self._out_matrix.set_chart(self._out_chart)
        self._op_label["text"] = " "
        self._out_matrix.inactivate()

    def _detach_out(self):
        ChartMatrixView(self._root, self._out_chart, title=self._out_label["text"])


#######################################################################
# Chart View
#######################################################################


class ChartView:
    """
    A component for viewing charts.  This is used by ``ChartParserApp`` to
    allow students to interactively experiment with various chart
    parsing techniques.  It is also used by ``Chart.draw()``.

    :ivar _chart: The chart that we are giving a view of.  This chart
       may be modified; after it is modified, you should call
       ``update``.
    :ivar _sentence: The list of tokens that the chart spans.

    :ivar _root: The root window.
    :ivar _chart_canvas: The canvas we're using to display the chart
        itself.
    :ivar _tree_canvas: The canvas we're using to display the tree
        that each edge spans.  May be None, if we're not displaying
        trees.
    :ivar _sentence_canvas: The canvas we're using to display the sentence
        text.  May be None, if we're not displaying the sentence text.
    :ivar _edgetags: A dictionary mapping from edges to the tags of
        the canvas elements (lines, etc) used to display that edge.
        The values of this dictionary have the form
        ``(linetag, rhstag1, dottag, rhstag2, lhstag)``.
    :ivar _treetags: A list of all the tags that make up the tree;
        used to erase the tree (without erasing the loclines).
    :ivar _chart_height: The height of the chart canvas.
    :ivar _sentence_height: The height of the sentence canvas.
    :ivar _tree_height: The height of the tree

    :ivar _text_height: The height of a text string (in the normal
        font).

    :ivar _edgelevels: A list of edges at each level of the chart (the
        top level is the 0th element).  This list is used to remember
        where edges should be drawn; and to make sure that no edges
        are overlapping on the chart view.

    :ivar _unitsize: Pixel size of one unit (from the location).  This
       is determined by the span of the chart's location, and the
       width of the chart display canvas.

    :ivar _fontsize: The current font size

    :ivar _marks: A dictionary from edges to marks.  Marks are
        strings, specifying colors (e.g. 'green').
    """

    _LEAF_SPACING = 10
    _MARGIN = 10
    _TREE_LEVEL_SIZE = 12
    _CHART_LEVEL_SIZE = 40

    def __init__(self, chart, root=None, **kw):
        """
        Construct a new ``Chart`` display.
        """
        # Process keyword args.
        draw_tree = kw.get("draw_tree", 0)
        draw_sentence = kw.get("draw_sentence", 1)
        self._fontsize = kw.get("fontsize", -12)

        # The chart!
        self._chart = chart

        # Callback functions
        self._callbacks = {}

        # Keep track of drawn edges
        self._edgelevels = []
        self._edgetags = {}

        # Keep track of which edges are marked.
        self._marks = {}

        # These are used to keep track of the set of tree tokens
        # currently displayed in the tree canvas.
        self._treetoks = []
        self._treetoks_edge = None
        self._treetoks_index = 0

        # Keep track of the tags used to draw the tree
        self._tree_tags = []

        # Put multiple edges on each level?
        self._compact = 0

        # If they didn't provide a main window, then set one up.
        if root is None:
            top = Tk()
            top.title("Chart View")

            def destroy1(e, top=top):
                top.destroy()

            def destroy2(top=top):
                top.destroy()

            top.bind("q", destroy1)
            b = Button(top, text="Done", command=destroy2)
            b.pack(side="bottom")
            self._root = top
        else:
            self._root = root

        # Create some fonts.
        self._init_fonts(root)

        # Create the chart canvas.
        (self._chart_sb, self._chart_canvas) = self._sb_canvas(self._root)
        self._chart_canvas["height"] = 300
        self._chart_canvas["closeenough"] = 15

        # Create the sentence canvas.
        if draw_sentence:
            cframe = Frame(self._root, relief="sunk", border=2)
            cframe.pack(fill="both", side="bottom")
            self._sentence_canvas = Canvas(cframe, height=50)
            self._sentence_canvas["background"] = "#e0e0e0"
            self._sentence_canvas.pack(fill="both")
            # self._sentence_canvas['height'] = self._sentence_height
        else:
            self._sentence_canvas = None

        # Create the tree canvas.
        if draw_tree:
            (sb, canvas) = self._sb_canvas(self._root, "n", "x")
            (self._tree_sb, self._tree_canvas) = (sb, canvas)
            self._tree_canvas["height"] = 200
        else:
            self._tree_canvas = None

        # Do some analysis to figure out how big the window should be
        self._analyze()
        self.draw()
        self._resize()
        self._grow()

        # Set up the configure callback, which will be called whenever
        # the window is resized.
        self._chart_canvas.bind("<Configure>", self._configure)

    def _init_fonts(self, root):
        self._boldfont = Font(family="helvetica", weight="bold", size=self._fontsize)
        self._font = Font(family="helvetica", size=self._fontsize)
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

    def _sb_canvas(self, root, expand="y", fill="both", side="bottom"):
        """
        Helper for __init__: construct a canvas with a scrollbar.
        """
        cframe = Frame(root, relief="sunk", border=2)
        cframe.pack(fill=fill, expand=expand, side=side)
        canvas = Canvas(cframe, background="#e0e0e0")

        # Give the canvas a scrollbar.
        sb = Scrollbar(cframe, orient="vertical")
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill=fill, expand="yes")

        # Connect the scrollbars to the canvas.
        sb["command"] = canvas.yview
        canvas["yscrollcommand"] = sb.set

        return (sb, canvas)

    def scroll_up(self, *e):
        self._chart_canvas.yview("scroll", -1, "units")

    def scroll_down(self, *e):
        self._chart_canvas.yview("scroll", 1, "units")

    def page_up(self, *e):
        self._chart_canvas.yview("scroll", -1, "pages")

    def page_down(self, *e):
        self._chart_canvas.yview("scroll", 1, "pages")

    def _grow(self):
        """
        Grow the window, if necessary
        """
        # Grow, if need-be
        N = self._chart.num_leaves()
        width = max(
            int(self._chart_canvas["width"]), N * self._unitsize + ChartView._MARGIN * 2
        )

        # It won't resize without the second (height) line, but I
        # don't understand why not.
        self._chart_canvas.configure(width=width)
        self._chart_canvas.configure(height=self._chart_canvas["height"])

        self._unitsize = (width - 2 * ChartView._MARGIN) / N

        # Reset the height for the sentence window.
        if self._sentence_canvas is not None:
            self._sentence_canvas["height"] = self._sentence_height

    def set_font_size(self, size):
        self._font.configure(size=-abs(size))
        self._boldfont.configure(size=-abs(size))
        self._sysfont.configure(size=-abs(size))
        self._analyze()
        self._grow()
        self.draw()

    def get_font_size(self):
        return abs(self._fontsize)

    def _configure(self, e):
        """
        The configure callback.  This is called whenever the window is
        resized.  It is also called when the window is first mapped.
        It figures out the unit size, and redraws the contents of each
        canvas.
        """
        N = self._chart.num_leaves()
        self._unitsize = (e.width - 2 * ChartView._MARGIN) / N
        self.draw()

    def update(self, chart=None):
        """
        Draw any edges that have not been drawn.  This is typically
        called when a after modifies the canvas that a CanvasView is
        displaying.  ``update`` will cause any edges that have been
        added to the chart to be drawn.

        If update is given a ``chart`` argument, then it will replace
        the current chart with the given chart.
        """
        if chart is not None:
            self._chart = chart
            self._edgelevels = []
            self._marks = {}
            self._analyze()
            self._grow()
            self.draw()
            self.erase_tree()
            self._resize()
        else:
            for edge in self._chart:
                if edge not in self._edgetags:
                    self._add_edge(edge)
            self._resize()

    def _edge_conflict(self, edge, lvl):
        """
        Return True if the given edge overlaps with any edge on the given
        level.  This is used by _add_edge to figure out what level a
        new edge should be added to.
        """
        (s1, e1) = edge.span()
        for otheredge in self._edgelevels[lvl]:
            (s2, e2) = otheredge.span()
            if (s1 <= s2 < e1) or (s2 <= s1 < e2) or (s1 == s2 == e1 == e2):
                return True
        return False

    def _analyze_edge(self, edge):
        """
        Given a new edge, recalculate:

            - _text_height
            - _unitsize (if the edge text is too big for the current
              _unitsize, then increase _unitsize)
        """
        c = self._chart_canvas

        if isinstance(edge, TreeEdge):
            lhs = edge.lhs()
            rhselts = []
            for elt in edge.rhs():
                if isinstance(elt, Nonterminal):
                    rhselts.append(str(elt.symbol()))
                else:
                    rhselts.append(repr(elt))
            rhs = " ".join(rhselts)
        else:
            lhs = edge.lhs()
            rhs = ""

        for s in (lhs, rhs):
            tag = c.create_text(
                0, 0, text=s, font=self._boldfont, anchor="nw", justify="left"
            )
            bbox = c.bbox(tag)
            c.delete(tag)
            width = bbox[2]  # + ChartView._LEAF_SPACING
            edgelen = max(edge.length(), 1)
            self._unitsize = max(self._unitsize, width / edgelen)
            self._text_height = max(self._text_height, bbox[3] - bbox[1])

    def _add_edge(self, edge, minlvl=0):
        """
        Add a single edge to the ChartView:

            - Call analyze_edge to recalculate display parameters
            - Find an available level
            - Call _draw_edge
        """
        # Do NOT show leaf edges in the chart.
        if isinstance(edge, LeafEdge):
            return

        if edge in self._edgetags:
            return
        self._analyze_edge(edge)
        self._grow()

        if not self._compact:
            self._edgelevels.append([edge])
            lvl = len(self._edgelevels) - 1
            self._draw_edge(edge, lvl)
            self._resize()
            return

        # Figure out what level to draw the edge on.
        lvl = 0
        while True:
            # If this level doesn't exist yet, create it.
            while lvl >= len(self._edgelevels):
                self._edgelevels.append([])
                self._resize()

            # Check if we can fit the edge in this level.
            if lvl >= minlvl and not self._edge_conflict(edge, lvl):
                # Go ahead and draw it.
                self._edgelevels[lvl].append(edge)
                break

            # Try the next level.
            lvl += 1

        self._draw_edge(edge, lvl)

    def view_edge(self, edge):
        level = None
        for i in range(len(self._edgelevels)):
            if edge in self._edgelevels[i]:
                level = i
                break
        if level is None:
            return
        # Try to view the new edge..
        y = (level + 1) * self._chart_level_size
        dy = self._text_height + 10
        self._chart_canvas.yview("moveto", 1.0)
        if self._chart_height != 0:
            self._chart_canvas.yview("moveto", (y - dy) / self._chart_height)

    def _draw_edge(self, edge, lvl):
        """
        Draw a single edge on the ChartView.
        """
        c = self._chart_canvas

        # Draw the arrow.
        x1 = edge.start() * self._unitsize + ChartView._MARGIN
        x2 = edge.end() * self._unitsize + ChartView._MARGIN
        if x2 == x1:
            x2 += max(4, self._unitsize / 5)
        y = (lvl + 1) * self._chart_level_size
        linetag = c.create_line(x1, y, x2, y, arrow="last", width=3)

        # Draw a label for the edge.
        if isinstance(edge, TreeEdge):
            rhs = []
            for elt in edge.rhs():
                if isinstance(elt, Nonterminal):
                    rhs.append(str(elt.symbol()))
                else:
                    rhs.append(repr(elt))
            pos = edge.dot()
        else:
            rhs = []
            pos = 0

        rhs1 = " ".join(rhs[:pos])
        rhs2 = " ".join(rhs[pos:])
        rhstag1 = c.create_text(x1 + 3, y, text=rhs1, font=self._font, anchor="nw")
        dotx = c.bbox(rhstag1)[2] + 6
        doty = (c.bbox(rhstag1)[1] + c.bbox(rhstag1)[3]) / 2
        dottag = c.create_oval(dotx - 2, doty - 2, dotx + 2, doty + 2)
        rhstag2 = c.create_text(dotx + 6, y, text=rhs2, font=self._font, anchor="nw")
        lhstag = c.create_text(
            (x1 + x2) / 2, y, text=str(edge.lhs()), anchor="s", font=self._boldfont
        )

        # Keep track of the edge's tags.
        self._edgetags[edge] = (linetag, rhstag1, dottag, rhstag2, lhstag)

        # Register a callback for clicking on the edge.
        def cb(event, self=self, edge=edge):
            self._fire_callbacks("select", edge)

        c.tag_bind(rhstag1, "<Button-1>", cb)
        c.tag_bind(rhstag2, "<Button-1>", cb)
        c.tag_bind(linetag, "<Button-1>", cb)
        c.tag_bind(dottag, "<Button-1>", cb)
        c.tag_bind(lhstag, "<Button-1>", cb)

        self._color_edge(edge)

    def _color_edge(self, edge, linecolor=None, textcolor=None):
        """
        Color in an edge with the given colors.
        If no colors are specified, use intelligent defaults
        (dependent on selection, etc.)
        """
        if edge not in self._edgetags:
            return
        c = self._chart_canvas

        if linecolor is not None and textcolor is not None:
            if edge in self._marks:
                linecolor = self._marks[edge]
            tags = self._edgetags[edge]
            c.itemconfig(tags[0], fill=linecolor)
            c.itemconfig(tags[1], fill=textcolor)
            c.itemconfig(tags[2], fill=textcolor, outline=textcolor)
            c.itemconfig(tags[3], fill=textcolor)
            c.itemconfig(tags[4], fill=textcolor)
            return
        else:
            N = self._chart.num_leaves()
            if edge in self._marks:
                self._color_edge(self._marks[edge])
            if edge.is_complete() and edge.span() == (0, N):
                self._color_edge(edge, "#084", "#042")
            elif isinstance(edge, LeafEdge):
                self._color_edge(edge, "#48c", "#246")
            else:
                self._color_edge(edge, "#00f", "#008")

    def mark_edge(self, edge, mark="#0df"):
        """
        Mark an edge
        """
        self._marks[edge] = mark
        self._color_edge(edge)

    def unmark_edge(self, edge=None):
        """
        Unmark an edge (or all edges)
        """
        if edge is None:
            old_marked_edges = list(self._marks.keys())
            self._marks = {}
            for edge in old_marked_edges:
                self._color_edge(edge)
        else:
            del self._marks[edge]
            self._color_edge(edge)

    def markonly_edge(self, edge, mark="#0df"):
        self.unmark_edge()
        self.mark_edge(edge, mark)

    def _analyze(self):
        """
        Analyze the sentence string, to figure out how big a unit needs
        to be, How big the tree should be, etc.
        """
        # Figure out the text height and the unit size.
        unitsize = 70  # min unitsize
        text_height = 0
        c = self._chart_canvas

        # Check against all tokens
        for leaf in self._chart.leaves():
            tag = c.create_text(
                0, 0, text=repr(leaf), font=self._font, anchor="nw", justify="left"
            )
            bbox = c.bbox(tag)
            c.delete(tag)
            width = bbox[2] + ChartView._LEAF_SPACING
            unitsize = max(width, unitsize)
            text_height = max(text_height, bbox[3] - bbox[1])

        self._unitsize = unitsize
        self._text_height = text_height
        self._sentence_height = self._text_height + 2 * ChartView._MARGIN

        # Check against edges.
        for edge in self._chart.edges():
            self._analyze_edge(edge)

        # Size of chart levels
        self._chart_level_size = self._text_height * 2

        # Default tree size..
        self._tree_height = 3 * (ChartView._TREE_LEVEL_SIZE + self._text_height)

        # Resize the scrollregions.
        self._resize()

    def _resize(self):
        """
        Update the scroll-regions for each canvas.  This ensures that
        everything is within a scroll-region, so the user can use the
        scrollbars to view the entire display.  This does *not*
        resize the window.
        """
        c = self._chart_canvas

        # Reset the chart scroll region
        width = self._chart.num_leaves() * self._unitsize + ChartView._MARGIN * 2

        levels = len(self._edgelevels)
        self._chart_height = (levels + 2) * self._chart_level_size
        c["scrollregion"] = (0, 0, width, self._chart_height)

        # Reset the tree scroll region
        if self._tree_canvas:
            self._tree_canvas["scrollregion"] = (0, 0, width, self._tree_height)

    def _draw_loclines(self):
        """
        Draw location lines.  These are vertical gridlines used to
        show where each location unit is.
        """
        BOTTOM = 50000
        c1 = self._tree_canvas
        c2 = self._sentence_canvas
        c3 = self._chart_canvas
        margin = ChartView._MARGIN
        self._loclines = []
        for i in range(0, self._chart.num_leaves() + 1):
            x = i * self._unitsize + margin

            if c1:
                t1 = c1.create_line(x, 0, x, BOTTOM)
                c1.tag_lower(t1)
            if c2:
                t2 = c2.create_line(x, 0, x, self._sentence_height)
                c2.tag_lower(t2)
            t3 = c3.create_line(x, 0, x, BOTTOM)
            c3.tag_lower(t3)
            t4 = c3.create_text(x + 2, 0, text=repr(i), anchor="nw", font=self._font)
            c3.tag_lower(t4)
            # if i % 4 == 0:
            #    if c1: c1.itemconfig(t1, width=2, fill='gray60')
            #    if c2: c2.itemconfig(t2, width=2, fill='gray60')
            #    c3.itemconfig(t3, width=2, fill='gray60')
            if i % 2 == 0:
                if c1:
                    c1.itemconfig(t1, fill="gray60")
                if c2:
                    c2.itemconfig(t2, fill="gray60")
                c3.itemconfig(t3, fill="gray60")
            else:
                if c1:
                    c1.itemconfig(t1, fill="gray80")
                if c2:
                    c2.itemconfig(t2, fill="gray80")
                c3.itemconfig(t3, fill="gray80")

    def _draw_sentence(self):
        """Draw the sentence string."""
        if self._chart.num_leaves() == 0:
            return
        c = self._sentence_canvas
        margin = ChartView._MARGIN
        y = ChartView._MARGIN

        for i, leaf in enumerate(self._chart.leaves()):
            x1 = i * self._unitsize + margin
            x2 = x1 + self._unitsize
            x = (x1 + x2) / 2
            tag = c.create_text(
                x, y, text=repr(leaf), font=self._font, anchor="n", justify="left"
            )
            bbox = c.bbox(tag)
            rt = c.create_rectangle(
                x1 + 2,
                bbox[1] - (ChartView._LEAF_SPACING / 2),
                x2 - 2,
                bbox[3] + (ChartView._LEAF_SPACING / 2),
                fill="#f0f0f0",
                outline="#f0f0f0",
            )
            c.tag_lower(rt)

    def erase_tree(self):
        for tag in self._tree_tags:
            self._tree_canvas.delete(tag)
        self._treetoks = []
        self._treetoks_edge = None
        self._treetoks_index = 0

    def draw_tree(self, edge=None):
        if edge is None and self._treetoks_edge is None:
            return
        if edge is None:
            edge = self._treetoks_edge

        # If it's a new edge, then get a new list of treetoks.
        if self._treetoks_edge != edge:
            self._treetoks = [t for t in self._chart.trees(edge) if isinstance(t, Tree)]
            self._treetoks_edge = edge
            self._treetoks_index = 0

        # Make sure there's something to draw.
        if len(self._treetoks) == 0:
            return

        # Erase the old tree.
        for tag in self._tree_tags:
            self._tree_canvas.delete(tag)

        # Draw the new tree.
        tree = self._treetoks[self._treetoks_index]
        self._draw_treetok(tree, edge.start())

        # Show how many trees are available for the edge.
        self._draw_treecycle()

        # Update the scroll region.
        w = self._chart.num_leaves() * self._unitsize + 2 * ChartView._MARGIN
        h = tree.height() * (ChartView._TREE_LEVEL_SIZE + self._text_height)
        self._tree_canvas["scrollregion"] = (0, 0, w, h)

    def cycle_tree(self):
        self._treetoks_index = (self._treetoks_index + 1) % len(self._treetoks)
        self.draw_tree(self._treetoks_edge)

    def _draw_treecycle(self):
        if len(self._treetoks) <= 1:
            return

        # Draw the label.
        label = "%d Trees" % len(self._treetoks)
        c = self._tree_canvas
        margin = ChartView._MARGIN
        right = self._chart.num_leaves() * self._unitsize + margin - 2
        tag = c.create_text(right, 2, anchor="ne", text=label, font=self._boldfont)
        self._tree_tags.append(tag)
        _, _, _, y = c.bbox(tag)

        # Draw the triangles.
        for i in range(len(self._treetoks)):
            x = right - 20 * (len(self._treetoks) - i - 1)
            if i == self._treetoks_index:
                fill = "#084"
            else:
                fill = "#fff"
            tag = c.create_polygon(
                x, y + 10, x - 5, y, x - 10, y + 10, fill=fill, outline="black"
            )
            self._tree_tags.append(tag)

            # Set up a callback: show the tree if they click on its
            # triangle.
            def cb(event, self=self, i=i):
                self._treetoks_index = i
                self.draw_tree()

            c.tag_bind(tag, "<Button-1>", cb)

    def _draw_treetok(self, treetok, index, depth=0):
        """
        :param index: The index of the first leaf in the tree.
        :return: The index of the first leaf after the tree.
        """
        c = self._tree_canvas
        margin = ChartView._MARGIN

        # Draw the children
        child_xs = []
        for child in treetok:
            if isinstance(child, Tree):
                child_x, index = self._draw_treetok(child, index, depth + 1)
                child_xs.append(child_x)
            else:
                child_xs.append((2 * index + 1) * self._unitsize / 2 + margin)
                index += 1

        # If we have children, then get the node's x by averaging their
        # node x's.  Otherwise, make room for ourselves.
        if child_xs:
            nodex = sum(child_xs) / len(child_xs)
        else:
            # [XX] breaks for null productions.
            nodex = (2 * index + 1) * self._unitsize / 2 + margin
            index += 1

        # Draw the node
        nodey = depth * (ChartView._TREE_LEVEL_SIZE + self._text_height)
        tag = c.create_text(
            nodex,
            nodey,
            anchor="n",
            justify="center",
            text=str(treetok.label()),
            fill="#042",
            font=self._boldfont,
        )
        self._tree_tags.append(tag)

        # Draw lines to the children.
        childy = nodey + ChartView._TREE_LEVEL_SIZE + self._text_height
        for childx, child in zip(child_xs, treetok):
            if isinstance(child, Tree) and child:
                # A "real" tree token:
                tag = c.create_line(
                    nodex,
                    nodey + self._text_height,
                    childx,
                    childy,
                    width=2,
                    fill="#084",
                )
                self._tree_tags.append(tag)
            if isinstance(child, Tree) and not child:
                # An unexpanded tree token:
                tag = c.create_line(
                    nodex,
                    nodey + self._text_height,
                    childx,
                    childy,
                    width=2,
                    fill="#048",
                    dash="2 3",
                )
                self._tree_tags.append(tag)
            if not isinstance(child, Tree):
                # A leaf:
                tag = c.create_line(
                    nodex,
                    nodey + self._text_height,
                    childx,
                    10000,
                    width=2,
                    fill="#084",
                )
                self._tree_tags.append(tag)

        return nodex, index

    def draw(self):
        """
        Draw everything (from scratch).
        """
        if self._tree_canvas:
            self._tree_canvas.delete("all")
            self.draw_tree()

        if self._sentence_canvas:
            self._sentence_canvas.delete("all")
            self._draw_sentence()

        self._chart_canvas.delete("all")
        self._edgetags = {}

        # Redraw any edges we erased.
        for lvl in range(len(self._edgelevels)):
            for edge in self._edgelevels[lvl]:
                self._draw_edge(edge, lvl)

        for edge in self._chart:
            self._add_edge(edge)

        self._draw_loclines()

    def add_callback(self, event, func):
        self._callbacks.setdefault(event, {})[func] = 1

    def remove_callback(self, event, func=None):
        if func is None:
            del self._callbacks[event]
        else:
            try:
                del self._callbacks[event][func]
            except:
                pass

    def _fire_callbacks(self, event, *args):
        if event not in self._callbacks:
            return
        for cb_func in list(self._callbacks[event].keys()):
            cb_func(*args)


#######################################################################
# Edge Rules
#######################################################################
# These version of the chart rules only apply to a specific edge.
# This lets the user select an edge, and then apply a rule.


class EdgeRule:
    """
    To create an edge rule, make an empty base class that uses
    EdgeRule as the first base class, and the basic rule as the
    second base class.  (Order matters!)
    """

    def __init__(self, edge):
        super = self.__class__.__bases__[1]
        self._edge = edge
        self.NUM_EDGES = super.NUM_EDGES - 1

    def apply(self, chart, grammar, *edges):
        super = self.__class__.__bases__[1]
        edges += (self._edge,)
        yield from super.apply(self, chart, grammar, *edges)

    def __str__(self):
        super = self.__class__.__bases__[1]
        return super.__str__(self)


class TopDownPredictEdgeRule(EdgeRule, TopDownPredictRule):
    pass


class BottomUpEdgeRule(EdgeRule, BottomUpPredictRule):
    pass


class BottomUpLeftCornerEdgeRule(EdgeRule, BottomUpPredictCombineRule):
    pass


class FundamentalEdgeRule(EdgeRule, SingleEdgeFundamentalRule):
    pass


#######################################################################
# Chart Parser Application
#######################################################################


class ChartParserApp:
    def __init__(self, grammar, tokens, title="Chart Parser Application"):
        # Initialize the parser
        self._init_parser(grammar, tokens)

        self._root = None
        try:
            # Create the root window.
            self._root = Tk()
            self._root.title(title)
            self._root.bind("<Control-q>", self.destroy)

            # Set up some frames.
            frame3 = Frame(self._root)
            frame2 = Frame(self._root)
            frame1 = Frame(self._root)
            frame3.pack(side="bottom", fill="none")
            frame2.pack(side="bottom", fill="x")
            frame1.pack(side="bottom", fill="both", expand=1)

            self._init_fonts(self._root)
            self._init_animation()
            self._init_chartview(frame1)
            self._init_rulelabel(frame2)
            self._init_buttons(frame3)
            self._init_menubar()

            self._matrix = None
            self._results = None

            # Set up keyboard bindings.
            self._init_bindings()

        except:
            print("Error creating Tree View")
            self.destroy()
            raise

    def destroy(self, *args):
        if self._root is None:
            return
        self._root.destroy()
        self._root = None

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._root.mainloop(*args, **kwargs)

    # ////////////////////////////////////////////////////////////
    # Initialization Helpers
    # ////////////////////////////////////////////////////////////

    def _init_parser(self, grammar, tokens):
        self._grammar = grammar
        self._tokens = tokens
        self._reset_parser()

    def _reset_parser(self):
        self._cp = SteppingChartParser(self._grammar)
        self._cp.initialize(self._tokens)
        self._chart = self._cp.chart()

        # Insert LeafEdges before the parsing starts.
        for _new_edge in LeafInitRule().apply(self._chart, self._grammar):
            pass

        # The step iterator -- use this to generate new edges
        self._cpstep = self._cp.step()

        # The currently selected edge
        self._selection = None

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())

    def _init_animation(self):
        # Are we stepping? (default=yes)
        self._step = IntVar(self._root)
        self._step.set(1)

        # What's our animation speed (default=fast)
        self._animate = IntVar(self._root)
        self._animate.set(3)  # Default speed = fast

        # Are we currently animating?
        self._animating = 0

    def _init_chartview(self, parent):
        self._cv = ChartView(self._chart, parent, draw_tree=1, draw_sentence=1)
        self._cv.add_callback("select", self._click_cv_edge)

    def _init_rulelabel(self, parent):
        ruletxt = "Last edge generated by:"

        self._rulelabel1 = Label(parent, text=ruletxt, font=self._boldfont)
        self._rulelabel2 = Label(
            parent, width=40, relief="groove", anchor="w", font=self._boldfont
        )
        self._rulelabel1.pack(side="left")
        self._rulelabel2.pack(side="left")
        step = Checkbutton(parent, variable=self._step, text="Step")
        step.pack(side="right")

    def _init_buttons(self, parent):
        frame1 = Frame(parent)
        frame2 = Frame(parent)
        frame1.pack(side="bottom", fill="x")
        frame2.pack(side="top", fill="none")

        Button(
            frame1,
            text="Reset\nParser",
            background="#90c0d0",
            foreground="black",
            command=self.reset,
        ).pack(side="right")
        # Button(frame1, text='Pause',
        #               background='#90c0d0', foreground='black',
        #               command=self.pause).pack(side='left')

        Button(
            frame1,
            text="Top Down\nStrategy",
            background="#90c0d0",
            foreground="black",
            command=self.top_down_strategy,
        ).pack(side="left")
        Button(
            frame1,
            text="Bottom Up\nStrategy",
            background="#90c0d0",
            foreground="black",
            command=self.bottom_up_strategy,
        ).pack(side="left")
        Button(
            frame1,
            text="Bottom Up\nLeft-Corner Strategy",
            background="#90c0d0",
            foreground="black",
            command=self.bottom_up_leftcorner_strategy,
        ).pack(side="left")

        Button(
            frame2,
            text="Top Down Init\nRule",
            background="#90f090",
            foreground="black",
            command=self.top_down_init,
        ).pack(side="left")
        Button(
            frame2,
            text="Top Down Predict\nRule",
            background="#90f090",
            foreground="black",
            command=self.top_down_predict,
        ).pack(side="left")
        Frame(frame2, width=20).pack(side="left")

        Button(
            frame2,
            text="Bottom Up Predict\nRule",
            background="#90f090",
            foreground="black",
            command=self.bottom_up,
        ).pack(side="left")
        Frame(frame2, width=20).pack(side="left")

        Button(
            frame2,
            text="Bottom Up Left-Corner\nPredict Rule",
            background="#90f090",
            foreground="black",
            command=self.bottom_up_leftcorner,
        ).pack(side="left")
        Frame(frame2, width=20).pack(side="left")

        Button(
            frame2,
            text="Fundamental\nRule",
            background="#90f090",
            foreground="black",
            command=self.fundamental,
        ).pack(side="left")

    def _init_bindings(self):
        self._root.bind("<Up>", self._cv.scroll_up)
        self._root.bind("<Down>", self._cv.scroll_down)
        self._root.bind("<Prior>", self._cv.page_up)
        self._root.bind("<Next>", self._cv.page_down)
        self._root.bind("<Control-q>", self.destroy)
        self._root.bind("<Control-x>", self.destroy)
        self._root.bind("<F1>", self.help)

        self._root.bind("<Control-s>", self.save_chart)
        self._root.bind("<Control-o>", self.load_chart)
        self._root.bind("<Control-r>", self.reset)

        self._root.bind("t", self.top_down_strategy)
        self._root.bind("b", self.bottom_up_strategy)
        self._root.bind("c", self.bottom_up_leftcorner_strategy)
        self._root.bind("<space>", self._stop_animation)

        self._root.bind("<Control-g>", self.edit_grammar)
        self._root.bind("<Control-t>", self.edit_sentence)

        # Animation speed control
        self._root.bind("-", lambda e, a=self._animate: a.set(1))
        self._root.bind("=", lambda e, a=self._animate: a.set(2))
        self._root.bind("+", lambda e, a=self._animate: a.set(3))

        # Step control
        self._root.bind("s", lambda e, s=self._step: s.set(not s.get()))

    def _init_menubar(self):
        menubar = Menu(self._root)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Save Chart",
            underline=0,
            command=self.save_chart,
            accelerator="Ctrl-s",
        )
        filemenu.add_command(
            label="Load Chart",
            underline=0,
            command=self.load_chart,
            accelerator="Ctrl-o",
        )
        filemenu.add_command(
            label="Reset Chart", underline=0, command=self.reset, accelerator="Ctrl-r"
        )
        filemenu.add_separator()
        filemenu.add_command(label="Save Grammar", command=self.save_grammar)
        filemenu.add_command(label="Load Grammar", command=self.load_grammar)
        filemenu.add_separator()
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(
            label="Edit Grammar",
            underline=5,
            command=self.edit_grammar,
            accelerator="Ctrl-g",
        )
        editmenu.add_command(
            label="Edit Text",
            underline=5,
            command=self.edit_sentence,
            accelerator="Ctrl-t",
        )
        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_command(
            label="Chart Matrix", underline=6, command=self.view_matrix
        )
        viewmenu.add_command(label="Results", underline=0, command=self.view_results)
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        rulemenu = Menu(menubar, tearoff=0)
        rulemenu.add_command(
            label="Top Down Strategy",
            underline=0,
            command=self.top_down_strategy,
            accelerator="t",
        )
        rulemenu.add_command(
            label="Bottom Up Strategy",
            underline=0,
            command=self.bottom_up_strategy,
            accelerator="b",
        )
        rulemenu.add_command(
            label="Bottom Up Left-Corner Strategy",
            underline=0,
            command=self.bottom_up_leftcorner_strategy,
            accelerator="c",
        )
        rulemenu.add_separator()
        rulemenu.add_command(label="Bottom Up Rule", command=self.bottom_up)
        rulemenu.add_command(
            label="Bottom Up Left-Corner Rule", command=self.bottom_up_leftcorner
        )
        rulemenu.add_command(label="Top Down Init Rule", command=self.top_down_init)
        rulemenu.add_command(
            label="Top Down Predict Rule", command=self.top_down_predict
        )
        rulemenu.add_command(label="Fundamental Rule", command=self.fundamental)
        menubar.add_cascade(label="Apply", underline=0, menu=rulemenu)

        animatemenu = Menu(menubar, tearoff=0)
        animatemenu.add_checkbutton(
            label="Step", underline=0, variable=self._step, accelerator="s"
        )
        animatemenu.add_separator()
        animatemenu.add_radiobutton(
            label="No Animation", underline=0, variable=self._animate, value=0
        )
        animatemenu.add_radiobutton(
            label="Slow Animation",
            underline=0,
            variable=self._animate,
            value=1,
            accelerator="-",
        )
        animatemenu.add_radiobutton(
            label="Normal Animation",
            underline=0,
            variable=self._animate,
            value=2,
            accelerator="=",
        )
        animatemenu.add_radiobutton(
            label="Fast Animation",
            underline=0,
            variable=self._animate,
            value=3,
            accelerator="+",
        )
        menubar.add_cascade(label="Animate", underline=1, menu=animatemenu)

        zoommenu = Menu(menubar, tearoff=0)
        zoommenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="Zoom", underline=0, menu=zoommenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        helpmenu.add_command(
            label="Instructions", underline=0, command=self.help, accelerator="F1"
        )
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        self._root.config(menu=menubar)

    # ////////////////////////////////////////////////////////////
    # Selection Handling
    # ////////////////////////////////////////////////////////////

    def _click_cv_edge(self, edge):
        if edge != self._selection:
            # Clicking on a new edge selects it.
            self._select_edge(edge)
        else:
            # Repeated clicks on one edge cycle its trees.
            self._cv.cycle_tree()
            # [XX] this can get confused if animation is running
            # faster than the callbacks...

    def _select_matrix_edge(self, edge):
        self._select_edge(edge)
        self._cv.view_edge(edge)

    def _select_edge(self, edge):
        self._selection = edge
        # Update the chart view.
        self._cv.markonly_edge(edge, "#f00")
        self._cv.draw_tree(edge)
        # Update the matrix view.
        if self._matrix:
            self._matrix.markonly_edge(edge)
        if self._matrix:
            self._matrix.view_edge(edge)

    def _deselect_edge(self):
        self._selection = None
        # Update the chart view.
        self._cv.unmark_edge()
        self._cv.erase_tree()
        # Update the matrix view
        if self._matrix:
            self._matrix.unmark_edge()

    def _show_new_edge(self, edge):
        self._display_rule(self._cp.current_chartrule())
        # Update the chart view.
        self._cv.update()
        self._cv.draw_tree(edge)
        self._cv.markonly_edge(edge, "#0df")
        self._cv.view_edge(edge)
        # Update the matrix view.
        if self._matrix:
            self._matrix.update()
        if self._matrix:
            self._matrix.markonly_edge(edge)
        if self._matrix:
            self._matrix.view_edge(edge)
        # Update the results view.
        if self._results:
            self._results.update(edge)

    # ////////////////////////////////////////////////////////////
    # Help/usage
    # ////////////////////////////////////////////////////////////

    def help(self, *e):
        self._animating = 0
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._root,
                "Help: Chart Parser Application",
                (__doc__ or "").strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._root,
                "Help: Chart Parser Application",
                (__doc__ or "").strip(),
                width=75,
            )

    def about(self, *e):
        ABOUT = "NLTK Chart Parser Application\n" + "Written by Edward Loper"
        showinfo("About: Chart Parser Application", ABOUT)

    # ////////////////////////////////////////////////////////////
    # File Menu
    # ////////////////////////////////////////////////////////////

    CHART_FILE_TYPES = [("Pickle file", ".pickle"), ("All files", "*")]
    GRAMMAR_FILE_TYPES = [
        ("Plaintext grammar file", ".cfg"),
        ("Pickle file", ".pickle"),
        ("All files", "*"),
    ]

    def load_chart(self, *args):
        "Load a chart from a pickle file"
        filename = askopenfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            with open(filename, "rb") as infile:
                chart = pickle.load(infile)
            self._chart = chart
            self._cv.update(chart)
            if self._matrix:
                self._matrix.set_chart(chart)
            if self._matrix:
                self._matrix.deselect_cell()
            if self._results:
                self._results.set_chart(chart)
            self._cp.set_chart(chart)
        except Exception as e:
            raise
            showerror("Error Loading Chart", "Unable to open file: %r" % filename)

    def save_chart(self, *args):
        "Save a chart to a pickle file"
        filename = asksaveasfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            with open(filename, "wb") as outfile:
                pickle.dump(self._chart, outfile)
        except Exception as e:
            raise
            showerror("Error Saving Chart", "Unable to open file: %r" % filename)

    def load_grammar(self, *args):
        "Load a grammar from a pickle file"
        filename = askopenfilename(
            filetypes=self.GRAMMAR_FILE_TYPES, defaultextension=".cfg"
        )
        if not filename:
            return
        try:
            if filename.endswith(".pickle"):
                with open(filename, "rb") as infile:
                    grammar = pickle.load(infile)
            else:
                with open(filename) as infile:
                    grammar = CFG.fromstring(infile.read())
            self.set_grammar(grammar)
        except Exception as e:
            showerror("Error Loading Grammar", "Unable to open file: %r" % filename)

    def save_grammar(self, *args):
        filename = asksaveasfilename(
            filetypes=self.GRAMMAR_FILE_TYPES, defaultextension=".cfg"
        )
        if not filename:
            return
        try:
            if filename.endswith(".pickle"):
                with open(filename, "wb") as outfile:
                    pickle.dump((self._chart, self._tokens), outfile)
            else:
                with open(filename, "w") as outfile:
                    prods = self._grammar.productions()
                    start = [p for p in prods if p.lhs() == self._grammar.start()]
                    rest = [p for p in prods if p.lhs() != self._grammar.start()]
                    for prod in start:
                        outfile.write("%s\n" % prod)
                    for prod in rest:
                        outfile.write("%s\n" % prod)
        except Exception as e:
            showerror("Error Saving Grammar", "Unable to open file: %r" % filename)

    def reset(self, *args):
        self._animating = 0
        self._reset_parser()
        self._cv.update(self._chart)
        if self._matrix:
            self._matrix.set_chart(self._chart)
        if self._matrix:
            self._matrix.deselect_cell()
        if self._results:
            self._results.set_chart(self._chart)

    # ////////////////////////////////////////////////////////////
    # Edit
    # ////////////////////////////////////////////////////////////

    def edit_grammar(self, *e):
        CFGEditor(self._root, self._grammar, self.set_grammar)

    def set_grammar(self, grammar):
        self._grammar = grammar
        self._cp.set_grammar(grammar)
        if self._results:
            self._results.set_grammar(grammar)

    def edit_sentence(self, *e):
        sentence = " ".join(self._tokens)
        title = "Edit Text"
        instr = "Enter a new sentence to parse."
        EntryDialog(self._root, sentence, instr, self.set_sentence, title)

    def set_sentence(self, sentence):
        self._tokens = list(sentence.split())
        self.reset()

    # ////////////////////////////////////////////////////////////
    # View Menu
    # ////////////////////////////////////////////////////////////

    def view_matrix(self, *e):
        if self._matrix is not None:
            self._matrix.destroy()
        self._matrix = ChartMatrixView(self._root, self._chart)
        self._matrix.add_callback("select", self._select_matrix_edge)

    def view_results(self, *e):
        if self._results is not None:
            self._results.destroy()
        self._results = ChartResultsView(self._root, self._chart, self._grammar)

    # ////////////////////////////////////////////////////////////
    # Zoom Menu
    # ////////////////////////////////////////////////////////////

    def resize(self):
        self._animating = 0
        self.set_font_size(self._size.get())

    def set_font_size(self, size):
        self._cv.set_font_size(size)
        self._font.configure(size=-abs(size))
        self._boldfont.configure(size=-abs(size))
        self._sysfont.configure(size=-abs(size))

    def get_font_size(self):
        return abs(self._size.get())

    # ////////////////////////////////////////////////////////////
    # Parsing
    # ////////////////////////////////////////////////////////////

    def apply_strategy(self, strategy, edge_strategy=None):
        # If we're animating, then stop.
        if self._animating:
            self._animating = 0
            return

        # Clear the rule display & mark.
        self._display_rule(None)
        # self._cv.unmark_edge()

        if self._step.get():
            selection = self._selection
            if (selection is not None) and (edge_strategy is not None):
                # Apply the given strategy to the selected edge.
                self._cp.set_strategy([edge_strategy(selection)])
                newedge = self._apply_strategy()

                # If it failed, then clear the selection.
                if newedge is None:
                    self._cv.unmark_edge()
                    self._selection = None
            else:
                self._cp.set_strategy(strategy)
                self._apply_strategy()

        else:
            self._cp.set_strategy(strategy)
            if self._animate.get():
                self._animating = 1
                self._animate_strategy()
            else:
                for edge in self._cpstep:
                    if edge is None:
                        break
                self._cv.update()
                if self._matrix:
                    self._matrix.update()
                if self._results:
                    self._results.update()

    def _stop_animation(self, *e):
        self._animating = 0

    def _animate_strategy(self, speed=1):
        if self._animating == 0:
            return
        if self._apply_strategy() is not None:
            if self._animate.get() == 0 or self._step.get() == 1:
                return
            if self._animate.get() == 1:
                self._root.after(3000, self._animate_strategy)
            elif self._animate.get() == 2:
                self._root.after(1000, self._animate_strategy)
            else:
                self._root.after(20, self._animate_strategy)

    def _apply_strategy(self):
        new_edge = next(self._cpstep)

        if new_edge is not None:
            self._show_new_edge(new_edge)
        return new_edge

    def _display_rule(self, rule):
        if rule is None:
            self._rulelabel2["text"] = ""
        else:
            name = str(rule)
            self._rulelabel2["text"] = name
            size = self._cv.get_font_size()

    # ////////////////////////////////////////////////////////////
    # Parsing Strategies
    # ////////////////////////////////////////////////////////////

    # Basic rules:
    _TD_INIT = [TopDownInitRule()]
    _TD_PREDICT = [TopDownPredictRule()]
    _BU_RULE = [BottomUpPredictRule()]
    _BU_LC_RULE = [BottomUpPredictCombineRule()]
    _FUNDAMENTAL = [SingleEdgeFundamentalRule()]

    # Complete strategies:
    _TD_STRATEGY = _TD_INIT + _TD_PREDICT + _FUNDAMENTAL
    _BU_STRATEGY = _BU_RULE + _FUNDAMENTAL
    _BU_LC_STRATEGY = _BU_LC_RULE + _FUNDAMENTAL

    # Button callback functions:
    def top_down_init(self, *e):
        self.apply_strategy(self._TD_INIT, None)

    def top_down_predict(self, *e):
        self.apply_strategy(self._TD_PREDICT, TopDownPredictEdgeRule)

    def bottom_up(self, *e):
        self.apply_strategy(self._BU_RULE, BottomUpEdgeRule)

    def bottom_up_leftcorner(self, *e):
        self.apply_strategy(self._BU_LC_RULE, BottomUpLeftCornerEdgeRule)

    def fundamental(self, *e):
        self.apply_strategy(self._FUNDAMENTAL, FundamentalEdgeRule)

    def bottom_up_strategy(self, *e):
        self.apply_strategy(self._BU_STRATEGY, BottomUpEdgeRule)

    def bottom_up_leftcorner_strategy(self, *e):
        self.apply_strategy(self._BU_LC_STRATEGY, BottomUpLeftCornerEdgeRule)

    def top_down_strategy(self, *e):
        self.apply_strategy(self._TD_STRATEGY, TopDownPredictEdgeRule)


def app():
    grammar = CFG.fromstring(
        """
    # Grammatical productions.
        S -> NP VP
        VP -> VP PP | V NP | V
        NP -> Det N | NP PP
        PP -> P NP
    # Lexical productions.
        NP -> 'John' | 'I'
        Det -> 'the' | 'my' | 'a'
        N -> 'dog' | 'cookie' | 'table' | 'cake' | 'fork'
        V -> 'ate' | 'saw'
        P -> 'on' | 'under' | 'with'
    """
    )

    sent = "John ate the cake on the table with a fork"
    sent = "John ate the cake on the table"
    tokens = list(sent.split())

    print("grammar= (")
    for rule in grammar.productions():
        print(("    ", repr(rule) + ","))
    print(")")
    print("tokens = %r" % tokens)
    print('Calling "ChartParserApp(grammar, tokens)"...')
    ChartParserApp(grammar, tokens).mainloop()


if __name__ == "__main__":
    app()

    # Chart comparer:
    # charts = ['/tmp/earley.pickle',
    #          '/tmp/topdown.pickle',
    #          '/tmp/bottomup.pickle']
    # ChartComparer(*charts).mainloop()

    # import profile
    # profile.run('demo2()', '/tmp/profile.out')
    # import pstats
    # p = pstats.Stats('/tmp/profile.out')
    # p.strip_dirs().sort_stats('time', 'cum').print_stats(60)
    # p.strip_dirs().sort_stats('cum', 'time').print_stats(60)

__all__ = ["app"]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\chartparser_app.py ===
# Natural Language Toolkit: Chart Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Jean Mark Gawron <gawron@mail.sdsu.edu>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring chart parsing.

Chart parsing is a flexible parsing algorithm that uses a data
structure called a "chart" to record hypotheses about syntactic
constituents.  Each hypothesis is represented by a single "edge" on
the chart.  A set of "chart rules" determine when new edges can be
added to the chart.  This set of rules controls the overall behavior
of the parser (e.g. whether it parses top-down or bottom-up).

The chart parsing tool demonstrates the process of parsing a single
sentence, with a given grammar and lexicon.  Its display is divided
into three sections: the bottom section displays the chart; the middle
section displays the sentence; and the top section displays the
partial syntax tree corresponding to the selected edge.  Buttons along
the bottom of the window are used to control the execution of the
algorithm.

The chart parsing tool allows for flexible control of the parsing
algorithm.  At each step of the algorithm, you can select which rule
or strategy you wish to apply.  This allows you to experiment with
mixing different strategies (e.g. top-down and bottom-up).  You can
exercise fine-grained control over the algorithm by selecting which
edge you wish to apply a rule to.
"""

# At some point, we should rewrite this tool to use the new canvas
# widget system.


import os.path
import pickle
from tkinter import (
    Button,
    Canvas,
    Checkbutton,
    Frame,
    IntVar,
    Label,
    Menu,
    Scrollbar,
    Tk,
    Toplevel,
)
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.font import Font
from tkinter.messagebox import showerror, showinfo

from nltk.draw import CFGEditor, TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import (
    CanvasFrame,
    ColorizedList,
    EntryDialog,
    MutableOptionMenu,
    ShowText,
    SymbolWidget,
)
from nltk.grammar import CFG, Nonterminal
from nltk.parse.chart import (
    BottomUpPredictCombineRule,
    BottomUpPredictRule,
    Chart,
    LeafEdge,
    LeafInitRule,
    SingleEdgeFundamentalRule,
    SteppingChartParser,
    TopDownInitRule,
    TopDownPredictRule,
    TreeEdge,
)
from nltk.tree import Tree
from nltk.util import in_idle

# Known bug: ChartView doesn't handle edges generated by epsilon
# productions (e.g., [Production: PP -> ]) very well.

#######################################################################
# Edge List
#######################################################################


class EdgeList(ColorizedList):
    ARROW = SymbolWidget.SYMBOLS["rightarrow"]

    def _init_colortags(self, textwidget, options):
        textwidget.tag_config("terminal", foreground="#006000")
        textwidget.tag_config("arrow", font="symbol", underline="0")
        textwidget.tag_config("dot", foreground="#000000")
        textwidget.tag_config(
            "nonterminal", foreground="blue", font=("helvetica", -12, "bold")
        )

    def _item_repr(self, item):
        contents = []
        contents.append(("%s\t" % item.lhs(), "nonterminal"))
        contents.append((self.ARROW, "arrow"))
        for i, elt in enumerate(item.rhs()):
            if i == item.dot():
                contents.append((" *", "dot"))
            if isinstance(elt, Nonterminal):
                contents.append((" %s" % elt.symbol(), "nonterminal"))
            else:
                contents.append((" %r" % elt, "terminal"))
        if item.is_complete():
            contents.append((" *", "dot"))
        return contents


#######################################################################
# Chart Matrix View
#######################################################################


class ChartMatrixView:
    """
    A view of a chart that displays the contents of the corresponding matrix.
    """

    def __init__(
        self, parent, chart, toplevel=True, title="Chart Matrix", show_numedges=False
    ):
        self._chart = chart
        self._cells = []
        self._marks = []

        self._selected_cell = None

        if toplevel:
            self._root = Toplevel(parent)
            self._root.title(title)
            self._root.bind("<Control-q>", self.destroy)
            self._init_quit(self._root)
        else:
            self._root = Frame(parent)

        self._init_matrix(self._root)
        self._init_list(self._root)
        if show_numedges:
            self._init_numedges(self._root)
        else:
            self._numedges_label = None

        self._callbacks = {}

        self._num_edges = 0

        self.draw()

    def _init_quit(self, root):
        quit = Button(root, text="Quit", command=self.destroy)
        quit.pack(side="bottom", expand=0, fill="none")

    def _init_matrix(self, root):
        cframe = Frame(root, border=2, relief="sunken")
        cframe.pack(expand=0, fill="none", padx=1, pady=3, side="top")
        self._canvas = Canvas(cframe, width=200, height=200, background="white")
        self._canvas.pack(expand=0, fill="none")

    def _init_numedges(self, root):
        self._numedges_label = Label(root, text="0 edges")
        self._numedges_label.pack(expand=0, fill="none", side="top")

    def _init_list(self, root):
        self._list = EdgeList(root, [], width=20, height=5)
        self._list.pack(side="top", expand=1, fill="both", pady=3)

        def cb(edge, self=self):
            self._fire_callbacks("select", edge)

        self._list.add_callback("select", cb)
        self._list.focus()

    def destroy(self, *e):
        if self._root is None:
            return
        try:
            self._root.destroy()
        except:
            pass
        self._root = None

    def set_chart(self, chart):
        if chart is not self._chart:
            self._chart = chart
            self._num_edges = 0
            self.draw()

    def update(self):
        if self._root is None:
            return

        # Count the edges in each cell
        N = len(self._cells)
        cell_edges = [[0 for i in range(N)] for j in range(N)]
        for edge in self._chart:
            cell_edges[edge.start()][edge.end()] += 1

        # Color the cells correspondingly.
        for i in range(N):
            for j in range(i, N):
                if cell_edges[i][j] == 0:
                    color = "gray20"
                else:
                    color = "#00{:02x}{:02x}".format(
                        min(255, 50 + 128 * cell_edges[i][j] / 10),
                        max(0, 128 - 128 * cell_edges[i][j] / 10),
                    )
                cell_tag = self._cells[i][j]
                self._canvas.itemconfig(cell_tag, fill=color)
                if (i, j) == self._selected_cell:
                    self._canvas.itemconfig(cell_tag, outline="#00ffff", width=3)
                    self._canvas.tag_raise(cell_tag)
                else:
                    self._canvas.itemconfig(cell_tag, outline="black", width=1)

        # Update the edge list.
        edges = list(self._chart.select(span=self._selected_cell))
        self._list.set(edges)

        # Update our edge count.
        self._num_edges = self._chart.num_edges()
        if self._numedges_label is not None:
            self._numedges_label["text"] = "%d edges" % self._num_edges

    def activate(self):
        self._canvas.itemconfig("inactivebox", state="hidden")
        self.update()

    def inactivate(self):
        self._canvas.itemconfig("inactivebox", state="normal")
        self.update()

    def add_callback(self, event, func):
        self._callbacks.setdefault(event, {})[func] = 1

    def remove_callback(self, event, func=None):
        if func is None:
            del self._callbacks[event]
        else:
            try:
                del self._callbacks[event][func]
            except:
                pass

    def _fire_callbacks(self, event, *args):
        if event not in self._callbacks:
            return
        for cb_func in list(self._callbacks[event].keys()):
            cb_func(*args)

    def select_cell(self, i, j):
        if self._root is None:
            return

        # If the cell is already selected (and the chart contents
        # haven't changed), then do nothing.
        if (i, j) == self._selected_cell and self._chart.num_edges() == self._num_edges:
            return

        self._selected_cell = (i, j)
        self.update()

        # Fire the callback.
        self._fire_callbacks("select_cell", i, j)

    def deselect_cell(self):
        if self._root is None:
            return
        self._selected_cell = None
        self._list.set([])
        self.update()

    def _click_cell(self, i, j):
        if self._selected_cell == (i, j):
            self.deselect_cell()
        else:
            self.select_cell(i, j)

    def view_edge(self, edge):
        self.select_cell(*edge.span())
        self._list.view(edge)

    def mark_edge(self, edge):
        if self._root is None:
            return
        self.select_cell(*edge.span())
        self._list.mark(edge)

    def unmark_edge(self, edge=None):
        if self._root is None:
            return
        self._list.unmark(edge)

    def markonly_edge(self, edge):
        if self._root is None:
            return
        self.select_cell(*edge.span())
        self._list.markonly(edge)

    def draw(self):
        if self._root is None:
            return
        LEFT_MARGIN = BOT_MARGIN = 15
        TOP_MARGIN = 5
        c = self._canvas
        c.delete("all")
        N = self._chart.num_leaves() + 1
        dx = (int(c["width"]) - LEFT_MARGIN) / N
        dy = (int(c["height"]) - TOP_MARGIN - BOT_MARGIN) / N

        c.delete("all")

        # Labels and dotted lines
        for i in range(N):
            c.create_text(
                LEFT_MARGIN - 2, i * dy + dy / 2 + TOP_MARGIN, text=repr(i), anchor="e"
            )
            c.create_text(
                i * dx + dx / 2 + LEFT_MARGIN,
                N * dy + TOP_MARGIN + 1,
                text=repr(i),
                anchor="n",
            )
            c.create_line(
                LEFT_MARGIN,
                dy * (i + 1) + TOP_MARGIN,
                dx * N + LEFT_MARGIN,
                dy * (i + 1) + TOP_MARGIN,
                dash=".",
            )
            c.create_line(
                dx * i + LEFT_MARGIN,
                TOP_MARGIN,
                dx * i + LEFT_MARGIN,
                dy * N + TOP_MARGIN,
                dash=".",
            )

        # A box around the whole thing
        c.create_rectangle(
            LEFT_MARGIN, TOP_MARGIN, LEFT_MARGIN + dx * N, dy * N + TOP_MARGIN, width=2
        )

        # Cells
        self._cells = [[None for i in range(N)] for j in range(N)]
        for i in range(N):
            for j in range(i, N):
                t = c.create_rectangle(
                    j * dx + LEFT_MARGIN,
                    i * dy + TOP_MARGIN,
                    (j + 1) * dx + LEFT_MARGIN,
                    (i + 1) * dy + TOP_MARGIN,
                    fill="gray20",
                )
                self._cells[i][j] = t

                def cb(event, self=self, i=i, j=j):
                    self._click_cell(i, j)

                c.tag_bind(t, "<Button-1>", cb)

        # Inactive box
        xmax, ymax = int(c["width"]), int(c["height"])
        t = c.create_rectangle(
            -100,
            -100,
            xmax + 100,
            ymax + 100,
            fill="gray50",
            state="hidden",
            tag="inactivebox",
        )
        c.tag_lower(t)

        # Update the cells.
        self.update()

    def pack(self, *args, **kwargs):
        self._root.pack(*args, **kwargs)


#######################################################################
# Chart Results View
#######################################################################


class ChartResultsView:
    def __init__(self, parent, chart, grammar, toplevel=True):
        self._chart = chart
        self._grammar = grammar
        self._trees = []
        self._y = 10
        self._treewidgets = []
        self._selection = None
        self._selectbox = None

        if toplevel:
            self._root = Toplevel(parent)
            self._root.title("Chart Parser Application: Results")
            self._root.bind("<Control-q>", self.destroy)
        else:
            self._root = Frame(parent)

        # Buttons
        if toplevel:
            buttons = Frame(self._root)
            buttons.pack(side="bottom", expand=0, fill="x")
            Button(buttons, text="Quit", command=self.destroy).pack(side="right")
            Button(buttons, text="Print All", command=self.print_all).pack(side="left")
            Button(buttons, text="Print Selection", command=self.print_selection).pack(
                side="left"
            )

        # Canvas frame.
        self._cframe = CanvasFrame(self._root, closeenough=20)
        self._cframe.pack(side="top", expand=1, fill="both")

        # Initial update
        self.update()

    def update(self, edge=None):
        if self._root is None:
            return
        # If the edge isn't a parse edge, do nothing.
        if edge is not None:
            if edge.lhs() != self._grammar.start():
                return
            if edge.span() != (0, self._chart.num_leaves()):
                return

        for parse in self._chart.parses(self._grammar.start()):
            if parse not in self._trees:
                self._add(parse)

    def _add(self, parse):
        # Add it to self._trees.
        self._trees.append(parse)

        # Create a widget for it.
        c = self._cframe.canvas()
        treewidget = tree_to_treesegment(c, parse)

        # Add it to the canvas frame.
        self._treewidgets.append(treewidget)
        self._cframe.add_widget(treewidget, 10, self._y)

        # Register callbacks.
        treewidget.bind_click(self._click)

        # Update y.
        self._y = treewidget.bbox()[3] + 10

    def _click(self, widget):
        c = self._cframe.canvas()
        if self._selection is not None:
            c.delete(self._selectbox)
        self._selection = widget
        (x1, y1, x2, y2) = widget.bbox()
        self._selectbox = c.create_rectangle(x1, y1, x2, y2, width=2, outline="#088")

    def _color(self, treewidget, color):
        treewidget.label()["color"] = color
        for child in treewidget.subtrees():
            if isinstance(child, TreeSegmentWidget):
                self._color(child, color)
            else:
                child["color"] = color

    def print_all(self, *e):
        if self._root is None:
            return
        self._cframe.print_to_file()

    def print_selection(self, *e):
        if self._root is None:
            return
        if self._selection is None:
            showerror("Print Error", "No tree selected")
        else:
            c = self._cframe.canvas()
            for widget in self._treewidgets:
                if widget is not self._selection:
                    self._cframe.destroy_widget(widget)
            c.delete(self._selectbox)
            (x1, y1, x2, y2) = self._selection.bbox()
            self._selection.move(10 - x1, 10 - y1)
            c["scrollregion"] = f"0 0 {x2 - x1 + 20} {y2 - y1 + 20}"
            self._cframe.print_to_file()

            # Restore our state.
            self._treewidgets = [self._selection]
            self.clear()
            self.update()

    def clear(self):
        if self._root is None:
            return
        for treewidget in self._treewidgets:
            self._cframe.destroy_widget(treewidget)
        self._trees = []
        self._treewidgets = []
        if self._selection is not None:
            self._cframe.canvas().delete(self._selectbox)
        self._selection = None
        self._y = 10

    def set_chart(self, chart):
        self.clear()
        self._chart = chart
        self.update()

    def set_grammar(self, grammar):
        self.clear()
        self._grammar = grammar
        self.update()

    def destroy(self, *e):
        if self._root is None:
            return
        try:
            self._root.destroy()
        except:
            pass
        self._root = None

    def pack(self, *args, **kwargs):
        self._root.pack(*args, **kwargs)


#######################################################################
# Chart Comparer
#######################################################################


class ChartComparer:
    """

    :ivar _root: The root window

    :ivar _charts: A dictionary mapping names to charts.  When
        charts are loaded, they are added to this dictionary.

    :ivar _left_chart: The left ``Chart``.
    :ivar _left_name: The name ``_left_chart`` (derived from filename)
    :ivar _left_matrix: The ``ChartMatrixView`` for ``_left_chart``
    :ivar _left_selector: The drop-down ``MutableOptionsMenu`` used
          to select ``_left_chart``.

    :ivar _right_chart: The right ``Chart``.
    :ivar _right_name: The name ``_right_chart`` (derived from filename)
    :ivar _right_matrix: The ``ChartMatrixView`` for ``_right_chart``
    :ivar _right_selector: The drop-down ``MutableOptionsMenu`` used
          to select ``_right_chart``.

    :ivar _out_chart: The out ``Chart``.
    :ivar _out_name: The name ``_out_chart`` (derived from filename)
    :ivar _out_matrix: The ``ChartMatrixView`` for ``_out_chart``
    :ivar _out_label: The label for ``_out_chart``.

    :ivar _op_label: A Label containing the most recent operation.
    """

    _OPSYMBOL = {
        "-": "-",
        "and": SymbolWidget.SYMBOLS["intersection"],
        "or": SymbolWidget.SYMBOLS["union"],
    }

    def __init__(self, *chart_filenames):
        # This chart is displayed when we don't have a value (eg
        # before any chart is loaded).
        faketok = [""] * 8
        self._emptychart = Chart(faketok)

        # The left & right charts start out empty.
        self._left_name = "None"
        self._right_name = "None"
        self._left_chart = self._emptychart
        self._right_chart = self._emptychart

        # The charts that have been loaded.
        self._charts = {"None": self._emptychart}

        # The output chart.
        self._out_chart = self._emptychart

        # The most recent operation
        self._operator = None

        # Set up the root window.
        self._root = Tk()
        self._root.title("Chart Comparison")
        self._root.bind("<Control-q>", self.destroy)
        self._root.bind("<Control-x>", self.destroy)

        # Initialize all widgets, etc.
        self._init_menubar(self._root)
        self._init_chartviews(self._root)
        self._init_divider(self._root)
        self._init_buttons(self._root)
        self._init_bindings(self._root)

        # Load any specified charts.
        for filename in chart_filenames:
            self.load_chart(filename)

    def destroy(self, *e):
        if self._root is None:
            return
        try:
            self._root.destroy()
        except:
            pass
        self._root = None

    def mainloop(self, *args, **kwargs):
        return
        self._root.mainloop(*args, **kwargs)

    # ////////////////////////////////////////////////////////////
    # Initialization
    # ////////////////////////////////////////////////////////////

    def _init_menubar(self, root):
        menubar = Menu(root)

        # File menu
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Load Chart",
            accelerator="Ctrl-o",
            underline=0,
            command=self.load_chart_dialog,
        )
        filemenu.add_command(
            label="Save Output",
            accelerator="Ctrl-s",
            underline=0,
            command=self.save_chart_dialog,
        )
        filemenu.add_separator()
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        # Compare menu
        opmenu = Menu(menubar, tearoff=0)
        opmenu.add_command(
            label="Intersection", command=self._intersection, accelerator="+"
        )
        opmenu.add_command(label="Union", command=self._union, accelerator="*")
        opmenu.add_command(
            label="Difference", command=self._difference, accelerator="-"
        )
        opmenu.add_separator()
        opmenu.add_command(label="Swap Charts", command=self._swapcharts)
        menubar.add_cascade(label="Compare", underline=0, menu=opmenu)

        # Add the menu
        self._root.config(menu=menubar)

    def _init_divider(self, root):
        divider = Frame(root, border=2, relief="sunken")
        divider.pack(side="top", fill="x", ipady=2)

    def _init_chartviews(self, root):
        opfont = ("symbol", -36)  # Font for operator.
        eqfont = ("helvetica", -36)  # Font for equals sign.

        frame = Frame(root, background="#c0c0c0")
        frame.pack(side="top", expand=1, fill="both")

        # The left matrix.
        cv1_frame = Frame(frame, border=3, relief="groove")
        cv1_frame.pack(side="left", padx=8, pady=7, expand=1, fill="both")
        self._left_selector = MutableOptionMenu(
            cv1_frame, list(self._charts.keys()), command=self._select_left
        )
        self._left_selector.pack(side="top", pady=5, fill="x")
        self._left_matrix = ChartMatrixView(
            cv1_frame, self._emptychart, toplevel=False, show_numedges=True
        )
        self._left_matrix.pack(side="bottom", padx=5, pady=5, expand=1, fill="both")
        self._left_matrix.add_callback("select", self.select_edge)
        self._left_matrix.add_callback("select_cell", self.select_cell)
        self._left_matrix.inactivate()

        # The operator.
        self._op_label = Label(
            frame, text=" ", width=3, background="#c0c0c0", font=opfont
        )
        self._op_label.pack(side="left", padx=5, pady=5)

        # The right matrix.
        cv2_frame = Frame(frame, border=3, relief="groove")
        cv2_frame.pack(side="left", padx=8, pady=7, expand=1, fill="both")
        self._right_selector = MutableOptionMenu(
            cv2_frame, list(self._charts.keys()), command=self._select_right
        )
        self._right_selector.pack(side="top", pady=5, fill="x")
        self._right_matrix = ChartMatrixView(
            cv2_frame, self._emptychart, toplevel=False, show_numedges=True
        )
        self._right_matrix.pack(side="bottom", padx=5, pady=5, expand=1, fill="both")
        self._right_matrix.add_callback("select", self.select_edge)
        self._right_matrix.add_callback("select_cell", self.select_cell)
        self._right_matrix.inactivate()

        # The equals sign
        Label(frame, text="=", width=3, background="#c0c0c0", font=eqfont).pack(
            side="left", padx=5, pady=5
        )

        # The output matrix.
        out_frame = Frame(frame, border=3, relief="groove")
        out_frame.pack(side="left", padx=8, pady=7, expand=1, fill="both")
        self._out_label = Label(out_frame, text="Output")
        self._out_label.pack(side="top", pady=9)
        self._out_matrix = ChartMatrixView(
            out_frame, self._emptychart, toplevel=False, show_numedges=True
        )
        self._out_matrix.pack(side="bottom", padx=5, pady=5, expand=1, fill="both")
        self._out_matrix.add_callback("select", self.select_edge)
        self._out_matrix.add_callback("select_cell", self.select_cell)
        self._out_matrix.inactivate()

    def _init_buttons(self, root):
        buttons = Frame(root)
        buttons.pack(side="bottom", pady=5, fill="x", expand=0)
        Button(buttons, text="Intersection", command=self._intersection).pack(
            side="left"
        )
        Button(buttons, text="Union", command=self._union).pack(side="left")
        Button(buttons, text="Difference", command=self._difference).pack(side="left")
        Frame(buttons, width=20).pack(side="left")
        Button(buttons, text="Swap Charts", command=self._swapcharts).pack(side="left")

        Button(buttons, text="Detach Output", command=self._detach_out).pack(
            side="right"
        )

    def _init_bindings(self, root):
        # root.bind('<Control-s>', self.save_chart)
        root.bind("<Control-o>", self.load_chart_dialog)
        # root.bind('<Control-r>', self.reset)

    # ////////////////////////////////////////////////////////////
    # Input Handling
    # ////////////////////////////////////////////////////////////

    def _select_left(self, name):
        self._left_name = name
        self._left_chart = self._charts[name]
        self._left_matrix.set_chart(self._left_chart)
        if name == "None":
            self._left_matrix.inactivate()
        self._apply_op()

    def _select_right(self, name):
        self._right_name = name
        self._right_chart = self._charts[name]
        self._right_matrix.set_chart(self._right_chart)
        if name == "None":
            self._right_matrix.inactivate()
        self._apply_op()

    def _apply_op(self):
        if self._operator == "-":
            self._difference()
        elif self._operator == "or":
            self._union()
        elif self._operator == "and":
            self._intersection()

    # ////////////////////////////////////////////////////////////
    # File
    # ////////////////////////////////////////////////////////////
    CHART_FILE_TYPES = [("Pickle file", ".pickle"), ("All files", "*")]

    def save_chart_dialog(self, *args):
        filename = asksaveasfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            with open(filename, "wb") as outfile:
                pickle.dump(self._out_chart, outfile)
        except Exception as e:
            showerror("Error Saving Chart", f"Unable to open file: {filename!r}\n{e}")

    def load_chart_dialog(self, *args):
        filename = askopenfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            self.load_chart(filename)
        except Exception as e:
            showerror("Error Loading Chart", f"Unable to open file: {filename!r}\n{e}")

    def load_chart(self, filename):
        with open(filename, "rb") as infile:
            chart = pickle.load(infile)
        name = os.path.basename(filename)
        if name.endswith(".pickle"):
            name = name[:-7]
        if name.endswith(".chart"):
            name = name[:-6]
        self._charts[name] = chart
        self._left_selector.add(name)
        self._right_selector.add(name)

        # If either left_matrix or right_matrix is empty, then
        # display the new chart.
        if self._left_chart is self._emptychart:
            self._left_selector.set(name)
        elif self._right_chart is self._emptychart:
            self._right_selector.set(name)

    def _update_chartviews(self):
        self._left_matrix.update()
        self._right_matrix.update()
        self._out_matrix.update()

    # ////////////////////////////////////////////////////////////
    # Selection
    # ////////////////////////////////////////////////////////////

    def select_edge(self, edge):
        if edge in self._left_chart:
            self._left_matrix.markonly_edge(edge)
        else:
            self._left_matrix.unmark_edge()
        if edge in self._right_chart:
            self._right_matrix.markonly_edge(edge)
        else:
            self._right_matrix.unmark_edge()
        if edge in self._out_chart:
            self._out_matrix.markonly_edge(edge)
        else:
            self._out_matrix.unmark_edge()

    def select_cell(self, i, j):
        self._left_matrix.select_cell(i, j)
        self._right_matrix.select_cell(i, j)
        self._out_matrix.select_cell(i, j)

    # ////////////////////////////////////////////////////////////
    # Operations
    # ////////////////////////////////////////////////////////////

    def _difference(self):
        if not self._checkcompat():
            return

        out_chart = Chart(self._left_chart.tokens())
        for edge in self._left_chart:
            if edge not in self._right_chart:
                out_chart.insert(edge, [])

        self._update("-", out_chart)

    def _intersection(self):
        if not self._checkcompat():
            return

        out_chart = Chart(self._left_chart.tokens())
        for edge in self._left_chart:
            if edge in self._right_chart:
                out_chart.insert(edge, [])

        self._update("and", out_chart)

    def _union(self):
        if not self._checkcompat():
            return

        out_chart = Chart(self._left_chart.tokens())
        for edge in self._left_chart:
            out_chart.insert(edge, [])
        for edge in self._right_chart:
            out_chart.insert(edge, [])

        self._update("or", out_chart)

    def _swapcharts(self):
        left, right = self._left_name, self._right_name
        self._left_selector.set(right)
        self._right_selector.set(left)

    def _checkcompat(self):
        if (
            self._left_chart.tokens() != self._right_chart.tokens()
            or self._left_chart.property_names() != self._right_chart.property_names()
            or self._left_chart == self._emptychart
            or self._right_chart == self._emptychart
        ):
            # Clear & inactivate the output chart.
            self._out_chart = self._emptychart
            self._out_matrix.set_chart(self._out_chart)
            self._out_matrix.inactivate()
            self._out_label["text"] = "Output"
            # Issue some other warning?
            return False
        else:
            return True

    def _update(self, operator, out_chart):
        self._operator = operator
        self._op_label["text"] = self._OPSYMBOL[operator]
        self._out_chart = out_chart
        self._out_matrix.set_chart(out_chart)
        self._out_label["text"] = "{} {} {}".format(
            self._left_name,
            self._operator,
            self._right_name,
        )

    def _clear_out_chart(self):
        self._out_chart = self._emptychart
        self._out_matrix.set_chart(self._out_chart)
        self._op_label["text"] = " "
        self._out_matrix.inactivate()

    def _detach_out(self):
        ChartMatrixView(self._root, self._out_chart, title=self._out_label["text"])


#######################################################################
# Chart View
#######################################################################


class ChartView:
    """
    A component for viewing charts.  This is used by ``ChartParserApp`` to
    allow students to interactively experiment with various chart
    parsing techniques.  It is also used by ``Chart.draw()``.

    :ivar _chart: The chart that we are giving a view of.  This chart
       may be modified; after it is modified, you should call
       ``update``.
    :ivar _sentence: The list of tokens that the chart spans.

    :ivar _root: The root window.
    :ivar _chart_canvas: The canvas we're using to display the chart
        itself.
    :ivar _tree_canvas: The canvas we're using to display the tree
        that each edge spans.  May be None, if we're not displaying
        trees.
    :ivar _sentence_canvas: The canvas we're using to display the sentence
        text.  May be None, if we're not displaying the sentence text.
    :ivar _edgetags: A dictionary mapping from edges to the tags of
        the canvas elements (lines, etc) used to display that edge.
        The values of this dictionary have the form
        ``(linetag, rhstag1, dottag, rhstag2, lhstag)``.
    :ivar _treetags: A list of all the tags that make up the tree;
        used to erase the tree (without erasing the loclines).
    :ivar _chart_height: The height of the chart canvas.
    :ivar _sentence_height: The height of the sentence canvas.
    :ivar _tree_height: The height of the tree

    :ivar _text_height: The height of a text string (in the normal
        font).

    :ivar _edgelevels: A list of edges at each level of the chart (the
        top level is the 0th element).  This list is used to remember
        where edges should be drawn; and to make sure that no edges
        are overlapping on the chart view.

    :ivar _unitsize: Pixel size of one unit (from the location).  This
       is determined by the span of the chart's location, and the
       width of the chart display canvas.

    :ivar _fontsize: The current font size

    :ivar _marks: A dictionary from edges to marks.  Marks are
        strings, specifying colors (e.g. 'green').
    """

    _LEAF_SPACING = 10
    _MARGIN = 10
    _TREE_LEVEL_SIZE = 12
    _CHART_LEVEL_SIZE = 40

    def __init__(self, chart, root=None, **kw):
        """
        Construct a new ``Chart`` display.
        """
        # Process keyword args.
        draw_tree = kw.get("draw_tree", 0)
        draw_sentence = kw.get("draw_sentence", 1)
        self._fontsize = kw.get("fontsize", -12)

        # The chart!
        self._chart = chart

        # Callback functions
        self._callbacks = {}

        # Keep track of drawn edges
        self._edgelevels = []
        self._edgetags = {}

        # Keep track of which edges are marked.
        self._marks = {}

        # These are used to keep track of the set of tree tokens
        # currently displayed in the tree canvas.
        self._treetoks = []
        self._treetoks_edge = None
        self._treetoks_index = 0

        # Keep track of the tags used to draw the tree
        self._tree_tags = []

        # Put multiple edges on each level?
        self._compact = 0

        # If they didn't provide a main window, then set one up.
        if root is None:
            top = Tk()
            top.title("Chart View")

            def destroy1(e, top=top):
                top.destroy()

            def destroy2(top=top):
                top.destroy()

            top.bind("q", destroy1)
            b = Button(top, text="Done", command=destroy2)
            b.pack(side="bottom")
            self._root = top
        else:
            self._root = root

        # Create some fonts.
        self._init_fonts(root)

        # Create the chart canvas.
        (self._chart_sb, self._chart_canvas) = self._sb_canvas(self._root)
        self._chart_canvas["height"] = 300
        self._chart_canvas["closeenough"] = 15

        # Create the sentence canvas.
        if draw_sentence:
            cframe = Frame(self._root, relief="sunk", border=2)
            cframe.pack(fill="both", side="bottom")
            self._sentence_canvas = Canvas(cframe, height=50)
            self._sentence_canvas["background"] = "#e0e0e0"
            self._sentence_canvas.pack(fill="both")
            # self._sentence_canvas['height'] = self._sentence_height
        else:
            self._sentence_canvas = None

        # Create the tree canvas.
        if draw_tree:
            (sb, canvas) = self._sb_canvas(self._root, "n", "x")
            (self._tree_sb, self._tree_canvas) = (sb, canvas)
            self._tree_canvas["height"] = 200
        else:
            self._tree_canvas = None

        # Do some analysis to figure out how big the window should be
        self._analyze()
        self.draw()
        self._resize()
        self._grow()

        # Set up the configure callback, which will be called whenever
        # the window is resized.
        self._chart_canvas.bind("<Configure>", self._configure)

    def _init_fonts(self, root):
        self._boldfont = Font(family="helvetica", weight="bold", size=self._fontsize)
        self._font = Font(family="helvetica", size=self._fontsize)
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

    def _sb_canvas(self, root, expand="y", fill="both", side="bottom"):
        """
        Helper for __init__: construct a canvas with a scrollbar.
        """
        cframe = Frame(root, relief="sunk", border=2)
        cframe.pack(fill=fill, expand=expand, side=side)
        canvas = Canvas(cframe, background="#e0e0e0")

        # Give the canvas a scrollbar.
        sb = Scrollbar(cframe, orient="vertical")
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill=fill, expand="yes")

        # Connect the scrollbars to the canvas.
        sb["command"] = canvas.yview
        canvas["yscrollcommand"] = sb.set

        return (sb, canvas)

    def scroll_up(self, *e):
        self._chart_canvas.yview("scroll", -1, "units")

    def scroll_down(self, *e):
        self._chart_canvas.yview("scroll", 1, "units")

    def page_up(self, *e):
        self._chart_canvas.yview("scroll", -1, "pages")

    def page_down(self, *e):
        self._chart_canvas.yview("scroll", 1, "pages")

    def _grow(self):
        """
        Grow the window, if necessary
        """
        # Grow, if need-be
        N = self._chart.num_leaves()
        width = max(
            int(self._chart_canvas["width"]), N * self._unitsize + ChartView._MARGIN * 2
        )

        # It won't resize without the second (height) line, but I
        # don't understand why not.
        self._chart_canvas.configure(width=width)
        self._chart_canvas.configure(height=self._chart_canvas["height"])

        self._unitsize = (width - 2 * ChartView._MARGIN) / N

        # Reset the height for the sentence window.
        if self._sentence_canvas is not None:
            self._sentence_canvas["height"] = self._sentence_height

    def set_font_size(self, size):
        self._font.configure(size=-abs(size))
        self._boldfont.configure(size=-abs(size))
        self._sysfont.configure(size=-abs(size))
        self._analyze()
        self._grow()
        self.draw()

    def get_font_size(self):
        return abs(self._fontsize)

    def _configure(self, e):
        """
        The configure callback.  This is called whenever the window is
        resized.  It is also called when the window is first mapped.
        It figures out the unit size, and redraws the contents of each
        canvas.
        """
        N = self._chart.num_leaves()
        self._unitsize = (e.width - 2 * ChartView._MARGIN) / N
        self.draw()

    def update(self, chart=None):
        """
        Draw any edges that have not been drawn.  This is typically
        called when a after modifies the canvas that a CanvasView is
        displaying.  ``update`` will cause any edges that have been
        added to the chart to be drawn.

        If update is given a ``chart`` argument, then it will replace
        the current chart with the given chart.
        """
        if chart is not None:
            self._chart = chart
            self._edgelevels = []
            self._marks = {}
            self._analyze()
            self._grow()
            self.draw()
            self.erase_tree()
            self._resize()
        else:
            for edge in self._chart:
                if edge not in self._edgetags:
                    self._add_edge(edge)
            self._resize()

    def _edge_conflict(self, edge, lvl):
        """
        Return True if the given edge overlaps with any edge on the given
        level.  This is used by _add_edge to figure out what level a
        new edge should be added to.
        """
        (s1, e1) = edge.span()
        for otheredge in self._edgelevels[lvl]:
            (s2, e2) = otheredge.span()
            if (s1 <= s2 < e1) or (s2 <= s1 < e2) or (s1 == s2 == e1 == e2):
                return True
        return False

    def _analyze_edge(self, edge):
        """
        Given a new edge, recalculate:

            - _text_height
            - _unitsize (if the edge text is too big for the current
              _unitsize, then increase _unitsize)
        """
        c = self._chart_canvas

        if isinstance(edge, TreeEdge):
            lhs = edge.lhs()
            rhselts = []
            for elt in edge.rhs():
                if isinstance(elt, Nonterminal):
                    rhselts.append(str(elt.symbol()))
                else:
                    rhselts.append(repr(elt))
            rhs = " ".join(rhselts)
        else:
            lhs = edge.lhs()
            rhs = ""

        for s in (lhs, rhs):
            tag = c.create_text(
                0, 0, text=s, font=self._boldfont, anchor="nw", justify="left"
            )
            bbox = c.bbox(tag)
            c.delete(tag)
            width = bbox[2]  # + ChartView._LEAF_SPACING
            edgelen = max(edge.length(), 1)
            self._unitsize = max(self._unitsize, width / edgelen)
            self._text_height = max(self._text_height, bbox[3] - bbox[1])

    def _add_edge(self, edge, minlvl=0):
        """
        Add a single edge to the ChartView:

            - Call analyze_edge to recalculate display parameters
            - Find an available level
            - Call _draw_edge
        """
        # Do NOT show leaf edges in the chart.
        if isinstance(edge, LeafEdge):
            return

        if edge in self._edgetags:
            return
        self._analyze_edge(edge)
        self._grow()

        if not self._compact:
            self._edgelevels.append([edge])
            lvl = len(self._edgelevels) - 1
            self._draw_edge(edge, lvl)
            self._resize()
            return

        # Figure out what level to draw the edge on.
        lvl = 0
        while True:
            # If this level doesn't exist yet, create it.
            while lvl >= len(self._edgelevels):
                self._edgelevels.append([])
                self._resize()

            # Check if we can fit the edge in this level.
            if lvl >= minlvl and not self._edge_conflict(edge, lvl):
                # Go ahead and draw it.
                self._edgelevels[lvl].append(edge)
                break

            # Try the next level.
            lvl += 1

        self._draw_edge(edge, lvl)

    def view_edge(self, edge):
        level = None
        for i in range(len(self._edgelevels)):
            if edge in self._edgelevels[i]:
                level = i
                break
        if level is None:
            return
        # Try to view the new edge..
        y = (level + 1) * self._chart_level_size
        dy = self._text_height + 10
        self._chart_canvas.yview("moveto", 1.0)
        if self._chart_height != 0:
            self._chart_canvas.yview("moveto", (y - dy) / self._chart_height)

    def _draw_edge(self, edge, lvl):
        """
        Draw a single edge on the ChartView.
        """
        c = self._chart_canvas

        # Draw the arrow.
        x1 = edge.start() * self._unitsize + ChartView._MARGIN
        x2 = edge.end() * self._unitsize + ChartView._MARGIN
        if x2 == x1:
            x2 += max(4, self._unitsize / 5)
        y = (lvl + 1) * self._chart_level_size
        linetag = c.create_line(x1, y, x2, y, arrow="last", width=3)

        # Draw a label for the edge.
        if isinstance(edge, TreeEdge):
            rhs = []
            for elt in edge.rhs():
                if isinstance(elt, Nonterminal):
                    rhs.append(str(elt.symbol()))
                else:
                    rhs.append(repr(elt))
            pos = edge.dot()
        else:
            rhs = []
            pos = 0

        rhs1 = " ".join(rhs[:pos])
        rhs2 = " ".join(rhs[pos:])
        rhstag1 = c.create_text(x1 + 3, y, text=rhs1, font=self._font, anchor="nw")
        dotx = c.bbox(rhstag1)[2] + 6
        doty = (c.bbox(rhstag1)[1] + c.bbox(rhstag1)[3]) / 2
        dottag = c.create_oval(dotx - 2, doty - 2, dotx + 2, doty + 2)
        rhstag2 = c.create_text(dotx + 6, y, text=rhs2, font=self._font, anchor="nw")
        lhstag = c.create_text(
            (x1 + x2) / 2, y, text=str(edge.lhs()), anchor="s", font=self._boldfont
        )

        # Keep track of the edge's tags.
        self._edgetags[edge] = (linetag, rhstag1, dottag, rhstag2, lhstag)

        # Register a callback for clicking on the edge.
        def cb(event, self=self, edge=edge):
            self._fire_callbacks("select", edge)

        c.tag_bind(rhstag1, "<Button-1>", cb)
        c.tag_bind(rhstag2, "<Button-1>", cb)
        c.tag_bind(linetag, "<Button-1>", cb)
        c.tag_bind(dottag, "<Button-1>", cb)
        c.tag_bind(lhstag, "<Button-1>", cb)

        self._color_edge(edge)

    def _color_edge(self, edge, linecolor=None, textcolor=None):
        """
        Color in an edge with the given colors.
        If no colors are specified, use intelligent defaults
        (dependent on selection, etc.)
        """
        if edge not in self._edgetags:
            return
        c = self._chart_canvas

        if linecolor is not None and textcolor is not None:
            if edge in self._marks:
                linecolor = self._marks[edge]
            tags = self._edgetags[edge]
            c.itemconfig(tags[0], fill=linecolor)
            c.itemconfig(tags[1], fill=textcolor)
            c.itemconfig(tags[2], fill=textcolor, outline=textcolor)
            c.itemconfig(tags[3], fill=textcolor)
            c.itemconfig(tags[4], fill=textcolor)
            return
        else:
            N = self._chart.num_leaves()
            if edge in self._marks:
                self._color_edge(self._marks[edge])
            if edge.is_complete() and edge.span() == (0, N):
                self._color_edge(edge, "#084", "#042")
            elif isinstance(edge, LeafEdge):
                self._color_edge(edge, "#48c", "#246")
            else:
                self._color_edge(edge, "#00f", "#008")

    def mark_edge(self, edge, mark="#0df"):
        """
        Mark an edge
        """
        self._marks[edge] = mark
        self._color_edge(edge)

    def unmark_edge(self, edge=None):
        """
        Unmark an edge (or all edges)
        """
        if edge is None:
            old_marked_edges = list(self._marks.keys())
            self._marks = {}
            for edge in old_marked_edges:
                self._color_edge(edge)
        else:
            del self._marks[edge]
            self._color_edge(edge)

    def markonly_edge(self, edge, mark="#0df"):
        self.unmark_edge()
        self.mark_edge(edge, mark)

    def _analyze(self):
        """
        Analyze the sentence string, to figure out how big a unit needs
        to be, How big the tree should be, etc.
        """
        # Figure out the text height and the unit size.
        unitsize = 70  # min unitsize
        text_height = 0
        c = self._chart_canvas

        # Check against all tokens
        for leaf in self._chart.leaves():
            tag = c.create_text(
                0, 0, text=repr(leaf), font=self._font, anchor="nw", justify="left"
            )
            bbox = c.bbox(tag)
            c.delete(tag)
            width = bbox[2] + ChartView._LEAF_SPACING
            unitsize = max(width, unitsize)
            text_height = max(text_height, bbox[3] - bbox[1])

        self._unitsize = unitsize
        self._text_height = text_height
        self._sentence_height = self._text_height + 2 * ChartView._MARGIN

        # Check against edges.
        for edge in self._chart.edges():
            self._analyze_edge(edge)

        # Size of chart levels
        self._chart_level_size = self._text_height * 2

        # Default tree size..
        self._tree_height = 3 * (ChartView._TREE_LEVEL_SIZE + self._text_height)

        # Resize the scrollregions.
        self._resize()

    def _resize(self):
        """
        Update the scroll-regions for each canvas.  This ensures that
        everything is within a scroll-region, so the user can use the
        scrollbars to view the entire display.  This does *not*
        resize the window.
        """
        c = self._chart_canvas

        # Reset the chart scroll region
        width = self._chart.num_leaves() * self._unitsize + ChartView._MARGIN * 2

        levels = len(self._edgelevels)
        self._chart_height = (levels + 2) * self._chart_level_size
        c["scrollregion"] = (0, 0, width, self._chart_height)

        # Reset the tree scroll region
        if self._tree_canvas:
            self._tree_canvas["scrollregion"] = (0, 0, width, self._tree_height)

    def _draw_loclines(self):
        """
        Draw location lines.  These are vertical gridlines used to
        show where each location unit is.
        """
        BOTTOM = 50000
        c1 = self._tree_canvas
        c2 = self._sentence_canvas
        c3 = self._chart_canvas
        margin = ChartView._MARGIN
        self._loclines = []
        for i in range(0, self._chart.num_leaves() + 1):
            x = i * self._unitsize + margin

            if c1:
                t1 = c1.create_line(x, 0, x, BOTTOM)
                c1.tag_lower(t1)
            if c2:
                t2 = c2.create_line(x, 0, x, self._sentence_height)
                c2.tag_lower(t2)
            t3 = c3.create_line(x, 0, x, BOTTOM)
            c3.tag_lower(t3)
            t4 = c3.create_text(x + 2, 0, text=repr(i), anchor="nw", font=self._font)
            c3.tag_lower(t4)
            # if i % 4 == 0:
            #    if c1: c1.itemconfig(t1, width=2, fill='gray60')
            #    if c2: c2.itemconfig(t2, width=2, fill='gray60')
            #    c3.itemconfig(t3, width=2, fill='gray60')
            if i % 2 == 0:
                if c1:
                    c1.itemconfig(t1, fill="gray60")
                if c2:
                    c2.itemconfig(t2, fill="gray60")
                c3.itemconfig(t3, fill="gray60")
            else:
                if c1:
                    c1.itemconfig(t1, fill="gray80")
                if c2:
                    c2.itemconfig(t2, fill="gray80")
                c3.itemconfig(t3, fill="gray80")

    def _draw_sentence(self):
        """Draw the sentence string."""
        if self._chart.num_leaves() == 0:
            return
        c = self._sentence_canvas
        margin = ChartView._MARGIN
        y = ChartView._MARGIN

        for i, leaf in enumerate(self._chart.leaves()):
            x1 = i * self._unitsize + margin
            x2 = x1 + self._unitsize
            x = (x1 + x2) / 2
            tag = c.create_text(
                x, y, text=repr(leaf), font=self._font, anchor="n", justify="left"
            )
            bbox = c.bbox(tag)
            rt = c.create_rectangle(
                x1 + 2,
                bbox[1] - (ChartView._LEAF_SPACING / 2),
                x2 - 2,
                bbox[3] + (ChartView._LEAF_SPACING / 2),
                fill="#f0f0f0",
                outline="#f0f0f0",
            )
            c.tag_lower(rt)

    def erase_tree(self):
        for tag in self._tree_tags:
            self._tree_canvas.delete(tag)
        self._treetoks = []
        self._treetoks_edge = None
        self._treetoks_index = 0

    def draw_tree(self, edge=None):
        if edge is None and self._treetoks_edge is None:
            return
        if edge is None:
            edge = self._treetoks_edge

        # If it's a new edge, then get a new list of treetoks.
        if self._treetoks_edge != edge:
            self._treetoks = [t for t in self._chart.trees(edge) if isinstance(t, Tree)]
            self._treetoks_edge = edge
            self._treetoks_index = 0

        # Make sure there's something to draw.
        if len(self._treetoks) == 0:
            return

        # Erase the old tree.
        for tag in self._tree_tags:
            self._tree_canvas.delete(tag)

        # Draw the new tree.
        tree = self._treetoks[self._treetoks_index]
        self._draw_treetok(tree, edge.start())

        # Show how many trees are available for the edge.
        self._draw_treecycle()

        # Update the scroll region.
        w = self._chart.num_leaves() * self._unitsize + 2 * ChartView._MARGIN
        h = tree.height() * (ChartView._TREE_LEVEL_SIZE + self._text_height)
        self._tree_canvas["scrollregion"] = (0, 0, w, h)

    def cycle_tree(self):
        self._treetoks_index = (self._treetoks_index + 1) % len(self._treetoks)
        self.draw_tree(self._treetoks_edge)

    def _draw_treecycle(self):
        if len(self._treetoks) <= 1:
            return

        # Draw the label.
        label = "%d Trees" % len(self._treetoks)
        c = self._tree_canvas
        margin = ChartView._MARGIN
        right = self._chart.num_leaves() * self._unitsize + margin - 2
        tag = c.create_text(right, 2, anchor="ne", text=label, font=self._boldfont)
        self._tree_tags.append(tag)
        _, _, _, y = c.bbox(tag)

        # Draw the triangles.
        for i in range(len(self._treetoks)):
            x = right - 20 * (len(self._treetoks) - i - 1)
            if i == self._treetoks_index:
                fill = "#084"
            else:
                fill = "#fff"
            tag = c.create_polygon(
                x, y + 10, x - 5, y, x - 10, y + 10, fill=fill, outline="black"
            )
            self._tree_tags.append(tag)

            # Set up a callback: show the tree if they click on its
            # triangle.
            def cb(event, self=self, i=i):
                self._treetoks_index = i
                self.draw_tree()

            c.tag_bind(tag, "<Button-1>", cb)

    def _draw_treetok(self, treetok, index, depth=0):
        """
        :param index: The index of the first leaf in the tree.
        :return: The index of the first leaf after the tree.
        """
        c = self._tree_canvas
        margin = ChartView._MARGIN

        # Draw the children
        child_xs = []
        for child in treetok:
            if isinstance(child, Tree):
                child_x, index = self._draw_treetok(child, index, depth + 1)
                child_xs.append(child_x)
            else:
                child_xs.append((2 * index + 1) * self._unitsize / 2 + margin)
                index += 1

        # If we have children, then get the node's x by averaging their
        # node x's.  Otherwise, make room for ourselves.
        if child_xs:
            nodex = sum(child_xs) / len(child_xs)
        else:
            # [XX] breaks for null productions.
            nodex = (2 * index + 1) * self._unitsize / 2 + margin
            index += 1

        # Draw the node
        nodey = depth * (ChartView._TREE_LEVEL_SIZE + self._text_height)
        tag = c.create_text(
            nodex,
            nodey,
            anchor="n",
            justify="center",
            text=str(treetok.label()),
            fill="#042",
            font=self._boldfont,
        )
        self._tree_tags.append(tag)

        # Draw lines to the children.
        childy = nodey + ChartView._TREE_LEVEL_SIZE + self._text_height
        for childx, child in zip(child_xs, treetok):
            if isinstance(child, Tree) and child:
                # A "real" tree token:
                tag = c.create_line(
                    nodex,
                    nodey + self._text_height,
                    childx,
                    childy,
                    width=2,
                    fill="#084",
                )
                self._tree_tags.append(tag)
            if isinstance(child, Tree) and not child:
                # An unexpanded tree token:
                tag = c.create_line(
                    nodex,
                    nodey + self._text_height,
                    childx,
                    childy,
                    width=2,
                    fill="#048",
                    dash="2 3",
                )
                self._tree_tags.append(tag)
            if not isinstance(child, Tree):
                # A leaf:
                tag = c.create_line(
                    nodex,
                    nodey + self._text_height,
                    childx,
                    10000,
                    width=2,
                    fill="#084",
                )
                self._tree_tags.append(tag)

        return nodex, index

    def draw(self):
        """
        Draw everything (from scratch).
        """
        if self._tree_canvas:
            self._tree_canvas.delete("all")
            self.draw_tree()

        if self._sentence_canvas:
            self._sentence_canvas.delete("all")
            self._draw_sentence()

        self._chart_canvas.delete("all")
        self._edgetags = {}

        # Redraw any edges we erased.
        for lvl in range(len(self._edgelevels)):
            for edge in self._edgelevels[lvl]:
                self._draw_edge(edge, lvl)

        for edge in self._chart:
            self._add_edge(edge)

        self._draw_loclines()

    def add_callback(self, event, func):
        self._callbacks.setdefault(event, {})[func] = 1

    def remove_callback(self, event, func=None):
        if func is None:
            del self._callbacks[event]
        else:
            try:
                del self._callbacks[event][func]
            except:
                pass

    def _fire_callbacks(self, event, *args):
        if event not in self._callbacks:
            return
        for cb_func in list(self._callbacks[event].keys()):
            cb_func(*args)


#######################################################################
# Edge Rules
#######################################################################
# These version of the chart rules only apply to a specific edge.
# This lets the user select an edge, and then apply a rule.


class EdgeRule:
    """
    To create an edge rule, make an empty base class that uses
    EdgeRule as the first base class, and the basic rule as the
    second base class.  (Order matters!)
    """

    def __init__(self, edge):
        super = self.__class__.__bases__[1]
        self._edge = edge
        self.NUM_EDGES = super.NUM_EDGES - 1

    def apply(self, chart, grammar, *edges):
        super = self.__class__.__bases__[1]
        edges += (self._edge,)
        yield from super.apply(self, chart, grammar, *edges)

    def __str__(self):
        super = self.__class__.__bases__[1]
        return super.__str__(self)


class TopDownPredictEdgeRule(EdgeRule, TopDownPredictRule):
    pass


class BottomUpEdgeRule(EdgeRule, BottomUpPredictRule):
    pass


class BottomUpLeftCornerEdgeRule(EdgeRule, BottomUpPredictCombineRule):
    pass


class FundamentalEdgeRule(EdgeRule, SingleEdgeFundamentalRule):
    pass


#######################################################################
# Chart Parser Application
#######################################################################


class ChartParserApp:
    def __init__(self, grammar, tokens, title="Chart Parser Application"):
        # Initialize the parser
        self._init_parser(grammar, tokens)

        self._root = None
        try:
            # Create the root window.
            self._root = Tk()
            self._root.title(title)
            self._root.bind("<Control-q>", self.destroy)

            # Set up some frames.
            frame3 = Frame(self._root)
            frame2 = Frame(self._root)
            frame1 = Frame(self._root)
            frame3.pack(side="bottom", fill="none")
            frame2.pack(side="bottom", fill="x")
            frame1.pack(side="bottom", fill="both", expand=1)

            self._init_fonts(self._root)
            self._init_animation()
            self._init_chartview(frame1)
            self._init_rulelabel(frame2)
            self._init_buttons(frame3)
            self._init_menubar()

            self._matrix = None
            self._results = None

            # Set up keyboard bindings.
            self._init_bindings()

        except:
            print("Error creating Tree View")
            self.destroy()
            raise

    def destroy(self, *args):
        if self._root is None:
            return
        self._root.destroy()
        self._root = None

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._root.mainloop(*args, **kwargs)

    # ////////////////////////////////////////////////////////////
    # Initialization Helpers
    # ////////////////////////////////////////////////////////////

    def _init_parser(self, grammar, tokens):
        self._grammar = grammar
        self._tokens = tokens
        self._reset_parser()

    def _reset_parser(self):
        self._cp = SteppingChartParser(self._grammar)
        self._cp.initialize(self._tokens)
        self._chart = self._cp.chart()

        # Insert LeafEdges before the parsing starts.
        for _new_edge in LeafInitRule().apply(self._chart, self._grammar):
            pass

        # The step iterator -- use this to generate new edges
        self._cpstep = self._cp.step()

        # The currently selected edge
        self._selection = None

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())

    def _init_animation(self):
        # Are we stepping? (default=yes)
        self._step = IntVar(self._root)
        self._step.set(1)

        # What's our animation speed (default=fast)
        self._animate = IntVar(self._root)
        self._animate.set(3)  # Default speed = fast

        # Are we currently animating?
        self._animating = 0

    def _init_chartview(self, parent):
        self._cv = ChartView(self._chart, parent, draw_tree=1, draw_sentence=1)
        self._cv.add_callback("select", self._click_cv_edge)

    def _init_rulelabel(self, parent):
        ruletxt = "Last edge generated by:"

        self._rulelabel1 = Label(parent, text=ruletxt, font=self._boldfont)
        self._rulelabel2 = Label(
            parent, width=40, relief="groove", anchor="w", font=self._boldfont
        )
        self._rulelabel1.pack(side="left")
        self._rulelabel2.pack(side="left")
        step = Checkbutton(parent, variable=self._step, text="Step")
        step.pack(side="right")

    def _init_buttons(self, parent):
        frame1 = Frame(parent)
        frame2 = Frame(parent)
        frame1.pack(side="bottom", fill="x")
        frame2.pack(side="top", fill="none")

        Button(
            frame1,
            text="Reset\nParser",
            background="#90c0d0",
            foreground="black",
            command=self.reset,
        ).pack(side="right")
        # Button(frame1, text='Pause',
        #               background='#90c0d0', foreground='black',
        #               command=self.pause).pack(side='left')

        Button(
            frame1,
            text="Top Down\nStrategy",
            background="#90c0d0",
            foreground="black",
            command=self.top_down_strategy,
        ).pack(side="left")
        Button(
            frame1,
            text="Bottom Up\nStrategy",
            background="#90c0d0",
            foreground="black",
            command=self.bottom_up_strategy,
        ).pack(side="left")
        Button(
            frame1,
            text="Bottom Up\nLeft-Corner Strategy",
            background="#90c0d0",
            foreground="black",
            command=self.bottom_up_leftcorner_strategy,
        ).pack(side="left")

        Button(
            frame2,
            text="Top Down Init\nRule",
            background="#90f090",
            foreground="black",
            command=self.top_down_init,
        ).pack(side="left")
        Button(
            frame2,
            text="Top Down Predict\nRule",
            background="#90f090",
            foreground="black",
            command=self.top_down_predict,
        ).pack(side="left")
        Frame(frame2, width=20).pack(side="left")

        Button(
            frame2,
            text="Bottom Up Predict\nRule",
            background="#90f090",
            foreground="black",
            command=self.bottom_up,
        ).pack(side="left")
        Frame(frame2, width=20).pack(side="left")

        Button(
            frame2,
            text="Bottom Up Left-Corner\nPredict Rule",
            background="#90f090",
            foreground="black",
            command=self.bottom_up_leftcorner,
        ).pack(side="left")
        Frame(frame2, width=20).pack(side="left")

        Button(
            frame2,
            text="Fundamental\nRule",
            background="#90f090",
            foreground="black",
            command=self.fundamental,
        ).pack(side="left")

    def _init_bindings(self):
        self._root.bind("<Up>", self._cv.scroll_up)
        self._root.bind("<Down>", self._cv.scroll_down)
        self._root.bind("<Prior>", self._cv.page_up)
        self._root.bind("<Next>", self._cv.page_down)
        self._root.bind("<Control-q>", self.destroy)
        self._root.bind("<Control-x>", self.destroy)
        self._root.bind("<F1>", self.help)

        self._root.bind("<Control-s>", self.save_chart)
        self._root.bind("<Control-o>", self.load_chart)
        self._root.bind("<Control-r>", self.reset)

        self._root.bind("t", self.top_down_strategy)
        self._root.bind("b", self.bottom_up_strategy)
        self._root.bind("c", self.bottom_up_leftcorner_strategy)
        self._root.bind("<space>", self._stop_animation)

        self._root.bind("<Control-g>", self.edit_grammar)
        self._root.bind("<Control-t>", self.edit_sentence)

        # Animation speed control
        self._root.bind("-", lambda e, a=self._animate: a.set(1))
        self._root.bind("=", lambda e, a=self._animate: a.set(2))
        self._root.bind("+", lambda e, a=self._animate: a.set(3))

        # Step control
        self._root.bind("s", lambda e, s=self._step: s.set(not s.get()))

    def _init_menubar(self):
        menubar = Menu(self._root)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Save Chart",
            underline=0,
            command=self.save_chart,
            accelerator="Ctrl-s",
        )
        filemenu.add_command(
            label="Load Chart",
            underline=0,
            command=self.load_chart,
            accelerator="Ctrl-o",
        )
        filemenu.add_command(
            label="Reset Chart", underline=0, command=self.reset, accelerator="Ctrl-r"
        )
        filemenu.add_separator()
        filemenu.add_command(label="Save Grammar", command=self.save_grammar)
        filemenu.add_command(label="Load Grammar", command=self.load_grammar)
        filemenu.add_separator()
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(
            label="Edit Grammar",
            underline=5,
            command=self.edit_grammar,
            accelerator="Ctrl-g",
        )
        editmenu.add_command(
            label="Edit Text",
            underline=5,
            command=self.edit_sentence,
            accelerator="Ctrl-t",
        )
        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_command(
            label="Chart Matrix", underline=6, command=self.view_matrix
        )
        viewmenu.add_command(label="Results", underline=0, command=self.view_results)
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        rulemenu = Menu(menubar, tearoff=0)
        rulemenu.add_command(
            label="Top Down Strategy",
            underline=0,
            command=self.top_down_strategy,
            accelerator="t",
        )
        rulemenu.add_command(
            label="Bottom Up Strategy",
            underline=0,
            command=self.bottom_up_strategy,
            accelerator="b",
        )
        rulemenu.add_command(
            label="Bottom Up Left-Corner Strategy",
            underline=0,
            command=self.bottom_up_leftcorner_strategy,
            accelerator="c",
        )
        rulemenu.add_separator()
        rulemenu.add_command(label="Bottom Up Rule", command=self.bottom_up)
        rulemenu.add_command(
            label="Bottom Up Left-Corner Rule", command=self.bottom_up_leftcorner
        )
        rulemenu.add_command(label="Top Down Init Rule", command=self.top_down_init)
        rulemenu.add_command(
            label="Top Down Predict Rule", command=self.top_down_predict
        )
        rulemenu.add_command(label="Fundamental Rule", command=self.fundamental)
        menubar.add_cascade(label="Apply", underline=0, menu=rulemenu)

        animatemenu = Menu(menubar, tearoff=0)
        animatemenu.add_checkbutton(
            label="Step", underline=0, variable=self._step, accelerator="s"
        )
        animatemenu.add_separator()
        animatemenu.add_radiobutton(
            label="No Animation", underline=0, variable=self._animate, value=0
        )
        animatemenu.add_radiobutton(
            label="Slow Animation",
            underline=0,
            variable=self._animate,
            value=1,
            accelerator="-",
        )
        animatemenu.add_radiobutton(
            label="Normal Animation",
            underline=0,
            variable=self._animate,
            value=2,
            accelerator="=",
        )
        animatemenu.add_radiobutton(
            label="Fast Animation",
            underline=0,
            variable=self._animate,
            value=3,
            accelerator="+",
        )
        menubar.add_cascade(label="Animate", underline=1, menu=animatemenu)

        zoommenu = Menu(menubar, tearoff=0)
        zoommenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="Zoom", underline=0, menu=zoommenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        helpmenu.add_command(
            label="Instructions", underline=0, command=self.help, accelerator="F1"
        )
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        self._root.config(menu=menubar)

    # ////////////////////////////////////////////////////////////
    # Selection Handling
    # ////////////////////////////////////////////////////////////

    def _click_cv_edge(self, edge):
        if edge != self._selection:
            # Clicking on a new edge selects it.
            self._select_edge(edge)
        else:
            # Repeated clicks on one edge cycle its trees.
            self._cv.cycle_tree()
            # [XX] this can get confused if animation is running
            # faster than the callbacks...

    def _select_matrix_edge(self, edge):
        self._select_edge(edge)
        self._cv.view_edge(edge)

    def _select_edge(self, edge):
        self._selection = edge
        # Update the chart view.
        self._cv.markonly_edge(edge, "#f00")
        self._cv.draw_tree(edge)
        # Update the matrix view.
        if self._matrix:
            self._matrix.markonly_edge(edge)
        if self._matrix:
            self._matrix.view_edge(edge)

    def _deselect_edge(self):
        self._selection = None
        # Update the chart view.
        self._cv.unmark_edge()
        self._cv.erase_tree()
        # Update the matrix view
        if self._matrix:
            self._matrix.unmark_edge()

    def _show_new_edge(self, edge):
        self._display_rule(self._cp.current_chartrule())
        # Update the chart view.
        self._cv.update()
        self._cv.draw_tree(edge)
        self._cv.markonly_edge(edge, "#0df")
        self._cv.view_edge(edge)
        # Update the matrix view.
        if self._matrix:
            self._matrix.update()
        if self._matrix:
            self._matrix.markonly_edge(edge)
        if self._matrix:
            self._matrix.view_edge(edge)
        # Update the results view.
        if self._results:
            self._results.update(edge)

    # ////////////////////////////////////////////////////////////
    # Help/usage
    # ////////////////////////////////////////////////////////////

    def help(self, *e):
        self._animating = 0
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._root,
                "Help: Chart Parser Application",
                (__doc__ or "").strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._root,
                "Help: Chart Parser Application",
                (__doc__ or "").strip(),
                width=75,
            )

    def about(self, *e):
        ABOUT = "NLTK Chart Parser Application\n" + "Written by Edward Loper"
        showinfo("About: Chart Parser Application", ABOUT)

    # ////////////////////////////////////////////////////////////
    # File Menu
    # ////////////////////////////////////////////////////////////

    CHART_FILE_TYPES = [("Pickle file", ".pickle"), ("All files", "*")]
    GRAMMAR_FILE_TYPES = [
        ("Plaintext grammar file", ".cfg"),
        ("Pickle file", ".pickle"),
        ("All files", "*"),
    ]

    def load_chart(self, *args):
        "Load a chart from a pickle file"
        filename = askopenfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            with open(filename, "rb") as infile:
                chart = pickle.load(infile)
            self._chart = chart
            self._cv.update(chart)
            if self._matrix:
                self._matrix.set_chart(chart)
            if self._matrix:
                self._matrix.deselect_cell()
            if self._results:
                self._results.set_chart(chart)
            self._cp.set_chart(chart)
        except Exception as e:
            raise
            showerror("Error Loading Chart", "Unable to open file: %r" % filename)

    def save_chart(self, *args):
        "Save a chart to a pickle file"
        filename = asksaveasfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            with open(filename, "wb") as outfile:
                pickle.dump(self._chart, outfile)
        except Exception as e:
            raise
            showerror("Error Saving Chart", "Unable to open file: %r" % filename)

    def load_grammar(self, *args):
        "Load a grammar from a pickle file"
        filename = askopenfilename(
            filetypes=self.GRAMMAR_FILE_TYPES, defaultextension=".cfg"
        )
        if not filename:
            return
        try:
            if filename.endswith(".pickle"):
                with open(filename, "rb") as infile:
                    grammar = pickle.load(infile)
            else:
                with open(filename) as infile:
                    grammar = CFG.fromstring(infile.read())
            self.set_grammar(grammar)
        except Exception as e:
            showerror("Error Loading Grammar", "Unable to open file: %r" % filename)

    def save_grammar(self, *args):
        filename = asksaveasfilename(
            filetypes=self.GRAMMAR_FILE_TYPES, defaultextension=".cfg"
        )
        if not filename:
            return
        try:
            if filename.endswith(".pickle"):
                with open(filename, "wb") as outfile:
                    pickle.dump((self._chart, self._tokens), outfile)
            else:
                with open(filename, "w") as outfile:
                    prods = self._grammar.productions()
                    start = [p for p in prods if p.lhs() == self._grammar.start()]
                    rest = [p for p in prods if p.lhs() != self._grammar.start()]
                    for prod in start:
                        outfile.write("%s\n" % prod)
                    for prod in rest:
                        outfile.write("%s\n" % prod)
        except Exception as e:
            showerror("Error Saving Grammar", "Unable to open file: %r" % filename)

    def reset(self, *args):
        self._animating = 0
        self._reset_parser()
        self._cv.update(self._chart)
        if self._matrix:
            self._matrix.set_chart(self._chart)
        if self._matrix:
            self._matrix.deselect_cell()
        if self._results:
            self._results.set_chart(self._chart)

    # ////////////////////////////////////////////////////////////
    # Edit
    # ////////////////////////////////////////////////////////////

    def edit_grammar(self, *e):
        CFGEditor(self._root, self._grammar, self.set_grammar)

    def set_grammar(self, grammar):
        self._grammar = grammar
        self._cp.set_grammar(grammar)
        if self._results:
            self._results.set_grammar(grammar)

    def edit_sentence(self, *e):
        sentence = " ".join(self._tokens)
        title = "Edit Text"
        instr = "Enter a new sentence to parse."
        EntryDialog(self._root, sentence, instr, self.set_sentence, title)

    def set_sentence(self, sentence):
        self._tokens = list(sentence.split())
        self.reset()

    # ////////////////////////////////////////////////////////////
    # View Menu
    # ////////////////////////////////////////////////////////////

    def view_matrix(self, *e):
        if self._matrix is not None:
            self._matrix.destroy()
        self._matrix = ChartMatrixView(self._root, self._chart)
        self._matrix.add_callback("select", self._select_matrix_edge)

    def view_results(self, *e):
        if self._results is not None:
            self._results.destroy()
        self._results = ChartResultsView(self._root, self._chart, self._grammar)

    # ////////////////////////////////////////////////////////////
    # Zoom Menu
    # ////////////////////////////////////////////////////////////

    def resize(self):
        self._animating = 0
        self.set_font_size(self._size.get())

    def set_font_size(self, size):
        self._cv.set_font_size(size)
        self._font.configure(size=-abs(size))
        self._boldfont.configure(size=-abs(size))
        self._sysfont.configure(size=-abs(size))

    def get_font_size(self):
        return abs(self._size.get())

    # ////////////////////////////////////////////////////////////
    # Parsing
    # ////////////////////////////////////////////////////////////

    def apply_strategy(self, strategy, edge_strategy=None):
        # If we're animating, then stop.
        if self._animating:
            self._animating = 0
            return

        # Clear the rule display & mark.
        self._display_rule(None)
        # self._cv.unmark_edge()

        if self._step.get():
            selection = self._selection
            if (selection is not None) and (edge_strategy is not None):
                # Apply the given strategy to the selected edge.
                self._cp.set_strategy([edge_strategy(selection)])
                newedge = self._apply_strategy()

                # If it failed, then clear the selection.
                if newedge is None:
                    self._cv.unmark_edge()
                    self._selection = None
            else:
                self._cp.set_strategy(strategy)
                self._apply_strategy()

        else:
            self._cp.set_strategy(strategy)
            if self._animate.get():
                self._animating = 1
                self._animate_strategy()
            else:
                for edge in self._cpstep:
                    if edge is None:
                        break
                self._cv.update()
                if self._matrix:
                    self._matrix.update()
                if self._results:
                    self._results.update()

    def _stop_animation(self, *e):
        self._animating = 0

    def _animate_strategy(self, speed=1):
        if self._animating == 0:
            return
        if self._apply_strategy() is not None:
            if self._animate.get() == 0 or self._step.get() == 1:
                return
            if self._animate.get() == 1:
                self._root.after(3000, self._animate_strategy)
            elif self._animate.get() == 2:
                self._root.after(1000, self._animate_strategy)
            else:
                self._root.after(20, self._animate_strategy)

    def _apply_strategy(self):
        new_edge = next(self._cpstep)

        if new_edge is not None:
            self._show_new_edge(new_edge)
        return new_edge

    def _display_rule(self, rule):
        if rule is None:
            self._rulelabel2["text"] = ""
        else:
            name = str(rule)
            self._rulelabel2["text"] = name
            size = self._cv.get_font_size()

    # ////////////////////////////////////////////////////////////
    # Parsing Strategies
    # ////////////////////////////////////////////////////////////

    # Basic rules:
    _TD_INIT = [TopDownInitRule()]
    _TD_PREDICT = [TopDownPredictRule()]
    _BU_RULE = [BottomUpPredictRule()]
    _BU_LC_RULE = [BottomUpPredictCombineRule()]
    _FUNDAMENTAL = [SingleEdgeFundamentalRule()]

    # Complete strategies:
    _TD_STRATEGY = _TD_INIT + _TD_PREDICT + _FUNDAMENTAL
    _BU_STRATEGY = _BU_RULE + _FUNDAMENTAL
    _BU_LC_STRATEGY = _BU_LC_RULE + _FUNDAMENTAL

    # Button callback functions:
    def top_down_init(self, *e):
        self.apply_strategy(self._TD_INIT, None)

    def top_down_predict(self, *e):
        self.apply_strategy(self._TD_PREDICT, TopDownPredictEdgeRule)

    def bottom_up(self, *e):
        self.apply_strategy(self._BU_RULE, BottomUpEdgeRule)

    def bottom_up_leftcorner(self, *e):
        self.apply_strategy(self._BU_LC_RULE, BottomUpLeftCornerEdgeRule)

    def fundamental(self, *e):
        self.apply_strategy(self._FUNDAMENTAL, FundamentalEdgeRule)

    def bottom_up_strategy(self, *e):
        self.apply_strategy(self._BU_STRATEGY, BottomUpEdgeRule)

    def bottom_up_leftcorner_strategy(self, *e):
        self.apply_strategy(self._BU_LC_STRATEGY, BottomUpLeftCornerEdgeRule)

    def top_down_strategy(self, *e):
        self.apply_strategy(self._TD_STRATEGY, TopDownPredictEdgeRule)


def app():
    grammar = CFG.fromstring(
        """
    # Grammatical productions.
        S -> NP VP
        VP -> VP PP | V NP | V
        NP -> Det N | NP PP
        PP -> P NP
    # Lexical productions.
        NP -> 'John' | 'I'
        Det -> 'the' | 'my' | 'a'
        N -> 'dog' | 'cookie' | 'table' | 'cake' | 'fork'
        V -> 'ate' | 'saw'
        P -> 'on' | 'under' | 'with'
    """
    )

    sent = "John ate the cake on the table with a fork"
    sent = "John ate the cake on the table"
    tokens = list(sent.split())

    print("grammar= (")
    for rule in grammar.productions():
        print(("    ", repr(rule) + ","))
    print(")")
    print("tokens = %r" % tokens)
    print('Calling "ChartParserApp(grammar, tokens)"...')
    ChartParserApp(grammar, tokens).mainloop()


if __name__ == "__main__":
    app()

    # Chart comparer:
    # charts = ['/tmp/earley.pickle',
    #          '/tmp/topdown.pickle',
    #          '/tmp/bottomup.pickle']
    # ChartComparer(*charts).mainloop()

    # import profile
    # profile.run('demo2()', '/tmp/profile.out')
    # import pstats
    # p = pstats.Stats('/tmp/profile.out')
    # p.strip_dirs().sort_stats('time', 'cum').print_stats(60)
    # p.strip_dirs().sort_stats('cum', 'time').print_stats(60)

__all__ = ["app"]

# === NexusCore/tools\exports\NexusCore_export_20250803_131253\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\chartparser_app.py ===
# Natural Language Toolkit: Chart Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Jean Mark Gawron <gawron@mail.sdsu.edu>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring chart parsing.

Chart parsing is a flexible parsing algorithm that uses a data
structure called a "chart" to record hypotheses about syntactic
constituents.  Each hypothesis is represented by a single "edge" on
the chart.  A set of "chart rules" determine when new edges can be
added to the chart.  This set of rules controls the overall behavior
of the parser (e.g. whether it parses top-down or bottom-up).

The chart parsing tool demonstrates the process of parsing a single
sentence, with a given grammar and lexicon.  Its display is divided
into three sections: the bottom section displays the chart; the middle
section displays the sentence; and the top section displays the
partial syntax tree corresponding to the selected edge.  Buttons along
the bottom of the window are used to control the execution of the
algorithm.

The chart parsing tool allows for flexible control of the parsing
algorithm.  At each step of the algorithm, you can select which rule
or strategy you wish to apply.  This allows you to experiment with
mixing different strategies (e.g. top-down and bottom-up).  You can
exercise fine-grained control over the algorithm by selecting which
edge you wish to apply a rule to.
"""

# At some point, we should rewrite this tool to use the new canvas
# widget system.


import os.path
import pickle
from tkinter import (
    Button,
    Canvas,
    Checkbutton,
    Frame,
    IntVar,
    Label,
    Menu,
    Scrollbar,
    Tk,
    Toplevel,
)
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.font import Font
from tkinter.messagebox import showerror, showinfo

from nltk.draw import CFGEditor, TreeSegmentWidget, tree_to_treesegment
from nltk.draw.util import (
    CanvasFrame,
    ColorizedList,
    EntryDialog,
    MutableOptionMenu,
    ShowText,
    SymbolWidget,
)
from nltk.grammar import CFG, Nonterminal
from nltk.parse.chart import (
    BottomUpPredictCombineRule,
    BottomUpPredictRule,
    Chart,
    LeafEdge,
    LeafInitRule,
    SingleEdgeFundamentalRule,
    SteppingChartParser,
    TopDownInitRule,
    TopDownPredictRule,
    TreeEdge,
)
from nltk.tree import Tree
from nltk.util import in_idle

# Known bug: ChartView doesn't handle edges generated by epsilon
# productions (e.g., [Production: PP -> ]) very well.

#######################################################################
# Edge List
#######################################################################


class EdgeList(ColorizedList):
    ARROW = SymbolWidget.SYMBOLS["rightarrow"]

    def _init_colortags(self, textwidget, options):
        textwidget.tag_config("terminal", foreground="#006000")
        textwidget.tag_config("arrow", font="symbol", underline="0")
        textwidget.tag_config("dot", foreground="#000000")
        textwidget.tag_config(
            "nonterminal", foreground="blue", font=("helvetica", -12, "bold")
        )

    def _item_repr(self, item):
        contents = []
        contents.append(("%s\t" % item.lhs(), "nonterminal"))
        contents.append((self.ARROW, "arrow"))
        for i, elt in enumerate(item.rhs()):
            if i == item.dot():
                contents.append((" *", "dot"))
            if isinstance(elt, Nonterminal):
                contents.append((" %s" % elt.symbol(), "nonterminal"))
            else:
                contents.append((" %r" % elt, "terminal"))
        if item.is_complete():
            contents.append((" *", "dot"))
        return contents


#######################################################################
# Chart Matrix View
#######################################################################


class ChartMatrixView:
    """
    A view of a chart that displays the contents of the corresponding matrix.
    """

    def __init__(
        self, parent, chart, toplevel=True, title="Chart Matrix", show_numedges=False
    ):
        self._chart = chart
        self._cells = []
        self._marks = []

        self._selected_cell = None

        if toplevel:
            self._root = Toplevel(parent)
            self._root.title(title)
            self._root.bind("<Control-q>", self.destroy)
            self._init_quit(self._root)
        else:
            self._root = Frame(parent)

        self._init_matrix(self._root)
        self._init_list(self._root)
        if show_numedges:
            self._init_numedges(self._root)
        else:
            self._numedges_label = None

        self._callbacks = {}

        self._num_edges = 0

        self.draw()

    def _init_quit(self, root):
        quit = Button(root, text="Quit", command=self.destroy)
        quit.pack(side="bottom", expand=0, fill="none")

    def _init_matrix(self, root):
        cframe = Frame(root, border=2, relief="sunken")
        cframe.pack(expand=0, fill="none", padx=1, pady=3, side="top")
        self._canvas = Canvas(cframe, width=200, height=200, background="white")
        self._canvas.pack(expand=0, fill="none")

    def _init_numedges(self, root):
        self._numedges_label = Label(root, text="0 edges")
        self._numedges_label.pack(expand=0, fill="none", side="top")

    def _init_list(self, root):
        self._list = EdgeList(root, [], width=20, height=5)
        self._list.pack(side="top", expand=1, fill="both", pady=3)

        def cb(edge, self=self):
            self._fire_callbacks("select", edge)

        self._list.add_callback("select", cb)
        self._list.focus()

    def destroy(self, *e):
        if self._root is None:
            return
        try:
            self._root.destroy()
        except:
            pass
        self._root = None

    def set_chart(self, chart):
        if chart is not self._chart:
            self._chart = chart
            self._num_edges = 0
            self.draw()

    def update(self):
        if self._root is None:
            return

        # Count the edges in each cell
        N = len(self._cells)
        cell_edges = [[0 for i in range(N)] for j in range(N)]
        for edge in self._chart:
            cell_edges[edge.start()][edge.end()] += 1

        # Color the cells correspondingly.
        for i in range(N):
            for j in range(i, N):
                if cell_edges[i][j] == 0:
                    color = "gray20"
                else:
                    color = "#00{:02x}{:02x}".format(
                        min(255, 50 + 128 * cell_edges[i][j] / 10),
                        max(0, 128 - 128 * cell_edges[i][j] / 10),
                    )
                cell_tag = self._cells[i][j]
                self._canvas.itemconfig(cell_tag, fill=color)
                if (i, j) == self._selected_cell:
                    self._canvas.itemconfig(cell_tag, outline="#00ffff", width=3)
                    self._canvas.tag_raise(cell_tag)
                else:
                    self._canvas.itemconfig(cell_tag, outline="black", width=1)

        # Update the edge list.
        edges = list(self._chart.select(span=self._selected_cell))
        self._list.set(edges)

        # Update our edge count.
        self._num_edges = self._chart.num_edges()
        if self._numedges_label is not None:
            self._numedges_label["text"] = "%d edges" % self._num_edges

    def activate(self):
        self._canvas.itemconfig("inactivebox", state="hidden")
        self.update()

    def inactivate(self):
        self._canvas.itemconfig("inactivebox", state="normal")
        self.update()

    def add_callback(self, event, func):
        self._callbacks.setdefault(event, {})[func] = 1

    def remove_callback(self, event, func=None):
        if func is None:
            del self._callbacks[event]
        else:
            try:
                del self._callbacks[event][func]
            except:
                pass

    def _fire_callbacks(self, event, *args):
        if event not in self._callbacks:
            return
        for cb_func in list(self._callbacks[event].keys()):
            cb_func(*args)

    def select_cell(self, i, j):
        if self._root is None:
            return

        # If the cell is already selected (and the chart contents
        # haven't changed), then do nothing.
        if (i, j) == self._selected_cell and self._chart.num_edges() == self._num_edges:
            return

        self._selected_cell = (i, j)
        self.update()

        # Fire the callback.
        self._fire_callbacks("select_cell", i, j)

    def deselect_cell(self):
        if self._root is None:
            return
        self._selected_cell = None
        self._list.set([])
        self.update()

    def _click_cell(self, i, j):
        if self._selected_cell == (i, j):
            self.deselect_cell()
        else:
            self.select_cell(i, j)

    def view_edge(self, edge):
        self.select_cell(*edge.span())
        self._list.view(edge)

    def mark_edge(self, edge):
        if self._root is None:
            return
        self.select_cell(*edge.span())
        self._list.mark(edge)

    def unmark_edge(self, edge=None):
        if self._root is None:
            return
        self._list.unmark(edge)

    def markonly_edge(self, edge):
        if self._root is None:
            return
        self.select_cell(*edge.span())
        self._list.markonly(edge)

    def draw(self):
        if self._root is None:
            return
        LEFT_MARGIN = BOT_MARGIN = 15
        TOP_MARGIN = 5
        c = self._canvas
        c.delete("all")
        N = self._chart.num_leaves() + 1
        dx = (int(c["width"]) - LEFT_MARGIN) / N
        dy = (int(c["height"]) - TOP_MARGIN - BOT_MARGIN) / N

        c.delete("all")

        # Labels and dotted lines
        for i in range(N):
            c.create_text(
                LEFT_MARGIN - 2, i * dy + dy / 2 + TOP_MARGIN, text=repr(i), anchor="e"
            )
            c.create_text(
                i * dx + dx / 2 + LEFT_MARGIN,
                N * dy + TOP_MARGIN + 1,
                text=repr(i),
                anchor="n",
            )
            c.create_line(
                LEFT_MARGIN,
                dy * (i + 1) + TOP_MARGIN,
                dx * N + LEFT_MARGIN,
                dy * (i + 1) + TOP_MARGIN,
                dash=".",
            )
            c.create_line(
                dx * i + LEFT_MARGIN,
                TOP_MARGIN,
                dx * i + LEFT_MARGIN,
                dy * N + TOP_MARGIN,
                dash=".",
            )

        # A box around the whole thing
        c.create_rectangle(
            LEFT_MARGIN, TOP_MARGIN, LEFT_MARGIN + dx * N, dy * N + TOP_MARGIN, width=2
        )

        # Cells
        self._cells = [[None for i in range(N)] for j in range(N)]
        for i in range(N):
            for j in range(i, N):
                t = c.create_rectangle(
                    j * dx + LEFT_MARGIN,
                    i * dy + TOP_MARGIN,
                    (j + 1) * dx + LEFT_MARGIN,
                    (i + 1) * dy + TOP_MARGIN,
                    fill="gray20",
                )
                self._cells[i][j] = t

                def cb(event, self=self, i=i, j=j):
                    self._click_cell(i, j)

                c.tag_bind(t, "<Button-1>", cb)

        # Inactive box
        xmax, ymax = int(c["width"]), int(c["height"])
        t = c.create_rectangle(
            -100,
            -100,
            xmax + 100,
            ymax + 100,
            fill="gray50",
            state="hidden",
            tag="inactivebox",
        )
        c.tag_lower(t)

        # Update the cells.
        self.update()

    def pack(self, *args, **kwargs):
        self._root.pack(*args, **kwargs)


#######################################################################
# Chart Results View
#######################################################################


class ChartResultsView:
    def __init__(self, parent, chart, grammar, toplevel=True):
        self._chart = chart
        self._grammar = grammar
        self._trees = []
        self._y = 10
        self._treewidgets = []
        self._selection = None
        self._selectbox = None

        if toplevel:
            self._root = Toplevel(parent)
            self._root.title("Chart Parser Application: Results")
            self._root.bind("<Control-q>", self.destroy)
        else:
            self._root = Frame(parent)

        # Buttons
        if toplevel:
            buttons = Frame(self._root)
            buttons.pack(side="bottom", expand=0, fill="x")
            Button(buttons, text="Quit", command=self.destroy).pack(side="right")
            Button(buttons, text="Print All", command=self.print_all).pack(side="left")
            Button(buttons, text="Print Selection", command=self.print_selection).pack(
                side="left"
            )

        # Canvas frame.
        self._cframe = CanvasFrame(self._root, closeenough=20)
        self._cframe.pack(side="top", expand=1, fill="both")

        # Initial update
        self.update()

    def update(self, edge=None):
        if self._root is None:
            return
        # If the edge isn't a parse edge, do nothing.
        if edge is not None:
            if edge.lhs() != self._grammar.start():
                return
            if edge.span() != (0, self._chart.num_leaves()):
                return

        for parse in self._chart.parses(self._grammar.start()):
            if parse not in self._trees:
                self._add(parse)

    def _add(self, parse):
        # Add it to self._trees.
        self._trees.append(parse)

        # Create a widget for it.
        c = self._cframe.canvas()
        treewidget = tree_to_treesegment(c, parse)

        # Add it to the canvas frame.
        self._treewidgets.append(treewidget)
        self._cframe.add_widget(treewidget, 10, self._y)

        # Register callbacks.
        treewidget.bind_click(self._click)

        # Update y.
        self._y = treewidget.bbox()[3] + 10

    def _click(self, widget):
        c = self._cframe.canvas()
        if self._selection is not None:
            c.delete(self._selectbox)
        self._selection = widget
        (x1, y1, x2, y2) = widget.bbox()
        self._selectbox = c.create_rectangle(x1, y1, x2, y2, width=2, outline="#088")

    def _color(self, treewidget, color):
        treewidget.label()["color"] = color
        for child in treewidget.subtrees():
            if isinstance(child, TreeSegmentWidget):
                self._color(child, color)
            else:
                child["color"] = color

    def print_all(self, *e):
        if self._root is None:
            return
        self._cframe.print_to_file()

    def print_selection(self, *e):
        if self._root is None:
            return
        if self._selection is None:
            showerror("Print Error", "No tree selected")
        else:
            c = self._cframe.canvas()
            for widget in self._treewidgets:
                if widget is not self._selection:
                    self._cframe.destroy_widget(widget)
            c.delete(self._selectbox)
            (x1, y1, x2, y2) = self._selection.bbox()
            self._selection.move(10 - x1, 10 - y1)
            c["scrollregion"] = f"0 0 {x2 - x1 + 20} {y2 - y1 + 20}"
            self._cframe.print_to_file()

            # Restore our state.
            self._treewidgets = [self._selection]
            self.clear()
            self.update()

    def clear(self):
        if self._root is None:
            return
        for treewidget in self._treewidgets:
            self._cframe.destroy_widget(treewidget)
        self._trees = []
        self._treewidgets = []
        if self._selection is not None:
            self._cframe.canvas().delete(self._selectbox)
        self._selection = None
        self._y = 10

    def set_chart(self, chart):
        self.clear()
        self._chart = chart
        self.update()

    def set_grammar(self, grammar):
        self.clear()
        self._grammar = grammar
        self.update()

    def destroy(self, *e):
        if self._root is None:
            return
        try:
            self._root.destroy()
        except:
            pass
        self._root = None

    def pack(self, *args, **kwargs):
        self._root.pack(*args, **kwargs)


#######################################################################
# Chart Comparer
#######################################################################


class ChartComparer:
    """

    :ivar _root: The root window

    :ivar _charts: A dictionary mapping names to charts.  When
        charts are loaded, they are added to this dictionary.

    :ivar _left_chart: The left ``Chart``.
    :ivar _left_name: The name ``_left_chart`` (derived from filename)
    :ivar _left_matrix: The ``ChartMatrixView`` for ``_left_chart``
    :ivar _left_selector: The drop-down ``MutableOptionsMenu`` used
          to select ``_left_chart``.

    :ivar _right_chart: The right ``Chart``.
    :ivar _right_name: The name ``_right_chart`` (derived from filename)
    :ivar _right_matrix: The ``ChartMatrixView`` for ``_right_chart``
    :ivar _right_selector: The drop-down ``MutableOptionsMenu`` used
          to select ``_right_chart``.

    :ivar _out_chart: The out ``Chart``.
    :ivar _out_name: The name ``_out_chart`` (derived from filename)
    :ivar _out_matrix: The ``ChartMatrixView`` for ``_out_chart``
    :ivar _out_label: The label for ``_out_chart``.

    :ivar _op_label: A Label containing the most recent operation.
    """

    _OPSYMBOL = {
        "-": "-",
        "and": SymbolWidget.SYMBOLS["intersection"],
        "or": SymbolWidget.SYMBOLS["union"],
    }

    def __init__(self, *chart_filenames):
        # This chart is displayed when we don't have a value (eg
        # before any chart is loaded).
        faketok = [""] * 8
        self._emptychart = Chart(faketok)

        # The left & right charts start out empty.
        self._left_name = "None"
        self._right_name = "None"
        self._left_chart = self._emptychart
        self._right_chart = self._emptychart

        # The charts that have been loaded.
        self._charts = {"None": self._emptychart}

        # The output chart.
        self._out_chart = self._emptychart

        # The most recent operation
        self._operator = None

        # Set up the root window.
        self._root = Tk()
        self._root.title("Chart Comparison")
        self._root.bind("<Control-q>", self.destroy)
        self._root.bind("<Control-x>", self.destroy)

        # Initialize all widgets, etc.
        self._init_menubar(self._root)
        self._init_chartviews(self._root)
        self._init_divider(self._root)
        self._init_buttons(self._root)
        self._init_bindings(self._root)

        # Load any specified charts.
        for filename in chart_filenames:
            self.load_chart(filename)

    def destroy(self, *e):
        if self._root is None:
            return
        try:
            self._root.destroy()
        except:
            pass
        self._root = None

    def mainloop(self, *args, **kwargs):
        return
        self._root.mainloop(*args, **kwargs)

    # ////////////////////////////////////////////////////////////
    # Initialization
    # ////////////////////////////////////////////////////////////

    def _init_menubar(self, root):
        menubar = Menu(root)

        # File menu
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Load Chart",
            accelerator="Ctrl-o",
            underline=0,
            command=self.load_chart_dialog,
        )
        filemenu.add_command(
            label="Save Output",
            accelerator="Ctrl-s",
            underline=0,
            command=self.save_chart_dialog,
        )
        filemenu.add_separator()
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        # Compare menu
        opmenu = Menu(menubar, tearoff=0)
        opmenu.add_command(
            label="Intersection", command=self._intersection, accelerator="+"
        )
        opmenu.add_command(label="Union", command=self._union, accelerator="*")
        opmenu.add_command(
            label="Difference", command=self._difference, accelerator="-"
        )
        opmenu.add_separator()
        opmenu.add_command(label="Swap Charts", command=self._swapcharts)
        menubar.add_cascade(label="Compare", underline=0, menu=opmenu)

        # Add the menu
        self._root.config(menu=menubar)

    def _init_divider(self, root):
        divider = Frame(root, border=2, relief="sunken")
        divider.pack(side="top", fill="x", ipady=2)

    def _init_chartviews(self, root):
        opfont = ("symbol", -36)  # Font for operator.
        eqfont = ("helvetica", -36)  # Font for equals sign.

        frame = Frame(root, background="#c0c0c0")
        frame.pack(side="top", expand=1, fill="both")

        # The left matrix.
        cv1_frame = Frame(frame, border=3, relief="groove")
        cv1_frame.pack(side="left", padx=8, pady=7, expand=1, fill="both")
        self._left_selector = MutableOptionMenu(
            cv1_frame, list(self._charts.keys()), command=self._select_left
        )
        self._left_selector.pack(side="top", pady=5, fill="x")
        self._left_matrix = ChartMatrixView(
            cv1_frame, self._emptychart, toplevel=False, show_numedges=True
        )
        self._left_matrix.pack(side="bottom", padx=5, pady=5, expand=1, fill="both")
        self._left_matrix.add_callback("select", self.select_edge)
        self._left_matrix.add_callback("select_cell", self.select_cell)
        self._left_matrix.inactivate()

        # The operator.
        self._op_label = Label(
            frame, text=" ", width=3, background="#c0c0c0", font=opfont
        )
        self._op_label.pack(side="left", padx=5, pady=5)

        # The right matrix.
        cv2_frame = Frame(frame, border=3, relief="groove")
        cv2_frame.pack(side="left", padx=8, pady=7, expand=1, fill="both")
        self._right_selector = MutableOptionMenu(
            cv2_frame, list(self._charts.keys()), command=self._select_right
        )
        self._right_selector.pack(side="top", pady=5, fill="x")
        self._right_matrix = ChartMatrixView(
            cv2_frame, self._emptychart, toplevel=False, show_numedges=True
        )
        self._right_matrix.pack(side="bottom", padx=5, pady=5, expand=1, fill="both")
        self._right_matrix.add_callback("select", self.select_edge)
        self._right_matrix.add_callback("select_cell", self.select_cell)
        self._right_matrix.inactivate()

        # The equals sign
        Label(frame, text="=", width=3, background="#c0c0c0", font=eqfont).pack(
            side="left", padx=5, pady=5
        )

        # The output matrix.
        out_frame = Frame(frame, border=3, relief="groove")
        out_frame.pack(side="left", padx=8, pady=7, expand=1, fill="both")
        self._out_label = Label(out_frame, text="Output")
        self._out_label.pack(side="top", pady=9)
        self._out_matrix = ChartMatrixView(
            out_frame, self._emptychart, toplevel=False, show_numedges=True
        )
        self._out_matrix.pack(side="bottom", padx=5, pady=5, expand=1, fill="both")
        self._out_matrix.add_callback("select", self.select_edge)
        self._out_matrix.add_callback("select_cell", self.select_cell)
        self._out_matrix.inactivate()

    def _init_buttons(self, root):
        buttons = Frame(root)
        buttons.pack(side="bottom", pady=5, fill="x", expand=0)
        Button(buttons, text="Intersection", command=self._intersection).pack(
            side="left"
        )
        Button(buttons, text="Union", command=self._union).pack(side="left")
        Button(buttons, text="Difference", command=self._difference).pack(side="left")
        Frame(buttons, width=20).pack(side="left")
        Button(buttons, text="Swap Charts", command=self._swapcharts).pack(side="left")

        Button(buttons, text="Detach Output", command=self._detach_out).pack(
            side="right"
        )

    def _init_bindings(self, root):
        # root.bind('<Control-s>', self.save_chart)
        root.bind("<Control-o>", self.load_chart_dialog)
        # root.bind('<Control-r>', self.reset)

    # ////////////////////////////////////////////////////////////
    # Input Handling
    # ////////////////////////////////////////////////////////////

    def _select_left(self, name):
        self._left_name = name
        self._left_chart = self._charts[name]
        self._left_matrix.set_chart(self._left_chart)
        if name == "None":
            self._left_matrix.inactivate()
        self._apply_op()

    def _select_right(self, name):
        self._right_name = name
        self._right_chart = self._charts[name]
        self._right_matrix.set_chart(self._right_chart)
        if name == "None":
            self._right_matrix.inactivate()
        self._apply_op()

    def _apply_op(self):
        if self._operator == "-":
            self._difference()
        elif self._operator == "or":
            self._union()
        elif self._operator == "and":
            self._intersection()

    # ////////////////////////////////////////////////////////////
    # File
    # ////////////////////////////////////////////////////////////
    CHART_FILE_TYPES = [("Pickle file", ".pickle"), ("All files", "*")]

    def save_chart_dialog(self, *args):
        filename = asksaveasfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            with open(filename, "wb") as outfile:
                pickle.dump(self._out_chart, outfile)
        except Exception as e:
            showerror("Error Saving Chart", f"Unable to open file: {filename!r}\n{e}")

    def load_chart_dialog(self, *args):
        filename = askopenfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            self.load_chart(filename)
        except Exception as e:
            showerror("Error Loading Chart", f"Unable to open file: {filename!r}\n{e}")

    def load_chart(self, filename):
        with open(filename, "rb") as infile:
            chart = pickle.load(infile)
        name = os.path.basename(filename)
        if name.endswith(".pickle"):
            name = name[:-7]
        if name.endswith(".chart"):
            name = name[:-6]
        self._charts[name] = chart
        self._left_selector.add(name)
        self._right_selector.add(name)

        # If either left_matrix or right_matrix is empty, then
        # display the new chart.
        if self._left_chart is self._emptychart:
            self._left_selector.set(name)
        elif self._right_chart is self._emptychart:
            self._right_selector.set(name)

    def _update_chartviews(self):
        self._left_matrix.update()
        self._right_matrix.update()
        self._out_matrix.update()

    # ////////////////////////////////////////////////////////////
    # Selection
    # ////////////////////////////////////////////////////////////

    def select_edge(self, edge):
        if edge in self._left_chart:
            self._left_matrix.markonly_edge(edge)
        else:
            self._left_matrix.unmark_edge()
        if edge in self._right_chart:
            self._right_matrix.markonly_edge(edge)
        else:
            self._right_matrix.unmark_edge()
        if edge in self._out_chart:
            self._out_matrix.markonly_edge(edge)
        else:
            self._out_matrix.unmark_edge()

    def select_cell(self, i, j):
        self._left_matrix.select_cell(i, j)
        self._right_matrix.select_cell(i, j)
        self._out_matrix.select_cell(i, j)

    # ////////////////////////////////////////////////////////////
    # Operations
    # ////////////////////////////////////////////////////////////

    def _difference(self):
        if not self._checkcompat():
            return

        out_chart = Chart(self._left_chart.tokens())
        for edge in self._left_chart:
            if edge not in self._right_chart:
                out_chart.insert(edge, [])

        self._update("-", out_chart)

    def _intersection(self):
        if not self._checkcompat():
            return

        out_chart = Chart(self._left_chart.tokens())
        for edge in self._left_chart:
            if edge in self._right_chart:
                out_chart.insert(edge, [])

        self._update("and", out_chart)

    def _union(self):
        if not self._checkcompat():
            return

        out_chart = Chart(self._left_chart.tokens())
        for edge in self._left_chart:
            out_chart.insert(edge, [])
        for edge in self._right_chart:
            out_chart.insert(edge, [])

        self._update("or", out_chart)

    def _swapcharts(self):
        left, right = self._left_name, self._right_name
        self._left_selector.set(right)
        self._right_selector.set(left)

    def _checkcompat(self):
        if (
            self._left_chart.tokens() != self._right_chart.tokens()
            or self._left_chart.property_names() != self._right_chart.property_names()
            or self._left_chart == self._emptychart
            or self._right_chart == self._emptychart
        ):
            # Clear & inactivate the output chart.
            self._out_chart = self._emptychart
            self._out_matrix.set_chart(self._out_chart)
            self._out_matrix.inactivate()
            self._out_label["text"] = "Output"
            # Issue some other warning?
            return False
        else:
            return True

    def _update(self, operator, out_chart):
        self._operator = operator
        self._op_label["text"] = self._OPSYMBOL[operator]
        self._out_chart = out_chart
        self._out_matrix.set_chart(out_chart)
        self._out_label["text"] = "{} {} {}".format(
            self._left_name,
            self._operator,
            self._right_name,
        )

    def _clear_out_chart(self):
        self._out_chart = self._emptychart
        self._out_matrix.set_chart(self._out_chart)
        self._op_label["text"] = " "
        self._out_matrix.inactivate()

    def _detach_out(self):
        ChartMatrixView(self._root, self._out_chart, title=self._out_label["text"])


#######################################################################
# Chart View
#######################################################################


class ChartView:
    """
    A component for viewing charts.  This is used by ``ChartParserApp`` to
    allow students to interactively experiment with various chart
    parsing techniques.  It is also used by ``Chart.draw()``.

    :ivar _chart: The chart that we are giving a view of.  This chart
       may be modified; after it is modified, you should call
       ``update``.
    :ivar _sentence: The list of tokens that the chart spans.

    :ivar _root: The root window.
    :ivar _chart_canvas: The canvas we're using to display the chart
        itself.
    :ivar _tree_canvas: The canvas we're using to display the tree
        that each edge spans.  May be None, if we're not displaying
        trees.
    :ivar _sentence_canvas: The canvas we're using to display the sentence
        text.  May be None, if we're not displaying the sentence text.
    :ivar _edgetags: A dictionary mapping from edges to the tags of
        the canvas elements (lines, etc) used to display that edge.
        The values of this dictionary have the form
        ``(linetag, rhstag1, dottag, rhstag2, lhstag)``.
    :ivar _treetags: A list of all the tags that make up the tree;
        used to erase the tree (without erasing the loclines).
    :ivar _chart_height: The height of the chart canvas.
    :ivar _sentence_height: The height of the sentence canvas.
    :ivar _tree_height: The height of the tree

    :ivar _text_height: The height of a text string (in the normal
        font).

    :ivar _edgelevels: A list of edges at each level of the chart (the
        top level is the 0th element).  This list is used to remember
        where edges should be drawn; and to make sure that no edges
        are overlapping on the chart view.

    :ivar _unitsize: Pixel size of one unit (from the location).  This
       is determined by the span of the chart's location, and the
       width of the chart display canvas.

    :ivar _fontsize: The current font size

    :ivar _marks: A dictionary from edges to marks.  Marks are
        strings, specifying colors (e.g. 'green').
    """

    _LEAF_SPACING = 10
    _MARGIN = 10
    _TREE_LEVEL_SIZE = 12
    _CHART_LEVEL_SIZE = 40

    def __init__(self, chart, root=None, **kw):
        """
        Construct a new ``Chart`` display.
        """
        # Process keyword args.
        draw_tree = kw.get("draw_tree", 0)
        draw_sentence = kw.get("draw_sentence", 1)
        self._fontsize = kw.get("fontsize", -12)

        # The chart!
        self._chart = chart

        # Callback functions
        self._callbacks = {}

        # Keep track of drawn edges
        self._edgelevels = []
        self._edgetags = {}

        # Keep track of which edges are marked.
        self._marks = {}

        # These are used to keep track of the set of tree tokens
        # currently displayed in the tree canvas.
        self._treetoks = []
        self._treetoks_edge = None
        self._treetoks_index = 0

        # Keep track of the tags used to draw the tree
        self._tree_tags = []

        # Put multiple edges on each level?
        self._compact = 0

        # If they didn't provide a main window, then set one up.
        if root is None:
            top = Tk()
            top.title("Chart View")

            def destroy1(e, top=top):
                top.destroy()

            def destroy2(top=top):
                top.destroy()

            top.bind("q", destroy1)
            b = Button(top, text="Done", command=destroy2)
            b.pack(side="bottom")
            self._root = top
        else:
            self._root = root

        # Create some fonts.
        self._init_fonts(root)

        # Create the chart canvas.
        (self._chart_sb, self._chart_canvas) = self._sb_canvas(self._root)
        self._chart_canvas["height"] = 300
        self._chart_canvas["closeenough"] = 15

        # Create the sentence canvas.
        if draw_sentence:
            cframe = Frame(self._root, relief="sunk", border=2)
            cframe.pack(fill="both", side="bottom")
            self._sentence_canvas = Canvas(cframe, height=50)
            self._sentence_canvas["background"] = "#e0e0e0"
            self._sentence_canvas.pack(fill="both")
            # self._sentence_canvas['height'] = self._sentence_height
        else:
            self._sentence_canvas = None

        # Create the tree canvas.
        if draw_tree:
            (sb, canvas) = self._sb_canvas(self._root, "n", "x")
            (self._tree_sb, self._tree_canvas) = (sb, canvas)
            self._tree_canvas["height"] = 200
        else:
            self._tree_canvas = None

        # Do some analysis to figure out how big the window should be
        self._analyze()
        self.draw()
        self._resize()
        self._grow()

        # Set up the configure callback, which will be called whenever
        # the window is resized.
        self._chart_canvas.bind("<Configure>", self._configure)

    def _init_fonts(self, root):
        self._boldfont = Font(family="helvetica", weight="bold", size=self._fontsize)
        self._font = Font(family="helvetica", size=self._fontsize)
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

    def _sb_canvas(self, root, expand="y", fill="both", side="bottom"):
        """
        Helper for __init__: construct a canvas with a scrollbar.
        """
        cframe = Frame(root, relief="sunk", border=2)
        cframe.pack(fill=fill, expand=expand, side=side)
        canvas = Canvas(cframe, background="#e0e0e0")

        # Give the canvas a scrollbar.
        sb = Scrollbar(cframe, orient="vertical")
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill=fill, expand="yes")

        # Connect the scrollbars to the canvas.
        sb["command"] = canvas.yview
        canvas["yscrollcommand"] = sb.set

        return (sb, canvas)

    def scroll_up(self, *e):
        self._chart_canvas.yview("scroll", -1, "units")

    def scroll_down(self, *e):
        self._chart_canvas.yview("scroll", 1, "units")

    def page_up(self, *e):
        self._chart_canvas.yview("scroll", -1, "pages")

    def page_down(self, *e):
        self._chart_canvas.yview("scroll", 1, "pages")

    def _grow(self):
        """
        Grow the window, if necessary
        """
        # Grow, if need-be
        N = self._chart.num_leaves()
        width = max(
            int(self._chart_canvas["width"]), N * self._unitsize + ChartView._MARGIN * 2
        )

        # It won't resize without the second (height) line, but I
        # don't understand why not.
        self._chart_canvas.configure(width=width)
        self._chart_canvas.configure(height=self._chart_canvas["height"])

        self._unitsize = (width - 2 * ChartView._MARGIN) / N

        # Reset the height for the sentence window.
        if self._sentence_canvas is not None:
            self._sentence_canvas["height"] = self._sentence_height

    def set_font_size(self, size):
        self._font.configure(size=-abs(size))
        self._boldfont.configure(size=-abs(size))
        self._sysfont.configure(size=-abs(size))
        self._analyze()
        self._grow()
        self.draw()

    def get_font_size(self):
        return abs(self._fontsize)

    def _configure(self, e):
        """
        The configure callback.  This is called whenever the window is
        resized.  It is also called when the window is first mapped.
        It figures out the unit size, and redraws the contents of each
        canvas.
        """
        N = self._chart.num_leaves()
        self._unitsize = (e.width - 2 * ChartView._MARGIN) / N
        self.draw()

    def update(self, chart=None):
        """
        Draw any edges that have not been drawn.  This is typically
        called when a after modifies the canvas that a CanvasView is
        displaying.  ``update`` will cause any edges that have been
        added to the chart to be drawn.

        If update is given a ``chart`` argument, then it will replace
        the current chart with the given chart.
        """
        if chart is not None:
            self._chart = chart
            self._edgelevels = []
            self._marks = {}
            self._analyze()
            self._grow()
            self.draw()
            self.erase_tree()
            self._resize()
        else:
            for edge in self._chart:
                if edge not in self._edgetags:
                    self._add_edge(edge)
            self._resize()

    def _edge_conflict(self, edge, lvl):
        """
        Return True if the given edge overlaps with any edge on the given
        level.  This is used by _add_edge to figure out what level a
        new edge should be added to.
        """
        (s1, e1) = edge.span()
        for otheredge in self._edgelevels[lvl]:
            (s2, e2) = otheredge.span()
            if (s1 <= s2 < e1) or (s2 <= s1 < e2) or (s1 == s2 == e1 == e2):
                return True
        return False

    def _analyze_edge(self, edge):
        """
        Given a new edge, recalculate:

            - _text_height
            - _unitsize (if the edge text is too big for the current
              _unitsize, then increase _unitsize)
        """
        c = self._chart_canvas

        if isinstance(edge, TreeEdge):
            lhs = edge.lhs()
            rhselts = []
            for elt in edge.rhs():
                if isinstance(elt, Nonterminal):
                    rhselts.append(str(elt.symbol()))
                else:
                    rhselts.append(repr(elt))
            rhs = " ".join(rhselts)
        else:
            lhs = edge.lhs()
            rhs = ""

        for s in (lhs, rhs):
            tag = c.create_text(
                0, 0, text=s, font=self._boldfont, anchor="nw", justify="left"
            )
            bbox = c.bbox(tag)
            c.delete(tag)
            width = bbox[2]  # + ChartView._LEAF_SPACING
            edgelen = max(edge.length(), 1)
            self._unitsize = max(self._unitsize, width / edgelen)
            self._text_height = max(self._text_height, bbox[3] - bbox[1])

    def _add_edge(self, edge, minlvl=0):
        """
        Add a single edge to the ChartView:

            - Call analyze_edge to recalculate display parameters
            - Find an available level
            - Call _draw_edge
        """
        # Do NOT show leaf edges in the chart.
        if isinstance(edge, LeafEdge):
            return

        if edge in self._edgetags:
            return
        self._analyze_edge(edge)
        self._grow()

        if not self._compact:
            self._edgelevels.append([edge])
            lvl = len(self._edgelevels) - 1
            self._draw_edge(edge, lvl)
            self._resize()
            return

        # Figure out what level to draw the edge on.
        lvl = 0
        while True:
            # If this level doesn't exist yet, create it.
            while lvl >= len(self._edgelevels):
                self._edgelevels.append([])
                self._resize()

            # Check if we can fit the edge in this level.
            if lvl >= minlvl and not self._edge_conflict(edge, lvl):
                # Go ahead and draw it.
                self._edgelevels[lvl].append(edge)
                break

            # Try the next level.
            lvl += 1

        self._draw_edge(edge, lvl)

    def view_edge(self, edge):
        level = None
        for i in range(len(self._edgelevels)):
            if edge in self._edgelevels[i]:
                level = i
                break
        if level is None:
            return
        # Try to view the new edge..
        y = (level + 1) * self._chart_level_size
        dy = self._text_height + 10
        self._chart_canvas.yview("moveto", 1.0)
        if self._chart_height != 0:
            self._chart_canvas.yview("moveto", (y - dy) / self._chart_height)

    def _draw_edge(self, edge, lvl):
        """
        Draw a single edge on the ChartView.
        """
        c = self._chart_canvas

        # Draw the arrow.
        x1 = edge.start() * self._unitsize + ChartView._MARGIN
        x2 = edge.end() * self._unitsize + ChartView._MARGIN
        if x2 == x1:
            x2 += max(4, self._unitsize / 5)
        y = (lvl + 1) * self._chart_level_size
        linetag = c.create_line(x1, y, x2, y, arrow="last", width=3)

        # Draw a label for the edge.
        if isinstance(edge, TreeEdge):
            rhs = []
            for elt in edge.rhs():
                if isinstance(elt, Nonterminal):
                    rhs.append(str(elt.symbol()))
                else:
                    rhs.append(repr(elt))
            pos = edge.dot()
        else:
            rhs = []
            pos = 0

        rhs1 = " ".join(rhs[:pos])
        rhs2 = " ".join(rhs[pos:])
        rhstag1 = c.create_text(x1 + 3, y, text=rhs1, font=self._font, anchor="nw")
        dotx = c.bbox(rhstag1)[2] + 6
        doty = (c.bbox(rhstag1)[1] + c.bbox(rhstag1)[3]) / 2
        dottag = c.create_oval(dotx - 2, doty - 2, dotx + 2, doty + 2)
        rhstag2 = c.create_text(dotx + 6, y, text=rhs2, font=self._font, anchor="nw")
        lhstag = c.create_text(
            (x1 + x2) / 2, y, text=str(edge.lhs()), anchor="s", font=self._boldfont
        )

        # Keep track of the edge's tags.
        self._edgetags[edge] = (linetag, rhstag1, dottag, rhstag2, lhstag)

        # Register a callback for clicking on the edge.
        def cb(event, self=self, edge=edge):
            self._fire_callbacks("select", edge)

        c.tag_bind(rhstag1, "<Button-1>", cb)
        c.tag_bind(rhstag2, "<Button-1>", cb)
        c.tag_bind(linetag, "<Button-1>", cb)
        c.tag_bind(dottag, "<Button-1>", cb)
        c.tag_bind(lhstag, "<Button-1>", cb)

        self._color_edge(edge)

    def _color_edge(self, edge, linecolor=None, textcolor=None):
        """
        Color in an edge with the given colors.
        If no colors are specified, use intelligent defaults
        (dependent on selection, etc.)
        """
        if edge not in self._edgetags:
            return
        c = self._chart_canvas

        if linecolor is not None and textcolor is not None:
            if edge in self._marks:
                linecolor = self._marks[edge]
            tags = self._edgetags[edge]
            c.itemconfig(tags[0], fill=linecolor)
            c.itemconfig(tags[1], fill=textcolor)
            c.itemconfig(tags[2], fill=textcolor, outline=textcolor)
            c.itemconfig(tags[3], fill=textcolor)
            c.itemconfig(tags[4], fill=textcolor)
            return
        else:
            N = self._chart.num_leaves()
            if edge in self._marks:
                self._color_edge(self._marks[edge])
            if edge.is_complete() and edge.span() == (0, N):
                self._color_edge(edge, "#084", "#042")
            elif isinstance(edge, LeafEdge):
                self._color_edge(edge, "#48c", "#246")
            else:
                self._color_edge(edge, "#00f", "#008")

    def mark_edge(self, edge, mark="#0df"):
        """
        Mark an edge
        """
        self._marks[edge] = mark
        self._color_edge(edge)

    def unmark_edge(self, edge=None):
        """
        Unmark an edge (or all edges)
        """
        if edge is None:
            old_marked_edges = list(self._marks.keys())
            self._marks = {}
            for edge in old_marked_edges:
                self._color_edge(edge)
        else:
            del self._marks[edge]
            self._color_edge(edge)

    def markonly_edge(self, edge, mark="#0df"):
        self.unmark_edge()
        self.mark_edge(edge, mark)

    def _analyze(self):
        """
        Analyze the sentence string, to figure out how big a unit needs
        to be, How big the tree should be, etc.
        """
        # Figure out the text height and the unit size.
        unitsize = 70  # min unitsize
        text_height = 0
        c = self._chart_canvas

        # Check against all tokens
        for leaf in self._chart.leaves():
            tag = c.create_text(
                0, 0, text=repr(leaf), font=self._font, anchor="nw", justify="left"
            )
            bbox = c.bbox(tag)
            c.delete(tag)
            width = bbox[2] + ChartView._LEAF_SPACING
            unitsize = max(width, unitsize)
            text_height = max(text_height, bbox[3] - bbox[1])

        self._unitsize = unitsize
        self._text_height = text_height
        self._sentence_height = self._text_height + 2 * ChartView._MARGIN

        # Check against edges.
        for edge in self._chart.edges():
            self._analyze_edge(edge)

        # Size of chart levels
        self._chart_level_size = self._text_height * 2

        # Default tree size..
        self._tree_height = 3 * (ChartView._TREE_LEVEL_SIZE + self._text_height)

        # Resize the scrollregions.
        self._resize()

    def _resize(self):
        """
        Update the scroll-regions for each canvas.  This ensures that
        everything is within a scroll-region, so the user can use the
        scrollbars to view the entire display.  This does *not*
        resize the window.
        """
        c = self._chart_canvas

        # Reset the chart scroll region
        width = self._chart.num_leaves() * self._unitsize + ChartView._MARGIN * 2

        levels = len(self._edgelevels)
        self._chart_height = (levels + 2) * self._chart_level_size
        c["scrollregion"] = (0, 0, width, self._chart_height)

        # Reset the tree scroll region
        if self._tree_canvas:
            self._tree_canvas["scrollregion"] = (0, 0, width, self._tree_height)

    def _draw_loclines(self):
        """
        Draw location lines.  These are vertical gridlines used to
        show where each location unit is.
        """
        BOTTOM = 50000
        c1 = self._tree_canvas
        c2 = self._sentence_canvas
        c3 = self._chart_canvas
        margin = ChartView._MARGIN
        self._loclines = []
        for i in range(0, self._chart.num_leaves() + 1):
            x = i * self._unitsize + margin

            if c1:
                t1 = c1.create_line(x, 0, x, BOTTOM)
                c1.tag_lower(t1)
            if c2:
                t2 = c2.create_line(x, 0, x, self._sentence_height)
                c2.tag_lower(t2)
            t3 = c3.create_line(x, 0, x, BOTTOM)
            c3.tag_lower(t3)
            t4 = c3.create_text(x + 2, 0, text=repr(i), anchor="nw", font=self._font)
            c3.tag_lower(t4)
            # if i % 4 == 0:
            #    if c1: c1.itemconfig(t1, width=2, fill='gray60')
            #    if c2: c2.itemconfig(t2, width=2, fill='gray60')
            #    c3.itemconfig(t3, width=2, fill='gray60')
            if i % 2 == 0:
                if c1:
                    c1.itemconfig(t1, fill="gray60")
                if c2:
                    c2.itemconfig(t2, fill="gray60")
                c3.itemconfig(t3, fill="gray60")
            else:
                if c1:
                    c1.itemconfig(t1, fill="gray80")
                if c2:
                    c2.itemconfig(t2, fill="gray80")
                c3.itemconfig(t3, fill="gray80")

    def _draw_sentence(self):
        """Draw the sentence string."""
        if self._chart.num_leaves() == 0:
            return
        c = self._sentence_canvas
        margin = ChartView._MARGIN
        y = ChartView._MARGIN

        for i, leaf in enumerate(self._chart.leaves()):
            x1 = i * self._unitsize + margin
            x2 = x1 + self._unitsize
            x = (x1 + x2) / 2
            tag = c.create_text(
                x, y, text=repr(leaf), font=self._font, anchor="n", justify="left"
            )
            bbox = c.bbox(tag)
            rt = c.create_rectangle(
                x1 + 2,
                bbox[1] - (ChartView._LEAF_SPACING / 2),
                x2 - 2,
                bbox[3] + (ChartView._LEAF_SPACING / 2),
                fill="#f0f0f0",
                outline="#f0f0f0",
            )
            c.tag_lower(rt)

    def erase_tree(self):
        for tag in self._tree_tags:
            self._tree_canvas.delete(tag)
        self._treetoks = []
        self._treetoks_edge = None
        self._treetoks_index = 0

    def draw_tree(self, edge=None):
        if edge is None and self._treetoks_edge is None:
            return
        if edge is None:
            edge = self._treetoks_edge

        # If it's a new edge, then get a new list of treetoks.
        if self._treetoks_edge != edge:
            self._treetoks = [t for t in self._chart.trees(edge) if isinstance(t, Tree)]
            self._treetoks_edge = edge
            self._treetoks_index = 0

        # Make sure there's something to draw.
        if len(self._treetoks) == 0:
            return

        # Erase the old tree.
        for tag in self._tree_tags:
            self._tree_canvas.delete(tag)

        # Draw the new tree.
        tree = self._treetoks[self._treetoks_index]
        self._draw_treetok(tree, edge.start())

        # Show how many trees are available for the edge.
        self._draw_treecycle()

        # Update the scroll region.
        w = self._chart.num_leaves() * self._unitsize + 2 * ChartView._MARGIN
        h = tree.height() * (ChartView._TREE_LEVEL_SIZE + self._text_height)
        self._tree_canvas["scrollregion"] = (0, 0, w, h)

    def cycle_tree(self):
        self._treetoks_index = (self._treetoks_index + 1) % len(self._treetoks)
        self.draw_tree(self._treetoks_edge)

    def _draw_treecycle(self):
        if len(self._treetoks) <= 1:
            return

        # Draw the label.
        label = "%d Trees" % len(self._treetoks)
        c = self._tree_canvas
        margin = ChartView._MARGIN
        right = self._chart.num_leaves() * self._unitsize + margin - 2
        tag = c.create_text(right, 2, anchor="ne", text=label, font=self._boldfont)
        self._tree_tags.append(tag)
        _, _, _, y = c.bbox(tag)

        # Draw the triangles.
        for i in range(len(self._treetoks)):
            x = right - 20 * (len(self._treetoks) - i - 1)
            if i == self._treetoks_index:
                fill = "#084"
            else:
                fill = "#fff"
            tag = c.create_polygon(
                x, y + 10, x - 5, y, x - 10, y + 10, fill=fill, outline="black"
            )
            self._tree_tags.append(tag)

            # Set up a callback: show the tree if they click on its
            # triangle.
            def cb(event, self=self, i=i):
                self._treetoks_index = i
                self.draw_tree()

            c.tag_bind(tag, "<Button-1>", cb)

    def _draw_treetok(self, treetok, index, depth=0):
        """
        :param index: The index of the first leaf in the tree.
        :return: The index of the first leaf after the tree.
        """
        c = self._tree_canvas
        margin = ChartView._MARGIN

        # Draw the children
        child_xs = []
        for child in treetok:
            if isinstance(child, Tree):
                child_x, index = self._draw_treetok(child, index, depth + 1)
                child_xs.append(child_x)
            else:
                child_xs.append((2 * index + 1) * self._unitsize / 2 + margin)
                index += 1

        # If we have children, then get the node's x by averaging their
        # node x's.  Otherwise, make room for ourselves.
        if child_xs:
            nodex = sum(child_xs) / len(child_xs)
        else:
            # [XX] breaks for null productions.
            nodex = (2 * index + 1) * self._unitsize / 2 + margin
            index += 1

        # Draw the node
        nodey = depth * (ChartView._TREE_LEVEL_SIZE + self._text_height)
        tag = c.create_text(
            nodex,
            nodey,
            anchor="n",
            justify="center",
            text=str(treetok.label()),
            fill="#042",
            font=self._boldfont,
        )
        self._tree_tags.append(tag)

        # Draw lines to the children.
        childy = nodey + ChartView._TREE_LEVEL_SIZE + self._text_height
        for childx, child in zip(child_xs, treetok):
            if isinstance(child, Tree) and child:
                # A "real" tree token:
                tag = c.create_line(
                    nodex,
                    nodey + self._text_height,
                    childx,
                    childy,
                    width=2,
                    fill="#084",
                )
                self._tree_tags.append(tag)
            if isinstance(child, Tree) and not child:
                # An unexpanded tree token:
                tag = c.create_line(
                    nodex,
                    nodey + self._text_height,
                    childx,
                    childy,
                    width=2,
                    fill="#048",
                    dash="2 3",
                )
                self._tree_tags.append(tag)
            if not isinstance(child, Tree):
                # A leaf:
                tag = c.create_line(
                    nodex,
                    nodey + self._text_height,
                    childx,
                    10000,
                    width=2,
                    fill="#084",
                )
                self._tree_tags.append(tag)

        return nodex, index

    def draw(self):
        """
        Draw everything (from scratch).
        """
        if self._tree_canvas:
            self._tree_canvas.delete("all")
            self.draw_tree()

        if self._sentence_canvas:
            self._sentence_canvas.delete("all")
            self._draw_sentence()

        self._chart_canvas.delete("all")
        self._edgetags = {}

        # Redraw any edges we erased.
        for lvl in range(len(self._edgelevels)):
            for edge in self._edgelevels[lvl]:
                self._draw_edge(edge, lvl)

        for edge in self._chart:
            self._add_edge(edge)

        self._draw_loclines()

    def add_callback(self, event, func):
        self._callbacks.setdefault(event, {})[func] = 1

    def remove_callback(self, event, func=None):
        if func is None:
            del self._callbacks[event]
        else:
            try:
                del self._callbacks[event][func]
            except:
                pass

    def _fire_callbacks(self, event, *args):
        if event not in self._callbacks:
            return
        for cb_func in list(self._callbacks[event].keys()):
            cb_func(*args)


#######################################################################
# Edge Rules
#######################################################################
# These version of the chart rules only apply to a specific edge.
# This lets the user select an edge, and then apply a rule.


class EdgeRule:
    """
    To create an edge rule, make an empty base class that uses
    EdgeRule as the first base class, and the basic rule as the
    second base class.  (Order matters!)
    """

    def __init__(self, edge):
        super = self.__class__.__bases__[1]
        self._edge = edge
        self.NUM_EDGES = super.NUM_EDGES - 1

    def apply(self, chart, grammar, *edges):
        super = self.__class__.__bases__[1]
        edges += (self._edge,)
        yield from super.apply(self, chart, grammar, *edges)

    def __str__(self):
        super = self.__class__.__bases__[1]
        return super.__str__(self)


class TopDownPredictEdgeRule(EdgeRule, TopDownPredictRule):
    pass


class BottomUpEdgeRule(EdgeRule, BottomUpPredictRule):
    pass


class BottomUpLeftCornerEdgeRule(EdgeRule, BottomUpPredictCombineRule):
    pass


class FundamentalEdgeRule(EdgeRule, SingleEdgeFundamentalRule):
    pass


#######################################################################
# Chart Parser Application
#######################################################################


class ChartParserApp:
    def __init__(self, grammar, tokens, title="Chart Parser Application"):
        # Initialize the parser
        self._init_parser(grammar, tokens)

        self._root = None
        try:
            # Create the root window.
            self._root = Tk()
            self._root.title(title)
            self._root.bind("<Control-q>", self.destroy)

            # Set up some frames.
            frame3 = Frame(self._root)
            frame2 = Frame(self._root)
            frame1 = Frame(self._root)
            frame3.pack(side="bottom", fill="none")
            frame2.pack(side="bottom", fill="x")
            frame1.pack(side="bottom", fill="both", expand=1)

            self._init_fonts(self._root)
            self._init_animation()
            self._init_chartview(frame1)
            self._init_rulelabel(frame2)
            self._init_buttons(frame3)
            self._init_menubar()

            self._matrix = None
            self._results = None

            # Set up keyboard bindings.
            self._init_bindings()

        except:
            print("Error creating Tree View")
            self.destroy()
            raise

    def destroy(self, *args):
        if self._root is None:
            return
        self._root.destroy()
        self._root = None

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self._root.mainloop(*args, **kwargs)

    # ////////////////////////////////////////////////////////////
    # Initialization Helpers
    # ////////////////////////////////////////////////////////////

    def _init_parser(self, grammar, tokens):
        self._grammar = grammar
        self._tokens = tokens
        self._reset_parser()

    def _reset_parser(self):
        self._cp = SteppingChartParser(self._grammar)
        self._cp.initialize(self._tokens)
        self._chart = self._cp.chart()

        # Insert LeafEdges before the parsing starts.
        for _new_edge in LeafInitRule().apply(self._chart, self._grammar):
            pass

        # The step iterator -- use this to generate new edges
        self._cpstep = self._cp.step()

        # The currently selected edge
        self._selection = None

    def _init_fonts(self, root):
        # See: <http://www.astro.washington.edu/owen/ROTKFolklore.html>
        self._sysfont = Font(font=Button()["font"])
        root.option_add("*Font", self._sysfont)

        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(root)
        self._size.set(self._sysfont.cget("size"))

        self._boldfont = Font(family="helvetica", weight="bold", size=self._size.get())
        self._font = Font(family="helvetica", size=self._size.get())

    def _init_animation(self):
        # Are we stepping? (default=yes)
        self._step = IntVar(self._root)
        self._step.set(1)

        # What's our animation speed (default=fast)
        self._animate = IntVar(self._root)
        self._animate.set(3)  # Default speed = fast

        # Are we currently animating?
        self._animating = 0

    def _init_chartview(self, parent):
        self._cv = ChartView(self._chart, parent, draw_tree=1, draw_sentence=1)
        self._cv.add_callback("select", self._click_cv_edge)

    def _init_rulelabel(self, parent):
        ruletxt = "Last edge generated by:"

        self._rulelabel1 = Label(parent, text=ruletxt, font=self._boldfont)
        self._rulelabel2 = Label(
            parent, width=40, relief="groove", anchor="w", font=self._boldfont
        )
        self._rulelabel1.pack(side="left")
        self._rulelabel2.pack(side="left")
        step = Checkbutton(parent, variable=self._step, text="Step")
        step.pack(side="right")

    def _init_buttons(self, parent):
        frame1 = Frame(parent)
        frame2 = Frame(parent)
        frame1.pack(side="bottom", fill="x")
        frame2.pack(side="top", fill="none")

        Button(
            frame1,
            text="Reset\nParser",
            background="#90c0d0",
            foreground="black",
            command=self.reset,
        ).pack(side="right")
        # Button(frame1, text='Pause',
        #               background='#90c0d0', foreground='black',
        #               command=self.pause).pack(side='left')

        Button(
            frame1,
            text="Top Down\nStrategy",
            background="#90c0d0",
            foreground="black",
            command=self.top_down_strategy,
        ).pack(side="left")
        Button(
            frame1,
            text="Bottom Up\nStrategy",
            background="#90c0d0",
            foreground="black",
            command=self.bottom_up_strategy,
        ).pack(side="left")
        Button(
            frame1,
            text="Bottom Up\nLeft-Corner Strategy",
            background="#90c0d0",
            foreground="black",
            command=self.bottom_up_leftcorner_strategy,
        ).pack(side="left")

        Button(
            frame2,
            text="Top Down Init\nRule",
            background="#90f090",
            foreground="black",
            command=self.top_down_init,
        ).pack(side="left")
        Button(
            frame2,
            text="Top Down Predict\nRule",
            background="#90f090",
            foreground="black",
            command=self.top_down_predict,
        ).pack(side="left")
        Frame(frame2, width=20).pack(side="left")

        Button(
            frame2,
            text="Bottom Up Predict\nRule",
            background="#90f090",
            foreground="black",
            command=self.bottom_up,
        ).pack(side="left")
        Frame(frame2, width=20).pack(side="left")

        Button(
            frame2,
            text="Bottom Up Left-Corner\nPredict Rule",
            background="#90f090",
            foreground="black",
            command=self.bottom_up_leftcorner,
        ).pack(side="left")
        Frame(frame2, width=20).pack(side="left")

        Button(
            frame2,
            text="Fundamental\nRule",
            background="#90f090",
            foreground="black",
            command=self.fundamental,
        ).pack(side="left")

    def _init_bindings(self):
        self._root.bind("<Up>", self._cv.scroll_up)
        self._root.bind("<Down>", self._cv.scroll_down)
        self._root.bind("<Prior>", self._cv.page_up)
        self._root.bind("<Next>", self._cv.page_down)
        self._root.bind("<Control-q>", self.destroy)
        self._root.bind("<Control-x>", self.destroy)
        self._root.bind("<F1>", self.help)

        self._root.bind("<Control-s>", self.save_chart)
        self._root.bind("<Control-o>", self.load_chart)
        self._root.bind("<Control-r>", self.reset)

        self._root.bind("t", self.top_down_strategy)
        self._root.bind("b", self.bottom_up_strategy)
        self._root.bind("c", self.bottom_up_leftcorner_strategy)
        self._root.bind("<space>", self._stop_animation)

        self._root.bind("<Control-g>", self.edit_grammar)
        self._root.bind("<Control-t>", self.edit_sentence)

        # Animation speed control
        self._root.bind("-", lambda e, a=self._animate: a.set(1))
        self._root.bind("=", lambda e, a=self._animate: a.set(2))
        self._root.bind("+", lambda e, a=self._animate: a.set(3))

        # Step control
        self._root.bind("s", lambda e, s=self._step: s.set(not s.get()))

    def _init_menubar(self):
        menubar = Menu(self._root)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(
            label="Save Chart",
            underline=0,
            command=self.save_chart,
            accelerator="Ctrl-s",
        )
        filemenu.add_command(
            label="Load Chart",
            underline=0,
            command=self.load_chart,
            accelerator="Ctrl-o",
        )
        filemenu.add_command(
            label="Reset Chart", underline=0, command=self.reset, accelerator="Ctrl-r"
        )
        filemenu.add_separator()
        filemenu.add_command(label="Save Grammar", command=self.save_grammar)
        filemenu.add_command(label="Load Grammar", command=self.load_grammar)
        filemenu.add_separator()
        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-x"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(
            label="Edit Grammar",
            underline=5,
            command=self.edit_grammar,
            accelerator="Ctrl-g",
        )
        editmenu.add_command(
            label="Edit Text",
            underline=5,
            command=self.edit_sentence,
            accelerator="Ctrl-t",
        )
        menubar.add_cascade(label="Edit", underline=0, menu=editmenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_command(
            label="Chart Matrix", underline=6, command=self.view_matrix
        )
        viewmenu.add_command(label="Results", underline=0, command=self.view_results)
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        rulemenu = Menu(menubar, tearoff=0)
        rulemenu.add_command(
            label="Top Down Strategy",
            underline=0,
            command=self.top_down_strategy,
            accelerator="t",
        )
        rulemenu.add_command(
            label="Bottom Up Strategy",
            underline=0,
            command=self.bottom_up_strategy,
            accelerator="b",
        )
        rulemenu.add_command(
            label="Bottom Up Left-Corner Strategy",
            underline=0,
            command=self.bottom_up_leftcorner_strategy,
            accelerator="c",
        )
        rulemenu.add_separator()
        rulemenu.add_command(label="Bottom Up Rule", command=self.bottom_up)
        rulemenu.add_command(
            label="Bottom Up Left-Corner Rule", command=self.bottom_up_leftcorner
        )
        rulemenu.add_command(label="Top Down Init Rule", command=self.top_down_init)
        rulemenu.add_command(
            label="Top Down Predict Rule", command=self.top_down_predict
        )
        rulemenu.add_command(label="Fundamental Rule", command=self.fundamental)
        menubar.add_cascade(label="Apply", underline=0, menu=rulemenu)

        animatemenu = Menu(menubar, tearoff=0)
        animatemenu.add_checkbutton(
            label="Step", underline=0, variable=self._step, accelerator="s"
        )
        animatemenu.add_separator()
        animatemenu.add_radiobutton(
            label="No Animation", underline=0, variable=self._animate, value=0
        )
        animatemenu.add_radiobutton(
            label="Slow Animation",
            underline=0,
            variable=self._animate,
            value=1,
            accelerator="-",
        )
        animatemenu.add_radiobutton(
            label="Normal Animation",
            underline=0,
            variable=self._animate,
            value=2,
            accelerator="=",
        )
        animatemenu.add_radiobutton(
            label="Fast Animation",
            underline=0,
            variable=self._animate,
            value=3,
            accelerator="+",
        )
        menubar.add_cascade(label="Animate", underline=1, menu=animatemenu)

        zoommenu = Menu(menubar, tearoff=0)
        zoommenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=12,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=14,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=18,
            command=self.resize,
        )
        zoommenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        menubar.add_cascade(label="Zoom", underline=0, menu=zoommenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        helpmenu.add_command(
            label="Instructions", underline=0, command=self.help, accelerator="F1"
        )
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        self._root.config(menu=menubar)

    # ////////////////////////////////////////////////////////////
    # Selection Handling
    # ////////////////////////////////////////////////////////////

    def _click_cv_edge(self, edge):
        if edge != self._selection:
            # Clicking on a new edge selects it.
            self._select_edge(edge)
        else:
            # Repeated clicks on one edge cycle its trees.
            self._cv.cycle_tree()
            # [XX] this can get confused if animation is running
            # faster than the callbacks...

    def _select_matrix_edge(self, edge):
        self._select_edge(edge)
        self._cv.view_edge(edge)

    def _select_edge(self, edge):
        self._selection = edge
        # Update the chart view.
        self._cv.markonly_edge(edge, "#f00")
        self._cv.draw_tree(edge)
        # Update the matrix view.
        if self._matrix:
            self._matrix.markonly_edge(edge)
        if self._matrix:
            self._matrix.view_edge(edge)

    def _deselect_edge(self):
        self._selection = None
        # Update the chart view.
        self._cv.unmark_edge()
        self._cv.erase_tree()
        # Update the matrix view
        if self._matrix:
            self._matrix.unmark_edge()

    def _show_new_edge(self, edge):
        self._display_rule(self._cp.current_chartrule())
        # Update the chart view.
        self._cv.update()
        self._cv.draw_tree(edge)
        self._cv.markonly_edge(edge, "#0df")
        self._cv.view_edge(edge)
        # Update the matrix view.
        if self._matrix:
            self._matrix.update()
        if self._matrix:
            self._matrix.markonly_edge(edge)
        if self._matrix:
            self._matrix.view_edge(edge)
        # Update the results view.
        if self._results:
            self._results.update(edge)

    # ////////////////////////////////////////////////////////////
    # Help/usage
    # ////////////////////////////////////////////////////////////

    def help(self, *e):
        self._animating = 0
        # The default font's not very legible; try using 'fixed' instead.
        try:
            ShowText(
                self._root,
                "Help: Chart Parser Application",
                (__doc__ or "").strip(),
                width=75,
                font="fixed",
            )
        except:
            ShowText(
                self._root,
                "Help: Chart Parser Application",
                (__doc__ or "").strip(),
                width=75,
            )

    def about(self, *e):
        ABOUT = "NLTK Chart Parser Application\n" + "Written by Edward Loper"
        showinfo("About: Chart Parser Application", ABOUT)

    # ////////////////////////////////////////////////////////////
    # File Menu
    # ////////////////////////////////////////////////////////////

    CHART_FILE_TYPES = [("Pickle file", ".pickle"), ("All files", "*")]
    GRAMMAR_FILE_TYPES = [
        ("Plaintext grammar file", ".cfg"),
        ("Pickle file", ".pickle"),
        ("All files", "*"),
    ]

    def load_chart(self, *args):
        "Load a chart from a pickle file"
        filename = askopenfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            with open(filename, "rb") as infile:
                chart = pickle.load(infile)
            self._chart = chart
            self._cv.update(chart)
            if self._matrix:
                self._matrix.set_chart(chart)
            if self._matrix:
                self._matrix.deselect_cell()
            if self._results:
                self._results.set_chart(chart)
            self._cp.set_chart(chart)
        except Exception as e:
            raise
            showerror("Error Loading Chart", "Unable to open file: %r" % filename)

    def save_chart(self, *args):
        "Save a chart to a pickle file"
        filename = asksaveasfilename(
            filetypes=self.CHART_FILE_TYPES, defaultextension=".pickle"
        )
        if not filename:
            return
        try:
            with open(filename, "wb") as outfile:
                pickle.dump(self._chart, outfile)
        except Exception as e:
            raise
            showerror("Error Saving Chart", "Unable to open file: %r" % filename)

    def load_grammar(self, *args):
        "Load a grammar from a pickle file"
        filename = askopenfilename(
            filetypes=self.GRAMMAR_FILE_TYPES, defaultextension=".cfg"
        )
        if not filename:
            return
        try:
            if filename.endswith(".pickle"):
                with open(filename, "rb") as infile:
                    grammar = pickle.load(infile)
            else:
                with open(filename) as infile:
                    grammar = CFG.fromstring(infile.read())
            self.set_grammar(grammar)
        except Exception as e:
            showerror("Error Loading Grammar", "Unable to open file: %r" % filename)

    def save_grammar(self, *args):
        filename = asksaveasfilename(
            filetypes=self.GRAMMAR_FILE_TYPES, defaultextension=".cfg"
        )
        if not filename:
            return
        try:
            if filename.endswith(".pickle"):
                with open(filename, "wb") as outfile:
                    pickle.dump((self._chart, self._tokens), outfile)
            else:
                with open(filename, "w") as outfile:
                    prods = self._grammar.productions()
                    start = [p for p in prods if p.lhs() == self._grammar.start()]
                    rest = [p for p in prods if p.lhs() != self._grammar.start()]
                    for prod in start:
                        outfile.write("%s\n" % prod)
                    for prod in rest:
                        outfile.write("%s\n" % prod)
        except Exception as e:
            showerror("Error Saving Grammar", "Unable to open file: %r" % filename)

    def reset(self, *args):
        self._animating = 0
        self._reset_parser()
        self._cv.update(self._chart)
        if self._matrix:
            self._matrix.set_chart(self._chart)
        if self._matrix:
            self._matrix.deselect_cell()
        if self._results:
            self._results.set_chart(self._chart)

    # ////////////////////////////////////////////////////////////
    # Edit
    # ////////////////////////////////////////////////////////////

    def edit_grammar(self, *e):
        CFGEditor(self._root, self._grammar, self.set_grammar)

    def set_grammar(self, grammar):
        self._grammar = grammar
        self._cp.set_grammar(grammar)
        if self._results:
            self._results.set_grammar(grammar)

    def edit_sentence(self, *e):
        sentence = " ".join(self._tokens)
        title = "Edit Text"
        instr = "Enter a new sentence to parse."
        EntryDialog(self._root, sentence, instr, self.set_sentence, title)

    def set_sentence(self, sentence):
        self._tokens = list(sentence.split())
        self.reset()

    # ////////////////////////////////////////////////////////////
    # View Menu
    # ////////////////////////////////////////////////////////////

    def view_matrix(self, *e):
        if self._matrix is not None:
            self._matrix.destroy()
        self._matrix = ChartMatrixView(self._root, self._chart)
        self._matrix.add_callback("select", self._select_matrix_edge)

    def view_results(self, *e):
        if self._results is not None:
            self._results.destroy()
        self._results = ChartResultsView(self._root, self._chart, self._grammar)

    # ////////////////////////////////////////////////////////////
    # Zoom Menu
    # ////////////////////////////////////////////////////////////

    def resize(self):
        self._animating = 0
        self.set_font_size(self._size.get())

    def set_font_size(self, size):
        self._cv.set_font_size(size)
        self._font.configure(size=-abs(size))
        self._boldfont.configure(size=-abs(size))
        self._sysfont.configure(size=-abs(size))

    def get_font_size(self):
        return abs(self._size.get())

    # ////////////////////////////////////////////////////////////
    # Parsing
    # ////////////////////////////////////////////////////////////

    def apply_strategy(self, strategy, edge_strategy=None):
        # If we're animating, then stop.
        if self._animating:
            self._animating = 0
            return

        # Clear the rule display & mark.
        self._display_rule(None)
        # self._cv.unmark_edge()

        if self._step.get():
            selection = self._selection
            if (selection is not None) and (edge_strategy is not None):
                # Apply the given strategy to the selected edge.
                self._cp.set_strategy([edge_strategy(selection)])
                newedge = self._apply_strategy()

                # If it failed, then clear the selection.
                if newedge is None:
                    self._cv.unmark_edge()
                    self._selection = None
            else:
                self._cp.set_strategy(strategy)
                self._apply_strategy()

        else:
            self._cp.set_strategy(strategy)
            if self._animate.get():
                self._animating = 1
                self._animate_strategy()
            else:
                for edge in self._cpstep:
                    if edge is None:
                        break
                self._cv.update()
                if self._matrix:
                    self._matrix.update()
                if self._results:
                    self._results.update()

    def _stop_animation(self, *e):
        self._animating = 0

    def _animate_strategy(self, speed=1):
        if self._animating == 0:
            return
        if self._apply_strategy() is not None:
            if self._animate.get() == 0 or self._step.get() == 1:
                return
            if self._animate.get() == 1:
                self._root.after(3000, self._animate_strategy)
            elif self._animate.get() == 2:
                self._root.after(1000, self._animate_strategy)
            else:
                self._root.after(20, self._animate_strategy)

    def _apply_strategy(self):
        new_edge = next(self._cpstep)

        if new_edge is not None:
            self._show_new_edge(new_edge)
        return new_edge

    def _display_rule(self, rule):
        if rule is None:
            self._rulelabel2["text"] = ""
        else:
            name = str(rule)
            self._rulelabel2["text"] = name
            size = self._cv.get_font_size()

    # ////////////////////////////////////////////////////////////
    # Parsing Strategies
    # ////////////////////////////////////////////////////////////

    # Basic rules:
    _TD_INIT = [TopDownInitRule()]
    _TD_PREDICT = [TopDownPredictRule()]
    _BU_RULE = [BottomUpPredictRule()]
    _BU_LC_RULE = [BottomUpPredictCombineRule()]
    _FUNDAMENTAL = [SingleEdgeFundamentalRule()]

    # Complete strategies:
    _TD_STRATEGY = _TD_INIT + _TD_PREDICT + _FUNDAMENTAL
    _BU_STRATEGY = _BU_RULE + _FUNDAMENTAL
    _BU_LC_STRATEGY = _BU_LC_RULE + _FUNDAMENTAL

    # Button callback functions:
    def top_down_init(self, *e):
        self.apply_strategy(self._TD_INIT, None)

    def top_down_predict(self, *e):
        self.apply_strategy(self._TD_PREDICT, TopDownPredictEdgeRule)

    def bottom_up(self, *e):
        self.apply_strategy(self._BU_RULE, BottomUpEdgeRule)

    def bottom_up_leftcorner(self, *e):
        self.apply_strategy(self._BU_LC_RULE, BottomUpLeftCornerEdgeRule)

    def fundamental(self, *e):
        self.apply_strategy(self._FUNDAMENTAL, FundamentalEdgeRule)

    def bottom_up_strategy(self, *e):
        self.apply_strategy(self._BU_STRATEGY, BottomUpEdgeRule)

    def bottom_up_leftcorner_strategy(self, *e):
        self.apply_strategy(self._BU_LC_STRATEGY, BottomUpLeftCornerEdgeRule)

    def top_down_strategy(self, *e):
        self.apply_strategy(self._TD_STRATEGY, TopDownPredictEdgeRule)


def app():
    grammar = CFG.fromstring(
        """
    # Grammatical productions.
        S -> NP VP
        VP -> VP PP | V NP | V
        NP -> Det N | NP PP
        PP -> P NP
    # Lexical productions.
        NP -> 'John' | 'I'
        Det -> 'the' | 'my' | 'a'
        N -> 'dog' | 'cookie' | 'table' | 'cake' | 'fork'
        V -> 'ate' | 'saw'
        P -> 'on' | 'under' | 'with'
    """
    )

    sent = "John ate the cake on the table with a fork"
    sent = "John ate the cake on the table"
    tokens = list(sent.split())

    print("grammar= (")
    for rule in grammar.productions():
        print(("    ", repr(rule) + ","))
    print(")")
    print("tokens = %r" % tokens)
    print('Calling "ChartParserApp(grammar, tokens)"...')
    ChartParserApp(grammar, tokens).mainloop()


if __name__ == "__main__":
    app()

    # Chart comparer:
    # charts = ['/tmp/earley.pickle',
    #          '/tmp/topdown.pickle',
    #          '/tmp/bottomup.pickle']
    # ChartComparer(*charts).mainloop()

    # import profile
    # profile.run('demo2()', '/tmp/profile.out')
    # import pstats
    # p = pstats.Stats('/tmp/profile.out')
    # p.strip_dirs().sort_stats('time', 'cum').print_stats(60)
    # p.strip_dirs().sort_stats('cum', 'time').print_stats(60)

__all__ = ["app"]

# === NexusCore/openenv\Lib\site-packages\nltk\app\chunkparser_app.py ===
# Natural Language Toolkit: Regexp Chunk Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring the regular expression based chunk
parser ``nltk.chunk.RegexpChunkParser``.
"""

# Todo: Add a way to select the development set from the menubar.  This
# might just need to be a selection box (conll vs treebank etc) plus
# configuration parameters to select what's being chunked (eg VP vs NP)
# and what part of the data is being used as the development set.

import random
import re
import textwrap
import time
from tkinter import (
    Button,
    Canvas,
    Checkbutton,
    Frame,
    IntVar,
    Label,
    Menu,
    Scrollbar,
    Text,
    Tk,
)
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.font import Font

from nltk.chunk import ChunkScore, RegexpChunkParser
from nltk.chunk.regexp import RegexpChunkRule
from nltk.corpus import conll2000, treebank_chunk
from nltk.draw.util import ShowText
from nltk.tree import Tree
from nltk.util import in_idle


class RegexpChunkApp:
    """
    A graphical tool for exploring the regular expression based chunk
    parser ``nltk.chunk.RegexpChunkParser``.

    See ``HELP`` for instructional text.
    """

    ##/////////////////////////////////////////////////////////////////
    ##  Help Text
    ##/////////////////////////////////////////////////////////////////

    #: A dictionary mapping from part of speech tags to descriptions,
    #: which is used in the help text.  (This should probably live with
    #: the conll and/or treebank corpus instead.)
    TAGSET = {
        "CC": "Coordinating conjunction",
        "PRP$": "Possessive pronoun",
        "CD": "Cardinal number",
        "RB": "Adverb",
        "DT": "Determiner",
        "RBR": "Adverb, comparative",
        "EX": "Existential there",
        "RBS": "Adverb, superlative",
        "FW": "Foreign word",
        "RP": "Particle",
        "JJ": "Adjective",
        "TO": "to",
        "JJR": "Adjective, comparative",
        "UH": "Interjection",
        "JJS": "Adjective, superlative",
        "VB": "Verb, base form",
        "LS": "List item marker",
        "VBD": "Verb, past tense",
        "MD": "Modal",
        "NNS": "Noun, plural",
        "NN": "Noun, singular or mass",
        "VBN": "Verb, past participle",
        "VBZ": "Verb,3rd ps. sing. present",
        "NNP": "Proper noun, singular",
        "NNPS": "Proper noun plural",
        "WDT": "wh-determiner",
        "PDT": "Predeterminer",
        "WP": "wh-pronoun",
        "POS": "Possessive ending",
        "WP$": "Possessive wh-pronoun",
        "PRP": "Personal pronoun",
        "WRB": "wh-adverb",
        "(": "open parenthesis",
        ")": "close parenthesis",
        "``": "open quote",
        ",": "comma",
        "''": "close quote",
        ".": "period",
        "#": "pound sign (currency marker)",
        "$": "dollar sign (currency marker)",
        "IN": "Preposition/subord. conjunction",
        "SYM": "Symbol (mathematical or scientific)",
        "VBG": "Verb, gerund/present participle",
        "VBP": "Verb, non-3rd ps. sing. present",
        ":": "colon",
    }

    #: Contents for the help box.  This is a list of tuples, one for
    #: each help page, where each tuple has four elements:
    #:   - A title (displayed as a tab)
    #:   - A string description of tabstops (see Tkinter.Text for details)
    #:   - The text contents for the help page.  You can use expressions
    #:     like <red>...</red> to colorize the text; see ``HELP_AUTOTAG``
    #:     for a list of tags you can use for colorizing.
    HELP = [
        (
            "Help",
            "20",
            "Welcome to the regular expression chunk-parser grammar editor.  "
            "You can use this editor to develop and test chunk parser grammars "
            "based on NLTK's RegexpChunkParser class.\n\n"
            # Help box.
            "Use this box ('Help') to learn more about the editor; click on the "
            "tabs for help on specific topics:"
            "<indent>\n"
            "Rules: grammar rule types\n"
            "Regexps: regular expression syntax\n"
            "Tags: part of speech tags\n</indent>\n"
            # Grammar.
            "Use the upper-left box ('Grammar') to edit your grammar.  "
            "Each line of your grammar specifies a single 'rule', "
            "which performs an action such as creating a chunk or merging "
            "two chunks.\n\n"
            # Dev set.
            "The lower-left box ('Development Set') runs your grammar on the "
            "development set, and displays the results.  "
            "Your grammar's chunks are <highlight>highlighted</highlight>, and "
            "the correct (gold standard) chunks are "
            "<underline>underlined</underline>.  If they "
            "match, they are displayed in <green>green</green>; otherwise, "
            "they are displayed in <red>red</red>.  The box displays a single "
            "sentence from the development set at a time; use the scrollbar or "
            "the next/previous buttons view additional sentences.\n\n"
            # Performance
            "The lower-right box ('Evaluation') tracks the performance of "
            "your grammar on the development set.  The 'precision' axis "
            "indicates how many of your grammar's chunks are correct; and "
            "the 'recall' axis indicates how many of the gold standard "
            "chunks your system generated.  Typically, you should try to "
            "design a grammar that scores high on both metrics.  The "
            "exact precision and recall of the current grammar, as well "
            "as their harmonic mean (the 'f-score'), are displayed in "
            "the status bar at the bottom of the window.",
        ),
        (
            "Rules",
            "10",
            "<h1>{...regexp...}</h1>"
            "<indent>\nChunk rule: creates new chunks from words matching "
            "regexp.</indent>\n\n"
            "<h1>}...regexp...{</h1>"
            "<indent>\nStrip rule: removes words matching regexp from existing "
            "chunks.</indent>\n\n"
            "<h1>...regexp1...}{...regexp2...</h1>"
            "<indent>\nSplit rule: splits chunks that match regexp1 followed by "
            "regexp2 in two.</indent>\n\n"
            "<h1>...regexp...{}...regexp...</h1>"
            "<indent>\nMerge rule: joins consecutive chunks that match regexp1 "
            "and regexp2</indent>\n",
        ),
        (
            "Regexps",
            "10 60",
            # "Regular Expression Syntax Summary:\n\n"
            "<h1>Pattern\t\tMatches...</h1>\n"
            "<hangindent>"
            "\t<<var>T</var>>\ta word with tag <var>T</var> "
            "(where <var>T</var> may be a regexp).\n"
            "\t<var>x</var>?\tan optional <var>x</var>\n"
            "\t<var>x</var>+\ta sequence of 1 or more <var>x</var>'s\n"
            "\t<var>x</var>*\ta sequence of 0 or more <var>x</var>'s\n"
            "\t<var>x</var>|<var>y</var>\t<var>x</var> or <var>y</var>\n"
            "\t.\tmatches any character\n"
            "\t(<var>x</var>)\tTreats <var>x</var> as a group\n"
            "\t# <var>x...</var>\tTreats <var>x...</var> "
            "(to the end of the line) as a comment\n"
            "\t\\<var>C</var>\tmatches character <var>C</var> "
            "(useful when <var>C</var> is a special character "
            "like + or #)\n"
            "</hangindent>"
            "\n<h1>Examples:</h1>\n"
            "<hangindent>"
            "\t<regexp><NN></regexp>\n"
            '\t\tMatches <match>"cow/NN"</match>\n'
            '\t\tMatches <match>"green/NN"</match>\n'
            "\t<regexp><VB.*></regexp>\n"
            '\t\tMatches <match>"eating/VBG"</match>\n'
            '\t\tMatches <match>"ate/VBD"</match>\n'
            "\t<regexp><IN><DT><NN></regexp>\n"
            '\t\tMatches <match>"on/IN the/DT car/NN"</match>\n'
            "\t<regexp><RB>?<VBD></regexp>\n"
            '\t\tMatches <match>"ran/VBD"</match>\n'
            '\t\tMatches <match>"slowly/RB ate/VBD"</match>\n'
            r"\t<regexp><\#><CD> # This is a comment...</regexp>\n"
            '\t\tMatches <match>"#/# 100/CD"</match>\n'
            "</hangindent>",
        ),
        (
            "Tags",
            "10 60",
            "<h1>Part of Speech Tags:</h1>\n"
            + "<hangindent>"
            + "<<TAGSET>>"
            + "</hangindent>\n",  # this gets auto-substituted w/ self.TAGSET
        ),
    ]

    HELP_AUTOTAG = [
        ("red", dict(foreground="#a00")),
        ("green", dict(foreground="#080")),
        ("highlight", dict(background="#ddd")),
        ("underline", dict(underline=True)),
        ("h1", dict(underline=True)),
        ("indent", dict(lmargin1=20, lmargin2=20)),
        ("hangindent", dict(lmargin1=0, lmargin2=60)),
        ("var", dict(foreground="#88f")),
        ("regexp", dict(foreground="#ba7")),
        ("match", dict(foreground="#6a6")),
    ]

    ##/////////////////////////////////////////////////////////////////
    ##  Config Parameters
    ##/////////////////////////////////////////////////////////////////

    _EVAL_DELAY = 1
    """If the user has not pressed any key for this amount of time (in
       seconds), and the current grammar has not been evaluated, then
       the eval demon will evaluate it."""

    _EVAL_CHUNK = 15
    """The number of sentences that should be evaluated by the eval
       demon each time it runs."""
    _EVAL_FREQ = 0.2
    """The frequency (in seconds) at which the eval demon is run"""
    _EVAL_DEMON_MIN = 0.02
    """The minimum amount of time that the eval demon should take each time
       it runs -- if it takes less than this time, _EVAL_CHUNK will be
       modified upwards."""
    _EVAL_DEMON_MAX = 0.04
    """The maximum amount of time that the eval demon should take each time
       it runs -- if it takes more than this time, _EVAL_CHUNK will be
       modified downwards."""

    _GRAMMARBOX_PARAMS = dict(
        width=40,
        height=12,
        background="#efe",
        highlightbackground="#efe",
        highlightthickness=1,
        relief="groove",
        border=2,
        wrap="word",
    )
    _HELPBOX_PARAMS = dict(
        width=15,
        height=15,
        background="#efe",
        highlightbackground="#efe",
        foreground="#555",
        highlightthickness=1,
        relief="groove",
        border=2,
        wrap="word",
    )
    _DEVSETBOX_PARAMS = dict(
        width=70,
        height=10,
        background="#eef",
        highlightbackground="#eef",
        highlightthickness=1,
        relief="groove",
        border=2,
        wrap="word",
        tabs=(30,),
    )
    _STATUS_PARAMS = dict(background="#9bb", relief="groove", border=2)
    _FONT_PARAMS = dict(family="helvetica", size=-20)
    _FRAME_PARAMS = dict(background="#777", padx=2, pady=2, border=3)
    _EVALBOX_PARAMS = dict(
        background="#eef",
        highlightbackground="#eef",
        highlightthickness=1,
        relief="groove",
        border=2,
        width=300,
        height=280,
    )
    _BUTTON_PARAMS = dict(
        background="#777", activebackground="#777", highlightbackground="#777"
    )
    _HELPTAB_BG_COLOR = "#aba"
    _HELPTAB_FG_COLOR = "#efe"

    _HELPTAB_FG_PARAMS = dict(background="#efe")
    _HELPTAB_BG_PARAMS = dict(background="#aba")
    _HELPTAB_SPACER = 6

    def normalize_grammar(self, grammar):
        # Strip comments
        grammar = re.sub(r"((\\.|[^#])*)(#.*)?", r"\1", grammar)
        # Normalize whitespace
        grammar = re.sub(" +", " ", grammar)
        grammar = re.sub(r"\n\s+", r"\n", grammar)
        grammar = grammar.strip()
        # [xx] Hack: automatically backslash $!
        grammar = re.sub(r"([^\\])\$", r"\1\\$", grammar)
        return grammar

    def __init__(
        self,
        devset_name="conll2000",
        devset=None,
        grammar="",
        chunk_label="NP",
        tagset=None,
    ):
        """
        :param devset_name: The name of the development set; used for
            display & for save files.  If either the name 'treebank'
            or the name 'conll2000' is used, and devset is None, then
            devset will be set automatically.
        :param devset: A list of chunked sentences
        :param grammar: The initial grammar to display.
        :param tagset: Dictionary from tags to string descriptions, used
            for the help page.  Defaults to ``self.TAGSET``.
        """
        self._chunk_label = chunk_label

        if tagset is None:
            tagset = self.TAGSET
        self.tagset = tagset

        # Named development sets:
        if devset is None:
            if devset_name == "conll2000":
                devset = conll2000.chunked_sents("train.txt")  # [:100]
            elif devset == "treebank":
                devset = treebank_chunk.chunked_sents()  # [:100]
            else:
                raise ValueError("Unknown development set %s" % devset_name)

        self.chunker = None
        """The chunker built from the grammar string"""

        self.grammar = grammar
        """The unparsed grammar string"""

        self.normalized_grammar = None
        """A normalized version of ``self.grammar``."""

        self.grammar_changed = 0
        """The last time() that the grammar was changed."""

        self.devset = devset
        """The development set -- a list of chunked sentences."""

        self.devset_name = devset_name
        """The name of the development set (for save files)."""

        self.devset_index = -1
        """The index into the development set of the first instance
           that's currently being viewed."""

        self._last_keypress = 0
        """The time() when a key was most recently pressed"""

        self._history = []
        """A list of (grammar, precision, recall, fscore) tuples for
           grammars that the user has already tried."""

        self._history_index = 0
        """When the user is scrolling through previous grammars, this
           is used to keep track of which grammar they're looking at."""

        self._eval_grammar = None
        """The grammar that is being currently evaluated by the eval
           demon."""

        self._eval_normalized_grammar = None
        """A normalized copy of ``_eval_grammar``."""

        self._eval_index = 0
        """The index of the next sentence in the development set that
           should be looked at by the eval demon."""

        self._eval_score = ChunkScore(chunk_label=chunk_label)
        """The ``ChunkScore`` object that's used to keep track of the score
        of the current grammar on the development set."""

        # Set up the main window.
        top = self.top = Tk()
        top.geometry("+50+50")
        top.title("Regexp Chunk Parser App")
        top.bind("<Control-q>", self.destroy)

        # Variable that restricts how much of the devset we look at.
        self._devset_size = IntVar(top)
        self._devset_size.set(100)

        # Set up all the tkinter widgets
        self._init_fonts(top)
        self._init_widgets(top)
        self._init_bindings(top)
        self._init_menubar(top)
        self.grammarbox.focus()

        # If a grammar was given, then display it.
        if grammar:
            self.grammarbox.insert("end", grammar + "\n")
            self.grammarbox.mark_set("insert", "1.0")

        # Display the first item in the development set
        self.show_devset(0)
        self.update()

    def _init_bindings(self, top):
        top.bind("<Control-n>", self._devset_next)
        top.bind("<Control-p>", self._devset_prev)
        top.bind("<Control-t>", self.toggle_show_trace)
        top.bind("<KeyPress>", self.update)
        top.bind("<Control-s>", lambda e: self.save_grammar())
        top.bind("<Control-o>", lambda e: self.load_grammar())
        self.grammarbox.bind("<Control-t>", self.toggle_show_trace)
        self.grammarbox.bind("<Control-n>", self._devset_next)
        self.grammarbox.bind("<Control-p>", self._devset_prev)

        # Redraw the eval graph when the window size changes
        self.evalbox.bind("<Configure>", self._eval_plot)

    def _init_fonts(self, top):
        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(top)
        self._size.set(20)
        self._font = Font(family="helvetica", size=-self._size.get())
        self._smallfont = Font(
            family="helvetica", size=-(int(self._size.get() * 14 // 20))
        )

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Reset Application", underline=0, command=self.reset)
        filemenu.add_command(
            label="Save Current Grammar",
            underline=0,
            accelerator="Ctrl-s",
            command=self.save_grammar,
        )
        filemenu.add_command(
            label="Load Grammar",
            underline=0,
            accelerator="Ctrl-o",
            command=self.load_grammar,
        )

        filemenu.add_command(
            label="Save Grammar History", underline=13, command=self.save_history
        )

        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=16,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=20,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=34,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        devsetmenu = Menu(menubar, tearoff=0)
        devsetmenu.add_radiobutton(
            label="50 sentences",
            variable=self._devset_size,
            value=50,
            command=self.set_devset_size,
        )
        devsetmenu.add_radiobutton(
            label="100 sentences",
            variable=self._devset_size,
            value=100,
            command=self.set_devset_size,
        )
        devsetmenu.add_radiobutton(
            label="200 sentences",
            variable=self._devset_size,
            value=200,
            command=self.set_devset_size,
        )
        devsetmenu.add_radiobutton(
            label="500 sentences",
            variable=self._devset_size,
            value=500,
            command=self.set_devset_size,
        )
        menubar.add_cascade(label="Development-Set", underline=0, menu=devsetmenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    def toggle_show_trace(self, *e):
        if self._showing_trace:
            self.show_devset()
        else:
            self.show_trace()
        return "break"

    _SCALE_N = 5  # center on the last 5 examples.
    _DRAW_LINES = False

    def _eval_plot(self, *e, **config):
        width = config.get("width", self.evalbox.winfo_width())
        height = config.get("height", self.evalbox.winfo_height())

        # Clear the canvas
        self.evalbox.delete("all")

        # Draw the precision & recall labels.
        tag = self.evalbox.create_text(
            10, height // 2 - 10, justify="left", anchor="w", text="Precision"
        )
        left, right = self.evalbox.bbox(tag)[2] + 5, width - 10
        tag = self.evalbox.create_text(
            left + (width - left) // 2,
            height - 10,
            anchor="s",
            text="Recall",
            justify="center",
        )
        top, bot = 10, self.evalbox.bbox(tag)[1] - 10

        # Draw masks for clipping the plot.
        bg = self._EVALBOX_PARAMS["background"]
        self.evalbox.lower(
            self.evalbox.create_rectangle(0, 0, left - 1, 5000, fill=bg, outline=bg)
        )
        self.evalbox.lower(
            self.evalbox.create_rectangle(0, bot + 1, 5000, 5000, fill=bg, outline=bg)
        )

        # Calculate the plot's scale.
        if self._autoscale.get() and len(self._history) > 1:
            max_precision = max_recall = 0
            min_precision = min_recall = 1
            for i in range(1, min(len(self._history), self._SCALE_N + 1)):
                grammar, precision, recall, fmeasure = self._history[-i]
                min_precision = min(precision, min_precision)
                min_recall = min(recall, min_recall)
                max_precision = max(precision, max_precision)
                max_recall = max(recall, max_recall)
            #             if max_precision-min_precision > max_recall-min_recall:
            #                 min_recall -= (max_precision-min_precision)/2
            #                 max_recall += (max_precision-min_precision)/2
            #             else:
            #                 min_precision -= (max_recall-min_recall)/2
            #                 max_precision += (max_recall-min_recall)/2
            #             if min_recall < 0:
            #                 max_recall -= min_recall
            #                 min_recall = 0
            #             if min_precision < 0:
            #                 max_precision -= min_precision
            #                 min_precision = 0
            min_precision = max(min_precision - 0.01, 0)
            min_recall = max(min_recall - 0.01, 0)
            max_precision = min(max_precision + 0.01, 1)
            max_recall = min(max_recall + 0.01, 1)
        else:
            min_precision = min_recall = 0
            max_precision = max_recall = 1

        # Draw the axis lines & grid lines
        for i in range(11):
            x = left + (right - left) * (
                (i / 10.0 - min_recall) / (max_recall - min_recall)
            )
            y = bot - (bot - top) * (
                (i / 10.0 - min_precision) / (max_precision - min_precision)
            )
            if left < x < right:
                self.evalbox.create_line(x, top, x, bot, fill="#888")
            if top < y < bot:
                self.evalbox.create_line(left, y, right, y, fill="#888")
        self.evalbox.create_line(left, top, left, bot)
        self.evalbox.create_line(left, bot, right, bot)

        # Display the plot's scale
        self.evalbox.create_text(
            left - 3,
            bot,
            justify="right",
            anchor="se",
            text="%d%%" % (100 * min_precision),
        )
        self.evalbox.create_text(
            left - 3,
            top,
            justify="right",
            anchor="ne",
            text="%d%%" % (100 * max_precision),
        )
        self.evalbox.create_text(
            left,
            bot + 3,
            justify="center",
            anchor="nw",
            text="%d%%" % (100 * min_recall),
        )
        self.evalbox.create_text(
            right,
            bot + 3,
            justify="center",
            anchor="ne",
            text="%d%%" % (100 * max_recall),
        )

        # Display the scores.
        prev_x = prev_y = None
        for i, (_, precision, recall, fscore) in enumerate(self._history):
            x = left + (right - left) * (
                (recall - min_recall) / (max_recall - min_recall)
            )
            y = bot - (bot - top) * (
                (precision - min_precision) / (max_precision - min_precision)
            )
            if i == self._history_index:
                self.evalbox.create_oval(
                    x - 2, y - 2, x + 2, y + 2, fill="#0f0", outline="#000"
                )
                self.status["text"] = (
                    "Precision: %.2f%%\t" % (precision * 100)
                    + "Recall: %.2f%%\t" % (recall * 100)
                    + "F-score: %.2f%%" % (fscore * 100)
                )
            else:
                self.evalbox.lower(
                    self.evalbox.create_oval(
                        x - 2, y - 2, x + 2, y + 2, fill="#afa", outline="#8c8"
                    )
                )
            if prev_x is not None and self._eval_lines.get():
                self.evalbox.lower(
                    self.evalbox.create_line(prev_x, prev_y, x, y, fill="#8c8")
                )
            prev_x, prev_y = x, y

    _eval_demon_running = False

    def _eval_demon(self):
        if self.top is None:
            return
        if self.chunker is None:
            self._eval_demon_running = False
            return

        # Note our starting time.
        t0 = time.time()

        # If are still typing, then wait for them to finish.
        if (
            time.time() - self._last_keypress < self._EVAL_DELAY
            and self.normalized_grammar != self._eval_normalized_grammar
        ):
            self._eval_demon_running = True
            return self.top.after(int(self._EVAL_FREQ * 1000), self._eval_demon)

        # If the grammar changed, restart the evaluation.
        if self.normalized_grammar != self._eval_normalized_grammar:
            # Check if we've seen this grammar already.  If so, then
            # just use the old evaluation values.
            for g, p, r, f in self._history:
                if self.normalized_grammar == self.normalize_grammar(g):
                    self._history.append((g, p, r, f))
                    self._history_index = len(self._history) - 1
                    self._eval_plot()
                    self._eval_demon_running = False
                    self._eval_normalized_grammar = None
                    return
            self._eval_index = 0
            self._eval_score = ChunkScore(chunk_label=self._chunk_label)
            self._eval_grammar = self.grammar
            self._eval_normalized_grammar = self.normalized_grammar

        # If the grammar is empty, the don't bother evaluating it, or
        # recording it in history -- the score will just be 0.
        if self.normalized_grammar.strip() == "":
            # self._eval_index = self._devset_size.get()
            self._eval_demon_running = False
            return

        # Score the next set of examples
        for gold in self.devset[
            self._eval_index : min(
                self._eval_index + self._EVAL_CHUNK, self._devset_size.get()
            )
        ]:
            guess = self._chunkparse(gold.leaves())
            self._eval_score.score(gold, guess)

        # update our index in the devset.
        self._eval_index += self._EVAL_CHUNK

        # Check if we're done
        if self._eval_index >= self._devset_size.get():
            self._history.append(
                (
                    self._eval_grammar,
                    self._eval_score.precision(),
                    self._eval_score.recall(),
                    self._eval_score.f_measure(),
                )
            )
            self._history_index = len(self._history) - 1
            self._eval_plot()
            self._eval_demon_running = False
            self._eval_normalized_grammar = None
        else:
            progress = 100 * self._eval_index / self._devset_size.get()
            self.status["text"] = "Evaluating on Development Set (%d%%)" % progress
            self._eval_demon_running = True
            self._adaptively_modify_eval_chunk(time.time() - t0)
            self.top.after(int(self._EVAL_FREQ * 1000), self._eval_demon)

    def _adaptively_modify_eval_chunk(self, t):
        """
        Modify _EVAL_CHUNK to try to keep the amount of time that the
        eval demon takes between _EVAL_DEMON_MIN and _EVAL_DEMON_MAX.

        :param t: The amount of time that the eval demon took.
        """
        if t > self._EVAL_DEMON_MAX and self._EVAL_CHUNK > 5:
            self._EVAL_CHUNK = min(
                self._EVAL_CHUNK - 1,
                max(
                    int(self._EVAL_CHUNK * (self._EVAL_DEMON_MAX / t)),
                    self._EVAL_CHUNK - 10,
                ),
            )
        elif t < self._EVAL_DEMON_MIN:
            self._EVAL_CHUNK = max(
                self._EVAL_CHUNK + 1,
                min(
                    int(self._EVAL_CHUNK * (self._EVAL_DEMON_MIN / t)),
                    self._EVAL_CHUNK + 10,
                ),
            )

    def _init_widgets(self, top):
        frame0 = Frame(top, **self._FRAME_PARAMS)
        frame0.grid_columnconfigure(0, weight=4)
        frame0.grid_columnconfigure(3, weight=2)
        frame0.grid_rowconfigure(1, weight=1)
        frame0.grid_rowconfigure(5, weight=1)

        # The grammar
        self.grammarbox = Text(frame0, font=self._font, **self._GRAMMARBOX_PARAMS)
        self.grammarlabel = Label(
            frame0,
            font=self._font,
            text="Grammar:",
            highlightcolor="black",
            background=self._GRAMMARBOX_PARAMS["background"],
        )
        self.grammarlabel.grid(column=0, row=0, sticky="SW")
        self.grammarbox.grid(column=0, row=1, sticky="NEWS")

        # Scroll bar for grammar
        grammar_scrollbar = Scrollbar(frame0, command=self.grammarbox.yview)
        grammar_scrollbar.grid(column=1, row=1, sticky="NWS")
        self.grammarbox.config(yscrollcommand=grammar_scrollbar.set)

        # grammar buttons
        bg = self._FRAME_PARAMS["background"]
        frame3 = Frame(frame0, background=bg)
        frame3.grid(column=0, row=2, sticky="EW")
        Button(
            frame3,
            text="Prev Grammar",
            command=self._history_prev,
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        Button(
            frame3,
            text="Next Grammar",
            command=self._history_next,
            **self._BUTTON_PARAMS,
        ).pack(side="left")

        # Help box
        self.helpbox = Text(frame0, font=self._smallfont, **self._HELPBOX_PARAMS)
        self.helpbox.grid(column=3, row=1, sticky="NEWS")
        self.helptabs = {}
        bg = self._FRAME_PARAMS["background"]
        helptab_frame = Frame(frame0, background=bg)
        helptab_frame.grid(column=3, row=0, sticky="SW")
        for i, (tab, tabstops, text) in enumerate(self.HELP):
            label = Label(helptab_frame, text=tab, font=self._smallfont)
            label.grid(column=i * 2, row=0, sticky="S")
            # help_frame.grid_columnconfigure(i, weight=1)
            # label.pack(side='left')
            label.bind("<ButtonPress>", lambda e, tab=tab: self.show_help(tab))
            self.helptabs[tab] = label
            Frame(
                helptab_frame, height=1, width=self._HELPTAB_SPACER, background=bg
            ).grid(column=i * 2 + 1, row=0)
        self.helptabs[self.HELP[0][0]].configure(font=self._font)
        self.helpbox.tag_config("elide", elide=True)
        for tag, params in self.HELP_AUTOTAG:
            self.helpbox.tag_config("tag-%s" % tag, **params)
        self.show_help(self.HELP[0][0])

        # Scroll bar for helpbox
        help_scrollbar = Scrollbar(frame0, command=self.helpbox.yview)
        self.helpbox.config(yscrollcommand=help_scrollbar.set)
        help_scrollbar.grid(column=4, row=1, sticky="NWS")

        # The dev set
        frame4 = Frame(frame0, background=self._FRAME_PARAMS["background"])
        self.devsetbox = Text(frame4, font=self._font, **self._DEVSETBOX_PARAMS)
        self.devsetbox.pack(expand=True, fill="both")
        self.devsetlabel = Label(
            frame0,
            font=self._font,
            text="Development Set:",
            justify="right",
            background=self._DEVSETBOX_PARAMS["background"],
        )
        self.devsetlabel.grid(column=0, row=4, sticky="SW")
        frame4.grid(column=0, row=5, sticky="NEWS")

        # dev set scrollbars
        self.devset_scroll = Scrollbar(frame0, command=self._devset_scroll)
        self.devset_scroll.grid(column=1, row=5, sticky="NWS")
        self.devset_xscroll = Scrollbar(
            frame4, command=self.devsetbox.xview, orient="horiz"
        )
        self.devsetbox["xscrollcommand"] = self.devset_xscroll.set
        self.devset_xscroll.pack(side="bottom", fill="x")

        # dev set buttons
        bg = self._FRAME_PARAMS["background"]
        frame1 = Frame(frame0, background=bg)
        frame1.grid(column=0, row=7, sticky="EW")
        Button(
            frame1,
            text="Prev Example (Ctrl-p)",
            command=self._devset_prev,
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        Button(
            frame1,
            text="Next Example (Ctrl-n)",
            command=self._devset_next,
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        self.devset_button = Button(
            frame1,
            text="Show example",
            command=self.show_devset,
            state="disabled",
            **self._BUTTON_PARAMS,
        )
        self.devset_button.pack(side="right")
        self.trace_button = Button(
            frame1, text="Show trace", command=self.show_trace, **self._BUTTON_PARAMS
        )
        self.trace_button.pack(side="right")

        # evaluation box
        self.evalbox = Canvas(frame0, **self._EVALBOX_PARAMS)
        label = Label(
            frame0,
            font=self._font,
            text="Evaluation:",
            justify="right",
            background=self._EVALBOX_PARAMS["background"],
        )
        label.grid(column=3, row=4, sticky="SW")
        self.evalbox.grid(column=3, row=5, sticky="NEWS", columnspan=2)

        # evaluation box buttons
        bg = self._FRAME_PARAMS["background"]
        frame2 = Frame(frame0, background=bg)
        frame2.grid(column=3, row=7, sticky="EW")
        self._autoscale = IntVar(self.top)
        self._autoscale.set(False)
        Checkbutton(
            frame2,
            variable=self._autoscale,
            command=self._eval_plot,
            text="Zoom",
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        self._eval_lines = IntVar(self.top)
        self._eval_lines.set(False)
        Checkbutton(
            frame2,
            variable=self._eval_lines,
            command=self._eval_plot,
            text="Lines",
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        Button(frame2, text="History", **self._BUTTON_PARAMS).pack(side="right")

        # The status label
        self.status = Label(frame0, font=self._font, **self._STATUS_PARAMS)
        self.status.grid(column=0, row=9, sticky="NEW", padx=3, pady=2, columnspan=5)

        # Help box & devset box can't be edited.
        self.helpbox["state"] = "disabled"
        self.devsetbox["state"] = "disabled"

        # Spacers
        bg = self._FRAME_PARAMS["background"]
        Frame(frame0, height=10, width=0, background=bg).grid(column=0, row=3)
        Frame(frame0, height=0, width=10, background=bg).grid(column=2, row=0)
        Frame(frame0, height=6, width=0, background=bg).grid(column=0, row=8)

        # pack the frame.
        frame0.pack(fill="both", expand=True)

        # Set up colors for the devset box
        self.devsetbox.tag_config("true-pos", background="#afa", underline="True")
        self.devsetbox.tag_config("false-neg", underline="True", foreground="#800")
        self.devsetbox.tag_config("false-pos", background="#faa")
        self.devsetbox.tag_config("trace", foreground="#666", wrap="none")
        self.devsetbox.tag_config("wrapindent", lmargin2=30, wrap="none")
        self.devsetbox.tag_config("error", foreground="#800")

        # And for the grammarbox
        self.grammarbox.tag_config("error", background="#fec")
        self.grammarbox.tag_config("comment", foreground="#840")
        self.grammarbox.tag_config("angle", foreground="#00f")
        self.grammarbox.tag_config("brace", foreground="#0a0")
        self.grammarbox.tag_config("hangindent", lmargin1=0, lmargin2=40)

    _showing_trace = False

    def show_trace(self, *e):
        self._showing_trace = True
        self.trace_button["state"] = "disabled"
        self.devset_button["state"] = "normal"

        self.devsetbox["state"] = "normal"
        # self.devsetbox['wrap'] = 'none'
        self.devsetbox.delete("1.0", "end")
        self.devsetlabel["text"] = "Development Set (%d/%d)" % (
            (self.devset_index + 1, self._devset_size.get())
        )

        if self.chunker is None:
            self.devsetbox.insert("1.0", "Trace: waiting for a valid grammar.")
            self.devsetbox.tag_add("error", "1.0", "end")
            return  # can't do anything more

        gold_tree = self.devset[self.devset_index]
        rules = self.chunker.rules()

        # Calculate the tag sequence
        tagseq = "\t"
        charnum = [1]
        for wordnum, (word, pos) in enumerate(gold_tree.leaves()):
            tagseq += "%s " % pos
            charnum.append(len(tagseq))
        self.charnum = {
            (i, j): charnum[j]
            for i in range(len(rules) + 1)
            for j in range(len(charnum))
        }
        self.linenum = {i: i * 2 + 2 for i in range(len(rules) + 1)}

        for i in range(len(rules) + 1):
            if i == 0:
                self.devsetbox.insert("end", "Start:\n")
                self.devsetbox.tag_add("trace", "end -2c linestart", "end -2c")
            else:
                self.devsetbox.insert("end", "Apply %s:\n" % rules[i - 1])
                self.devsetbox.tag_add("trace", "end -2c linestart", "end -2c")
            # Display the tag sequence.
            self.devsetbox.insert("end", tagseq + "\n")
            self.devsetbox.tag_add("wrapindent", "end -2c linestart", "end -2c")
            # Run a partial parser, and extract gold & test chunks
            chunker = RegexpChunkParser(rules[:i])
            test_tree = self._chunkparse(gold_tree.leaves())
            gold_chunks = self._chunks(gold_tree)
            test_chunks = self._chunks(test_tree)
            # Compare them.
            for chunk in gold_chunks.intersection(test_chunks):
                self._color_chunk(i, chunk, "true-pos")
            for chunk in gold_chunks - test_chunks:
                self._color_chunk(i, chunk, "false-neg")
            for chunk in test_chunks - gold_chunks:
                self._color_chunk(i, chunk, "false-pos")
        self.devsetbox.insert("end", "Finished.\n")
        self.devsetbox.tag_add("trace", "end -2c linestart", "end -2c")

        # This is a hack, because the x-scrollbar isn't updating its
        # position right -- I'm not sure what the underlying cause is
        # though.  (This is on OS X w/ python 2.5)
        self.top.after(100, self.devset_xscroll.set, 0, 0.3)

    def show_help(self, tab):
        self.helpbox["state"] = "normal"
        self.helpbox.delete("1.0", "end")
        for name, tabstops, text in self.HELP:
            if name == tab:
                text = text.replace(
                    "<<TAGSET>>",
                    "\n".join(
                        "\t%s\t%s" % item
                        for item in sorted(
                            list(self.tagset.items()),
                            key=lambda t_w: re.match(r"\w+", t_w[0])
                            and (0, t_w[0])
                            or (1, t_w[0]),
                        )
                    ),
                )

                self.helptabs[name].config(**self._HELPTAB_FG_PARAMS)
                self.helpbox.config(tabs=tabstops)
                self.helpbox.insert("1.0", text + "\n" * 20)
                C = "1.0 + %d chars"
                for tag, params in self.HELP_AUTOTAG:
                    pattern = f"(?s)(<{tag}>)(.*?)(</{tag}>)"
                    for m in re.finditer(pattern, text):
                        self.helpbox.tag_add("elide", C % m.start(1), C % m.end(1))
                        self.helpbox.tag_add(
                            "tag-%s" % tag, C % m.start(2), C % m.end(2)
                        )
                        self.helpbox.tag_add("elide", C % m.start(3), C % m.end(3))
            else:
                self.helptabs[name].config(**self._HELPTAB_BG_PARAMS)
        self.helpbox["state"] = "disabled"

    def _history_prev(self, *e):
        self._view_history(self._history_index - 1)
        return "break"

    def _history_next(self, *e):
        self._view_history(self._history_index + 1)
        return "break"

    def _view_history(self, index):
        # Bounds & sanity checking:
        index = max(0, min(len(self._history) - 1, index))
        if not self._history:
            return
        # Already viewing the requested history item?
        if index == self._history_index:
            return
        # Show the requested grammar.  It will get added to _history
        # only if they edit it (causing self.update() to get run.)
        self.grammarbox["state"] = "normal"
        self.grammarbox.delete("1.0", "end")
        self.grammarbox.insert("end", self._history[index][0])
        self.grammarbox.mark_set("insert", "1.0")
        self._history_index = index
        self._syntax_highlight_grammar(self._history[index][0])
        # Record the normalized grammar & regenerate the chunker.
        self.normalized_grammar = self.normalize_grammar(self._history[index][0])
        if self.normalized_grammar:
            rules = [
                RegexpChunkRule.fromstring(line)
                for line in self.normalized_grammar.split("\n")
            ]
        else:
            rules = []
        self.chunker = RegexpChunkParser(rules)
        # Show the score.
        self._eval_plot()
        # Update the devset box
        self._highlight_devset()
        if self._showing_trace:
            self.show_trace()
        # Update the grammar label
        if self._history_index < len(self._history) - 1:
            self.grammarlabel["text"] = "Grammar {}/{}:".format(
                self._history_index + 1,
                len(self._history),
            )
        else:
            self.grammarlabel["text"] = "Grammar:"

    def _devset_next(self, *e):
        self._devset_scroll("scroll", 1, "page")
        return "break"

    def _devset_prev(self, *e):
        self._devset_scroll("scroll", -1, "page")
        return "break"

    def destroy(self, *e):
        if self.top is None:
            return
        self.top.destroy()
        self.top = None

    def _devset_scroll(self, command, *args):
        N = 1  # size of a page -- one sentence.
        showing_trace = self._showing_trace
        if command == "scroll" and args[1].startswith("unit"):
            self.show_devset(self.devset_index + int(args[0]))
        elif command == "scroll" and args[1].startswith("page"):
            self.show_devset(self.devset_index + N * int(args[0]))
        elif command == "moveto":
            self.show_devset(int(float(args[0]) * self._devset_size.get()))
        else:
            assert 0, f"bad scroll command {command} {args}"
        if showing_trace:
            self.show_trace()

    def show_devset(self, index=None):
        if index is None:
            index = self.devset_index

        # Bounds checking
        index = min(max(0, index), self._devset_size.get() - 1)

        if index == self.devset_index and not self._showing_trace:
            return
        self.devset_index = index

        self._showing_trace = False
        self.trace_button["state"] = "normal"
        self.devset_button["state"] = "disabled"

        # Clear the text box.
        self.devsetbox["state"] = "normal"
        self.devsetbox["wrap"] = "word"
        self.devsetbox.delete("1.0", "end")
        self.devsetlabel["text"] = "Development Set (%d/%d)" % (
            (self.devset_index + 1, self._devset_size.get())
        )

        # Add the sentences
        sample = self.devset[self.devset_index : self.devset_index + 1]
        self.charnum = {}
        self.linenum = {0: 1}
        for sentnum, sent in enumerate(sample):
            linestr = ""
            for wordnum, (word, pos) in enumerate(sent.leaves()):
                self.charnum[sentnum, wordnum] = len(linestr)
                linestr += f"{word}/{pos} "
                self.charnum[sentnum, wordnum + 1] = len(linestr)
            self.devsetbox.insert("end", linestr[:-1] + "\n\n")

        # Highlight chunks in the dev set
        if self.chunker is not None:
            self._highlight_devset()
        self.devsetbox["state"] = "disabled"

        # Update the scrollbar
        first = self.devset_index / self._devset_size.get()
        last = (self.devset_index + 2) / self._devset_size.get()
        self.devset_scroll.set(first, last)

    def _chunks(self, tree):
        chunks = set()
        wordnum = 0
        for child in tree:
            if isinstance(child, Tree):
                if child.label() == self._chunk_label:
                    chunks.add((wordnum, wordnum + len(child)))
                wordnum += len(child)
            else:
                wordnum += 1
        return chunks

    def _syntax_highlight_grammar(self, grammar):
        if self.top is None:
            return
        self.grammarbox.tag_remove("comment", "1.0", "end")
        self.grammarbox.tag_remove("angle", "1.0", "end")
        self.grammarbox.tag_remove("brace", "1.0", "end")
        self.grammarbox.tag_add("hangindent", "1.0", "end")
        for lineno, line in enumerate(grammar.split("\n")):
            if not line.strip():
                continue
            m = re.match(r"(\\.|[^#])*(#.*)?", line)
            comment_start = None
            if m.group(2):
                comment_start = m.start(2)
                s = "%d.%d" % (lineno + 1, m.start(2))
                e = "%d.%d" % (lineno + 1, m.end(2))
                self.grammarbox.tag_add("comment", s, e)
            for m in re.finditer("[<>{}]", line):
                if comment_start is not None and m.start() >= comment_start:
                    break
                s = "%d.%d" % (lineno + 1, m.start())
                e = "%d.%d" % (lineno + 1, m.end())
                if m.group() in "<>":
                    self.grammarbox.tag_add("angle", s, e)
                else:
                    self.grammarbox.tag_add("brace", s, e)

    def _grammarcheck(self, grammar):
        if self.top is None:
            return
        self.grammarbox.tag_remove("error", "1.0", "end")
        self._grammarcheck_errs = []
        for lineno, line in enumerate(grammar.split("\n")):
            line = re.sub(r"((\\.|[^#])*)(#.*)?", r"\1", line)
            line = line.strip()
            if line:
                try:
                    RegexpChunkRule.fromstring(line)
                except ValueError as e:
                    self.grammarbox.tag_add(
                        "error", "%s.0" % (lineno + 1), "%s.0 lineend" % (lineno + 1)
                    )
        self.status["text"] = ""

    def update(self, *event):
        # Record when update was called (for grammarcheck)
        if event:
            self._last_keypress = time.time()

        # Read the grammar from the Text box.
        self.grammar = grammar = self.grammarbox.get("1.0", "end")

        # If the grammar hasn't changed, do nothing:
        normalized_grammar = self.normalize_grammar(grammar)
        if normalized_grammar == self.normalized_grammar:
            return
        else:
            self.normalized_grammar = normalized_grammar

        # If the grammar has changed, and we're looking at history,
        # then stop looking at history.
        if self._history_index < len(self._history) - 1:
            self.grammarlabel["text"] = "Grammar:"

        self._syntax_highlight_grammar(grammar)

        # The grammar has changed; try parsing it.  If it doesn't
        # parse, do nothing.  (flag error location?)
        try:
            # Note: the normalized grammar has no blank lines.
            if normalized_grammar:
                rules = [
                    RegexpChunkRule.fromstring(line)
                    for line in normalized_grammar.split("\n")
                ]
            else:
                rules = []
        except ValueError as e:
            # Use the un-normalized grammar for error highlighting.
            self._grammarcheck(grammar)
            self.chunker = None
            return

        self.chunker = RegexpChunkParser(rules)
        self.grammarbox.tag_remove("error", "1.0", "end")
        self.grammar_changed = time.time()
        # Display the results
        if self._showing_trace:
            self.show_trace()
        else:
            self._highlight_devset()
        # Start the eval demon
        if not self._eval_demon_running:
            self._eval_demon()

    def _highlight_devset(self, sample=None):
        if sample is None:
            sample = self.devset[self.devset_index : self.devset_index + 1]

        self.devsetbox.tag_remove("true-pos", "1.0", "end")
        self.devsetbox.tag_remove("false-neg", "1.0", "end")
        self.devsetbox.tag_remove("false-pos", "1.0", "end")

        # Run the grammar on the test cases.
        for sentnum, gold_tree in enumerate(sample):
            # Run the chunk parser
            test_tree = self._chunkparse(gold_tree.leaves())
            # Extract gold & test chunks
            gold_chunks = self._chunks(gold_tree)
            test_chunks = self._chunks(test_tree)
            # Compare them.
            for chunk in gold_chunks.intersection(test_chunks):
                self._color_chunk(sentnum, chunk, "true-pos")
            for chunk in gold_chunks - test_chunks:
                self._color_chunk(sentnum, chunk, "false-neg")
            for chunk in test_chunks - gold_chunks:
                self._color_chunk(sentnum, chunk, "false-pos")

    def _chunkparse(self, words):
        try:
            return self.chunker.parse(words)
        except (ValueError, IndexError) as e:
            # There's an error somewhere in the grammar, but we're not sure
            # exactly where, so just mark the whole grammar as bad.
            # E.g., this is caused by: "({<NN>})"
            self.grammarbox.tag_add("error", "1.0", "end")
            # Treat it as tagging nothing:
            return words

    def _color_chunk(self, sentnum, chunk, tag):
        start, end = chunk
        self.devsetbox.tag_add(
            tag,
            f"{self.linenum[sentnum]}.{self.charnum[sentnum, start]}",
            f"{self.linenum[sentnum]}.{self.charnum[sentnum, end] - 1}",
        )

    def reset(self):
        # Clear various variables
        self.chunker = None
        self.grammar = None
        self.normalized_grammar = None
        self.grammar_changed = 0
        self._history = []
        self._history_index = 0
        # Update the on-screen display.
        self.grammarbox.delete("1.0", "end")
        self.show_devset(0)
        self.update()
        # self._eval_plot()

    SAVE_GRAMMAR_TEMPLATE = (
        "# Regexp Chunk Parsing Grammar\n"
        "# Saved %(date)s\n"
        "#\n"
        "# Development set: %(devset)s\n"
        "#   Precision: %(precision)s\n"
        "#   Recall:    %(recall)s\n"
        "#   F-score:   %(fscore)s\n\n"
        "%(grammar)s\n"
    )

    def save_grammar(self, filename=None):
        if not filename:
            ftypes = [("Chunk Gramamr", ".chunk"), ("All files", "*")]
            filename = asksaveasfilename(filetypes=ftypes, defaultextension=".chunk")
            if not filename:
                return
        if self._history and self.normalized_grammar == self.normalize_grammar(
            self._history[-1][0]
        ):
            precision, recall, fscore = (
                "%.2f%%" % (100 * v) for v in self._history[-1][1:]
            )
        elif self.chunker is None:
            precision = recall = fscore = "Grammar not well formed"
        else:
            precision = recall = fscore = "Not finished evaluation yet"

        with open(filename, "w") as outfile:
            outfile.write(
                self.SAVE_GRAMMAR_TEMPLATE
                % dict(
                    date=time.ctime(),
                    devset=self.devset_name,
                    precision=precision,
                    recall=recall,
                    fscore=fscore,
                    grammar=self.grammar.strip(),
                )
            )

    def load_grammar(self, filename=None):
        if not filename:
            ftypes = [("Chunk Gramamr", ".chunk"), ("All files", "*")]
            filename = askopenfilename(filetypes=ftypes, defaultextension=".chunk")
            if not filename:
                return
        self.grammarbox.delete("1.0", "end")
        self.update()
        with open(filename) as infile:
            grammar = infile.read()
        grammar = re.sub(
            r"^\# Regexp Chunk Parsing Grammar[\s\S]*" "F-score:.*\n", "", grammar
        ).lstrip()
        self.grammarbox.insert("1.0", grammar)
        self.update()

    def save_history(self, filename=None):
        if not filename:
            ftypes = [("Chunk Gramamr History", ".txt"), ("All files", "*")]
            filename = asksaveasfilename(filetypes=ftypes, defaultextension=".txt")
            if not filename:
                return

        with open(filename, "w") as outfile:
            outfile.write("# Regexp Chunk Parsing Grammar History\n")
            outfile.write("# Saved %s\n" % time.ctime())
            outfile.write("# Development set: %s\n" % self.devset_name)
            for i, (g, p, r, f) in enumerate(self._history):
                hdr = (
                    "Grammar %d/%d (precision=%.2f%%, recall=%.2f%%, "
                    "fscore=%.2f%%)"
                    % (i + 1, len(self._history), p * 100, r * 100, f * 100)
                )
                outfile.write("\n%s\n" % hdr)
                outfile.write("".join("  %s\n" % line for line in g.strip().split()))

            if not (
                self._history
                and self.normalized_grammar
                == self.normalize_grammar(self._history[-1][0])
            ):
                if self.chunker is None:
                    outfile.write("\nCurrent Grammar (not well-formed)\n")
                else:
                    outfile.write("\nCurrent Grammar (not evaluated)\n")
                outfile.write(
                    "".join("  %s\n" % line for line in self.grammar.strip().split())
                )

    def about(self, *e):
        ABOUT = "NLTK RegExp Chunk Parser Application\n" + "Written by Edward Loper"
        TITLE = "About: Regular Expression Chunk Parser Application"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self.top, TITLE, ABOUT)

    def set_devset_size(self, size=None):
        if size is not None:
            self._devset_size.set(size)
        self._devset_size.set(min(len(self.devset), self._devset_size.get()))
        self.show_devset(1)
        self.show_devset(0)
        # what about history?  Evaluated at diff dev set sizes!

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._smallfont.configure(size=min(-10, -(abs(size)) * 14 // 20))

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self.top.mainloop(*args, **kwargs)


def app():
    RegexpChunkApp().mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]

# === NexusCore/tools\exports\export_20250803_114325\source_code\NexusCore\openenv\Lib\site-packages\nltk\app\chunkparser_app.py ===
# Natural Language Toolkit: Regexp Chunk Parser Application
#
# Copyright (C) 2001-2024 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A graphical tool for exploring the regular expression based chunk
parser ``nltk.chunk.RegexpChunkParser``.
"""

# Todo: Add a way to select the development set from the menubar.  This
# might just need to be a selection box (conll vs treebank etc) plus
# configuration parameters to select what's being chunked (eg VP vs NP)
# and what part of the data is being used as the development set.

import random
import re
import textwrap
import time
from tkinter import (
    Button,
    Canvas,
    Checkbutton,
    Frame,
    IntVar,
    Label,
    Menu,
    Scrollbar,
    Text,
    Tk,
)
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.font import Font

from nltk.chunk import ChunkScore, RegexpChunkParser
from nltk.chunk.regexp import RegexpChunkRule
from nltk.corpus import conll2000, treebank_chunk
from nltk.draw.util import ShowText
from nltk.tree import Tree
from nltk.util import in_idle


class RegexpChunkApp:
    """
    A graphical tool for exploring the regular expression based chunk
    parser ``nltk.chunk.RegexpChunkParser``.

    See ``HELP`` for instructional text.
    """

    ##/////////////////////////////////////////////////////////////////
    ##  Help Text
    ##/////////////////////////////////////////////////////////////////

    #: A dictionary mapping from part of speech tags to descriptions,
    #: which is used in the help text.  (This should probably live with
    #: the conll and/or treebank corpus instead.)
    TAGSET = {
        "CC": "Coordinating conjunction",
        "PRP$": "Possessive pronoun",
        "CD": "Cardinal number",
        "RB": "Adverb",
        "DT": "Determiner",
        "RBR": "Adverb, comparative",
        "EX": "Existential there",
        "RBS": "Adverb, superlative",
        "FW": "Foreign word",
        "RP": "Particle",
        "JJ": "Adjective",
        "TO": "to",
        "JJR": "Adjective, comparative",
        "UH": "Interjection",
        "JJS": "Adjective, superlative",
        "VB": "Verb, base form",
        "LS": "List item marker",
        "VBD": "Verb, past tense",
        "MD": "Modal",
        "NNS": "Noun, plural",
        "NN": "Noun, singular or mass",
        "VBN": "Verb, past participle",
        "VBZ": "Verb,3rd ps. sing. present",
        "NNP": "Proper noun, singular",
        "NNPS": "Proper noun plural",
        "WDT": "wh-determiner",
        "PDT": "Predeterminer",
        "WP": "wh-pronoun",
        "POS": "Possessive ending",
        "WP$": "Possessive wh-pronoun",
        "PRP": "Personal pronoun",
        "WRB": "wh-adverb",
        "(": "open parenthesis",
        ")": "close parenthesis",
        "``": "open quote",
        ",": "comma",
        "''": "close quote",
        ".": "period",
        "#": "pound sign (currency marker)",
        "$": "dollar sign (currency marker)",
        "IN": "Preposition/subord. conjunction",
        "SYM": "Symbol (mathematical or scientific)",
        "VBG": "Verb, gerund/present participle",
        "VBP": "Verb, non-3rd ps. sing. present",
        ":": "colon",
    }

    #: Contents for the help box.  This is a list of tuples, one for
    #: each help page, where each tuple has four elements:
    #:   - A title (displayed as a tab)
    #:   - A string description of tabstops (see Tkinter.Text for details)
    #:   - The text contents for the help page.  You can use expressions
    #:     like <red>...</red> to colorize the text; see ``HELP_AUTOTAG``
    #:     for a list of tags you can use for colorizing.
    HELP = [
        (
            "Help",
            "20",
            "Welcome to the regular expression chunk-parser grammar editor.  "
            "You can use this editor to develop and test chunk parser grammars "
            "based on NLTK's RegexpChunkParser class.\n\n"
            # Help box.
            "Use this box ('Help') to learn more about the editor; click on the "
            "tabs for help on specific topics:"
            "<indent>\n"
            "Rules: grammar rule types\n"
            "Regexps: regular expression syntax\n"
            "Tags: part of speech tags\n</indent>\n"
            # Grammar.
            "Use the upper-left box ('Grammar') to edit your grammar.  "
            "Each line of your grammar specifies a single 'rule', "
            "which performs an action such as creating a chunk or merging "
            "two chunks.\n\n"
            # Dev set.
            "The lower-left box ('Development Set') runs your grammar on the "
            "development set, and displays the results.  "
            "Your grammar's chunks are <highlight>highlighted</highlight>, and "
            "the correct (gold standard) chunks are "
            "<underline>underlined</underline>.  If they "
            "match, they are displayed in <green>green</green>; otherwise, "
            "they are displayed in <red>red</red>.  The box displays a single "
            "sentence from the development set at a time; use the scrollbar or "
            "the next/previous buttons view additional sentences.\n\n"
            # Performance
            "The lower-right box ('Evaluation') tracks the performance of "
            "your grammar on the development set.  The 'precision' axis "
            "indicates how many of your grammar's chunks are correct; and "
            "the 'recall' axis indicates how many of the gold standard "
            "chunks your system generated.  Typically, you should try to "
            "design a grammar that scores high on both metrics.  The "
            "exact precision and recall of the current grammar, as well "
            "as their harmonic mean (the 'f-score'), are displayed in "
            "the status bar at the bottom of the window.",
        ),
        (
            "Rules",
            "10",
            "<h1>{...regexp...}</h1>"
            "<indent>\nChunk rule: creates new chunks from words matching "
            "regexp.</indent>\n\n"
            "<h1>}...regexp...{</h1>"
            "<indent>\nStrip rule: removes words matching regexp from existing "
            "chunks.</indent>\n\n"
            "<h1>...regexp1...}{...regexp2...</h1>"
            "<indent>\nSplit rule: splits chunks that match regexp1 followed by "
            "regexp2 in two.</indent>\n\n"
            "<h1>...regexp...{}...regexp...</h1>"
            "<indent>\nMerge rule: joins consecutive chunks that match regexp1 "
            "and regexp2</indent>\n",
        ),
        (
            "Regexps",
            "10 60",
            # "Regular Expression Syntax Summary:\n\n"
            "<h1>Pattern\t\tMatches...</h1>\n"
            "<hangindent>"
            "\t<<var>T</var>>\ta word with tag <var>T</var> "
            "(where <var>T</var> may be a regexp).\n"
            "\t<var>x</var>?\tan optional <var>x</var>\n"
            "\t<var>x</var>+\ta sequence of 1 or more <var>x</var>'s\n"
            "\t<var>x</var>*\ta sequence of 0 or more <var>x</var>'s\n"
            "\t<var>x</var>|<var>y</var>\t<var>x</var> or <var>y</var>\n"
            "\t.\tmatches any character\n"
            "\t(<var>x</var>)\tTreats <var>x</var> as a group\n"
            "\t# <var>x...</var>\tTreats <var>x...</var> "
            "(to the end of the line) as a comment\n"
            "\t\\<var>C</var>\tmatches character <var>C</var> "
            "(useful when <var>C</var> is a special character "
            "like + or #)\n"
            "</hangindent>"
            "\n<h1>Examples:</h1>\n"
            "<hangindent>"
            "\t<regexp><NN></regexp>\n"
            '\t\tMatches <match>"cow/NN"</match>\n'
            '\t\tMatches <match>"green/NN"</match>\n'
            "\t<regexp><VB.*></regexp>\n"
            '\t\tMatches <match>"eating/VBG"</match>\n'
            '\t\tMatches <match>"ate/VBD"</match>\n'
            "\t<regexp><IN><DT><NN></regexp>\n"
            '\t\tMatches <match>"on/IN the/DT car/NN"</match>\n'
            "\t<regexp><RB>?<VBD></regexp>\n"
            '\t\tMatches <match>"ran/VBD"</match>\n'
            '\t\tMatches <match>"slowly/RB ate/VBD"</match>\n'
            r"\t<regexp><\#><CD> # This is a comment...</regexp>\n"
            '\t\tMatches <match>"#/# 100/CD"</match>\n'
            "</hangindent>",
        ),
        (
            "Tags",
            "10 60",
            "<h1>Part of Speech Tags:</h1>\n"
            + "<hangindent>"
            + "<<TAGSET>>"
            + "</hangindent>\n",  # this gets auto-substituted w/ self.TAGSET
        ),
    ]

    HELP_AUTOTAG = [
        ("red", dict(foreground="#a00")),
        ("green", dict(foreground="#080")),
        ("highlight", dict(background="#ddd")),
        ("underline", dict(underline=True)),
        ("h1", dict(underline=True)),
        ("indent", dict(lmargin1=20, lmargin2=20)),
        ("hangindent", dict(lmargin1=0, lmargin2=60)),
        ("var", dict(foreground="#88f")),
        ("regexp", dict(foreground="#ba7")),
        ("match", dict(foreground="#6a6")),
    ]

    ##/////////////////////////////////////////////////////////////////
    ##  Config Parameters
    ##/////////////////////////////////////////////////////////////////

    _EVAL_DELAY = 1
    """If the user has not pressed any key for this amount of time (in
       seconds), and the current grammar has not been evaluated, then
       the eval demon will evaluate it."""

    _EVAL_CHUNK = 15
    """The number of sentences that should be evaluated by the eval
       demon each time it runs."""
    _EVAL_FREQ = 0.2
    """The frequency (in seconds) at which the eval demon is run"""
    _EVAL_DEMON_MIN = 0.02
    """The minimum amount of time that the eval demon should take each time
       it runs -- if it takes less than this time, _EVAL_CHUNK will be
       modified upwards."""
    _EVAL_DEMON_MAX = 0.04
    """The maximum amount of time that the eval demon should take each time
       it runs -- if it takes more than this time, _EVAL_CHUNK will be
       modified downwards."""

    _GRAMMARBOX_PARAMS = dict(
        width=40,
        height=12,
        background="#efe",
        highlightbackground="#efe",
        highlightthickness=1,
        relief="groove",
        border=2,
        wrap="word",
    )
    _HELPBOX_PARAMS = dict(
        width=15,
        height=15,
        background="#efe",
        highlightbackground="#efe",
        foreground="#555",
        highlightthickness=1,
        relief="groove",
        border=2,
        wrap="word",
    )
    _DEVSETBOX_PARAMS = dict(
        width=70,
        height=10,
        background="#eef",
        highlightbackground="#eef",
        highlightthickness=1,
        relief="groove",
        border=2,
        wrap="word",
        tabs=(30,),
    )
    _STATUS_PARAMS = dict(background="#9bb", relief="groove", border=2)
    _FONT_PARAMS = dict(family="helvetica", size=-20)
    _FRAME_PARAMS = dict(background="#777", padx=2, pady=2, border=3)
    _EVALBOX_PARAMS = dict(
        background="#eef",
        highlightbackground="#eef",
        highlightthickness=1,
        relief="groove",
        border=2,
        width=300,
        height=280,
    )
    _BUTTON_PARAMS = dict(
        background="#777", activebackground="#777", highlightbackground="#777"
    )
    _HELPTAB_BG_COLOR = "#aba"
    _HELPTAB_FG_COLOR = "#efe"

    _HELPTAB_FG_PARAMS = dict(background="#efe")
    _HELPTAB_BG_PARAMS = dict(background="#aba")
    _HELPTAB_SPACER = 6

    def normalize_grammar(self, grammar):
        # Strip comments
        grammar = re.sub(r"((\\.|[^#])*)(#.*)?", r"\1", grammar)
        # Normalize whitespace
        grammar = re.sub(" +", " ", grammar)
        grammar = re.sub(r"\n\s+", r"\n", grammar)
        grammar = grammar.strip()
        # [xx] Hack: automatically backslash $!
        grammar = re.sub(r"([^\\])\$", r"\1\\$", grammar)
        return grammar

    def __init__(
        self,
        devset_name="conll2000",
        devset=None,
        grammar="",
        chunk_label="NP",
        tagset=None,
    ):
        """
        :param devset_name: The name of the development set; used for
            display & for save files.  If either the name 'treebank'
            or the name 'conll2000' is used, and devset is None, then
            devset will be set automatically.
        :param devset: A list of chunked sentences
        :param grammar: The initial grammar to display.
        :param tagset: Dictionary from tags to string descriptions, used
            for the help page.  Defaults to ``self.TAGSET``.
        """
        self._chunk_label = chunk_label

        if tagset is None:
            tagset = self.TAGSET
        self.tagset = tagset

        # Named development sets:
        if devset is None:
            if devset_name == "conll2000":
                devset = conll2000.chunked_sents("train.txt")  # [:100]
            elif devset == "treebank":
                devset = treebank_chunk.chunked_sents()  # [:100]
            else:
                raise ValueError("Unknown development set %s" % devset_name)

        self.chunker = None
        """The chunker built from the grammar string"""

        self.grammar = grammar
        """The unparsed grammar string"""

        self.normalized_grammar = None
        """A normalized version of ``self.grammar``."""

        self.grammar_changed = 0
        """The last time() that the grammar was changed."""

        self.devset = devset
        """The development set -- a list of chunked sentences."""

        self.devset_name = devset_name
        """The name of the development set (for save files)."""

        self.devset_index = -1
        """The index into the development set of the first instance
           that's currently being viewed."""

        self._last_keypress = 0
        """The time() when a key was most recently pressed"""

        self._history = []
        """A list of (grammar, precision, recall, fscore) tuples for
           grammars that the user has already tried."""

        self._history_index = 0
        """When the user is scrolling through previous grammars, this
           is used to keep track of which grammar they're looking at."""

        self._eval_grammar = None
        """The grammar that is being currently evaluated by the eval
           demon."""

        self._eval_normalized_grammar = None
        """A normalized copy of ``_eval_grammar``."""

        self._eval_index = 0
        """The index of the next sentence in the development set that
           should be looked at by the eval demon."""

        self._eval_score = ChunkScore(chunk_label=chunk_label)
        """The ``ChunkScore`` object that's used to keep track of the score
        of the current grammar on the development set."""

        # Set up the main window.
        top = self.top = Tk()
        top.geometry("+50+50")
        top.title("Regexp Chunk Parser App")
        top.bind("<Control-q>", self.destroy)

        # Variable that restricts how much of the devset we look at.
        self._devset_size = IntVar(top)
        self._devset_size.set(100)

        # Set up all the tkinter widgets
        self._init_fonts(top)
        self._init_widgets(top)
        self._init_bindings(top)
        self._init_menubar(top)
        self.grammarbox.focus()

        # If a grammar was given, then display it.
        if grammar:
            self.grammarbox.insert("end", grammar + "\n")
            self.grammarbox.mark_set("insert", "1.0")

        # Display the first item in the development set
        self.show_devset(0)
        self.update()

    def _init_bindings(self, top):
        top.bind("<Control-n>", self._devset_next)
        top.bind("<Control-p>", self._devset_prev)
        top.bind("<Control-t>", self.toggle_show_trace)
        top.bind("<KeyPress>", self.update)
        top.bind("<Control-s>", lambda e: self.save_grammar())
        top.bind("<Control-o>", lambda e: self.load_grammar())
        self.grammarbox.bind("<Control-t>", self.toggle_show_trace)
        self.grammarbox.bind("<Control-n>", self._devset_next)
        self.grammarbox.bind("<Control-p>", self._devset_prev)

        # Redraw the eval graph when the window size changes
        self.evalbox.bind("<Configure>", self._eval_plot)

    def _init_fonts(self, top):
        # TWhat's our font size (default=same as sysfont)
        self._size = IntVar(top)
        self._size.set(20)
        self._font = Font(family="helvetica", size=-self._size.get())
        self._smallfont = Font(
            family="helvetica", size=-(int(self._size.get() * 14 // 20))
        )

    def _init_menubar(self, parent):
        menubar = Menu(parent)

        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Reset Application", underline=0, command=self.reset)
        filemenu.add_command(
            label="Save Current Grammar",
            underline=0,
            accelerator="Ctrl-s",
            command=self.save_grammar,
        )
        filemenu.add_command(
            label="Load Grammar",
            underline=0,
            accelerator="Ctrl-o",
            command=self.load_grammar,
        )

        filemenu.add_command(
            label="Save Grammar History", underline=13, command=self.save_history
        )

        filemenu.add_command(
            label="Exit", underline=1, command=self.destroy, accelerator="Ctrl-q"
        )
        menubar.add_cascade(label="File", underline=0, menu=filemenu)

        viewmenu = Menu(menubar, tearoff=0)
        viewmenu.add_radiobutton(
            label="Tiny",
            variable=self._size,
            underline=0,
            value=10,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Small",
            variable=self._size,
            underline=0,
            value=16,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Medium",
            variable=self._size,
            underline=0,
            value=20,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Large",
            variable=self._size,
            underline=0,
            value=24,
            command=self.resize,
        )
        viewmenu.add_radiobutton(
            label="Huge",
            variable=self._size,
            underline=0,
            value=34,
            command=self.resize,
        )
        menubar.add_cascade(label="View", underline=0, menu=viewmenu)

        devsetmenu = Menu(menubar, tearoff=0)
        devsetmenu.add_radiobutton(
            label="50 sentences",
            variable=self._devset_size,
            value=50,
            command=self.set_devset_size,
        )
        devsetmenu.add_radiobutton(
            label="100 sentences",
            variable=self._devset_size,
            value=100,
            command=self.set_devset_size,
        )
        devsetmenu.add_radiobutton(
            label="200 sentences",
            variable=self._devset_size,
            value=200,
            command=self.set_devset_size,
        )
        devsetmenu.add_radiobutton(
            label="500 sentences",
            variable=self._devset_size,
            value=500,
            command=self.set_devset_size,
        )
        menubar.add_cascade(label="Development-Set", underline=0, menu=devsetmenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", underline=0, command=self.about)
        menubar.add_cascade(label="Help", underline=0, menu=helpmenu)

        parent.config(menu=menubar)

    def toggle_show_trace(self, *e):
        if self._showing_trace:
            self.show_devset()
        else:
            self.show_trace()
        return "break"

    _SCALE_N = 5  # center on the last 5 examples.
    _DRAW_LINES = False

    def _eval_plot(self, *e, **config):
        width = config.get("width", self.evalbox.winfo_width())
        height = config.get("height", self.evalbox.winfo_height())

        # Clear the canvas
        self.evalbox.delete("all")

        # Draw the precision & recall labels.
        tag = self.evalbox.create_text(
            10, height // 2 - 10, justify="left", anchor="w", text="Precision"
        )
        left, right = self.evalbox.bbox(tag)[2] + 5, width - 10
        tag = self.evalbox.create_text(
            left + (width - left) // 2,
            height - 10,
            anchor="s",
            text="Recall",
            justify="center",
        )
        top, bot = 10, self.evalbox.bbox(tag)[1] - 10

        # Draw masks for clipping the plot.
        bg = self._EVALBOX_PARAMS["background"]
        self.evalbox.lower(
            self.evalbox.create_rectangle(0, 0, left - 1, 5000, fill=bg, outline=bg)
        )
        self.evalbox.lower(
            self.evalbox.create_rectangle(0, bot + 1, 5000, 5000, fill=bg, outline=bg)
        )

        # Calculate the plot's scale.
        if self._autoscale.get() and len(self._history) > 1:
            max_precision = max_recall = 0
            min_precision = min_recall = 1
            for i in range(1, min(len(self._history), self._SCALE_N + 1)):
                grammar, precision, recall, fmeasure = self._history[-i]
                min_precision = min(precision, min_precision)
                min_recall = min(recall, min_recall)
                max_precision = max(precision, max_precision)
                max_recall = max(recall, max_recall)
            #             if max_precision-min_precision > max_recall-min_recall:
            #                 min_recall -= (max_precision-min_precision)/2
            #                 max_recall += (max_precision-min_precision)/2
            #             else:
            #                 min_precision -= (max_recall-min_recall)/2
            #                 max_precision += (max_recall-min_recall)/2
            #             if min_recall < 0:
            #                 max_recall -= min_recall
            #                 min_recall = 0
            #             if min_precision < 0:
            #                 max_precision -= min_precision
            #                 min_precision = 0
            min_precision = max(min_precision - 0.01, 0)
            min_recall = max(min_recall - 0.01, 0)
            max_precision = min(max_precision + 0.01, 1)
            max_recall = min(max_recall + 0.01, 1)
        else:
            min_precision = min_recall = 0
            max_precision = max_recall = 1

        # Draw the axis lines & grid lines
        for i in range(11):
            x = left + (right - left) * (
                (i / 10.0 - min_recall) / (max_recall - min_recall)
            )
            y = bot - (bot - top) * (
                (i / 10.0 - min_precision) / (max_precision - min_precision)
            )
            if left < x < right:
                self.evalbox.create_line(x, top, x, bot, fill="#888")
            if top < y < bot:
                self.evalbox.create_line(left, y, right, y, fill="#888")
        self.evalbox.create_line(left, top, left, bot)
        self.evalbox.create_line(left, bot, right, bot)

        # Display the plot's scale
        self.evalbox.create_text(
            left - 3,
            bot,
            justify="right",
            anchor="se",
            text="%d%%" % (100 * min_precision),
        )
        self.evalbox.create_text(
            left - 3,
            top,
            justify="right",
            anchor="ne",
            text="%d%%" % (100 * max_precision),
        )
        self.evalbox.create_text(
            left,
            bot + 3,
            justify="center",
            anchor="nw",
            text="%d%%" % (100 * min_recall),
        )
        self.evalbox.create_text(
            right,
            bot + 3,
            justify="center",
            anchor="ne",
            text="%d%%" % (100 * max_recall),
        )

        # Display the scores.
        prev_x = prev_y = None
        for i, (_, precision, recall, fscore) in enumerate(self._history):
            x = left + (right - left) * (
                (recall - min_recall) / (max_recall - min_recall)
            )
            y = bot - (bot - top) * (
                (precision - min_precision) / (max_precision - min_precision)
            )
            if i == self._history_index:
                self.evalbox.create_oval(
                    x - 2, y - 2, x + 2, y + 2, fill="#0f0", outline="#000"
                )
                self.status["text"] = (
                    "Precision: %.2f%%\t" % (precision * 100)
                    + "Recall: %.2f%%\t" % (recall * 100)
                    + "F-score: %.2f%%" % (fscore * 100)
                )
            else:
                self.evalbox.lower(
                    self.evalbox.create_oval(
                        x - 2, y - 2, x + 2, y + 2, fill="#afa", outline="#8c8"
                    )
                )
            if prev_x is not None and self._eval_lines.get():
                self.evalbox.lower(
                    self.evalbox.create_line(prev_x, prev_y, x, y, fill="#8c8")
                )
            prev_x, prev_y = x, y

    _eval_demon_running = False

    def _eval_demon(self):
        if self.top is None:
            return
        if self.chunker is None:
            self._eval_demon_running = False
            return

        # Note our starting time.
        t0 = time.time()

        # If are still typing, then wait for them to finish.
        if (
            time.time() - self._last_keypress < self._EVAL_DELAY
            and self.normalized_grammar != self._eval_normalized_grammar
        ):
            self._eval_demon_running = True
            return self.top.after(int(self._EVAL_FREQ * 1000), self._eval_demon)

        # If the grammar changed, restart the evaluation.
        if self.normalized_grammar != self._eval_normalized_grammar:
            # Check if we've seen this grammar already.  If so, then
            # just use the old evaluation values.
            for g, p, r, f in self._history:
                if self.normalized_grammar == self.normalize_grammar(g):
                    self._history.append((g, p, r, f))
                    self._history_index = len(self._history) - 1
                    self._eval_plot()
                    self._eval_demon_running = False
                    self._eval_normalized_grammar = None
                    return
            self._eval_index = 0
            self._eval_score = ChunkScore(chunk_label=self._chunk_label)
            self._eval_grammar = self.grammar
            self._eval_normalized_grammar = self.normalized_grammar

        # If the grammar is empty, the don't bother evaluating it, or
        # recording it in history -- the score will just be 0.
        if self.normalized_grammar.strip() == "":
            # self._eval_index = self._devset_size.get()
            self._eval_demon_running = False
            return

        # Score the next set of examples
        for gold in self.devset[
            self._eval_index : min(
                self._eval_index + self._EVAL_CHUNK, self._devset_size.get()
            )
        ]:
            guess = self._chunkparse(gold.leaves())
            self._eval_score.score(gold, guess)

        # update our index in the devset.
        self._eval_index += self._EVAL_CHUNK

        # Check if we're done
        if self._eval_index >= self._devset_size.get():
            self._history.append(
                (
                    self._eval_grammar,
                    self._eval_score.precision(),
                    self._eval_score.recall(),
                    self._eval_score.f_measure(),
                )
            )
            self._history_index = len(self._history) - 1
            self._eval_plot()
            self._eval_demon_running = False
            self._eval_normalized_grammar = None
        else:
            progress = 100 * self._eval_index / self._devset_size.get()
            self.status["text"] = "Evaluating on Development Set (%d%%)" % progress
            self._eval_demon_running = True
            self._adaptively_modify_eval_chunk(time.time() - t0)
            self.top.after(int(self._EVAL_FREQ * 1000), self._eval_demon)

    def _adaptively_modify_eval_chunk(self, t):
        """
        Modify _EVAL_CHUNK to try to keep the amount of time that the
        eval demon takes between _EVAL_DEMON_MIN and _EVAL_DEMON_MAX.

        :param t: The amount of time that the eval demon took.
        """
        if t > self._EVAL_DEMON_MAX and self._EVAL_CHUNK > 5:
            self._EVAL_CHUNK = min(
                self._EVAL_CHUNK - 1,
                max(
                    int(self._EVAL_CHUNK * (self._EVAL_DEMON_MAX / t)),
                    self._EVAL_CHUNK - 10,
                ),
            )
        elif t < self._EVAL_DEMON_MIN:
            self._EVAL_CHUNK = max(
                self._EVAL_CHUNK + 1,
                min(
                    int(self._EVAL_CHUNK * (self._EVAL_DEMON_MIN / t)),
                    self._EVAL_CHUNK + 10,
                ),
            )

    def _init_widgets(self, top):
        frame0 = Frame(top, **self._FRAME_PARAMS)
        frame0.grid_columnconfigure(0, weight=4)
        frame0.grid_columnconfigure(3, weight=2)
        frame0.grid_rowconfigure(1, weight=1)
        frame0.grid_rowconfigure(5, weight=1)

        # The grammar
        self.grammarbox = Text(frame0, font=self._font, **self._GRAMMARBOX_PARAMS)
        self.grammarlabel = Label(
            frame0,
            font=self._font,
            text="Grammar:",
            highlightcolor="black",
            background=self._GRAMMARBOX_PARAMS["background"],
        )
        self.grammarlabel.grid(column=0, row=0, sticky="SW")
        self.grammarbox.grid(column=0, row=1, sticky="NEWS")

        # Scroll bar for grammar
        grammar_scrollbar = Scrollbar(frame0, command=self.grammarbox.yview)
        grammar_scrollbar.grid(column=1, row=1, sticky="NWS")
        self.grammarbox.config(yscrollcommand=grammar_scrollbar.set)

        # grammar buttons
        bg = self._FRAME_PARAMS["background"]
        frame3 = Frame(frame0, background=bg)
        frame3.grid(column=0, row=2, sticky="EW")
        Button(
            frame3,
            text="Prev Grammar",
            command=self._history_prev,
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        Button(
            frame3,
            text="Next Grammar",
            command=self._history_next,
            **self._BUTTON_PARAMS,
        ).pack(side="left")

        # Help box
        self.helpbox = Text(frame0, font=self._smallfont, **self._HELPBOX_PARAMS)
        self.helpbox.grid(column=3, row=1, sticky="NEWS")
        self.helptabs = {}
        bg = self._FRAME_PARAMS["background"]
        helptab_frame = Frame(frame0, background=bg)
        helptab_frame.grid(column=3, row=0, sticky="SW")
        for i, (tab, tabstops, text) in enumerate(self.HELP):
            label = Label(helptab_frame, text=tab, font=self._smallfont)
            label.grid(column=i * 2, row=0, sticky="S")
            # help_frame.grid_columnconfigure(i, weight=1)
            # label.pack(side='left')
            label.bind("<ButtonPress>", lambda e, tab=tab: self.show_help(tab))
            self.helptabs[tab] = label
            Frame(
                helptab_frame, height=1, width=self._HELPTAB_SPACER, background=bg
            ).grid(column=i * 2 + 1, row=0)
        self.helptabs[self.HELP[0][0]].configure(font=self._font)
        self.helpbox.tag_config("elide", elide=True)
        for tag, params in self.HELP_AUTOTAG:
            self.helpbox.tag_config("tag-%s" % tag, **params)
        self.show_help(self.HELP[0][0])

        # Scroll bar for helpbox
        help_scrollbar = Scrollbar(frame0, command=self.helpbox.yview)
        self.helpbox.config(yscrollcommand=help_scrollbar.set)
        help_scrollbar.grid(column=4, row=1, sticky="NWS")

        # The dev set
        frame4 = Frame(frame0, background=self._FRAME_PARAMS["background"])
        self.devsetbox = Text(frame4, font=self._font, **self._DEVSETBOX_PARAMS)
        self.devsetbox.pack(expand=True, fill="both")
        self.devsetlabel = Label(
            frame0,
            font=self._font,
            text="Development Set:",
            justify="right",
            background=self._DEVSETBOX_PARAMS["background"],
        )
        self.devsetlabel.grid(column=0, row=4, sticky="SW")
        frame4.grid(column=0, row=5, sticky="NEWS")

        # dev set scrollbars
        self.devset_scroll = Scrollbar(frame0, command=self._devset_scroll)
        self.devset_scroll.grid(column=1, row=5, sticky="NWS")
        self.devset_xscroll = Scrollbar(
            frame4, command=self.devsetbox.xview, orient="horiz"
        )
        self.devsetbox["xscrollcommand"] = self.devset_xscroll.set
        self.devset_xscroll.pack(side="bottom", fill="x")

        # dev set buttons
        bg = self._FRAME_PARAMS["background"]
        frame1 = Frame(frame0, background=bg)
        frame1.grid(column=0, row=7, sticky="EW")
        Button(
            frame1,
            text="Prev Example (Ctrl-p)",
            command=self._devset_prev,
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        Button(
            frame1,
            text="Next Example (Ctrl-n)",
            command=self._devset_next,
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        self.devset_button = Button(
            frame1,
            text="Show example",
            command=self.show_devset,
            state="disabled",
            **self._BUTTON_PARAMS,
        )
        self.devset_button.pack(side="right")
        self.trace_button = Button(
            frame1, text="Show trace", command=self.show_trace, **self._BUTTON_PARAMS
        )
        self.trace_button.pack(side="right")

        # evaluation box
        self.evalbox = Canvas(frame0, **self._EVALBOX_PARAMS)
        label = Label(
            frame0,
            font=self._font,
            text="Evaluation:",
            justify="right",
            background=self._EVALBOX_PARAMS["background"],
        )
        label.grid(column=3, row=4, sticky="SW")
        self.evalbox.grid(column=3, row=5, sticky="NEWS", columnspan=2)

        # evaluation box buttons
        bg = self._FRAME_PARAMS["background"]
        frame2 = Frame(frame0, background=bg)
        frame2.grid(column=3, row=7, sticky="EW")
        self._autoscale = IntVar(self.top)
        self._autoscale.set(False)
        Checkbutton(
            frame2,
            variable=self._autoscale,
            command=self._eval_plot,
            text="Zoom",
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        self._eval_lines = IntVar(self.top)
        self._eval_lines.set(False)
        Checkbutton(
            frame2,
            variable=self._eval_lines,
            command=self._eval_plot,
            text="Lines",
            **self._BUTTON_PARAMS,
        ).pack(side="left")
        Button(frame2, text="History", **self._BUTTON_PARAMS).pack(side="right")

        # The status label
        self.status = Label(frame0, font=self._font, **self._STATUS_PARAMS)
        self.status.grid(column=0, row=9, sticky="NEW", padx=3, pady=2, columnspan=5)

        # Help box & devset box can't be edited.
        self.helpbox["state"] = "disabled"
        self.devsetbox["state"] = "disabled"

        # Spacers
        bg = self._FRAME_PARAMS["background"]
        Frame(frame0, height=10, width=0, background=bg).grid(column=0, row=3)
        Frame(frame0, height=0, width=10, background=bg).grid(column=2, row=0)
        Frame(frame0, height=6, width=0, background=bg).grid(column=0, row=8)

        # pack the frame.
        frame0.pack(fill="both", expand=True)

        # Set up colors for the devset box
        self.devsetbox.tag_config("true-pos", background="#afa", underline="True")
        self.devsetbox.tag_config("false-neg", underline="True", foreground="#800")
        self.devsetbox.tag_config("false-pos", background="#faa")
        self.devsetbox.tag_config("trace", foreground="#666", wrap="none")
        self.devsetbox.tag_config("wrapindent", lmargin2=30, wrap="none")
        self.devsetbox.tag_config("error", foreground="#800")

        # And for the grammarbox
        self.grammarbox.tag_config("error", background="#fec")
        self.grammarbox.tag_config("comment", foreground="#840")
        self.grammarbox.tag_config("angle", foreground="#00f")
        self.grammarbox.tag_config("brace", foreground="#0a0")
        self.grammarbox.tag_config("hangindent", lmargin1=0, lmargin2=40)

    _showing_trace = False

    def show_trace(self, *e):
        self._showing_trace = True
        self.trace_button["state"] = "disabled"
        self.devset_button["state"] = "normal"

        self.devsetbox["state"] = "normal"
        # self.devsetbox['wrap'] = 'none'
        self.devsetbox.delete("1.0", "end")
        self.devsetlabel["text"] = "Development Set (%d/%d)" % (
            (self.devset_index + 1, self._devset_size.get())
        )

        if self.chunker is None:
            self.devsetbox.insert("1.0", "Trace: waiting for a valid grammar.")
            self.devsetbox.tag_add("error", "1.0", "end")
            return  # can't do anything more

        gold_tree = self.devset[self.devset_index]
        rules = self.chunker.rules()

        # Calculate the tag sequence
        tagseq = "\t"
        charnum = [1]
        for wordnum, (word, pos) in enumerate(gold_tree.leaves()):
            tagseq += "%s " % pos
            charnum.append(len(tagseq))
        self.charnum = {
            (i, j): charnum[j]
            for i in range(len(rules) + 1)
            for j in range(len(charnum))
        }
        self.linenum = {i: i * 2 + 2 for i in range(len(rules) + 1)}

        for i in range(len(rules) + 1):
            if i == 0:
                self.devsetbox.insert("end", "Start:\n")
                self.devsetbox.tag_add("trace", "end -2c linestart", "end -2c")
            else:
                self.devsetbox.insert("end", "Apply %s:\n" % rules[i - 1])
                self.devsetbox.tag_add("trace", "end -2c linestart", "end -2c")
            # Display the tag sequence.
            self.devsetbox.insert("end", tagseq + "\n")
            self.devsetbox.tag_add("wrapindent", "end -2c linestart", "end -2c")
            # Run a partial parser, and extract gold & test chunks
            chunker = RegexpChunkParser(rules[:i])
            test_tree = self._chunkparse(gold_tree.leaves())
            gold_chunks = self._chunks(gold_tree)
            test_chunks = self._chunks(test_tree)
            # Compare them.
            for chunk in gold_chunks.intersection(test_chunks):
                self._color_chunk(i, chunk, "true-pos")
            for chunk in gold_chunks - test_chunks:
                self._color_chunk(i, chunk, "false-neg")
            for chunk in test_chunks - gold_chunks:
                self._color_chunk(i, chunk, "false-pos")
        self.devsetbox.insert("end", "Finished.\n")
        self.devsetbox.tag_add("trace", "end -2c linestart", "end -2c")

        # This is a hack, because the x-scrollbar isn't updating its
        # position right -- I'm not sure what the underlying cause is
        # though.  (This is on OS X w/ python 2.5)
        self.top.after(100, self.devset_xscroll.set, 0, 0.3)

    def show_help(self, tab):
        self.helpbox["state"] = "normal"
        self.helpbox.delete("1.0", "end")
        for name, tabstops, text in self.HELP:
            if name == tab:
                text = text.replace(
                    "<<TAGSET>>",
                    "\n".join(
                        "\t%s\t%s" % item
                        for item in sorted(
                            list(self.tagset.items()),
                            key=lambda t_w: re.match(r"\w+", t_w[0])
                            and (0, t_w[0])
                            or (1, t_w[0]),
                        )
                    ),
                )

                self.helptabs[name].config(**self._HELPTAB_FG_PARAMS)
                self.helpbox.config(tabs=tabstops)
                self.helpbox.insert("1.0", text + "\n" * 20)
                C = "1.0 + %d chars"
                for tag, params in self.HELP_AUTOTAG:
                    pattern = f"(?s)(<{tag}>)(.*?)(</{tag}>)"
                    for m in re.finditer(pattern, text):
                        self.helpbox.tag_add("elide", C % m.start(1), C % m.end(1))
                        self.helpbox.tag_add(
                            "tag-%s" % tag, C % m.start(2), C % m.end(2)
                        )
                        self.helpbox.tag_add("elide", C % m.start(3), C % m.end(3))
            else:
                self.helptabs[name].config(**self._HELPTAB_BG_PARAMS)
        self.helpbox["state"] = "disabled"

    def _history_prev(self, *e):
        self._view_history(self._history_index - 1)
        return "break"

    def _history_next(self, *e):
        self._view_history(self._history_index + 1)
        return "break"

    def _view_history(self, index):
        # Bounds & sanity checking:
        index = max(0, min(len(self._history) - 1, index))
        if not self._history:
            return
        # Already viewing the requested history item?
        if index == self._history_index:
            return
        # Show the requested grammar.  It will get added to _history
        # only if they edit it (causing self.update() to get run.)
        self.grammarbox["state"] = "normal"
        self.grammarbox.delete("1.0", "end")
        self.grammarbox.insert("end", self._history[index][0])
        self.grammarbox.mark_set("insert", "1.0")
        self._history_index = index
        self._syntax_highlight_grammar(self._history[index][0])
        # Record the normalized grammar & regenerate the chunker.
        self.normalized_grammar = self.normalize_grammar(self._history[index][0])
        if self.normalized_grammar:
            rules = [
                RegexpChunkRule.fromstring(line)
                for line in self.normalized_grammar.split("\n")
            ]
        else:
            rules = []
        self.chunker = RegexpChunkParser(rules)
        # Show the score.
        self._eval_plot()
        # Update the devset box
        self._highlight_devset()
        if self._showing_trace:
            self.show_trace()
        # Update the grammar label
        if self._history_index < len(self._history) - 1:
            self.grammarlabel["text"] = "Grammar {}/{}:".format(
                self._history_index + 1,
                len(self._history),
            )
        else:
            self.grammarlabel["text"] = "Grammar:"

    def _devset_next(self, *e):
        self._devset_scroll("scroll", 1, "page")
        return "break"

    def _devset_prev(self, *e):
        self._devset_scroll("scroll", -1, "page")
        return "break"

    def destroy(self, *e):
        if self.top is None:
            return
        self.top.destroy()
        self.top = None

    def _devset_scroll(self, command, *args):
        N = 1  # size of a page -- one sentence.
        showing_trace = self._showing_trace
        if command == "scroll" and args[1].startswith("unit"):
            self.show_devset(self.devset_index + int(args[0]))
        elif command == "scroll" and args[1].startswith("page"):
            self.show_devset(self.devset_index + N * int(args[0]))
        elif command == "moveto":
            self.show_devset(int(float(args[0]) * self._devset_size.get()))
        else:
            assert 0, f"bad scroll command {command} {args}"
        if showing_trace:
            self.show_trace()

    def show_devset(self, index=None):
        if index is None:
            index = self.devset_index

        # Bounds checking
        index = min(max(0, index), self._devset_size.get() - 1)

        if index == self.devset_index and not self._showing_trace:
            return
        self.devset_index = index

        self._showing_trace = False
        self.trace_button["state"] = "normal"
        self.devset_button["state"] = "disabled"

        # Clear the text box.
        self.devsetbox["state"] = "normal"
        self.devsetbox["wrap"] = "word"
        self.devsetbox.delete("1.0", "end")
        self.devsetlabel["text"] = "Development Set (%d/%d)" % (
            (self.devset_index + 1, self._devset_size.get())
        )

        # Add the sentences
        sample = self.devset[self.devset_index : self.devset_index + 1]
        self.charnum = {}
        self.linenum = {0: 1}
        for sentnum, sent in enumerate(sample):
            linestr = ""
            for wordnum, (word, pos) in enumerate(sent.leaves()):
                self.charnum[sentnum, wordnum] = len(linestr)
                linestr += f"{word}/{pos} "
                self.charnum[sentnum, wordnum + 1] = len(linestr)
            self.devsetbox.insert("end", linestr[:-1] + "\n\n")

        # Highlight chunks in the dev set
        if self.chunker is not None:
            self._highlight_devset()
        self.devsetbox["state"] = "disabled"

        # Update the scrollbar
        first = self.devset_index / self._devset_size.get()
        last = (self.devset_index + 2) / self._devset_size.get()
        self.devset_scroll.set(first, last)

    def _chunks(self, tree):
        chunks = set()
        wordnum = 0
        for child in tree:
            if isinstance(child, Tree):
                if child.label() == self._chunk_label:
                    chunks.add((wordnum, wordnum + len(child)))
                wordnum += len(child)
            else:
                wordnum += 1
        return chunks

    def _syntax_highlight_grammar(self, grammar):
        if self.top is None:
            return
        self.grammarbox.tag_remove("comment", "1.0", "end")
        self.grammarbox.tag_remove("angle", "1.0", "end")
        self.grammarbox.tag_remove("brace", "1.0", "end")
        self.grammarbox.tag_add("hangindent", "1.0", "end")
        for lineno, line in enumerate(grammar.split("\n")):
            if not line.strip():
                continue
            m = re.match(r"(\\.|[^#])*(#.*)?", line)
            comment_start = None
            if m.group(2):
                comment_start = m.start(2)
                s = "%d.%d" % (lineno + 1, m.start(2))
                e = "%d.%d" % (lineno + 1, m.end(2))
                self.grammarbox.tag_add("comment", s, e)
            for m in re.finditer("[<>{}]", line):
                if comment_start is not None and m.start() >= comment_start:
                    break
                s = "%d.%d" % (lineno + 1, m.start())
                e = "%d.%d" % (lineno + 1, m.end())
                if m.group() in "<>":
                    self.grammarbox.tag_add("angle", s, e)
                else:
                    self.grammarbox.tag_add("brace", s, e)

    def _grammarcheck(self, grammar):
        if self.top is None:
            return
        self.grammarbox.tag_remove("error", "1.0", "end")
        self._grammarcheck_errs = []
        for lineno, line in enumerate(grammar.split("\n")):
            line = re.sub(r"((\\.|[^#])*)(#.*)?", r"\1", line)
            line = line.strip()
            if line:
                try:
                    RegexpChunkRule.fromstring(line)
                except ValueError as e:
                    self.grammarbox.tag_add(
                        "error", "%s.0" % (lineno + 1), "%s.0 lineend" % (lineno + 1)
                    )
        self.status["text"] = ""

    def update(self, *event):
        # Record when update was called (for grammarcheck)
        if event:
            self._last_keypress = time.time()

        # Read the grammar from the Text box.
        self.grammar = grammar = self.grammarbox.get("1.0", "end")

        # If the grammar hasn't changed, do nothing:
        normalized_grammar = self.normalize_grammar(grammar)
        if normalized_grammar == self.normalized_grammar:
            return
        else:
            self.normalized_grammar = normalized_grammar

        # If the grammar has changed, and we're looking at history,
        # then stop looking at history.
        if self._history_index < len(self._history) - 1:
            self.grammarlabel["text"] = "Grammar:"

        self._syntax_highlight_grammar(grammar)

        # The grammar has changed; try parsing it.  If it doesn't
        # parse, do nothing.  (flag error location?)
        try:
            # Note: the normalized grammar has no blank lines.
            if normalized_grammar:
                rules = [
                    RegexpChunkRule.fromstring(line)
                    for line in normalized_grammar.split("\n")
                ]
            else:
                rules = []
        except ValueError as e:
            # Use the un-normalized grammar for error highlighting.
            self._grammarcheck(grammar)
            self.chunker = None
            return

        self.chunker = RegexpChunkParser(rules)
        self.grammarbox.tag_remove("error", "1.0", "end")
        self.grammar_changed = time.time()
        # Display the results
        if self._showing_trace:
            self.show_trace()
        else:
            self._highlight_devset()
        # Start the eval demon
        if not self._eval_demon_running:
            self._eval_demon()

    def _highlight_devset(self, sample=None):
        if sample is None:
            sample = self.devset[self.devset_index : self.devset_index + 1]

        self.devsetbox.tag_remove("true-pos", "1.0", "end")
        self.devsetbox.tag_remove("false-neg", "1.0", "end")
        self.devsetbox.tag_remove("false-pos", "1.0", "end")

        # Run the grammar on the test cases.
        for sentnum, gold_tree in enumerate(sample):
            # Run the chunk parser
            test_tree = self._chunkparse(gold_tree.leaves())
            # Extract gold & test chunks
            gold_chunks = self._chunks(gold_tree)
            test_chunks = self._chunks(test_tree)
            # Compare them.
            for chunk in gold_chunks.intersection(test_chunks):
                self._color_chunk(sentnum, chunk, "true-pos")
            for chunk in gold_chunks - test_chunks:
                self._color_chunk(sentnum, chunk, "false-neg")
            for chunk in test_chunks - gold_chunks:
                self._color_chunk(sentnum, chunk, "false-pos")

    def _chunkparse(self, words):
        try:
            return self.chunker.parse(words)
        except (ValueError, IndexError) as e:
            # There's an error somewhere in the grammar, but we're not sure
            # exactly where, so just mark the whole grammar as bad.
            # E.g., this is caused by: "({<NN>})"
            self.grammarbox.tag_add("error", "1.0", "end")
            # Treat it as tagging nothing:
            return words

    def _color_chunk(self, sentnum, chunk, tag):
        start, end = chunk
        self.devsetbox.tag_add(
            tag,
            f"{self.linenum[sentnum]}.{self.charnum[sentnum, start]}",
            f"{self.linenum[sentnum]}.{self.charnum[sentnum, end] - 1}",
        )

    def reset(self):
        # Clear various variables
        self.chunker = None
        self.grammar = None
        self.normalized_grammar = None
        self.grammar_changed = 0
        self._history = []
        self._history_index = 0
        # Update the on-screen display.
        self.grammarbox.delete("1.0", "end")
        self.show_devset(0)
        self.update()
        # self._eval_plot()

    SAVE_GRAMMAR_TEMPLATE = (
        "# Regexp Chunk Parsing Grammar\n"
        "# Saved %(date)s\n"
        "#\n"
        "# Development set: %(devset)s\n"
        "#   Precision: %(precision)s\n"
        "#   Recall:    %(recall)s\n"
        "#   F-score:   %(fscore)s\n\n"
        "%(grammar)s\n"
    )

    def save_grammar(self, filename=None):
        if not filename:
            ftypes = [("Chunk Gramamr", ".chunk"), ("All files", "*")]
            filename = asksaveasfilename(filetypes=ftypes, defaultextension=".chunk")
            if not filename:
                return
        if self._history and self.normalized_grammar == self.normalize_grammar(
            self._history[-1][0]
        ):
            precision, recall, fscore = (
                "%.2f%%" % (100 * v) for v in self._history[-1][1:]
            )
        elif self.chunker is None:
            precision = recall = fscore = "Grammar not well formed"
        else:
            precision = recall = fscore = "Not finished evaluation yet"

        with open(filename, "w") as outfile:
            outfile.write(
                self.SAVE_GRAMMAR_TEMPLATE
                % dict(
                    date=time.ctime(),
                    devset=self.devset_name,
                    precision=precision,
                    recall=recall,
                    fscore=fscore,
                    grammar=self.grammar.strip(),
                )
            )

    def load_grammar(self, filename=None):
        if not filename:
            ftypes = [("Chunk Gramamr", ".chunk"), ("All files", "*")]
            filename = askopenfilename(filetypes=ftypes, defaultextension=".chunk")
            if not filename:
                return
        self.grammarbox.delete("1.0", "end")
        self.update()
        with open(filename) as infile:
            grammar = infile.read()
        grammar = re.sub(
            r"^\# Regexp Chunk Parsing Grammar[\s\S]*" "F-score:.*\n", "", grammar
        ).lstrip()
        self.grammarbox.insert("1.0", grammar)
        self.update()

    def save_history(self, filename=None):
        if not filename:
            ftypes = [("Chunk Gramamr History", ".txt"), ("All files", "*")]
            filename = asksaveasfilename(filetypes=ftypes, defaultextension=".txt")
            if not filename:
                return

        with open(filename, "w") as outfile:
            outfile.write("# Regexp Chunk Parsing Grammar History\n")
            outfile.write("# Saved %s\n" % time.ctime())
            outfile.write("# Development set: %s\n" % self.devset_name)
            for i, (g, p, r, f) in enumerate(self._history):
                hdr = (
                    "Grammar %d/%d (precision=%.2f%%, recall=%.2f%%, "
                    "fscore=%.2f%%)"
                    % (i + 1, len(self._history), p * 100, r * 100, f * 100)
                )
                outfile.write("\n%s\n" % hdr)
                outfile.write("".join("  %s\n" % line for line in g.strip().split()))

            if not (
                self._history
                and self.normalized_grammar
                == self.normalize_grammar(self._history[-1][0])
            ):
                if self.chunker is None:
                    outfile.write("\nCurrent Grammar (not well-formed)\n")
                else:
                    outfile.write("\nCurrent Grammar (not evaluated)\n")
                outfile.write(
                    "".join("  %s\n" % line for line in self.grammar.strip().split())
                )

    def about(self, *e):
        ABOUT = "NLTK RegExp Chunk Parser Application\n" + "Written by Edward Loper"
        TITLE = "About: Regular Expression Chunk Parser Application"
        try:
            from tkinter.messagebox import Message

            Message(message=ABOUT, title=TITLE).show()
        except:
            ShowText(self.top, TITLE, ABOUT)

    def set_devset_size(self, size=None):
        if size is not None:
            self._devset_size.set(size)
        self._devset_size.set(min(len(self.devset), self._devset_size.get()))
        self.show_devset(1)
        self.show_devset(0)
        # what about history?  Evaluated at diff dev set sizes!

    def resize(self, size=None):
        if size is not None:
            self._size.set(size)
        size = self._size.get()
        self._font.configure(size=-(abs(size)))
        self._smallfont.configure(size=min(-10, -(abs(size)) * 14 // 20))

    def mainloop(self, *args, **kwargs):
        """
        Enter the Tkinter mainloop.  This function must be called if
        this demo is created from a non-interactive program (e.g.
        from a secript); otherwise, the demo will close as soon as
        the script completes.
        """
        if in_idle():
            return
        self.top.mainloop(*args, **kwargs)


def app():
    RegexpChunkApp().mainloop()


if __name__ == "__main__":
    app()

__all__ = ["app"]