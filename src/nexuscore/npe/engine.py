# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# フォルダ: src/nexuscore/npe/
# ファイル名: engine.py
#
# 日付: 2025年9月28日
# 日本時間: 06:25
#
# バージョン: 8.0 (Grand Unification)
#
# 改修内容:
#   - ModuleNotFoundError の原因となっていた、存在しない `llms.py` への
#     依存を完全に撤廃しました。
#   - 代わりに、システムの公式なLLM司令塔である `LLMRouter` をインポートし、
#     すべてのLLMの選択、起動、コスト計算を `LLMRouter` に委任するように
#     アーキテクチャを近代化しました。
#   - これにより、NPEがシステムの他の部分と完全に調和して動作するようになり、
#     一貫したガバナンスとルーティングが実現します。
# ==============================================================================

from __future__ import annotations
import logging
from typing import Any, Dict

# --- ★★★★★ ここからが v8.0 統合の核心 ★★★★★ ---
# 存在しない .llms の代わりに、公式の LLMRouter とそのユーティリティをインポート
from nexuscore.llm.llm_router import LLMRouter, _estimate_cost_usd
# --- ★★★★★ ここまで ★★★★★ ---

from .policies import context_scanner, secure_context_builder
from .logger import log_transaction
from .budget import budget_manager

class NexusProtocolEngine:
    """
    NPE v8.0: LLMRouterと統合され、ガバナンスとルーティングを一元管理する。
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        # LLM司令塔であるLLMRouterのインスタンスを生成
        self.llm_router = LLMRouter()
        self.logger.info("Nexus Protocol Engine (v8.0) with LLMRouter integration is running.")

    def process_task(self, prompt: str, metadata: Dict[str, Any], project_id: str = "proj-001") -> str:
        log_data = {"project_id": project_id, "task_metadata": metadata}

        # --- ガバナンス・フェーズ ---
        # 1. セキュリティスキャン
        context_type = context_scanner(prompt)
        log_data["context_type"] = context_type
        if context_type == "sensitive":
            self.logger.warning("[NPE Security] Sensitive data detected. Applying security protocols.")
            prompt = secure_context_builder(prompt)
            log_data["is_masked"] = True

        # 2. ルーティング判断 (LLMRouterを使用)
        # LLMRouterがプロンプトを分析し、最適なLLMクライアントを選択
        llm_client = self.llm_router.get_llm_for_task(prompt)
        model_name = llm_client.model_name
        log_data["initial_route_decision"] = model_name
        
        # 3. 経済性チェック (LLMRouterのコスト計算ロジックを使用)
        # トークン数は概算。正確な値は実際のAPI応答から取得するのが望ましい。
        estimated_in_tokens = len(prompt) // 2 
        estimated_out_tokens = 2000 # デフォルトの想定
        
        cost_in, cost_out = _estimate_cost_usd(
            provider=model_name.split(':')[0] if ':' in model_name else 'unknown',
            model=model_name.split(':')[-1],
            in_tokens=estimated_in_tokens,
            out_tokens=estimated_out_tokens
        )
        estimated_cost = (cost_in or 0) + (cost_out or 0)
        log_data["estimated_cost"] = estimated_cost

        if not budget_manager.check_budget(project_id, estimated_cost):
            self.logger.error(f"[NPE Economic] ERROR: Budget insufficient for model '{model_name}'. Task aborted.")
            log_transaction({**log_data, "status": "aborted_budget_exceeded"})
            # 予算オーバー時は、エラーを示す空の文字列を返す
            return ""
        
        log_data["final_route_decision"] = model_name

        # --- 実行フェーズ ---
        self.logger.info(f"[NPE Executor] Executing task with model '{model_name}'.")
        try:
            # LLMRouterが選択したクライアントでタスクを実行
            result = llm_client.execute(prompt, system_prompt="", as_json=metadata.get("as_json", False))
            # (注: 実際のコストはAPI応答から取得し、ここで記録するのが理想)
            actual_cost = estimated_cost 
        except Exception as e:
            self.logger.error(f"[NPE Executor] Task execution failed with model '{model_name}': {e}", exc_info=True)
            log_transaction({**log_data, "status": "error_execution_failed"})
            return ""

        # --- 記録フェーズ ---
        budget_manager.record_cost(project_id, actual_cost)
        log_data["status"] = "success"
        log_data["actual_cost"] = actual_cost
        log_transaction(log_data)
        
        return result
