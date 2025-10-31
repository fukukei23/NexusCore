# npe/budget.py
import time
from collections import defaultdict

class BudgetManager:
    """
    プロジェクトやユーザーごとのAI利用予算を管理する。
    本番ではRedisやDBで永続化することを想定。
    """
    def __init__(self):
        self.budgets = defaultdict(lambda: 10.0)  # デフォルト予算を$10とする
        self.costs = defaultdict(float)

    def check_budget(self, project_id: str, estimated_cost: float) -> bool:
        """予算が十分か確認する"""
        remaining = self.budgets[project_id] - self.costs[project_id]
        print(f"[BudgetManager] Project '{project_id}': Remaining Budget ${remaining:.4f}. Estimated Cost ${estimated_cost:.4f}.")
        if remaining >= estimated_cost:
            return True
        print(f"[BudgetManager] WARN: Budget exceeded for project '{project_id}'.")
        return False

    def record_cost(self, project_id: str, actual_cost: float):
        """実績コストを記録する"""
        self.costs[project_id] += actual_cost
        print(f"[BudgetManager] Recorded cost ${actual_cost:.4f} for project '{project_id}'.")

    def get_remaining_budget(self, project_id: str) -> float:
        """残予算を返す"""
        return self.budgets[project_id] - self.costs[project_id]

# シングルトンインスタンスとして利用
budget_manager = BudgetManager()