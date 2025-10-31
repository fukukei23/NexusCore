# ==============================================================================
# ファイル: src/nexuscore/agents/planner_agent.py
# 版数  : v.fix-P29 + budget-hook
# 概要  : ユーザー要求を「実装計画（JSON）」へ変換
# 変更点:
#   - Step2: 予算フック on_budget_tick を追加し、LLM実行直前に1行呼ぶ
# 依存  : src/nexuscore/agents/base_agent.py
#         src/nexuscore/utils/json_sanitizer.py
# ==============================================================================

from __future__ import annotations
import os
import json
from typing import Any, Dict, Optional, Callable, List

try:
    from .base_agent import BaseAgent
    from ..utils.json_sanitizer import sanitize_json_like
except ImportError:
    # --- フォールバック定義 ---
    # このエージェントを単体でテストする際の依存関係を解決します。
    def sanitize_json_like(x: Any) -> Any:
        try:
            return json.loads(x) if isinstance(x, str) else x
        except Exception:
            return x
    class BaseAgent:
        def __init__(self, *args, **kwargs): print("警告: BaseAgentが見つかりません。（フォールバック）")
        def execute_llm_task(self, prompt: str, as_json: bool = False) -> str:
            return "{}" if as_json else ""
        def _call_llm(self, prompt: str, system_prompt: str, as_json: bool = False) -> str:
             return self.execute_llm_task(prompt, as_json)

class PlannerAgent(BaseAgent):
    SYSTEM_INSTRUCTION = (
        "You are a precise product planner. Return ONLY a valid JSON object. "
        "No explanations. No code fences."
    )

    PLAN_GUIDANCE = """
# 目的
ユーザー要求を、CoderAgent / TesterAgent が参照できる「実装計画(JSON)」に変換してください。

# 出力要件（JSONのみ / コードフェンス禁止）
- ルートは JSON オブジェクト。
- 必須キー: "functions_to_implement"（配列）
- 各要素は次を含む:
  - name: string（スネークケース推奨）
  - description: string
  - args: array of object（{name, type, description, required}）
  - returns: string | object
  - dependencies: string[]（任意）
  - tests: string[]（任意）
  - acceptance_criteria: string[]（任意）
  - priority: "P0"|"P1"|"P2"|"P3"（任意）
- 幻覚禁止。要求・文脈に忠実であること。
"""

    # Orchestrator から注入可能な予算フック
    on_budget_tick: Optional[Callable[[str], None]] = None

    def __init__(self, api_key: str = None, model: str = None, language: str = "ja"):
        # BaseAgentのコンストラクタを呼び出す
        super().__init__(api_key, model)
        self.language = language
        self.debug = os.getenv("PLANNER_DEBUG", "0") == "1"
        self.last_raw_response: Optional[str] = None

    # -------- Public API -------- #
    def create_plan(self, user_requirement: str, context: Optional[Dict[str, Any]] = None) -> str:
        plan = self._run_and_coerce(user_requirement, context)
        return json.dumps(plan, ensure_ascii=False, indent=2)

    def create_plan_dict(self, user_requirement: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self._run_and_coerce(user_requirement, context)

    # -------- Internal -------- #
    def _budget(self, step: str) -> None:
        try:
            if callable(self.on_budget_tick):
                self.on_budget_tick(step)
        except Exception:
            pass

    def _run_and_coerce(self, user_requirement: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        prompt = self._build_prompt(user_requirement, context)
        # Step2: 予算カウント
        self._budget("planner:create_plan")
        raw = self._call_llm(prompt, self.SYSTEM_INSTRUCTION, as_json=True)
        self.last_raw_response = raw

        data = sanitize_json_like(raw)
        if self.debug:
            print("[PlannerAgent] RAW:", raw)

        plan = self._coerce_plan_schema(data)
        if self._is_empty_plan(plan):
            plan = self._fallback_plan(user_requirement, context)
        return plan

    def _build_prompt(self, user_requirement: str, context: Optional[Dict[str, Any]]) -> str:
        ctx_lines: List[str] = []
        if context:
            important = ("persona", "core_features", "constraints", "non_functional", "risk_policy")
            ctx_lines.append("# 追加コンテキスト")
            ctx_lines.append(json.dumps({k: v for k, v in context.items() if k in important}, ensure_ascii=False))
        lang_hint = "日本語で簡潔に" if self.language == "ja" else "Write concise English."
        return (
            f"{self.SYSTEM_INSTRUCTION}\n"
            f"{self.PLAN_GUIDANCE}\n"
            f"# 言語トーン: {lang_hint}\n"
            f"# ユーザー要求\n{user_requirement}\n"
            + ("\n".join(ctx_lines) if ctx_lines else "")
        )

    def _coerce_plan_schema(self, obj: Any) -> Dict[str, Any]:
        plan: Dict[str, Any] = {"functions_to_implement": []}
        if isinstance(obj, dict):
            fti = obj.get("functions_to_implement")
            if isinstance(fti, list):
                plan["functions_to_implement"] = [p for p in (self._coerce_function_spec(x) for x in fti) if p]
        elif isinstance(obj, list):
            plan["functions_to_implement"] = [p for p in (self._coerce_function_spec(x) for x in obj) if p]
        return plan

    def _coerce_function_spec(self, x: Any) -> Optional[Dict[str, Any]]:
        if isinstance(x, str):
            return {
                "name": self._to_snake_case(x)[:64] or "func",
                "description": x,
                "args": [],
                "returns": "None",
                "dependencies": [],
                "tests": [],
                "acceptance_criteria": [],
                "priority": "P1",
            }
        if not isinstance(x, dict):
            return None

        name = self._to_snake_case(str(x.get("name") or "func"))[:64]
        desc = x.get("description") if isinstance(x.get("description"), str) and x.get("description").strip() else "No description provided."

        args_in = x.get("args", [])
        args: list[Dict[str, Any]] = []
        if isinstance(args_in, list):
            for a in args_in:
                if isinstance(a, dict):
                    args.append({
                        "name": str(a.get("name") or "arg"),
                        "type": str(a.get("type") or "Any"),
                        "description": str(a.get("description") or "No description."),
                        "required": bool(a.get("required", True)),
                    })
                elif isinstance(a, str):
                    args.append({"name": self._to_snake_case(a) or "arg", "type": "Any", "description": a, "required": True})

        returns = x.get("returns", "None")
        if not isinstance(returns, (str, dict)):
            returns = "None"

        deps = x.get("dependencies", [])
        if not isinstance(deps, list):
            deps = []
        deps = [str(d) for d in deps if isinstance(d, (str, int))]

        tests = x.get("tests", [])
        if not isinstance(tests, list):
            tests = []
        tests = [str(t) for t in tests if isinstance(t, (str, int))]

        ac = x.get("acceptance_criteria", [])
        if not isinstance(ac, list):
            ac = []
        ac = [str(t) for t in ac if isinstance(t, (str, int))]

        pr = str(x.get("priority") or "P1").upper()
        if pr not in {"P0", "P1", "P2", "P3"}:
            pr = "P1"

        return {
            "name": name,
            "description": desc,
            "args": args,
            "returns": returns,
            "dependencies": deps,
            "tests": tests,
            "acceptance_criteria": ac,
            "priority": pr,
        }

    def _is_empty_plan(self, plan: Dict[str, Any]) -> bool:
        f = plan.get("functions_to_implement")
        return not (isinstance(f, list) and len(f) > 0)

    def _fallback_plan(self, user_requirement: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        name = self._to_snake_case(user_requirement)[:32] or "planned_function"
        return {
            "functions_to_implement": [{
                "name": name,
                "description": f"Auto-generated stub for: {user_requirement[:80]}",
                "args": [],
                "returns": "None",
                "dependencies": [],
                "tests": ["Should run without exceptions.", "Smoke import succeeds."],
                "acceptance_criteria": ["Code compiles and minimal flow executes."],
                "priority": "P2",
            }]
        }

    @staticmethod
    def _to_snake_case(s: str) -> str:
        import re
        s = s.strip()
        s = re.sub(r"[^\w]+", "_", s)
        s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
        s = s.replace("__", "_").strip("_")
        return s.lower()

# 直接実行（スモークテスト）
if __name__ == "__main__":
    import sys
    requirement = " ".join(sys.argv[1:]) or "商品収集と競合分析を自動化し、BUYMAに最適な価格と在庫提案を行う。"
    
    # PlannerAgentのインスタンス化にはAPIキーとモデルが必要になる可能性があるため、
    # 環境変数などから取得する想定でNoneを渡しています。
    # 実際のBaseAgentの実装に合わせて調整してください。
    agent = PlannerAgent(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o", language="ja")
    print(agent.create_plan(requirement))
