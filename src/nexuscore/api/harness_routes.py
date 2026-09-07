"""Task 23: ハーネスWeb UI薄い実装（plan Phase 4・ADR-002決定A）

plan雛形からの意図的変更（実契約突合・変更記録方式）:
- 配置はplan雛形の ``webapp/harness_routes.py`` から ``api/harness_routes.py`` へ変更
  （FastAPIアプリの実体は ``api/fastapi_app.py``・ADR-002決定A）
- LLMRouter経路はCLIと同じく不使用・``harness_cli.build_llm`` / ``build_registry`` 再利用（DRY）
- ask承認UIはTTY結合のAskSessionでは表現できないため本実装は ``ask=False``
  （registry=読む系のみ・fail-closed。ask承認UIは将来拡張=run_state ask履歴結線§122と同時期）
- 既定providerはmock（オフライン・安全側。実LLMはフォーム明示指定時のみ）

既知制限: 同期実行（1リクエスト内でループ完走）・長時間タスクはHTTPタイムアウトしうる
（非同期化・ジョブ化はPhase 5強化層スコープ）
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from nexuscore.cli.harness_cli import build_llm, build_registry
from nexuscore.harness.circuit_breaker import CircuitBreaker
from nexuscore.harness.loop import AgentHarness
from nexuscore.harness.run_state import RunStateStore
from nexuscore.harness.tool_gate import ToolGate

router = APIRouter(prefix="/harness")

_PROVIDER_CHOICES = ("openai", "anthropic", "google", "glm", "minimax",
                     "deepseek", "moonshot", "openrouter", "mock")

_FORM_HTML = """<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>NexusCore Harness</title></head>
<body>
<h1>NexusCore Harness</h1>
<form action="/harness/run" method="post">
  <label>Task <input name="task" style="width:60%%"></label>
  <label>provider <select name="provider">{options}</select></label>
  <button>Run</button>
</form>
</body>
</html>"""


def _run_harness(task: str, provider: str) -> str:
    """harnessを同期実行し結果JSON文字列を返す（ask無し=読む系のみ・fail-closed）"""
    llm = build_llm(provider, None)
    gate = ToolGate(policy_path="tool_policy.yaml")
    store = RunStateStore()
    reg = build_registry(ask=False)
    br = CircuitBreaker(provider=provider)
    h = AgentHarness(llm=llm, gate=gate, tool_registry=reg,
                     state_store=store, breaker=br, ask_session=None)
    out = h.run(task)
    return json.dumps(out, ensure_ascii=False, default=str)


@router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    """タスク入力フォーム（provider選択・ask承認は将来拡張）"""
    options = "".join(f'<option value="{p}">{p}</option>' for p in _PROVIDER_CHOICES)
    note = ("ask承認はTTY結合のため本UIでは無効（読む系のみ・fail-closed）"
            "・実承認はCLI --ask で実施")
    return HTMLResponse(_FORM_HTML.format(options=options) + f"<p>{note}</p>")


@router.post("/run")
async def run(task: str = Form(...), provider: str = Form("mock")) -> HTMLResponse:
    """フォームからharnessを同期実行し結果JSONを表示する"""
    if provider not in _PROVIDER_CHOICES:
        return HTMLResponse("unsupported provider", status_code=400)
    return HTMLResponse(f"<pre>{_run_harness(task, provider)}</pre>")
