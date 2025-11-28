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

# 4.4: Retry と例外分類
try:
    from nexuscore.core.retry_utils import retry_with_context, RetryContext
    from nexuscore.core.errors import (
        ModelRateLimitError,
        ModelTimeoutError,
        ModelConnectionError,
        InvalidModelOutputError,
        convert_http_error_to_nexus_error,
    )
    HAS_RETRY = True
except ImportError:
    HAS_RETRY = False
    retry_with_context = None  # type: ignore
    RetryContext = None  # type: ignore
    ModelRateLimitError = Exception  # type: ignore
    ModelTimeoutError = Exception  # type: ignore
    ModelConnectionError = Exception  # type: ignore
    InvalidModelOutputError = Exception  # type: ignore
    convert_http_error_to_nexus_error = None  # type: ignore


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
        # 4.4: RetryContext を保持（self_healing_service から設定可能）
        self.retry_context: Optional[RetryContext] = None

    # ---------------------------- Public API ---------------------------- #
    def execute_llm_task(
        self,
        prompt: str,
        as_json: bool = False,
        task_type: Optional[str] = None,
        retry_context: Optional[RetryContext] = None,
        **kwargs
    ) -> str:
        """
        ルーター経由で最適な LLM を取得し実行。
        as_json=True のときは、system に JSON-only ガード文を自動付与する。

        Args:
            prompt: ユーザープロンプト
            as_json: JSON 形式で返すか
            task_type: タスクタイプ（オプション）
            retry_context: RetryContext インスタンス（retry_count と error_class を記録）
            **kwargs: その他の引数

        Returns:
            LLM の応答文字列
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

        # 4.4: Retry 対応の内部関数
        def _execute_llm_internal() -> str:
            # ルーターから LLM クライアントを取得
            llm = None
            try:
                if self.llm_router and hasattr(self.llm_router, "get_llm_for_task"):
                    llm = self.llm_router.get_llm_for_task(prompt, task_type=task_type)
                elif self.llm_router and hasattr(self.llm_router, "get_default_llm"):
                    llm = self.llm_router.get_default_llm()
            except Exception as e:
                self.logger.error(f"LLM クライアント取得に失敗: {e}", exc_info=True)
                # HTTP エラーを NexusCore 例外に変換
                if HAS_RETRY and convert_http_error_to_nexus_error:
                    raise convert_http_error_to_nexus_error(e)
                raise

            # 実行
            if llm and hasattr(llm, "execute"):
                try:
                    result = llm.execute(
                        prompt=prompt,
                        system_prompt=system_prompt,
                        as_json=as_json,
                        **kwargs
                    )
                    # as_json=True の場合、JSON パースを試行して検証
                    if as_json and result:
                        import json
                        try:
                            json.loads(result)
                        except json.JSONDecodeError as e:
                            if HAS_RETRY:
                                raise InvalidModelOutputError(f"Invalid JSON output: {e}")
                            raise
                    return result
                except Exception as e:
                    # HTTP エラーを NexusCore 例外に変換
                    if HAS_RETRY and convert_http_error_to_nexus_error:
                        raise convert_http_error_to_nexus_error(e)
                    raise
            else:
                self.logger.warning("有効な LLM クライアントが見つからず、空レスポンスを返します。")
                return "{}" if as_json else ""

        # 4.4: Retry を適用（retry_context パラメータまたは self.retry_context を使用）
        active_retry_context = retry_context or self.retry_context
        if HAS_RETRY and retry_with_context:
            from nexuscore.core.errors import (
                ModelRateLimitError,
                ModelTimeoutError,
                ModelConnectionError,
            )
            wrapped_func = retry_with_context(
                _execute_llm_internal,
                max_retries=2,
                base_delay=1.0,
                retry_on=(ModelRateLimitError, ModelTimeoutError, ModelConnectionError),
                logger_instance=self.logger,
                context=active_retry_context,
            )
            try:
                return wrapped_func()
            except Exception as e:
                self.logger.error(f"LLM 実行エラー（Retry 後も失敗）: {e}", exc_info=True)
                # フォールバック
                return "{}" if as_json else ""
        else:
            # Retry が利用できない場合は従来通り
            try:
                return _execute_llm_internal()
            except Exception as e:
                self.logger.error(f"LLM 実行エラー: {e}", exc_info=True)
                # フォールバック
                return "{}" if as_json else ""
