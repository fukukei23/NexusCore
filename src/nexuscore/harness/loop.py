"""Task 14: 最小ループ AgentHarness（spec §5 + round7修正条項3件）

round7修正条項（plan 1949-1951行）を反映:
- **loop↔breaker連携順序固定**: (1)LLM呼出前にallow_request()チェック→OPENなら
  state書込+graceful exit (2)429検出→record_failure(is_429=True) (3)OPEN遷移→
  state.save()→raiseの順序固定 (4)tokens/wall=90%でstate.save+graceful exit
  （warn80%はログのみ・90%でabort）(5)SIGINTでstate.save+graceful return
- **deny時tool_result形式**: {"role":"tool","tool_call_id":tc.id,"content":"denied: "+reason}
- **exec呼出前budget確認**: wall/tool残りを道具実行前に累計チェック・超過見込みなら
  ToolResult(status="would_exceed_limit") を返し実行せず（Phase 3のexecでも同経路）

起票2件（バックログ・Task 14実装時必須）の実装:
- **probe成功記録の結線**: LLM呼出直前にallow_probe()を記録し、成功なら
  record_probe_success()・失敗ならrecord_probe_failure()を呼ぶ
  （HALF_OPEN→CLOSED復帰はtest_probe_recovery_half_open_to_closedで結合検証）
- **deny_paths供給経路C案（registry束縛）**: 初期化時にpolicyのdeny_pathsを
  deny_paths引数を持つ道具へ束縛（ToolGate.deny_paths_for経由・policyが唯一の
  情報源・LLM引数のdeny_pathsは破棄）。ループ本体と道具は束縛機構を除き無改変。

plan雛形からの変更点（実装時判断）:
- 雛形の ``gate.evaluate(tool=tc.name, args=...)`` は Task 10 改名前の引数名 →
  ``tool_args=`` に修正（commit 000d58f6）
- 雛形のdeny時 ``record_failure(is_429=False)`` は削除。denyはpolicy判定であって
  provider障害でなく、spec §5はブレーカトリガを「60秒窓内429×3・タイムアウト連続」
  と規定する（3回denyでブレーカOPEN→LLM呼出不能は意図しない暴走止め）
- 雛形は1ステップで先頭tool_callのみ処理してbreak → **全tool_calls処理**に修正
  （OpenAI契約: 全tool_callに対応するtool resultを返す前に次requestは400になる）
- token比較は直前応答のみ → **run通算の累計**に修正
- tool result連結の前にassistantメッセージ(tool_calls付き)を連結
  （OpenAI契約: tool resultには直前のassistant tool_callsメッセージが必要）
- state.save()がPartialFailureならresume契約が維持できないため abort_reason=
  "state_save_failed" でabort（Task 12 round7「loopがabort判断」の履行）

3機MLR採用修正（2026-09-05・42指摘中採用11件・却下12種はふくけい承認済み）:
- SIGINT時に現在のstepで保存（雛形は0固定で進捗が失われる）
- 道具完了後の保存はin_flight=None（「実行中」でないため。in_flightは将来の
  ステップ内中断保存用・Phase 2）
- ブレーカ記録はprovider系例外（requests.RequestException / status_code属性）のみ・
  プログラミングエラーは記録せずraise（spec §5トリガ=「429×3・タイムアウト連続」）
- tool_calls_usedは実行試行（error含む）で加算（成功時のみだとerror反復でbudget回避可）
- _bind_deny_pathsにfunctools.wraps・切詰めtool_resultに[truncated]マーカー
- probe結線の契約: 本クラスは単一ループ・直列実行前提（複数run()の並行実行で
  breakerを共有する構成はPhase 1では想定外）
"""
from __future__ import annotations

import functools
import inspect
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import requests

from nexuscore.harness.circuit_breaker import CircuitBreaker, State
from nexuscore.harness.run_state import RunState, RunStateStore, SaveResult
from nexuscore.harness.tool_gate import Mode, ToolGate
from nexuscore.harness.tools import ToolResult

log = logging.getLogger(__name__)

MAX_TOOL_RESULT_CHARS = 10_000  # plan雛形どおり・LLMコンテキスト保護


@dataclass
class Limits:
    """4ハードリミット+段階的反応（spec §10）

    - max_steps / max_tool_calls: 到達で即abort・即would_exceed_limit
    - max_wall_seconds / max_tokens: 80%でログ警告（継続）・90%でabort
    """

    max_steps: int = 25
    max_wall_seconds: float = 600.0
    max_tool_calls: int = 40
    max_tokens: int = 500_000
    warn_at_fraction: float = 0.8  # 80%でログ警告（round7: ログのみ）
    abort_at_fraction: float = 0.9  # 90%でabort（round7(4)）


class AgentHarness:
    """tool callingループ+ToolGate/ブレーキャ/RunState統合（Phase 1 MVP）

    Args:
        llm: complete_with_tools(messages, tools) を持つプロバイダ（Task 5-9契約）
        gate: ToolGate（fail-closed・道具1回ごと個別判定）
        tool_registry: {tool名: 呼出可能}。deny_paths引数を持つ道具には
            初期化時にpolicy値を束縛する（C案）
        state_store: RunStateStore（原子的保存・quarantine）
        breaker: CircuitBreaker（プロバイダ単位）
        limits: Limits（既定値あり）
    """

    def __init__(
        self,
        *,
        llm: Any,
        gate: ToolGate,
        tool_registry: dict[str, Callable],
        state_store: RunStateStore,
        breaker: CircuitBreaker,
        limits: Limits | None = None,
    ) -> None:
        self.llm = llm
        self.gate = gate
        # C案: policyが唯一の情報源。deny_paths引数を持つ道具だけ束縛対象
        # （read_file等の非対応道具に渡すとTypeErrorになるためsignature検査）
        self.tools: dict[str, Callable] = {}
        for name, fn in tool_registry.items():
            if "deny_paths" in inspect.signature(fn).parameters:
                self.tools[name] = self._bind_deny_paths(fn, gate.deny_paths_for(name))
            else:
                self.tools[name] = fn
        self.state = state_store
        self.breaker = breaker
        self.limits = limits or Limits()

    @staticmethod
    def _bind_deny_paths(fn: Callable, deny_paths: list[str]) -> Callable:
        """道具へpolicyのdeny_pathsを束縛する（LLM引数のdeny_pathsは破棄）

        呼出契約は常に ``fn(**tc.args)``（keyword引数のみ）のため bound への
        位置引数渡しは発生しない（*argsは防御目的・MLR却下O1の根拠）。
        """

        @functools.wraps(fn)
        def bound(*args: Any, _fn: Callable = fn, _deny: list[str] = deny_paths,
                  **kwargs: Any) -> Any:
            kwargs.pop("deny_paths", None)  # LLM引数では上書きさせない
            return _fn(*args, deny_paths=_deny, **kwargs)

        return bound

    def run(self, task: str, messages: list[dict] | None = None) -> dict:
        """タスクを実行し、完了応答またはabort理由付きdictを返す

        LLM例外（429含む）はブレーキャ記録後にre-raiseする（リトライはprovider層・
        Task 5-7 urllib3 Retryの管轄。本ループは握りつぶさない）。
        """
        msgs = list(messages) if messages else [{"role": "user", "content": task}]
        tools = self._tool_defs()
        started = time.monotonic()
        total_tokens = 0
        tool_calls_used = 0
        warned = {"steps": False, "wall": False, "tokens": False}
        try:
            current_step = 0
            for step in range(self.limits.max_steps):
                current_step = step
                # round7(1): LLM呼出前に許可チェック→OPENなら呼出せずgraceful exit
                if not self.breaker.allow_request():
                    return self._graceful("breaker_open", step, total_tokens)
                # 起票①probe結線: HALF_OPEN中の呼出はprobeとして扱う
                # （契約: 単一ループ・直列実行前提。並行run()でのbreaker共有は想定外）
                is_probe = self.breaker.allow_probe()
                try:
                    out = self.llm.complete_with_tools(messages=msgs, tools=tools)
                except Exception as exc:
                    if is_probe:
                        self.breaker.record_probe_failure()
                    elif _is_provider_error(exc):
                        self.breaker.record_failure(is_429=_is_429(exc))
                    else:
                        # プログラミングエラー等はブレーキャ記録対象外
                        # （spec §5トリガ=「429×3・タイムアウト連続」・MLR採用）
                        log.warning("non-provider error (%s): not recorded to breaker",
                                    type(exc).__name__)
                    # round7(3): OPEN遷移→state.save()→raiseの順序固定
                    # （_gracefulの呼び出しはsave目的・戻り値は破棄してraiseするのが
                    #  round7(3)の契約）
                    if self.breaker.state == State.OPEN:
                        self._graceful("breaker_open", step, total_tokens)
                    raise
                if is_probe:
                    self.breaker.record_probe_success()
                tokens = (out.get("usage") or {}).get("total_tokens", 0)
                total_tokens += tokens
                # round7(4): 90%でabort（warnはログのみ・後段）
                if self._over_abort(started, total_tokens):
                    return self._graceful("limits", step, total_tokens)
                tool_calls = out.get("tool_calls") or []
                if not tool_calls:
                    return self._graceful(None, step + 1, total_tokens,
                                          content=out.get("content"))
                self._warn(started, total_tokens, step, warned)
                # tool resultの前にassistantメッセージを連結（OpenAI契約）
                msgs.append({
                    "role": "assistant",
                    "content": out.get("content") or "",
                    "tool_calls": [tc.to_openai() for tc in tool_calls],
                })
                for tc in tool_calls:
                    # round7③: 道具実行前のbudget確認・超過見込みは実行せず通知
                    if (tool_calls_used >= self.limits.max_tool_calls
                            or self._over_abort(started, total_tokens)):
                        msgs.append(self._tool_result(tc, ToolResult(
                            status="would_exceed_limit")))
                        continue
                    d = self.gate.evaluate(tool=tc.name, tool_args=tc.args,
                                           ask_supported=False)
                    # 判定順序の根拠: gate denyを先に見る（policy不在toolはここで
                    # 拒否）。「unknown tool」経路はpolicy=allowかつregistry未登録の
                    # 不整合時のみ到達する（MLR採用: 順序根拠の明記）
                    if d.mode == Mode.DENY:
                        # round7②: denyはpolicy判定・ブレーキャには記録しない
                        msgs.append(self._tool_result(
                            tc, f"denied: {d.reason}"))
                        continue
                    fn = self.tools.get(tc.name)
                    if fn is None:
                        msgs.append(self._tool_result(
                            tc, f"error: unknown tool {tc.name!r}"))
                        continue
                    tool_calls_used += 1  # 実行試行で加算（error反復でのbudget回避防止）
                    try:
                        result = fn(**tc.args)
                    except Exception as exc:  # noqa: BLE001 道具障害はLLMへ通知
                        msgs.append(self._tool_result(tc, f"error: {exc}"))
                        continue
                    msgs.append(self._tool_result(tc, result))
                # 1ステップ分の道具処理完了をスナップショット保存
                # （完了後なのでin_flight=None・in_flightは将来のステップ内中断保存用）
                if self._save_state(step + 1, total_tokens) is False:
                    return self._graceful("state_save_failed", step + 1,
                                          total_tokens)
            # for-else相当: max_steps消費
            return self._graceful("limits", self.limits.max_steps, total_tokens)
        except KeyboardInterrupt:
            # round7(5): SIGINT→state.save→graceful return（現在のstepで保存）
            return self._graceful("sigint", current_step, total_tokens)

    def _graceful(self, reason: str | None, step: int, tokens: int,
                  content: str | None = None) -> dict:
        """state保存してから応答を返す（save失敗はstate_save_failedへ切替）"""
        saved = self._save_state(step, tokens, abort_reason=reason)
        if saved is False:
            return self._finish("state_save_failed", step, tokens)
        return self._finish(reason, step, tokens, content=content)

    def _finish(self, reason: str | None, step: int, tokens: int,
                content: str | None = None) -> dict:
        out: dict[str, Any] = {
            "content": content,
            "loop_steps": step,
            "tokens_used": tokens,
            "abort_reason": reason,
        }
        out.update(self.breaker.export_state())
        return out

    def _save_state(self, step: int, tokens: int, abort_reason: str | None = None,
                    in_flight: str | None = None) -> bool:
        """RunState保存（PartialFailure=False・Success=True）"""
        snapshot = self.breaker.export_state()
        state = RunState(
            loop_steps=step,
            tokens_used=tokens,
            in_flight_tool=in_flight,
            abort_reason=abort_reason,
            **snapshot,
        )
        return self.state.save(state) == SaveResult.SUCCESS

    def _over_abort(self, started: float, tokens: int) -> bool:
        """round7(4): wall/tokenが90%到達でTrue"""
        elapsed = time.monotonic() - started
        return (elapsed >= self.limits.max_wall_seconds * self.limits.abort_at_fraction
                or tokens >= self.limits.max_tokens * self.limits.abort_at_fraction)

    def _warn(self, started: float, tokens: int, step: int,
              warned: dict[str, bool]) -> None:
        """round7(4): 80%到達で1回だけログ警告（継続）"""
        frac = self.limits.warn_at_fraction
        if (not warned["wall"]
                and time.monotonic() - started >= self.limits.max_wall_seconds * frac):
            warned["wall"] = True
            log.warning("wall budget at %d%%", int(frac * 100))
        if (not warned["tokens"]
                and tokens >= self.limits.max_tokens * frac):
            warned["tokens"] = True
            log.warning("token budget at %d%%", int(frac * 100))
        if (not warned["steps"] and step >= self.limits.max_steps * frac):
            warned["steps"] = True
            log.warning("step budget at %d%%", int(frac * 100))

    @staticmethod
    def _tool_result(tc: Any, result: Any) -> dict:
        """tool resultメッセージを組む（ToolResultはstr化・内容は上限切詰め+

        切詰め時は[truncated]マーカーを付けてLLMに続きがあることを通知（MLR採用）
        """
        content = str(result)
        if len(content) > MAX_TOOL_RESULT_CHARS:
            content = (content[:MAX_TOOL_RESULT_CHARS]
                       + f"\n[truncated from {len(content)} chars]")
        return {"role": "tool", "tool_call_id": tc.id, "content": content}

    def _tool_defs(self) -> list[dict]:
        return [{"type": "function",
                 "function": {"name": n, "parameters": {"type": "object",
                                                        "properties": {}}}}
                for n in self.tools]


def _is_429(exc: BaseException) -> bool:
    """例外から429を検出する（requests.HTTPError互換のresponse.status_code・
    直接のstatus_code属性の両方に対応）"""
    code = getattr(getattr(exc, "response", None), "status_code", None)
    if code is None:
        code = getattr(exc, "status_code", None)
    return code == 429


def _is_provider_error(exc: BaseException) -> bool:
    """provider/ネットワーク系例外かを判定する（MLR採用: ブレーカ記録対象の限定）

    requests.RequestException（HTTPError/Timeout/ConnectionError/RetryError含む）
    またはstatus_code属性を持つ例外をprovider系とみなす。プログラミングエラー
    （TypeError等）はspec §5トリガ外のため記録しない。
    """
    return isinstance(exc, requests.RequestException) or hasattr(exc, "status_code")
