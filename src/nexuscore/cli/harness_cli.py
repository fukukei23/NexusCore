"""spec §6 Phase 1: CLI版デモシナリオ（Task 15）

実行例: ``python -m nexuscore.cli.harness_cli "<task>" --provider openai``

plan雛形からの意図的変更（実契約突合の結果・Task 14と同様の変更記録方式）:
- 雛形の ``LLMRouter().get_llm_for_task()`` 設計は破棄。理由: RoutedLLMは
  complete_with_tools 未実装（_routed_llm.py:34-107・execute()のみ）で
  harness契約不適合。代わりに create_provider() 経由で ToolCallingMixin
  済みプロバイダを直接生成する。RoutedLLMのtool対応はスコープ外・別途起票。
- --provider mock で LocalToolCallDummyLLM を選択可能（オフライン動作確認用）
- テスト注入のため main(argv, llm_factory)・--state-path・--model を追加

3機MLR採用分（2026-09-05・review_log参照）:
- CLIは毎回新規run（既存stateのresume読込はTask 16チェックポイントで対応予定）
- policy不在（gate fail-closed全拒否）時、tool要求を続けるLLMならlimits abortで
  終了する＝正しいfail-closed挙動・content即答LLMなら完走する
- 予期せぬ例外はJSON（abort_reason=cli_error）+exit 1で返す（トレースバック不是・
  SystemExitはargparse同型の意図的経路として透過）
- abort時は理由をstderrへ1行出力（exitコードは1に統一・spec §6「非ゼロ」どおり）
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nexuscore.harness.ask import AskSession
from nexuscore.harness.circuit_breaker import CircuitBreaker
from nexuscore.harness.loop import AgentHarness
from nexuscore.harness.mock_provider import LocalToolCallDummyLLM
from nexuscore.harness.run_state import RunStateStore
from nexuscore.harness.tool_gate import ToolGate
from nexuscore.harness.tools import list_dir, read_file, search_text
from nexuscore.harness.tools.exec import run_command
from nexuscore.harness.tools.write import edit_file, write_file

# 実在確認済みモデルのみ（2026-09-05 Task 16実測: gpt-5.1-instantは404・アカウントに無し。
# gpt-5.1は/v1/models一覧で実在確認・deepseek-chatはチェックポイント実行で実測）
DEFAULT_MODELS: dict[str, str] = {"openai": "openai:gpt-5.1",
                                  "deepseek": "deepseek:deepseek-chat"}
TOOL_CAPABLE = ("openai", "anthropic", "google", "glm", "minimax",
                "deepseek", "moonshot", "openrouter", "mock")


def build_llm(provider: str, model: str | None) -> Any:
    """provider名から complete_with_tools を持つLLM実体を構築する（mockはオフライン）"""
    if provider == "mock":
        return LocalToolCallDummyLLM()
    name = model or DEFAULT_MODELS.get(provider)
    if not name:
        raise SystemExit(f"unsupported provider: {provider} (--model で指定可)")
    from nexuscore.llm.provider_factory import create_provider
    return create_provider(name)


def build_registry(ask: bool) -> dict[str, Any]:
    """Task 21: CLIのtool registry構築を抽出（テスト可能化）

    --ask=True 時は書く系（write_file/edit_file）と撃つ系（run_command・
    policy既定 default: ask のためAskSessionありの文脈でのみ登録）を追加。
    --ask=False 時は読む系のみ（fail-closed維持・exec/writeは登録しない）。
    """
    reg = {"read_file": read_file, "list_dir": list_dir,
           "search_text": search_text}
    if ask:
        reg["write_file"] = write_file
        reg["edit_file"] = edit_file
        reg["run_command"] = run_command
    return reg


def main(argv: list[str] | None = None,
         llm_factory: Callable[[str, str | None], Any] | None = None) -> int:
    """CLI入口。JSON 1行を出力し abort_reason なし=0 / あり=1 を返す"""
    p = argparse.ArgumentParser(prog="nexuscore-harness")
    p.add_argument("task", nargs="+")
    p.add_argument("--provider", default="openai", choices=TOOL_CAPABLE,
                   help="mock=オフラインダミー(APIキー不要)・openai以外は--model必須")
    p.add_argument("--model", default=None, help='実プロバイダ時は"vendor:model"形式')
    p.add_argument("--policy", default="tool_policy.yaml")
    p.add_argument("--state-path", default=None)
    p.add_argument("--ask", action="store_true",
                   help="書く系道具の対話確認を有効化（TTY必須・非TTYはdenyに倒る）")
    args = p.parse_args(argv)
    try:
        llm = (llm_factory or build_llm)(args.provider, args.model)
        gate = ToolGate(policy_path=Path(args.policy))
        store = (RunStateStore(path=Path(args.state_path)) if args.state_path
                 else RunStateStore())
        reg = build_registry(ask=args.ask)
        ask_session = (AskSession(store=store) if args.ask else None)
        br = CircuitBreaker(provider=args.provider)
        h = AgentHarness(llm=llm, gate=gate, tool_registry=reg,
                         state_store=store, breaker=br, ask_session=ask_session)
        ctx = (f"作業ディレクトリ: {os.getcwd()}\n"
               "相対パスはこのディレクトリ基準です。/workspace などは存在しません。\n"
               "cdで移動せず、引数に絶対パスを渡してください。")
        out = h.run(" ".join(args.task), system_prompt=ctx)
    except Exception as exc:  # noqa: BLE001 CLI観測可能性: JSONで異常を返す
        out = {"abort_reason": "cli_error", "error": str(exc)}
    reason = out.get("abort_reason")
    if reason:
        print(f"aborted: {reason}", file=sys.stderr)
    print(json.dumps(out, ensure_ascii=False, default=str))
    return 0 if reason is None else 1


if __name__ == "__main__":
    sys.exit(main())
