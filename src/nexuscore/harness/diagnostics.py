"""Phase 0 計測CLI（過去事故の再発防止・設計spec §3 fail-fast条項の実測項目）

plan記載コードからの修正点（実装時判断・詳細はcommitメッセージ）:
- argparseのサブパーサー二重登録バグを修正
- mro/override_check の --out を尊重（planテストが--outを検証するため）
- override_check は自クラス定義のみ対象（inspect.getmembersは継承分まで
  拾い「常に撤退」と誤判定するため・CRITERIA.mdの定義に合わせた）
- retry_diff は共通HTTP層(http_client)のRetry実装も併記
  （providerクラス名のみ検査すると共有層カバーを見落とし誤判定するため）
- tool_echo は実HTTP呼出を試行し結果をありのまま記録（ok捏造禁止）
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib
import inspect
import json
import re
import sys
import time
from pathlib import Path

# ToolCallingMixin が追加予定のメソッド名（override_checkの判定対象）
MIXIN_METHODS = (
    "complete_with_tools",
    "_adapt_request_openai_to_native",
    "_adapt_response_native_to_internal",
    "_call_http_tool",
)
# 参考: 既存プロバイダが定義済みの主力メソッド（情報として併記）
WATCH_METHODS = ("complete", "execute", "_build_real_call")

PROVIDER_CLASSES = {
    "openai": "nexuscore.llm.providers.openai_provider.OpenAILLM",
    "glm": "nexuscore.llm.providers.glm_provider.GLMLLM",
    "minimax": "nexuscore.llm.providers.minimax_provider.MiniMaxLLM",
    "openrouter": "nexuscore.llm.providers.openrouter_provider.OpenRouterLLM",
    "deepseek": "nexuscore.llm.providers.deepseek_provider.DeepSeekLLM",
    "moonshot": "nexuscore.llm.providers.moonshot_provider.MoonshotLLM",
    "anthropic": "nexuscore.llm.providers.anthropic_provider.AnthropicLLM",
    "gemini": "nexuscore.llm.providers.gemini_provider.GeminiLLM",
}
# echo往復に使うモデル名（llm_profiles.py実測値・APIエラー時は出力に生じるため再試行可能）
ECHO_MODELS = {
    "openai": "gpt-5-mini",
    "glm": "glm-5.2",
    "minimax": "MiniMax-M3",
    "openrouter": "openai/gpt-4.1",
    "deepseek": "deepseek-chat",
    "moonshot": "moonshot-v1-8k",
}


def _out_root() -> Path:
    """計測結果の出力ルート（コマンド実行ごとにタイムスタンプディレクトリ）"""
    root = Path("artifacts/phase0") / time.strftime("%Y-%m-%dT%H-%M-%S")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _import(qualified: str):
    """FQCN文字列からクラスを動的importする"""
    mod, _, cls = qualified.rpartition(".")
    return getattr(importlib.import_module(mod), cls)


def cmd_mro(args: argparse.Namespace) -> int:
    """4クラスのMRO（継承順）を出力。Mixin追加による上書き要否の判定材料"""
    cls = _import(args.class_name)
    lines = [
        f"{i:2d} {c.__module__}.{c.__name__}"
        for i, c in enumerate(cls.__mro__)
    ]
    body = "\n".join(lines)
    out = Path(args.out) if args.out else _out_root() / "mro.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(out)
    return 0


def cmd_override_check(args: argparse.Namespace) -> int:
    """Mixin追加予定メソッドとprovider自クラス定義の衝突有無を検査

    CRITERIA.md定義: 「上書き」= 子クラスでのインスタンスメソッド新規定義のみ。
    継承により得たメソッド（BaseLLM.execute等）は対象外。
    """
    cls = _import(args.class_name)
    own_funcs = {
        n for n, v in vars(cls).items() if inspect.isfunction(v)
    }
    mixin_overlap = sorted(own_funcs & set(MIXIN_METHODS))
    watch_defined = sorted(own_funcs & set(WATCH_METHODS))
    sections = [
        f"class: {cls.__module__}.{cls.__name__}",
        f"mixin_overlap: {mixin_overlap if mixin_overlap else '[]'}",
        f"watch_defined(参考・既存主力メソッドの自クラス定義): "
        f"{watch_defined if watch_defined else '[]'}",
    ]
    if mixin_overlap:
        sections.append(
            f"判定: 撤退候補 — Mixin予定メソッドと衝突: {mixin_overlap}"
        )
    else:
        sections.append("判定: (なし=上書き不要)")
    body = "\n".join(sections)
    out = Path(args.out) if args.out else _out_root() / "override_check.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(out)
    return 0


def cmd_factory_pos(args: argparse.Namespace) -> int:
    """HTTP_CLIENT_FACTORY の呼出位置を記録（providers/__init__等の生成経路）"""
    hits: list[str] = []
    for p in sorted(Path(args.src_root).rglob("*.py")):
        txt = p.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"HTTP_CLIENT_FACTORY\.[a-z_]+", txt):
            line_no = txt[: m.start()].count("\n") + 1
            hits.append(f"{p}:{line_no}: {m.group()}")
    body = "\n".join(hits) if hits else "(呼出なし)"
    out = _out_root() / "factory_pos.txt"
    out.write_text(body, encoding="utf-8")
    print(out)
    print(f"hits={len(hits)}")
    return 0


def cmd_retry_diff(args: argparse.Namespace) -> int:
    """リトライ実装の差分（provider毎 + 共通HTTP層）をJSONで出力"""
    targets = {k: v for k, v in PROVIDER_CLASSES.items()
               if k in ("openai", "glm", "minimax", "openrouter",
                        "deepseek", "moonshot")}
    # openai_compat系は OpenAICompatLLM を共有するため代表1件に圧縮
    targets["openai_compat(共有基底)"] = (
        "nexuscore.llm.providers.openai_compat.OpenAICompatLLM"
    )
    targets["anthropic"] = PROVIDER_CLASSES["anthropic"]
    targets["gemini"] = PROVIDER_CLASSES["gemini"]

    shared_src = ""
    http_client = Path("src/nexuscore/llm/http_client.py")
    if http_client.exists():
        shared_src = http_client.read_text(encoding="utf-8")

    shared_layer = {
        "has_backoff": "backoff_factor" in shared_src,
        "has_max_retries": "Retry(" in shared_src,
        "has_status_forcelist_429": "429" in shared_src,
        "explicit_retry_after_parsing": "Retry-After" in shared_src,
        "note": (
            "urllib3 Retry はデフォルトで Retry-After ヘッダを尊重する"
            "（respect_retry_after_headers 既定True）"
        ),
    }

    report: dict[str, dict] = {}
    for name, fqcn in targets.items():
        cls = _import(fqcn)
        names = dir(cls)
        provider_own = {
            "has_backoff": any("backoff" in n.lower() for n in names),
            "has_retry_after": any("retry_after" in n.lower() for n in names),
            "has_max_retries": any(
                "max_retries" in n.lower() or "max_retry" in n.lower()
                for n in names
            ),
        }
        # 実効値 = provider自前 or 共有層カバー（backoff/max_retriesは共有層で担保）
        effective = {
            "has_backoff": provider_own["has_backoff"]
            or shared_layer["has_backoff"],
            "has_retry_after": provider_own["has_retry_after"]
            or shared_layer["explicit_retry_after_parsing"]
            or shared_layer["has_status_forcelist_429"],
            "has_max_retries": provider_own["has_max_retries"]
            or shared_layer["has_max_retries"],
        }
        report[name] = {
            "provider_own": provider_own,
            "effective_with_shared_layer": effective,
        }
    report["_shared_layer"] = shared_layer
    report["_measured_at"] = dt.datetime.now().isoformat(timespec="seconds")

    out = _out_root() / "retry_diff.json"
    out.write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(out)
    # 実効値ですべて欠落するプロバイダが3種以上なら撤退基準該当
    diff_count = sum(
        1 for k, r in report.items()
        if not k.startswith("_") and not all(
            r["effective_with_shared_layer"].values()
        )
    )
    print(f"effective_lacking_providers={diff_count}")
    if diff_count >= 3:
        print(
            f"⚠️ 撤退基準該当: 実効リトライ欠落 {diff_count}種",
            file=sys.stderr,
        )
        return 2
    return 0


def cmd_tool_echo(args: argparse.Namespace) -> int:
    """OpenAI互換系のtools受付とecho往復を実測（要実API・1回ずつ）

    実HTTP呼出を試行し、結果（成功/エラー/スキップ）をありのまま記録する。
    okを捏造しない（planのスケルトンは常時ok:trueを書くため修正）。
    """
    entry = {"provider": args.provider, "ts": dt.datetime.now().isoformat()}
    fqcn = PROVIDER_CLASSES.get(args.provider)
    if not fqcn:
        entry["skipped"] = f"unknown provider: {args.provider}"
    else:
        cls = _import(fqcn)
        llm = cls(model_name=ECHO_MODELS.get(args.provider, "test-model"))
        entry["model"] = getattr(llm, "model_name", None)
        entry["real_calls"] = getattr(llm, "real_calls", False)
        if not getattr(llm, "real_calls", False):
            entry["skipped"] = "stub mode (no API key or dry-run)"
        else:
            payload = {
                "model": llm.model_name,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Call the echo tool with text='phase0'. "
                            "Use the tool, do not answer in text."
                        ),
                    }
                ],
                "tools": [{
                    "type": "function",
                    "function": {
                        "name": "echo",
                        "description": "Echo the given text back.",
                        "parameters": {
                            "type": "object",
                            "properties": {"text": {"type": "string"}},
                            "required": ["text"],
                        },
                    },
                }],
                "tool_choice": "auto",
            }
            api_path = getattr(llm, "api_path", "/v1/chat/completions")
            url = f"{llm.base_url}{api_path}"
            entry["url"] = url
            try:
                from nexuscore.llm.runtime import REQUEST_TIMEOUT

                resp = llm.session.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {llm.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                )
                entry["http_status"] = resp.status_code
                if resp.status_code != 200:
                    entry["ok"] = False
                    entry["error_snippet"] = resp.text[:500]
                else:
                    data = resp.json()
                    msg = (data.get("choices") or [{}])[0].get("message", {})
                    tcs = msg.get("tool_calls") or []
                    entry["ok"] = True
                    entry["returned_tool_calls"] = len(tcs)
                    entry["first_tool_name"] = (
                        tcs[0]["function"]["name"] if tcs else None
                    )
                    entry["content_snippet"] = str(msg.get("content"))[:200]
            except Exception as exc:  # noqa: BLE001 - 計測なので全例外記録
                entry["ok"] = False
                entry["error"] = f"{type(exc).__name__}: {exc}"
    out = _out_root() / "tools_echo.jsonl"
    with out.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(out)
    print(json.dumps(entry, ensure_ascii=False))
    return 0


def cmd_ack(args: argparse.Namespace) -> int:
    """CHECKLIST.md の4項目記入を検証（全項目記入で完了）"""
    cl = Path("artifacts/phase0/CHECKLIST.md")
    if not cl.exists():
        print("CHECKLIST.md が未作成")
        return 1
    items = ["MRO", "上書き要否", "HTTP_FACTORY位置", "リトライ差分", "tools受付"]
    text = cl.read_text(encoding="utf-8")
    missing = [i for i in items if i not in text]
    if missing:
        print(f"未記入項目: {missing}")
        return 1
    print("CHECKLIST.md 完備")
    return 0


def main(argv: list[str] | None = None) -> int:
    """計測CLI エントリポイント"""
    p = argparse.ArgumentParser(description=__doc__)
    sp = p.add_subparsers(dest="cmd", required=True)

    sp_mro = sp.add_parser("mro", help="クラスのMROを出力")
    sp_mro.add_argument("--class", dest="class_name", required=True)
    sp_mro.add_argument("--out", default=None)

    sp_ovr = sp.add_parser("override_check", help="Mixin予定メソッド衝突検査")
    sp_ovr.add_argument("--class", dest="class_name", required=True)
    sp_ovr.add_argument("--out", default=None)

    sp_fac = sp.add_parser("factory_pos", help="HTTP_CLIENT_FACTORY呼出位置")
    sp_fac.add_argument("--src-root", dest="src_root", default="src")

    sp.add_parser("retry_diff", help="リトライ実装差分（provider毎+共有層）")

    sp_echo = sp.add_parser("tool_echo", help="tools受付echo往復実測")
    sp_echo.add_argument("--provider", required=True)

    sp.add_parser("ack", help="CHECKLIST.md 完備確認")

    args = p.parse_args(argv)
    handler = globals()[f"cmd_{args.cmd}"]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
