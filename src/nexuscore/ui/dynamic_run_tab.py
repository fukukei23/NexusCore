"""CR-NEXUS-054 Phase C: 動的オーケストレーション実行タブ（GLM生成・Fable検証済み）。

ゴール駆動の DynamicRunLoop をUIから起動し、結果と DecisionTrace を表示する。
"""

from __future__ import annotations

import traceback

import gradio as gr

from nexuscore.core.agent_factory import assemble_agent_team
from nexuscore.core.dynamic_orchestrator import DynamicRunLoop
from nexuscore.core.dynamic_router import ActionRegistry
from nexuscore.core.goal_spec import GoalSpec, standard_criteria
from nexuscore.core.llm_assisted_router import LLMAssistedRouter
from nexuscore.core.orchestrator import Orchestrator


def build_dynamic_run_tab() -> None:
    """「Dynamic Run」タブのコンポーネントを構築する。

    gr.Tab は呼び出し側（unified_gradio_ui）が開くため、ここでは作らない。
    """
    gr.Markdown(
        "ゴール駆動の動的オーケストレーション（CR-NEXUS-054）。"
        "達成条件を満たすまで、必要なフェーズだけをその場で選んで実行します。"
        "全ルーティング判断は理由付きでトレースに記録されます。"
    )

    requirement = gr.Textbox(lines=3, label="要件", placeholder="例: フィボナッチ数列を計算する関数を作成して")
    project_path = gr.Textbox(label="プロジェクトパス", placeholder="/tmp/demo")  # nosec B108 — UI入力例（実パス操作なし）
    max_actions = gr.Slider(minimum=1, maximum=30, value=12, step=1, label="最大アクション数（暴走防止予算）")

    with gr.Row():
        skip_architecture = gr.Checkbox(value=True, label="Architectureフェーズをスキップ")
        use_llm_routing = gr.Checkbox(value=False, label="LLM支援ルーティングを使う")

    run_btn = gr.Button("動的実行", variant="primary")

    result_md = gr.Markdown()
    trace_code = gr.Code(label="Decision Trace（ルーティング判断の記録）")

    def run_dynamic(
        requirement: str,
        project_path: str,
        max_actions: float,
        skip_architecture: bool,
        use_llm_routing: bool,
    ) -> tuple[str, str]:
        """UI入力から動的実行ループを起動し、(結果メッセージ, トレース) を返す。"""
        if not requirement or not project_path:
            return "⚠️ 要件とプロジェクトパスを入力してください", ""

        try:
            team = assemble_agent_team(project_path)
            llm_router = team["llm_router"]

            orchestrator = Orchestrator(
                project_path=project_path,
                constitution={"description": "dynamic run via UI"},
                **team,
            )

            skip = frozenset({"architecture"}) if skip_architecture else frozenset()
            goal = GoalSpec(
                description=requirement,
                criteria=standard_criteria(),
                max_actions=int(max_actions),
                skip_actions=skip,
            )

            router = None
            if use_llm_routing:
                registry = ActionRegistry.from_orchestrator(orchestrator)
                router = LLMAssistedRouter.from_llm_router(
                    llm_router=llm_router,
                    registry=registry,
                    goal_description=requirement,
                    skip_actions=skip,
                )

            loop = DynamicRunLoop(orchestrator=orchestrator, goal=goal, router=router)
            result = loop.run(requirement)

            status = "✅ 成功" if result.success else "❌ 失敗"
            result_msg = f"{status}: {result.message}（{result.actions_executed}アクション）"
            return result_msg, result.trace.summary()

        except Exception as e:  # noqa: BLE001 — UIにはエラー全文を表示して止めない
            return f"❌ エラー: {e}", traceback.format_exc()

    run_btn.click(
        fn=run_dynamic,
        inputs=[requirement, project_path, max_actions, skip_architecture, use_llm_routing],
        outputs=[result_md, trace_code],
    )
