# ==============================================================================
# NexusCore DeepSeek Connection Test (v2)
# 目的: llm_router.py を利用してDeepSeek APIへの接続性を検証する
# 実行方法: プロジェクトルートから `python tests/test_deepseek.py` を実行
# ==============================================================================

import logging
import sys
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
    from nexuscore.llm.llm_router import LLMRouter
except ImportError as e:
    print(f"モジュールのインポートに失敗しました: {e}")
    print("`src` ディレクトリの構造が正しいか確認してください。")
    sys.exit(1)

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_deepseek_test():
    """
    DeepSeekの各モデルに対して接続テストを実行します。
    """
    logging.info("DeepSeek 接続テストを開始します...")

    try:
        router = LLMRouter()
    except Exception as e:
        logging.error(f"LLMRouterの初期化中にエラーが発生しました: {e}", exc_info=True)
        return

    models_to_test = ["deepseek-reasoner", "deepseek-chat"]

    for model_name in models_to_test:
        logging.info(f"--- モデル '{model_name}' のテストを開始 ---")
        try:
            # ★★★ 修正点: クライアント生成をtry-exceptで囲む ★★★
            client = router._make_client(model_name)

            # ここから下はクライアント生成が成功した場合のみ実行される
            system_prompt = "You are a helpful assistant. Respond in Japanese."
            prompt = f"この文章は、DeepSeekのモデル「{model_name}」への接続テストです。成功したら「接続成功」とだけ返答してください。"

            logging.info(f"モデル '{model_name}' にリクエストを送信します...")
            response = client.execute(prompt=prompt, system_prompt=system_prompt)

            if "接続成功" in response:
                logging.info(f"✅ テスト成功！ モデル '{model_name}' からの応答: {response}")
            else:
                logging.warning(
                    f"⚠️ テストは成功しましたが、予期しない応答です。モデル '{model_name}' からの応答: {response}"
                )

        except ValueError as ve:
            # APIキー未設定の場合に llm_router.py が発生させる ValueError をここで捕捉
            logging.error(f"❌ テスト失敗 ({model_name}): 設定エラーです。 -> {ve}")
            logging.error(
                "👉 プロジェクトルートの .env ファイルに `DEEPSEEK_API_KEY` が正しく設定されているか確認してください。"
            )
            break  # APIキーがない場合、以降のテストは無意味なのでループを抜ける

        except Exception as e:
            # その他の予期せぬエラー（API接続エラーなど）
            logging.error(
                f"❌ テスト失敗 ({model_name}): API呼び出し中にエラーが発生しました - {e}",
                exc_info=True,
            )
            logging.error(
                "👉 考えられる原因: APIキーが間違っている、ネットワーク接続に問題がある、DeepSeek側のサーバーがダウンしている。"
            )

        finally:
            logging.info(f"--- モデル '{model_name}' のテストを終了 ---\n")


if __name__ == "__main__":
    run_deepseek_test()
