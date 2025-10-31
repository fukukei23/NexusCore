# npe/engine.py

# あなたの優れたルーティングロジックをNPEに統合する
from .llms import get_llm_client, get_model_cost # llms.pyを改修
from .policies import context_scanner, secure_context_builder
from .logger import log_transaction
from .budget import budget_manager

class NexusProtocolEngine:
    def __init__(self):
        print("Nexus Protocol Engine (v2) with Economic Governance is running.")

    def process_task(self, prompt: str, metadata: dict, project_id="proj-001"):
        log_data = {"project_id": project_id, "task_metadata": metadata}

        # --- ガバナンス・フェーズ ---
        # 1. セキュリティスキャン (既存のNPE機能)
        context_type = context_scanner(prompt)
        log_data["context_type"] = context_type
        if context_type == "sensitive":
            print("[NPE Security] Sensitive data detected. Applying security protocols.")
            prompt = secure_context_builder(prompt) # マスキング
            log_data["is_masked"] = True

        # 2. ルーティング判断 (あなたのLLMRouterのロジックをここに統合)
        route_decision = self._analyze_task_for_npe(prompt, metadata, context_type)
        log_data["initial_route_decision"] = route_decision
        
        # 3. 経済性チェック (新機能)
        estimated_cost = get_model_cost(route_decision, prompt)
        log_data["estimated_cost"] = estimated_cost

        if not budget_manager.check_budget(project_id, estimated_cost):
            # 予算オーバーの場合、より安価なモデルにフォールバックする
            print(f"[NPE Economic] Budget insufficient. Attempting to reroute to a cheaper model.")
            original_decision = route_decision
            route_decision = self._fallback_to_cheaper_model(original_decision)
            log_data["rerouted_to"] = route_decision
            # 再度コストをチェック
            estimated_cost = get_model_cost(route_decision, prompt)
            if not budget_manager.check_budget(project_id, estimated_cost):
                print("[NPE Economic] ERROR: No cheaper model available within budget. Task aborted.")
                log_transaction({**log_data, "status": "aborted_budget_exceeded"})
                return "Error: Task aborted due to budget limits."
        
        log_data["final_route_decision"] = route_decision

        # --- 実行フェーズ ---
        print(f"[NPE Executor] Executing task with '{route_decision}'.")
        client = get_llm_client(route_decision)
        # result, actual_cost = client.generate(...) # 応答と実際のコストを取得
        
        # --- ここではダミーの結果とコストを返す ---
        result = f"Response from {route_decision}."
        actual_cost = estimated_cost * 1.05 # 若干の誤差をシミュレート
        
        # --- 記録フェーズ ---
        budget_manager.record_cost(project_id, actual_cost)
        log_data["status"] = "success"
        log_data["actual_cost"] = actual_cost
        log_transaction(log_data)
        
        return result

    def _analyze_task_for_npe(self, prompt: str, metadata: dict, context_type: str) -> str:
        """あなたのルーターロジックをNPE用に拡張・統合"""
        # セキュリティポリシーを最優先
        if context_type == "sensitive":
            # 機密情報が含まれている場合は、たとえどんなタスクでもローカルLLM（を想定した安価なモデル）に強制ルーティング
            return "anthropic_haiku" # 最も安価なモデルをローカルLLMの代理とする

        if metadata and metadata.get("task_type") == "code_generation":
            return "openai_gpt4o"
        
        if "要約してください" in prompt or "summarize" in prompt.lower():
            return "anthropic_sonnet"

        if len(prompt) > 10000:
            return "anthropic_claude3_opus"

        return "openai_gpt4o" # デフォルト

    def _fallback_to_cheaper_model(self, current_model: str) -> str:
        """より安価なモデルへのフォールバックロジック"""
        fallback_map = {
            "openai_gpt4o": "anthropic_sonnet",
            "anthropic_claude3_opus": "anthropic_sonnet",
            "anthropic_sonnet": "anthropic_haiku",
            "anthropic_haiku": "anthropic_haiku" # これ以上安いものはない
        }
        fallback_model = fallback_map.get(current_model, "anthropic_haiku")
        print(f"[NPE Economic] Fallback from '{current_model}' to '{fallback_model}'.")
        return fallback_model