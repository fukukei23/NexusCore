# ==============================================================================
# ファイル: src/nexuscore/agents/base_agent.py
# 目的  : すべての Agent の LLM 呼び出し基盤。llm_router 経由でモデル選択。
# ポイント:
#   - as_json=True のとき、system に「JSONのみ」ガード文を自動付与（中央集権）
#   - 鍵優先度: 環境変数 > .env > secrets.py（.env は起動時に環境へロード）
#   - llm_router が無い/失敗時のフォールバックを内蔵
# 依存  : src/nexuscore/llm/llm_router.py
# ==============================================================================
from __future__ import annotations

import os
import logging
from typing import Optional

# .env を環境にロード（既存環境変数は上書きしない = 環境変数が最優先）
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except Exception:
    pass

# ルーターの読み込み
try:
    from ..llm.llm_router import LLMRouter
except Exception:
    LLMRouter = None


class BaseAgent:
    """
    すべてのエージェントが継承する基底クラス。
    - execute_llm_task(prompt, as_json=False) を通じて LLM を実行
    - as_json=True の場合は「JSONのみ」system 指示を自動付与
    """
    # 各派生クラスで上書き可能
    SYSTEM_PROMPT: str = "You are a helpful assistant."

    def __init__(self) -> None:
        self.logger = logging.getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            logging.basicConfig(level=logging.INFO)
        # ルーター初期化（失敗しても動作は継続する）
        self.llm_router: Optional[object] = None
        try:
            if LLMRouter is not None:
                self.llm_router = LLMRouter()
            else:
                self.logger.warning("LLMRouter が見つかりません。ローカルフォールバックに切り替えます。")
        except Exception as e:
            self.logger.error(f"LLMRouter 初期化に失敗: {e}", exc_info=True)
            self.llm_router = None

    # ---------------------------- Public API ---------------------------- #
    def execute_llm_task(self, prompt: str, as_json: bool = False, task_type: Optional[str] = None, **kwargs) -> str:
        """
        ルーター経由で最適な LLM を取得し実行。
        as_json=True のときは、system に JSON-only ガード文を自動付与する。
        """
        # JSON-only の中央集権ガード
        json_guard = (
            "You are a structured JSON emitter. "
            "Return ONLY a valid JSON object or array. "
            "NO code fences, NO surrounding text."
        )
        system_prompt = self.SYSTEM_PROMPT
        if as_json:
            system_prompt = f"{system_prompt}\n{json_guard}"

        # ルーターから LLM クライアントを取得
        llm = None
        try:
            if self.llm_router and hasattr(self.llm_router, "get_llm_for_task"):
                llm = self.llm_router.get_llm_for_task(prompt, task_type=task_type)
            elif self.llm_router and hasattr(self.llm_router, "get_default_llm"):
                llm = self.llm_router.get_default_llm()
        except Exception as e:
            self.logger.error(f"LLM クライアント取得に失敗: {e}", exc_info=True)
            llm = None

        # 実行
        try:
            if llm and hasattr(llm, "execute"):
                return llm.execute(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    as_json=as_json,
                    **kwargs
                )
            else:
                self.logger.warning("有効な LLM クライアントが見つからず、空レスポンスを返します。")
        except Exception as e:
            self.logger.error(f"LLM 実行エラー: {e}", exc_info=True)

        # フォールバック（失敗時）
        return "{}" if as_json else ""
