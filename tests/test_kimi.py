# ==============================================================================
# NexusCore Kimi (Moonshot) Connection and Auto-Switch Test (v2)
# 目的: 1. Kimi APIへの基本的な接続性を検証する
#       2. 長短プロンプトに応じたモデル自動切り替え機能が正しく動作するか検証する
# 実行方法: プロジェクトルートから `python tests/test_kimi.py` を実行
# ==============================================================================

import pytest

# Kimi API は現在利用不可のためモジュールごとスキップ
pytest.skip("Kimi API is unavailable; skipping Kimi-related tests.", allow_module_level=True)

import os
import sys
import logging
from pathlib import Path

# --- プロジェクトルートをsys.pathに追加 ---
try:
    _ROOT = Path(__file__).resolve().parents[1]
    _SRC = _ROOT / "src"
    if str(_SRC) not in sys.path:
        sys.path.insert(0, str(_SRC))
    print(f"プロジェクトのソースディレクトリを追加しました: {_SRC}")
except IndexError:
    print("エラー: このスクリプトはプロジェクトの 'tests' ディレクトリに配置してください。")
    sys.exit(1)

# --- テスト対象のモジュールをインポート ---
try:
    from nexuscore.llm.llm_router import LLMRouter, MoonshotLLM, BaseLLM
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    print("`src` ディレクトリの構造が正しいか確認してください。")
    sys.exit(1)

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_kimi_test():
    """
    Kimi (Moonshot) の接続性とモデル自動切り替え機能をテストします。
    """
    logging.info("Kimi (Moonshot) 接続テストを開始します...")

    try:
        router = LLMRouter()
    except ValueError as ve:
        logging.error(f"LLMRouterの初期化中に設定エラーが発生しました: {ve}", exc_info=True)
        return
    except Exception as e:
        logging.error(f"LLMRouterの初期化中に予期せぬエラーが発生しました: {e}", exc_info=True)
        return

    # --- Part 1 は成功しているので、ここではスキップも可能 ---
    # (このまま実行しても問題ありません)
    logging.info("\n--- [Part 1] 基本的なAPI接続テストを開始 ---")
    try:
        client = router._make_client("kimi-k2-turbo-preview")
        system_prompt = "You are a helpful assistant. Respond in Japanese."
        prompt = "この文章はKimi APIへの基本的な接続テストです。成功したら「Kimi基本接続成功」とだけ返答してください。"
        logging.info(f"モデル '{client.model_name}' にリクエストを送信します...")
        response = client.execute(prompt=prompt, system_prompt=system_prompt)

        if "Kimi基本接続成功" in response:
            logging.info(f"✅ [Part 1] テスト成功！ モデル '{client.model_name}' からの応答: {response}")
        else:
            logging.warning(f"⚠️ [Part 1] テストは成功しましたが、予期しない応答です。応答: {response}")
    except ValueError as ve:
        logging.error(f"❌ [Part 1] テスト失敗: 設定エラーです。 -> {ve}")
        return
    except Exception as e:
        logging.error(f"❌ [Part 1] テスト失敗: API呼び出し中にエラーが発生しました。 -> {e}", exc_info=True)
        return
    finally:
        logging.info("--- [Part 1] 基本的なAPI接続テストを終了 ---\n")


    # ==========================================================================
    # Part 2: モデル自動切り替え機能テスト
    # ==========================================================================
    logging.info("--- [Part 2] モデル自動切り替えテストを開始 ---")
    
    # --- Test Case: 短文プロンプト ---
    logging.info("--- [Case 2a] 短文プロンプトのテスト ---")
    short_prompt = "日本の首都について教えてください。"
    expected_short_model = "kimi-k2-turbo-preview"
    
    try:
        logging.info(f"ルーターに短文プロンプト（{len(short_prompt)}文字）を渡します...")
        client_short = router.get_llm_for_task(short_prompt)

        if isinstance(client_short, MoonshotLLM) and client_short.model_name == expected_short_model:
            logging.info(f"✅ [Case 2a] モデル選択成功！期待通り '{expected_short_model}' が選択されました。")
            response_short = client_short.execute(prompt=short_prompt, system_prompt="簡潔に日本語で回答せよ。")
            logging.info(f"✅ [Case 2a] APIコール成功！応答: {response_short[:100]}...")
        else:
            logging.error(f"❌ [Case 2a] モデル選択失敗！")
            logging.error(f"  期待したモデル: {expected_short_model}")
            # ★★★ 修正点: ログ出力のバグを修正 ★★★
            actual_model = client_short.model_name if isinstance(client_short, BaseLLM) else type(client_short).__name__
            logging.error(f"  実際に選択されたモデル: {actual_model}")
            
    except Exception as e:
        logging.error(f"❌ [Case 2a] テスト中にエラーが発生しました: {e}", exc_info=True)
    finally:
        logging.info("--- [Case 2a] 短文プロンプトのテストを終了 ---\n")

    # --- Test Case: 長文プロンプト ---
    logging.info("--- [Case 2b] 長文プロンプトのテスト ---")
    long_prompt = "これは長文テストです。" * 500
    expected_long_model = "kimi-k2-0711-preview"

    try:
        logging.info(f"ルーターに長文プロンプト（{len(long_prompt)}文字）を渡します...")
        client_long = router.get_llm_for_task(long_prompt)

        if isinstance(client_long, MoonshotLLM) and client_long.model_name == expected_long_model:
            logging.info(f"✅ [Case 2b] モデル選択成功！期待通り '{expected_long_model}' が選択されました。")
            prompt = "この長文テキストの要点を3つにまとめてください。"
            response_long = client_long.execute(prompt=prompt, system_prompt="長文要約アシスタントです。日本語で回答してください。")
            logging.info(f"✅ [Case 2b] APIコール成功！応答: {response_long[:200]}...")

        else:
            logging.error(f"❌ [Case 2b] モデル選択失敗！")
            logging.error(f"  期待したモデル: {expected_long_model}")
            # ★★★ 修正点: ログ出力のバグを修正 ★★★
            actual_model = client_long.model_name if isinstance(client_long, BaseLLM) else type(client_long).__name__
            logging.error(f"  実際に選択されたモデル: {actual_model}")

    except Exception as e:
        logging.error(f"❌ [Case 2b] テスト中にエラーが発生しました: {e}", exc_info=True)

    finally:
        logging.info("\n--- [Part 2] モデル自動切り替えテストを終了 ---")


if __name__ == "__main__":
    run_kimi_test()
