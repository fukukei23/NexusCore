# ==============================================================================
# フォルダ: src/nexuscore/agents/
# ファイル名: base_agent.py
# メモ: 【統合・最終版】
#      - お客様の既存コードと、提案したLLMRouterアーキテクチャを完全に統合。
#      - このファイルをそのままコピペで置き換えることで、すべてのエージェントが
#        タスクに応じて最適なLLMを自動で使い分ける能力を手にします。
# ==============================================================================
import logging
import sys
import os

# --- パス設定とLLMRouterのインポート ---
# このファイル(src/nexuscore/agents/base_agent.py)からの相対パスでプロジェクトルートを解決
current_dir = os.path.dirname(os.path.abspath(__file__))
# current_dir = src/nexuscore/agents
# src_path = src/nexuscore
src_path = os.path.dirname(current_dir)
if src_path not in sys.path:
    # sys.pathに src/nexuscore を追加
    sys.path.insert(0, src_path)

# さらに一つ上の階層 (src) もパスに追加
# これにより、 from nexuscore.llm.llm_router import LLMRouter のような絶対インポートが可能になる
grandparent_dir = os.path.dirname(src_path)
if grandparent_dir not in sys.path:
    sys.path.insert(0, grandparent_dir)


try:
    # 新しく作成したLLMRouterをインポート
    from nexuscore.llm.llm_router import LLMRouter
except ImportError as e:
    print(f"エラー: LLMRouterをインポートできませんでした: {e}")
    print("src/nexuscore/llm/llm_router.py が正しい場所に存在するか確認してください。")
    sys.exit(1)
except Exception as e:
    print(f"予期せぬエラーが発生しました: {e}")
    sys.exit(1)


class BaseAgent:
    """
    すべてのエージェントの基底クラス。
    LLMRouterを内蔵し、タスクに応じた最適なLLMの選択を自動化する。
    """
    # 各エージェント固有のシステムプロンプトを、それぞれのクラスで上書きして使用する
    SYSTEM_PROMPT = "あなたは、有能なAIアシスタントです。"

    def __init__(self):
        """
        BaseAgentを初期化する。
        APIキーやモデル名の管理はすべてLLMRouterに委任するため、引数は不要。
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # ★★★★★ ここがアーキテクチャの核心 ★★★★★
        # APIキーやモデル名を直接扱わず、LLMRouterのインスタンスを保持するだけ。
        # これにより、このBaseAgent自身は、どのLLMが使われるかを一切知る必要がなくなる。
        try:
            self.llm_router = LLMRouter()
            self.logger.info(f"Agent initialized with LLMRouter.")
        except Exception as e:
            self.logger.critical(f"LLMRouterの初期化に失敗しました。アプリケーションを起動できません。: {e}")
            # secrets.pyの読み込み失敗など、致命的なエラーの場合はプログラムを終了させる
            raise e
        # ★★★★★ ここまで ★★★★★

    def execute_llm_task(self, prompt: str, **kwargs) -> str:
        """
        タスク（プロンプト）に最適なLLMを選択し、実行する。
        
        Args:
            prompt (str): LLMに与える具体的な指示。
            **kwargs: as_json (bool), temperature (float) などのオプション。
        
        Returns:
            str: LLMからの応答テキスト。
        """
        try:
            # 1. ルーターにタスク内容を伝え、最適なLLMクライアントを取得
            #    プロンプト自体をタスク説明として利用する
            optimal_llm_client = self.llm_router.get_llm_for_task(prompt)
            
            self.logger.info(f"Executing task with optimal LLM: {optimal_llm_client.model_name}")
            
            # 2. 取得したクライアントを使ってタスクを実行
            #    SYSTEM_PROMPTは、このエージェント自身のものを使用する
            return optimal_llm_client.execute(
                prompt=prompt,
                system_prompt=self.SYSTEM_PROMPT,
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"LLMタスクの実行中にエラーが発生しました: {e}", exc_info=True)
            # エラーが発生した場合でも、システムの動作を止めないように空文字列を返す
            return ""
