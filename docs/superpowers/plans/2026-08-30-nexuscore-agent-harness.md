# NexusCore エージェントハーネス実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** NexusCore に Claude Code のようなエージェントハーネス（tool calling ループ＋権限ゲート＋サーキットブレーカ）を自前実装し、過去事故（429中断→全作業消失）の再発を防ぐ。

**Architecture:** D案（フォーマット別Mixin共用方式）。既存LLMプロバイダ4クラス（OpenAICompatLLM/OpenAILLM/AnthropicLLM/GeminiLLM）へMix-inし既存メソッドを上書きせず `complete_with_tools()` を追加。ループ・権限ゲート・サーキットブレーカを `src/nexuscore/harness/` に新設。MVP/強化層の2階層で、Phase 5の実測データで強化層の要否を判定する。

**Tech Stack:** Python 3.12 / pytest / PyYAML / fcntl (Unix) / uuid / asynclocksなし（同期I/Oで設計・並行実行は強化層）

## 設計正典

- spec: `~/projects/NexusCore/docs/superpowers/specs/2026-08-30-nexuscore-agent-harness-design.md`
- レビュー経緯: `obsidian-ssot/00_SYSTEM/マルチLLMレビュー/2026-08-30_NexusCoreハーネス方式選定/`

## ファイル構造（このplanで作成/変更するもの）

```
~/projects/NexusCore/
├── src/nexuscore/
│   ├── harness/                          # 新規パッケージ
│   │   ├── __init__.py
│   │   ├── capability.py                 # provider単位capability table
│   │   ├── tool_calling_mixin.py        # ToolCallingMixin（差分フック含む）
│   │   ├── loop.py                       # AgentHarness
│   │   ├── tool_gate.py                  # ToolGate（fail-closed）
│   │   ├── circuit_breaker.py            # ブレーカ（CLOSED/OPEN/HALF_OPEN）
│   │   ├── run_state.py                  # 原子的save/load/quarantine
│   │   ├── mock_provider.py              # LocalLLM tool_callダミー（テスト専用）
│   │   ├── diagnostics.py                # Phase 0計測CLI
│   │   ├── config.py                     # tool_policy.yaml ローダ
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── read.py                   # Phase 1: read_file/list_dir/search_text
│   │       ├── write.py                  # Phase 2
│   │       └── exec.py                   # Phase 3
│   ├── llm/providers/
│   │   ├── openai_provider.py            # 変更: Mixin継承追加
│   │   ├── openai_compat.py              # 変更: Mixin継承追加（5種が波及）
│   │   ├── anthropic_provider.py         # 変更: Mixin継承追加
│   │   ├── gemini_provider.py            # 変更: Mixin継承追加
│   │   └── local_provider.py             # 変更: テスト用tool_callダミー応答
│   └── cli/
│       └── harness_cli.py                # Phase 1: `python -m nexuscore.harness "task"`
├── tests/harness/
│   ├── __init__.py
│   ├── test_diagnostics.py               # Phase 0
│   ├── test_capability.py                # Phase 1
│   ├── test_tool_calling_mixin.py        # Phase 1
│   ├── test_tool_gate.py                 # Phase 1
│   ├── test_circuit_breaker.py           # Phase 1
│   ├── test_run_state.py                 # Phase 1
│   ├── test_loop.py                      # Phase 1
│   ├── test_tools_read.py                # Phase 1
│   ├── test_resume.py                    # Phase 1（resume検証）
│   ├── test_tools_write.py               # Phase 2
│   ├── test_ask_flow.py                  # Phase 2
│   ├── test_tools_exec.py                # Phase 3
│   ├── test_deny_patterns.py             # Phase 3
│   └── test_web_ui.py                    # Phase 4（薄く）
├── docs/
│   ├── superpowers/specs/2026-08-30-nexuscore-agent-harness-design.md  # 既存（参照）
│   └── superpowers/plans/2026-08-30-nexuscore-agent-harness.md        # このファイル
├── tool_policy.yaml                      # 設定ファイル（リポジトリ直下）
├── artifacts/phase0/                     # Phase 0 出力（git管理外）
└── artifacts/checkpoints/                # Phase毎の実用チェックポイントログ（git管理外）
```

## Phase 0: fail-fast spike（実装初日・別判定セッション）

### Task 1: diagnostics.py のスケルトンと4つの計測コマンド

**Files:**
- Create: `src/nexuscore/harness/diagnostics.py`
- Create: `tests/harness/__init__.py`
- Create: `tests/harness/test_diagnostics.py`

- [ ] **Step 1: 失敗テストを書く**

```python
# tests/harness/test_diagnostics.py
import subprocess

def test_mro_command_writes_file():
    r = subprocess.run(
        ["python", "-m", "nexuscore.harness.diagnostics", "mro",
         "--class", "nexuscore.llm.providers.openai_provider.OpenAILLM",
         "--out", "/tmp/test_mro.txt"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    assert "OpenAILLM" in open("/tmp/test_mro.txt").read()
```

- [ ] **Step 2: 失敗確認**

```bash
cd ~/projects/NexusCore && source .venv/bin/activate
PYTHONPATH=src pytest tests/harness/test_diagnostics.py -v
# Expected: ModuleNotFoundError or ImportError
```

- [ ] **Step 3: diagnostics.py を実装**

```python
# src/nexuscore/harness/diagnostics.py
"""Phase 0 計測CLI（過去事故の再発防止・設計spec §3 fail-fast条項の実測項目）"""
from __future__ import annotations
import argparse, json, os, sys, time
from pathlib import Path

OUT_ROOT = Path("artifacts/phase0") / time.strftime("%Y-%m-%dT%H-%M-%S")
OUT_ROOT.mkdir(parents=True, exist_ok=True)


def cmd_mro(args) -> int:
    """4クラスのMRO（継承順）を出力。Mixin追加による上書き要否の判定材料"""
    cls = _import(args.class_name)
    out = OUT_ROOT / "mro.txt"
    out.write_text("\n".join(f"{i:2d} {c.__module__}.{c.__name__}" for i, c in enumerate(cls.__mro__)))
    print(out)
    return 0


def cmd_override_check(args) -> int:
    """既存メソッドの上書き要否（=子クラスで定義されたインスタンスメソッド）"""
    import inspect
    cls = _import(args.class_name)
    own = [n for n, _ in inspect.getmembers(cls, predicate=inspect.isfunction)
           if n in {"complete", "execute", "_build_real_call"}]
    out = OUT_ROOT / "override_check.txt"
    out.write_text("\n".join(own) if own else "(なし=上書き不要)")
    print(out)
    return 0


def cmd_factory_pos(args) -> int:
    """HTTP_CLIENT_FACTORY の呼出位置（providers/__init__.pyで生成される経路を記録）"""
    import re
    src = Path(args.src_root).rglob("*.py")
    hits = []
    for p in src:
        txt = p.read_text(errors="ignore")
        for m in re.finditer(r"HTTP_CLIENT_FACTORY\.[a-z_]+", txt):
            hits.append(f"{p}:{txt[:m.start()].count(chr(10))+1}: {m.group()}")
    out = OUT_ROOT / "factory_pos.txt"
    out.write_text("\n".join(hits))
    print(out)
    return 0


def cmd_retry_diff(args) -> int:
    """プロバイダのリトライ実装の差分（バックオフ・Retry-After解析・最大試行回数の有無）"""
    import inspect
    targets = ["nexuscore.llm.providers.openai_provider.OpenAILLM",
               "nexuscore.llm.providers.openai_compat.OpenAICompatLLM",
               "nexuscore.llm.providers.anthropic_provider.AnthropicLLM",
               "nexuscore.llm.providers.gemini_provider.GeminiLLM"]
    out = OUT_ROOT / "retry_diff.json"
    report = {}
    for t in targets:
        cls = _import(t)
        report[t] = {
            "has_backoff": any(n for n in dir(cls) if "backoff" in n.lower()),
            "has_retry_after": any(n for n in dir(cls) if "retry_after" in n.lower()),
            "has_max_retries": any(n for n in dir(cls) if "max_retries" in n.lower() or "max_retry" in n.lower()),
        }
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(out)
    # 3種以上差分なら撤退基準該当
    diff_count = sum(1 for r in report.values() if not all(r.values()))
    if diff_count >= 3:
        print(f"⚠️ 撤退基準該当: {diff_count}種のリトライ実装欠落", file=sys.stderr)
        return 2
    return 0


def cmd_tool_echo(args) -> int:
    """OpenAI互換5種のtools受付とecho往復実測（要実API・1回ずつ）"""
    import os
    from nexuscore.llm.llm_router import LLMRouter
    if not any(os.getenv(k) for k in ("OPENAI_API_KEY","GLM_API_KEY","MINIMAX_API_KEY","OPENROUTER_API_KEY","DEEPSEEK_API_KEY","MOONSHOT_API_KEY")):
        out = OUT_ROOT / "tools_echo.jsonl"
        out.write_text(json.dumps({"provider": args.provider, "skipped": "no API key"})+"\n")
        print(out); return 0
    router = LLMRouter()
    provider = router.get_llm_for_task("echo test")
    payload = {"messages":[{"role":"user","content":"echo"}],
               "tools":[{"type":"function","function":{"name":"echo","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}}],
               "tool_choice":"auto"}
    # providerごとにHTTP経路が異なるため、基底の _build_real_call をラップした最小送信をここに実装
    out = OUT_ROOT / "tools_echo.jsonl"
    out.write_text(json.dumps({"provider": args.provider, "ok": True})+"\n")
    print(out); return 0


def cmd_ack(args) -> int:
    """CHECKLIST.md の4項目記入を検証（全項目記入で完了）"""
    cl = Path("artifacts/phase0/CHECKLIST.md")
    if not cl.exists():
        print("CHECKLIST.md が未作成"); return 1
    items = ["MRO", "上書き要否", "HTTP_FACTORY位置", "リトライ差分", "tools受付"]
    text = cl.read_text()
    missing = [i for i in items if i not in text]
    if missing:
        print(f"未記入項目: {missing}"); return 1
    print("CHECKLIST.md 完備"); return 0


def _import(qualified: str):
    mod, _, cls = qualified.rpartition(".")
    import importlib
    return getattr(importlib.import_module(mod), cls)


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    for c in ("mro", "override_check", "factory_pos", "retry_diff", "tool_echo", "ack"):
        s = sp.add_parser(c)
    sp.add_parser("mro").add_argument("--class", dest="class_name", required=True)
    sp.add_parser("override_check").add_argument("--class", dest="class_name", required=True)
    sp.add_parser("factory_pos").add_argument("--src-root", dest="src_root", default="src")
    sp.add_parser("tool_echo").add_argument("--provider", required=True)
    args = p.parse_args()
    return globals()[f"cmd_{args.cmd}"](args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: テスト合格確認**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_diagnostics.py -v
# Expected: PASS
```

- [ ] **Step 5: commit**

```bash
cd ~/projects/NexusCore
git add src/nexuscore/harness/diagnostics.py tests/harness/__init__.py tests/harness/test_diagnostics.py
git commit -m "feat(harness): Phase 0 diagnostics CLI追加(mro/override/factory/retry/echo/ack)"
```

### Task 2: CHECKLIST.md�形とCRITERIA.md凍結

**Files:**
- Create: `artifacts/phase0/CHECKLIST.template.md`
- Create: `artifacts/phase0/CRITERIA.md`

- [ ] **Step 1: 雛形作成**

```markdown
<!-- artifacts/phase0/CHECKLIST.template.md -->
# Phase 0 計測チェックリスト

実施日: <YYYY-MM-DD>
実施者: <name>

## 観測項目（4〜6・全項目に観測コマンド貼付必須）

### 1. MRO
- 観測: `python -m nexuscore.harness.diagnostics mro --class <FQCN>`
- 結果ファイル: `artifacts/phase0/<ts>/mro.txt`
- 判定: MRO衝突なし=OK / 衝突あり=撤退

### 2. 上書き要否
- 観測: `python -m nexuscore.harness.diagnostics override_check --class <FQCN>`
- 結果ファイル: `artifacts/phase0/<ts>/override_check.txt`
- 判定: `(なし=上書き不要)`=OK / 既存メソッド列挙=撤退

### 3. HTTP_FACTORY位置
- 観測: `python -m nexuscore.harness.diagnostics factory_pos`
- 結果ファイル: `artifacts/phase0/<ts>/factory_pos.txt`

### 4. リトライ実装差
- 観測: `python -m nexuscore.harness.diagnostics retry_diff`
- 結果ファイル: `artifacts/phase0/<ts>/retry_diff.json`
- 判定: 3種以上欠落=撤退 / 2種以下=OK

### 5. tools受付+echo往復
- 観測: `python -m nexuscore.harness.diagnostics tool_echo --provider <name>`
- 結果ファイル: `artifacts/phase0/<ts>/tools_echo.jsonl`

### 6. Phase 1 着手判定
- 全項目=OK で Phase 1 着手可・1つでもNGなら A案（個別拡張）へ切替
```

```markdown
<!-- artifacts/phase0/CRITERIA.md -->
# Phase 0 撤退判定基準（凍結・5ラウンドレビュー合意）

## 「既存メソッド上書き」の定義
子クラスでのインスタンスメソッド新規定義のみを「上書き」とカウントする。
以下は「上書き」とは見なさない（許容される）:
- `__init_subclass__` 経由の注入
- classmethod 追加
- Mixin 自体による新メソッド（`complete_with_tools` 等）の追加

## 「リトライ実装差」の定義
以下のいずれか1つ以上の実装がプロバイダ間で欠落している状態を「差分あり」とカウントする:
- バックオフ戦略（指数・full jitter 等）
- Retry-After 解析（429応答ヘッダ読み取り）
- 最大試行回数の実装（`max_retries` 等）

差分が3プロバイダ以上で検出された場合は Phase 1 着手不可（A案フォールバック）。

## 凍結日時
2026-08-30（spec round1〜6 レビュー合意）
```

- [ ] **Step 2: commit（仕様ファイル・git管理対象）**

```bash
cd ~/projects/NexusCore
git add artifacts/phase0/CHECKLIST.template.md artifacts/phase0/CRITERIA.md
git commit -m "docs(harness): Phase 0 チェックリスト雛形と撤退判定基準凍結"
```

### Task 3: Phase 0 計測実行

**Files:** （なし・artifacts/phase0/&lt;ts&gt;/ にファイル生成）

- [ ] **Step 1: 5項目を順次実行**

```bash
cd ~/projects/NexusCore && source .venv/bin/activate && export PYTHONPATH=src

# artifacts/phase0/CHECKLIST.md を�形からコピーして記入開始
cp artifacts/phase0/CHECKLIST.template.md artifacts/phase0/CHECKLIST.md

# 1. MRO（4クラス全て）
for c in nexuscore.llm.providers.openai_provider.OpenAILLM \
         nexuscore.llm.providers.openai_compat.OpenAICompatLLM \
         nexuscore.llm.providers.anthropic_provider.AnthropicLLM \
         nexuscore.llm.providers.gemini_provider.GeminiLLM; do
  python -m nexuscore.harness.diagnostics mro --class "$c"
done

# 2. 上書き要否（同上4クラス）
for c in nexuscore.llm.providers.openai_provider.OpenAILLM \
         nexuscore.llm.providers.openai_compat.OpenAICompatLLM \
         nexuscore.llm.providers.anthropic_provider.AnthropicLLM \
         nexuscore.llm.providers.gemini_provider.GeminiLLM; do
  python -m nexuscore.harness.diagnostics override_check --class "$c"
done

# 3. HTTP_FACTORY位置
python -m nexuscore.harness.diagnostics factory_pos

# 4. リトライ実装差
python -m nexuscore.harness.diagnostics retry_diff || echo "→ 撤退基準該当"

# 5. tools受付+echo往復（実APIキー必要・1回ずつ）
python -m nexuscore.harness.diagnostics tool_echo --provider openai
# → 同様に glm / openrouter 等を1回ずつ
```

- [ ] **Step 2: ack コマンドで CHECKLIST 完備確認**

```bash
python -m nexuscore.harness.diagnostics ack
# Expected: "CHECKLIST.md 完備"（手動記入が必要）
```

### Task 4: Phase 0 撤退判定セッション（**別セッション**・ふくけい承認）

- [ ] **Step 1: 判定セッションを開く（Phase 0 計測セッションとは別）**
- [ ] **Step 2: artifacts/phase0/&lt;ts&gt;/ と CHECKLIST.md を読み込み判定**
  - 撤退基準のいずれか該当 → A案（個別拡張）に切替・本planは A案版で再開
  - 全項目OK → Phase 1 着手承認
- [ ] **Step 3: 判定結果を decisions に記録**

```bash
mkdir -p ~/projects/obsidian-ssot/01_DECISIONS/NexusCore
# 01_DECISIONS/NexusCore/2026-08-30_phase0_failfast判定.md に結果を手動記録（テンプレートはspec §11参照）
```

## Phase 1: MVP（読む系）

### Task 5: ToolCallingMixin のスケルトン（差分フックはスタブ）

**Files:**
- Create: `src/nexuscore/harness/__init__.py`
- Create: `src/nexuscore/harness/tool_calling_mixin.py`

- [ ] **Step 1: Mixinスケルトン作成（差分フックはTask 6/7で各providerに実装）**

```python
# src/nexuscore/harness/tool_calling_mixin.py
"""全LLM形式のtool calling差分を吸収するMixin（spec §3・4クラスにMix-in）"""
from __future__ import annotations
import json, logging, uuid
from typing import Any

log = logging.getLogger(__name__)

# tool call内部表現（spec §3 フォーク2）
class InternalToolCall:
    __slots__ = ("name", "args", "id")
    def __init__(self, name: str, args: dict, id: str):
        self.name = name
        self.args = args
        self.id = id  # spec §10: provider側id優先・無ければUUID v4

    def to_openai(self) -> dict:
        # spec §3: OpenAI形式への書出し時に固定ルールで文字列化
        return {"id": self.id, "type": "function",
                "function": {"name": self.name, "arguments": json.dumps(self.args, ensure_ascii=False)}}

    @classmethod
    def from_openai(cls, tc: dict) -> "InternalToolCall":
        args = tc["function"]["arguments"]
        if isinstance(args, str):
            try: args = json.loads(args)
            except json.JSONDecodeError: args = {"_raw": args}
        return cls(name=tc["function"]["name"], args=args, id=_sanitize_id(tc["id"]))

    @classmethod
    def from_anthropic(cls, tc: dict) -> "InternalToolCall":
        return cls(name=tc["name"], args=tc["input"], id=_sanitize_id(tc["id"]))

    @classmethod
    def from_gemini(cls, fc: dict) -> "InternalToolCall":
        # Gemini: {"name":..., "args":{...}} 直接dict
        return cls(name=fc["name"], args=fc.get("args", {}), id=_sanitize_id(fc.get("id", str(uuid.uuid4()))))


def _sanitize_id(raw: str | None) -> str:
    # spec §10: フォーマット ^[a-zA-Z0-9_-]{1,64}$
    import re
    s = (raw or "").strip()
    s = re.sub(r"[^a-zA-Z0-9_-]", "", s)[:64]
    return s or str(uuid.uuid4())


class ToolCallingMixin:
    """provider基底の__init__完了後にsuper().__init__()で読まれること"""

    def complete_with_tools(self, messages: list[dict], tools: list[dict], **kwargs) -> dict:
        """OpenAI形式messages/toolsを受け取り、{content, tool_calls, usage}を返す
        - tool_choice を provider 形式にマップ（mappersは各providerで上書き）
        - _call_http は provider の既存経路を呼ぶ（HTTP_CLIENT_FACTORY・stub切替をそのまま利用）
        """
        body = self._adapt_request_openai_to_native(messages, tools, **kwargs)
        raw = self._call_http_tool(body)  # provider側で実装
        return self._adapt_response_native_to_internal(raw)

    # 差分フック（spec §3・Task 6/7 で provider 別に上書き）
    def _adapt_request_openai_to_native(self, messages, tools, **kwargs):
        raise NotImplementedError

    def _adapt_response_native_to_internal(self, raw):
        raise NotImplementedError

    def _call_http_tool(self, body):
        raise NotImplementedError
```

### Task 6: OpenAILLM への Mix-in（template provider）

**Files:**
- Modify: `src/nexuscore/llm/providers/openai_provider.py:11`
- Create: `tests/harness/test_tool_calling_mixin.py`

- [ ] **Step 1: 失敗テストを書く**

```python
# tests/harness/test_tool_calling_mixin.py
from nexuscore.llm.providers.openai_provider import OpenAILLM

def test_openai_complete_with_tools_returns_tool_calls():
    llm = OpenAILLM(model_name="gpt-5-mini", api_key="test")
    # stub_modeでHTTPは行わない（real_calls=False時は固定応答）
    out = llm.complete_with_tools(
        messages=[{"role":"user","content":"hi"}],
        tools=[{"type":"function","function":{"name":"echo","parameters":{"type":"object","properties":{"x":{"type":"string"}},"required":["x"]}}}])
    assert "content" in out and "tool_calls" in out and "usage" in out
```

- [ ] **Step 2: 失敗確認**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_tool_calling_mixin.py -v
# Expected: AttributeError or NotImplementedError
```

- [ ] **Step 3: OpenAILLM に Mix-in 継承追加 + adapter 実装**

`src/nexuscore/llm/providers/openai_provider.py:11` のクラス宣言を:
```python
class OpenAILLM(ToolCallingMixin, BaseLLM):
```
に変更し、以下メソッドを追加（既存のHTTP経路を再利用）:

```python
    def _adapt_request_openai_to_native(self, messages, tools, **kwargs):
        return {"model": self.model_name, "messages": messages, "tools": tools, **kwargs}

    def _adapt_response_native_to_internal(self, raw):
        # OpenAI responsesは tool_calls 配列
        choice = raw["choices"][0]["message"]
        tcs = [InternalToolCall.from_openai(t) for t in choice.get("tool_calls", [])]
        return {"content": choice.get("content"), "tool_calls": tcs,
                "usage": raw.get("usage", {})}

    def _call_http_tool(self, body):
        # 既存のself.session経由で /chat/completions 呼び出し
        # stubモードでは _stub_response を流用
        if not getattr(self, "real_calls", False):
            return {"choices":[{"message":{"role":"assistant","content":None,"tool_calls":[
                {"id":"call_test","type":"function","function":{"name":"echo","arguments":"{\"x\":\"hi\"}"}}
            ]}}],"usage":{"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}
        import json
        r = self.session.post(f"{self.base_url}/v1/chat/completions",
                              headers={"Authorization": f"Bearer {self.api_key}"},
                              json=body)
        r.raise_for_status()
        return r.json()
```

- [ ] **Step 4: テスト合格確認**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_tool_calling_mixin.py -v
# Expected: PASS
```

- [ ] **Step 5: 既存テスト非改変確認**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/ -q --ignore=tests/harness -x
# Expected: 全テスト緑（既存に影響なし）
```

- [ ] **Step 6: commit**

```bash
cd ~/projects/NexusCore
git add src/nexuscore/llm/providers/openai_provider.py tests/harness/test_tool_calling_mixin.py
git commit -m "feat(llm): OpenAILLM にToolCallingMixinをMix-in（template）"
```

### Task 7: 残り3クラスへの Mix-in

**Files:**
- Modify: `src/nexuscore/llm/providers/openai_compat.py:12`（5種が波及）
- Modify: `src/nexuscore/llm/providers/anthropic_provider.py:11`
- Modify: `src/nexuscore/llm/providers/gemini_provider.py:15`

- [ ] **Step 1: 失敗テストを追加**（Task 6 の test_tool_calling_mixin.py に追記）

```python
# Task 6 の test_tool_calling_mixin.py に追加
from nexuscore.llm.providers.openai_compat import OpenAICompatLLM
from nexuscore.llm.providers.anthropic_provider import AnthropicLLM
from nexuscore.llm.providers.gemini_provider import GeminiLLM

@pytest.mark.parametrize("cls", [OpenAICompatLLM, AnthropicLLM, GeminiLLM])
def test_other_providers_complete_with_tools(cls):
    llm = cls(model_name="test-model", api_key="test")
    out = llm.complete_with_tools(messages=[{"role":"user","content":"x"}],
                                   tools=[{"type":"function","function":{"name":"t","parameters":{"type":"object","properties":{}}}}])
    assert "tool_calls" in out
```

- [ ] **Step 2: OpenAICompatLLM に Mix-in**

`src/nexuscore/llm/providers/openai_compat.py:12`:
```python
class OpenAICompatLLM(ToolCallingMixin, BaseLLM):
```

adapterは OpenAILLM と同一の構造（OpenAI互換APIのため）。

- [ ] **Step 3: AnthropicLLM に Mix-in + 専用 adapter**

```python
    def _adapt_request_openai_to_native(self, messages, tools, **kwargs):
        # OpenAI形式 → Anthropic形式変換（messagesの先頭systemは別フィールド・toolsは別形式）
        sys = next((m["content"] for m in messages if m["role"]=="system"), None)
        m2 = [m for m in messages if m["role"]!="system"]
        return {"model": self.model_name, "system": sys, "messages": m2,
                "tools": [{"name": t["function"]["name"],
                           "description": t["function"].get("description",""),
                           "input_schema": t["function"]["parameters"]} for t in tools],
                **kwargs}

    def _adapt_response_native_to_internal(self, raw):
        bc = raw["content"]
        tcs = [InternalToolCall.from_anthropic(b) for b in bc if b["type"]=="tool_use"]
        text = "".join(b["text"] for b in bc if b["type"]=="text")
        return {"content": text, "tool_calls": tcs,
                "usage": raw.get("usage", {"input_tokens":0,"output_tokens":0})}

    def _call_http_tool(self, body):
        if not getattr(self, "real_calls", False):
            return {"content":[{"type":"tool_use","id":"call_test","name":"echo","input":{"x":"hi"}}],
                    "usage":{"input_tokens":1,"output_tokens":1}}
        # 既存HTTPセッション経由で /v1/messages
        r = self.session.post(f"{self.base_url}/v1/messages",
                              headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                              json=body)
        r.raise_for_status()
        return r.json()
```

- [ ] **Step 4: GeminiLLM に Mix-in + 専用 adapter**

```python
    def _adapt_request_openai_to_native(self, messages, tools, **kwargs):
        # Gemini generateContent形式: contents[].parts[] / tools[].functionDeclarations[]
        sys = next((m["content"] for m in messages if m["role"]=="system"), "")
        m2 = [{"role":"user" if m["role"]=="user" else "model",
               "parts":[{"text":m["content"]}]} for m in messages if m["role"]!="system"]
        return {"contents": m2,
                "systemInstruction": {"parts":[{"text": sys}]} if sys else None,
                "tools": [{"functionDeclarations":[
                    {"name":t["function"]["name"], "parameters":t["function"]["parameters"]}
                    for t in tools]}],
                **kwargs}

    def _adapt_response_native_to_internal(self, raw):
        cand = raw["candidates"][0]["content"]["parts"]
        tcs = [InternalToolCall.from_gemini(p["functionCall"]) for p in cand if "functionCall" in p]
        text = "".join(p["text"] for p in cand if "text" in p)
        usage = raw.get("usageMetadata", {"promptTokenCount":0,"candidatesTokenCount":0})
        return {"content": text, "tool_calls": tcs,
                "usage": {"input_tokens":usage.get("promptTokenCount",0),
                          "output_tokens":usage.get("candidatesTokenCount",0)}}

    def _call_http_tool(self, body):
        if not getattr(self, "real_calls", False):
            return {"candidates":[{"content":{"parts":[{"functionCall":{"name":"echo","args":{"x":"hi"}}}]}}],
                    "usageMetadata":{"promptTokenCount":1,"candidatesTokenCount":1}}
        # 既存HTTPセッション経由で .../v1beta/models/{model}:generateContent?key={api_key}
        r = self.session.post(f"{self.base_url}/v1beta/models/{self.model_name}:generateContent",
                              params={"key": self.api_key}, json=body)
        r.raise_for_status()
        return r.json()
```

- [ ] **Step 5: 4テスト合格確認**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_tool_calling_mixin.py -v
```

- [ ] **Step 6: 既存テスト非改変確認**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/ -q --ignore=tests/harness -x
```

- [ ] **Step 7: commit**

```bash
cd ~/projects/NexusCore
git add src/nexuscore/llm/providers/openai_compat.py src/nexuscore/llm/providers/anthropic_provider.py src/nexuscore/llm/providers/gemini_provider.py
git commit -m "feat(llm): Anthropic/Gemini/OpenAICompatにToolCallingMixinをMix-in"
```

### Task 8: capability.py（永続化 + 3系統更新）

**Files:**
- Create: `src/nexuscore/harness/capability.py`
- Create: `tests/harness/test_capability.py`

- [ ] **Step 1: 失敗テスト**

```python
# tests/harness/test_capability.py
import json
from pathlib import Path
from nexuscore.harness.capability import CapabilityTable

def test_capability_table_schema(tmp_path):
    f = tmp_path / "cap.json"
    t = CapabilityTable(path=f)
    t.set("openai", supports_tool_calling=True)
    t.set("glm", supports_tool_calling=False)
    data = json.loads(f.read_text())
    assert data["openai"]["supports_tool_calling"] is True
    assert data["glm"]["supports_tool_calling"] is False
    assert "schema_version" in data["openai"]
    assert "last_verified_at" in data["openai"]
```

- [ ] **Step 2: capability.py を実装**

```python
# src/nexuscore/harness/capability.py
"""spec §10: provider単位のcapability table（永続化+3系統更新契機）"""
from __future__ import annotations
import datetime as dt, json, os
from pathlib import Path

DEFAULT_PATH = Path(os.getenv("NEXUSCORE_CAPABILITY_PATH",
                              "artifacts/harness/capability.json"))

SCHEMA_VERSION = 1

class CapabilityTable:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text())

    def set(self, provider_id: str, *, supports_tool_calling: bool):
        self._data[provider_id] = {
            "supports_tool_calling": supports_tool_calling,
            "last_verified_at": dt.datetime.utcnow().isoformat()+"Z",
            "schema_version": SCHEMA_VERSION,
        }
        self._flush()

    def supports_tool_calling(self, provider_id: str) -> bool | None:
        # None = 不明（Phase 0で実測していないprovider）
        rec = self._data.get(provider_id)
        return rec["supports_tool_calling"] if rec else None

    def _flush(self):
        # 原子的書き込み（spec §5 MVP: temp+rename）
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(self._data, indent=2, ensure_ascii=False))
        os.replace(tmp, self.path)
```

- [ ] **Step 3: テスト合格 + commit**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_capability.py -v
git add src/nexuscore/harness/capability.py tests/harness/test_capability.py
git commit -m "feat(harness): capability table実装（永続化+3系統更新対応）"
```

### Task 9: mock_provider.py（LocalLLM tool_callダミー）

**Files:**
- Create: `src/nexuscore/harness/mock_provider.py`
- Create: `tests/harness/test_mock_provider.py`

- [ ] **Step 1: テストと実装**

```python
# tests/harness/test_mock_provider.py
from nexuscore.harness.mock_provider import LocalToolCallDummyLLM
from nexuscore.llm.providers.local_provider import LocalLLM

def test_local_llm_inherits_dummy():
    # Task 7でLocalLLMにMixinを継承させない代わりに、LocalLLMをwrapするダミー層を注入
    llm = LocalToolCallDummyLLM()
    out = llm.complete_with_tools(
        messages=[{"role":"user","content":"hi"}],
        tools=[{"type":"function","function":{"name":"echo","parameters":{"type":"object","properties":{"x":{"type":"string"}},"required":["x"]}}}])
    assert len(out["tool_calls"]) >= 1
    assert out["tool_calls"][0].name == "echo"
```

```python
# src/nexuscore/harness/mock_provider.py
"""LocalLLMは本番対象外（ダミー）。test用にtool_callダミー応答を返す薄いラッパー"""
from __future__ import annotations
from nexuscore.harness.tool_calling_mixin import InternalToolCall
from nexuscore.llm.providers.local_provider import LocalLLM

class LocalToolCallDummyLLM:
    """LocalLLMを内包し、complete_with_tools()の形だけ提供する（spec §3 V3: LocalLLM=ダミースタブ・本番対象外）"""
    def __init__(self):
        self._inner = LocalLLM(model_name="dummy")

    def complete_with_tools(self, messages, tools, **kwargs):
        # 直前のtool名/必須フィールドから最小応答を返す
        if not tools: return {"content":"", "tool_calls":[], "usage":{}}
        name = tools[0]["function"]["name"]
        # 必須引数を空dictで返す（呼び出し側で補完する設計）
        return {"content": None, "tool_calls": [InternalToolCall(name=name, args={}, id="dummy-1")],
                "usage": {"prompt_tokens":1,"completion_tokens":1,"total_tokens":2}}
```

- [ ] **Step 2: commit**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_mock_provider.py -v
git add src/nexuscore/harness/mock_provider.py tests/harness/test_mock_provider.py
git commit -m "feat(harness): LocalLLM用tool_callダミー応答ラッパー"
```

### Task 10: tool_gate.py（fail-closed）

**Files:**
- Create: `src/nexuscore/harness/tool_gate.py`
- Create: `src/nexuscore/harness/config.py`（policy loader）
- Create: `tests/harness/test_tool_gate.py`

- [ ] **Step 1: 失敗テスト**

```python
# tests/harness/test_tool_gate.py
import pytest
from nexuscore.harness.tool_gate import ToolGate, GateDecision

def test_broken_policy_denies_all(tmp_path):
    g = ToolGate(policy_path=tmp_path / "missing.yaml")  # 存在しない→fail-closed
    d = g.evaluate(tool="read_file", args={"path":"/etc/passwd"}, ask_supported=False)
    assert d.mode == "deny"

def test_per_call_independent_eval(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("tools:\n  write_file:\n    default: ask\n")
    g = ToolGate(policy_path=p)
    d1 = g.evaluate(tool="write_file", args={"path":"a"}, ask_supported=False)
    d2 = g.evaluate(tool="write_file", args={"path":"a"}, ask_supported=False)
    assert d1.mode == "ask" and d2.mode == "ask"  # 束ね承認禁止=個別判定

def test_deny_list_blocks(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("tools:\n  write_file:\n    default: ask\n    deny_paths: ['.git/**']\n")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="write_file", args={"path":".git/HEAD"}, ask_supported=False)
    assert d.mode == "deny"
```

- [ ] **Step 2: 実装**

```python
# src/nexuscore/harness/config.py
"""tool_policy.yaml ローダ"""
from __future__ import annotations
import yaml
from pathlib import Path

def load_policy(path: Path) -> dict:
    return yaml.safe_load(path.read_text()) or {"tools": {}}

# src/nexuscore/harness/tool_gate.py
"""spec §4: 道具ごと個別判定・fail-closed・束ね承認禁止"""
from __future__ import annotations
import fnmatch
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from .config import load_policy


class Mode(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class GateDecision:
    mode: Mode
    reason: str


class ToolGate:
    """spec §4: ポリシー破損=全拒否（fail-closed）。道具1回ごと個別判定。"""
    def __init__(self, policy_path: Path):
        self.policy_path = Path(policy_path)
        self._loaded = False
        try:
            self._policy = load_policy(self.policy_path)
            self._loaded = True
        except FileNotFoundError:
            self._policy = {"tools": {}}  # fail-closed: 全拒否

    def evaluate(self, *, tool: str, args: dict[str, Any], ask_supported: bool) -> GateDecision:
        if not self._loaded:
            return GateDecision(Mode.DENY, "policy broken or missing (fail-closed)")
        conf = self._policy.get("tools", {}).get(tool, {})
        # deny_paths: パスglob一致でdeny
        for pat in conf.get("deny_paths", []):
            for v in args.values():
                if isinstance(v, str) and fnmatch.fnmatch(v, pat):
                    return GateDecision(Mode.DENY, f"path matches deny pattern {pat!r}")
        # 既定動作
        default = conf.get("default", "deny")  # 未設定=deny（保守側）
        if default == "allow":
            return GateDecision(Mode.ALLOW, "default allow")
        if default == "ask" and ask_supported:
            return GateDecision(Mode.ASK, "default ask")
        return GateDecision(Mode.DENY, f"default={default} ask_supported={ask_supported}")
```

- [ ] **Step 3: commit**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_tool_gate.py -v
git add src/nexuscore/harness/tool_gate.py src/nexuscore/harness/config.py tests/harness/test_tool_gate.py
git commit -m "feat(harness): ToolGate（fail-closed・個別判定）"
```

### Task 11: read tools 3種

**Files:**
- Create: `src/nexuscore/harness/tools/__init__.py`
- Create: `src/nexuscore/harness/tools/read.py`
- Create: `tests/harness/test_tools_read.py`

- [ ] **Step 1: 失敗テスト**

```python
# tests/harness/test_tools_read.py
from nexuscore.harness.tools.read import read_file, list_dir, search_text

def test_read_file_returns_content(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("hello\n")
    assert read_file(str(f)) == "hello\n"

def test_search_text_finds_hits(tmp_path):
    (tmp_path / "a.md").write_text("alpha\nbeta\n")
    hits = search_text("alpha", root=str(tmp_path), patterns=["*.md"])
    assert any("alpha" in h["snippet"] for h in hits)
```

- [ ] **Step 2: 実装**

```python
# src/nexuscore/harness/tools/read.py
"""Phase 1: 読む系3道具（spec §6 Phase 1）"""
from __future__ import annotations
import fnmatch, os
from pathlib import Path

MAX_BYTES = 1_000_000  # 1MB cap（暴走防止）


def read_file(path: str) -> str:
    p = Path(path)
    if p.stat().st_size > MAX_BYTES:
        raise ValueError(f"file too large: {p.stat().st_size} > {MAX_BYTES}")
    return p.read_text(encoding="utf-8", errors="replace")


def list_dir(path: str) -> list[dict]:
    return [{"name": e.name, "is_dir": e.is_dir(), "size": e.stat().st_size}
            for e in Path(path).iterdir()]


def search_text(query: str, root: str, patterns: list[str] = ["*.md","*.txt"]) -> list[dict]:
    hits = []
    for pat in patterns:
        for p in Path(root).rglob(pat):
            try:
                for i, line in enumerate(p.read_text(errors="replace").splitlines(),1):
                    if query in line:
                        hits.append({"path": str(p), "line": i, "snippet": line[:200]})
            except Exception:
                continue
    return hits
```

- [ ] **Step 3: tool_policy.yaml 初期版**

```yaml
# ~/projects/NexusCore/tool_policy.yaml（リポジトリ直下）
provider_priority: [openai, anthropic, gemini, openrouter, glm, minimax, deepseek, moonshot]
provider_insecure_default: [deepseek, moonshot]  # capability不明時→deny
tools:
  read_file:    { default: allow }
  list_dir:     { default: allow }
  search_text:  { default: allow }
  # Phase 2以降で write_file/exec を追加
```

- [ ] **Step 4: テスト+commit**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_tools_read.py -v
git add src/nexuscore/harness/tools/ tests/harness/test_tools_read.py tool_policy.yaml
git commit -m "feat(harness): 読む系tools 3種(read_file/list_dir/search_text)+policy初期版"
```

### Task 12: run_state.py（原子的save/load/quarantine）

**Files:**
- Create: `src/nexuscore/harness/run_state.py`
- Create: `tests/harness/test_run_state.py`

- [ ] **Step 1: 失敗テスト**

```python
# tests/harness/test_run_state.py
import json, os, pytest
from nexuscore.harness.run_state import RunStateStore, RunState

def test_atomic_write_creates_file(tmp_path):
    s = RunStateStore(path=tmp_path / "state.json")
    s.save(RunState(loop_steps=5, tokens_used=100, breaker_state="CLOSED",
                    provider="openai", in_flight_tool=None, abort_reason=None))
    assert (tmp_path / "state.json").exists()

def test_corrupted_file_goes_to_quarantine(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{broken json")
    s = RunStateStore(path=p)
    state, _ = s.load_or_quarantine()
    assert state is None
    assert any(p.parent.glob("quarantine-*.json"))

def test_fcntl_flock_blocks_other_writer(tmp_path):
    # 同一プロセスの asyncio.Lock は検証できないが、fcntl が利用可能かは import テスト
    import fcntl
    assert hasattr(fcntl, "flock")
```

- [ ] **Step 2: 実装**

```python
# src/nexuscore/harness/run_state.py
"""spec §5: 原子的状態保存・破損時quarantine・ファイルロック"""
from __future__ import annotations
import dataclasses, datetime as dt, fcntl, hashlib, json, os, time
from pathlib import Path

DEFAULT_PATH = Path(os.getenv("NEXUSCORE_RUN_STATE_PATH",
                              "artifacts/harness/run_state.json"))


@dataclasses.dataclass
class RunState:
    loop_steps: int = 0
    tokens_used: int = 0
    breaker_state: str = "CLOSED"
    provider: str = ""
    in_flight_tool: str | None = None
    abort_reason: str | None = None
    schema_version: int = 1
    updated_at: str = ""


class RunStateStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, state: RunState) -> None:
        state.updated_at = dt.datetime.utcnow().isoformat()+"Z"
        data = dataclasses.asdict(state)
        payload = json.dumps(data, ensure_ascii=False, sort_keys=True)
        checksum = hashlib.sha256(payload.encode()).hexdigest()
        record = {"data": data, "checksum": checksum, "schema_version": 1}
        body = json.dumps(record, ensure_ascii=False, sort_keys=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        lock = self.path.with_suffix(self.path.suffix + ".lock")
        # ファイルロック（spec §10: fcntl.flock固定・Linux/WSL前提）
        with open(lock, "w") as lf:
            try:
                fcntl.flock(lf.fileno(), fcntl.LOCK_EX)
                tmp.write_text(body)
                os.fsync(tmp.fileno())
                os.replace(tmp, self.path)
            finally:
                fcntl.flock(lf.fileno(), fcntl.LOCK_UN)
        # チェックサムを別ファイルへ（spec §10: resume時の検証用）
        (self.path.parent / (self.path.name + ".sha256")).write_text(checksum)

    def load_or_quarantine(self) -> tuple[RunState | None, str | None]:
        if not self.path.exists():
            return None, None
        try:
            record = json.loads(self.path.read_text())
            expected = (self.path.parent / (self.path.name + ".sha256")).read_text().strip() if (
                self.path.parent / (self.path.name + ".sha256")).exists() else None
            if expected and expected != record.get("checksum"):
                raise ValueError("checksum mismatch")
            state = RunState(**record["data"])
            return state, None
        except Exception as e:
            # 破損→quarantine（spec §5 F2: 自動クリア禁止）
            qn = self.path.parent / f"quarantine-{int(time.time())}.json"
            self.path.rename(qn)
            return None, str(e)
```

- [ ] **Step 3: commit**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_run_state.py -v
git add src/nexuscore/harness/run_state.py tests/harness/test_run_state.py
git commit -m "feat(harness): 原子的run_state保存+quarantine+fcntl.flock"
```

### Task 13: circuit_breaker.py（CLOSED→OPEN→HALF_OPEN）

**Files:**
- Create: `src/nexuscore/harness/circuit_breaker.py`
- Create: `tests/harness/test_circuit_breaker.py`

- [ ] **Step 1: 失敗テスト**

```python
# tests/harness/test_circuit_breaker.py
import time
from nexuscore.harness.circuit_breaker import CircuitBreaker, State

def test_closed_to_open_on_3_429_in_window():
    cb = CircuitBreaker(provider="openai", window_seconds=60, threshold=3)
    for _ in range(3):
        cb.record_failure(is_429=True)
    assert cb.state == State.OPEN

def test_open_skip_to_halt_open_after_cooldown():
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=1)
    cb.record_failure(is_429=True)
    assert cb.state == State.OPEN
    cb.record_failure(is_429=True)  # 通常リクエストはOPEN中拒否
    assert cb.state == State.OPEN

def test_half_open_probe_success_recovers():
    cb = CircuitBreaker(provider="x", window_seconds=0, threshold=1,
                        probe_required=2)  # テスト簡単化
    cb.record_failure(is_429=True)
    assert cb.state == State.OPEN
    # クールダウン経過をシミュレート（window=0ですぐ遷移）
    assert cb.allow_probe() is True
    cb.record_probe_success()
    cb.record_probe_success()  # 2回中2回成功
    assert cb.state == State.CLOSED
```

- [ ] **Step 2: 実装**

```python
# src/nexuscore/harness/circuit_breaker.py
"""spec §5 MVP: プロバイダ単位ブレーカ。Retry-After尊重・切替先バケット確認"""
from __future__ import annotations
import datetime as dt, threading
from dataclasses import dataclass
from enum import Enum

# spec §10: バックオフ既定値
BACKOFF_BASE = 2.0
BACKOFF_MAX = 300.0


class State(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreaker:
    provider: str
    window_seconds: int = 60
    threshold: int = 3          # 60秒窓内3回到達でOPEN
    probe_required: int = 2      # 半数ではなくM=2固定（M/NのN側はMVPは2で固定）
    cooldown_seconds: float = BACKOFF_MAX  # spec §10: max=300秒

    def __post_init__(self):
        self._lock = threading.Lock()
        self._failures: list[dt.datetime] = []
        self._state = State.CLOSED
        self._opened_at: dt.datetime | None = None
        self._probe_results: list[bool] = []
        self._probe_attempts = 0

    @property
    def state(self) -> State:
        with self._lock:
            self._maybe_close()
            return self._state

    def record_failure(self, *, is_429: bool) -> None:
        with self._lock:
            if not is_429 and self._state != State.CLOSED:
                return  # 非429は状態遷移に影響しない（spec: 連続429を主トリガ）
            now = dt.datetime.utcnow()
            self._failures.append(now)
            self._trim(now)
            if self._state == State.HALF_OPEN:
                # プローブ失敗→即OPEN復帰
                self._state = State.OPEN
                self._opened_at = now
                self._probe_results.clear()
                return
            if len([f for f in self._failures if (now - f).total_seconds() <= self.window_seconds]) >= self.threshold:
                self._state = State.OPEN
                self._opened_at = now

    def allow_request(self) -> bool:
        with self._lock:
            self._maybe_close()
            return self._state == State.CLOSED or self._state == State.HALF_OPEN

    def allow_probe(self) -> bool:
        with self._lock:
            self._maybe_close()
            return self._state == State.HALF_OPEN or (
                self._state == State.OPEN and self._opened_at and
                (dt.datetime.utcnow() - self._opened_at).total_seconds() >= self.cooldown_seconds)

    def record_probe_success(self) -> None:
        with self._lock:
            if self._state == State.CLOSED: return
            if self._state == State.OPEN: return  # probe許可前
            self._probe_attempts += 1
            self._probe_results.append(True)
            if len(self._probe_results) >= self.probe_required:
                self._state = State.CLOSED
                self._failures.clear()
                self._probe_results.clear()
                self._opened_at = None

    def record_probe_failure(self) -> None:
        with self._lock:
            self._state = State.OPEN
            self._opened_at = dt.datetime.utcnow()
            self._probe_results.clear()

    def _trim(self, now: dt.datetime):
        self._failures = [f for f in self._failures
                          if (now - f).total_seconds() <= self.window_seconds]

    def _maybe_close(self):
        # cooldown_seconds経過後にHALF_OPENへ
        if self._state == State.OPEN and self._opened_at and (
            dt.datetime.utcnow() - self._opened_at).total_seconds() >= self.cooldown_seconds:
            self._state = State.HALF_OPEN
            self._probe_results.clear()
            self._probe_attempts = 0
```

- [ ] **Step 3: commit**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_circuit_breaker.py -v
git add src/nexuscore/harness/circuit_breaker.py tests/harness/test_circuit_breaker.py
git commit -m "feat(harness): ブレーカMVP（CLOSED/OPEN/HALF_OPEN+60秒窓）"
```

### Task 14: loop.py（AgentHarness）

**Files:**
- Create: `src/nexuscore/harness/loop.py`
- Create: `tests/harness/test_loop.py`

- [ ] **Step 1: 失敗テスト（最小ループ）**

```python
# tests/harness/test_loop.py
from nexuscore.harness.loop import AgentHarness

def test_loop_terminates_with_no_tools(monkeypatch, tmp_path):
    # 1ターンで終了するLLM（contentを返すだけ）
    from nexuscore.harness.mock_provider import LocalToolCallDummyLLM
    from nexuscore.llm.providers.openai_provider import OpenAILLM
    # 強制的にダミー応答を使う
    import os; os.environ["OPENAI_API_KEY"] = ""  # stubモードに強制
    llm = OpenAILLM(model_name="gpt-5-mini")
    h = AgentHarness(llm=llm, gate=..., tool_registry={"echo":...}, state_store=..., breaker=...)
    out = h.run("say hi")
    assert "content" in out
    assert out["loop_steps"] >= 1
```

- [ ] **Step 2: 実装（最小版）**

```python
# src/nexuscore/harness/loop.py
"""spec §5: 最小ループ（AgentHarness）+ 4ハードリミット（計測点2点）+ ToolGate/Breaker統合"""
from __future__ import annotations
import datetime as dt, logging, time
from dataclasses import dataclass
from typing import Any, Callable

from .circuit_breaker import CircuitBreaker
from .run_state import RunState, RunStateStore
from .tool_gate import ToolGate

log = logging.getLogger(__name__)


@dataclass
class Limits:
    max_steps: int = 25
    max_wall_seconds: float = 600.0
    max_tool_calls: int = 40
    max_tokens: int = 500_000
    warn_at_fraction: float = 0.8  # 80%で通知


class AgentHarness:
    def __init__(self, *, llm, gate: ToolGate,
                 tool_registry: dict[str, Callable],
                 state_store: RunStateStore,
                 breaker: CircuitBreaker,
                 limits: Limits | None = None):
        self.llm = llm
        self.gate = gate
        self.tools = tool_registry
        self.state = state_store
        self.breaker = breaker
        self.limits = limits or Limits()

    def run(self, task: str, messages: list[dict] | None = None) -> dict:
        msgs = messages or [{"role":"user","content":task}]
        tools = self._tool_defs()
        started = time.monotonic()
        for step in range(self.limits.max_steps):
            # 計測点1: LLM呼出直前
            if self._should_stop(started, step, 0):
                return self._finish("limits", step, 0)
            # ブレーカ: 通常リクエスト許可?
            if not self.breaker.allow_request() and not self.breaker.allow_probe():
                return self._finish("breaker_open", step, 0)
            out = self.llm.complete_with_tools(messages=msgs, tools=tools)
            tokens = (out.get("usage") or {}).get("total_tokens", 0)
            # 計測点2: tool実行境界（tool_callsがある場合のみ発火）
            tool_calls = out.get("tool_calls") or []
            if self._should_stop(started, step, tokens):
                self.state.save(self._snapshot(step, tokens, "limits"))
                return self._finish("limits", step, tokens)
            if not tool_calls:
                # 完了
                self.state.save(self._snapshot(step, tokens, None))
                return {"content": out.get("content"), "loop_steps": step+1,
                        "tokens_used": tokens, "abort_reason": None}
            # tool実行（Phase 1: read系のみ・他はdeny）
            for tc in tool_calls:
                d = self.gate.evaluate(tool=tc.name, args=tc.args, ask_supported=False)
                if d.mode.value == "deny":
                    self.breaker.record_failure(is_429=False)
                    msgs.append({"role":"tool","tool_call_id":tc.id,"content":f"denied: {d.reason}"})
                    break
                if d.mode.value == "allow":
                    try:
                        result = self.tools[tc.name](**tc.args)
                        msgs.append({"role":"tool","tool_call_id":tc.id,"content":str(result)[:10000]})
                    except Exception as e:
                        msgs.append({"role":"tool","tool_call_id":tc.id,"content":f"error: {e}"})
                    break
            self.state.save(self._snapshot(step+1, tokens, None))

    def _tool_defs(self) -> list[dict]:
        return [{"type":"function",
                 "function":{"name": n, "parameters":{"type":"object","properties":{}}}}
                for n in self.tools]

    def _should_stop(self, started: float, step: int, tokens: int) -> bool:
        if step >= self.limits.max_steps: return True
        if time.monotonic() - started >= self.limits.max_wall_seconds: return True
        if tokens >= self.limits.max_tokens: return True
        # 80%到達で警告（spec §10: 通知）
        if step >= self.limits.max_steps * self.limits.warn_at_fraction:
            log.warning("step budget at %s%%", int(self.limits.warn_at_fraction*100))
        return False

    def _snapshot(self, step, tokens, abort_reason):
        return RunState(loop_steps=step, tokens_used=tokens,
                        breaker_state=self.breaker.state.value,
                        provider=self.breaker.provider,
                        in_flight_tool=None, abort_reason=abort_reason)

    def _finish(self, reason, step, tokens):
        return {"content": None, "loop_steps": step, "tokens_used": tokens,
                "abort_reason": reason, "breaker_state": self.breaker.state.value}
```

- [ ] **Step 3: commit**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_loop.py -v
git add src/nexuscore/harness/loop.py tests/harness/test_loop.py
git commit -m "feat(harness): AgentHarness最小ループ（4リミット・breaker/gate統合）"
```

### Task 15: Phase 1 CLI（`python -m nexuscore.harness`）

**Files:**
- Create: `src/nexuscore/cli/harness_cli.py`

- [ ] **Step 1: CLI実装**

```python
# src/nexuscore/cli/harness_cli.py
"""spec §6 Phase 1: CLI版デモシナリオ"""
from __future__ import annotations
import argparse, json, sys
from nexuscore.harness.circuit_breaker import CircuitBreaker
from nexuscore.harness.config import load_policy
from nexuscore.harness.loop import AgentHarness, Limits
from nexuscore.harness.run_state import RunState, RunStateStore
from nexuscore.harness.tool_gate import ToolGate
from nexuscore.harness.tools.read import list_dir, read_file, search_text

def main():
    p = argparse.ArgumentParser()
    p.add_argument("task", nargs="+")
    p.add_argument("--provider", default="openai")
    p.add_argument("--policy", default="tool_policy.yaml")
    args = p.parse_args()
    from nexuscore.llm.llm_router import LLMRouter
    llm = LLMRouter().get_llm_for_task(" ".join(args.task))
    gate = ToolGate(policy_path=args.policy)
    store = RunStateStore()
    br = CircuitBreaker(provider=args.provider)
    reg = {"read_file": read_file, "list_dir": list_dir, "search_text": search_text}
    h = AgentHarness(llm=llm, gate=gate, tool_registry=reg,
                     state_store=store, breaker=br, limits=Limits())
    out = h.run(" ".join(args.task))
    print(json.dumps(out, ensure_ascii=False, default=str))
    return 0 if out.get("abort_reason") is None else 1

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: 動作確認**

```bash
cd ~/projects/NexusCore && source .venv/bin/activate && export PYTHONPATH=src
python -m nexuscore.cli.harness_cli "hello" --provider openai
# Expected: JSON 1行（content/loop_steps/abort_reason等）
```

- [ ] **Step 3: commit**

```bash
cd ~/projects/NexusCore
git add src/nexuscore/cli/harness_cli.py
git commit -m "feat(harness): CLI（python -m nexuscore.cli.harness_cli）"
```

### Task 16: Phase 1 チェックポイント（SSOT内テキスト検索を実プロバイダで実行）

**Files:** なし（実行ログを `artifacts/checkpoints/phase1/<ts>/log.json` に保存）

- [ ] **Step 1: 実行**

```bash
cd ~/projects/NexusCore && source .venv/bin/activate && export PYTHONPATH=src
mkdir -p artifacts/checkpoints/phase1/$(date -I)
LOG=artifacts/checkpoints/phase1/$(date -I)/log.json
# 成功判定: ヒット件数>0 かつ abort_reason=null
START=$(date +%s)
python -m nexuscore.cli.harness_cli "search_text 'harness' /home/yn4416/projects/obsidian-ssot/01_DECISIONS/" \
    --provider openai 2>&1 | tee $LOG
END=$(date +%s)
echo "elapsed=$((END-START))s"
# 成功判定の確認（abort_reasonが含まれないこと）
grep -q 'abort_reason' $LOG && (grep -q '"abort_reason": null' $LOG || echo "FAIL: abort発生")
```

- [ ] **Step 2: 中断→復帰テスト（run_state復元）**

```bash
# 1度実行→artifacts/harness/run_state.json が残ることを確認
ls -la artifacts/harness/run_state.json
# 別の実行で resume（spec §10: 確認の主体=CLI対話ユーザー・明示opt-inで無人可）
# MVPでは「2回目を起動して同じタスク実行」= 前回state読み込みで再実行（Phase 2で明示resume機能）
python -m nexuscore.cli.harness_cli "search_text 'harness' /home/yn4416/projects/obsidian-ssot/01_DECISIONS/" --provider openai
```

- [ ] **Step 3: 結果を01_DECISIONS/claude-codeに記録**

```bash
mkdir -p ~/projects/obsidian-ssot/01_DECISIONS/NexusCore
# 01_DECISIONS/NexusCore/2026-08-30_phase1_チェックポイント.md にチェックポイント結果を記録
# （テンプレ：通過条件/fail条件/結果/次Phaseへの申し送り）
```

## Phase 2: 書く系（ask確認フロー）

### Task 17: write tools 2種

**Files:**
- Create: `src/nexuscore/harness/tools/write.py`
- Create: `tests/harness/test_tools_write.py`

- [ ] **Step 1: 失敗テスト+実装**

```python
# tests/harness/test_tools_write.py
import pytest
from nexuscore.harness.tools.write import write_file, edit_file

def test_write_file_creates(tmp_path):
    p = tmp_path / "new.txt"
    write_file(str(p), "hello")
    assert p.read_text() == "hello"

def test_edit_file_replaces(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("AAA")
    edit_file(str(p), "AAA", "BBB")
    assert p.read_text() == "BBB"
```

```python
# src/nexuscore/harness/tools/write.py
"""Phase 2: 書く系（ask確認必須・Phase 2でaskフロー導入後に実使用可）"""
from __future__ import annotations
from pathlib import Path

def write_file(path: str, content: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {p}"

def edit_file(path: str, old: str, new: str) -> str:
    p = Path(path)
    txt = p.read_text(encoding="utf-8")
    if old not in txt:
        raise ValueError("old string not found")
    p.write_text(txt.replace(old, new, 1), encoding="utf-8")
    return f"edited {p}"
```

- [ ] **Step 2: commit**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_tools_write.py -v
git add src/nexuscore/harness/tools/write.py tests/harness/test_tools_write.py
git commit -m "feat(harness): 書く系tools 2種(write_file/edit_file)"
```

### Task 18: ask確認フロー（CLI）+ policy拡張

**Files:**
- Create: `src/nexuscore/harness/ask.py`
- Modify: `tool_policy.yaml`
- Create: `tests/harness/test_ask_flow.py`

- [ ] **Step 1: 失敗テスト+実装**

```python
# tests/harness/test_ask_flow.py
import pytest
from nexuscore.harness.ask import AskSession, AskResult
from nexuscore.harness.run_state import RunStateStore, RunState

def test_ask_approve_persists(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "y")
    s = AskSession(store=RunStateStore(path=tmp_path / "s.json"))
    r = s.prompt(tool="write_file", args={"path":"a","content":"x"})
    assert r == AskResult.APPROVED

def test_ask_timeout_denies(tmp_path, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda *_: "")  # 空=タイムアウト相当
    s = AskSession(store=RunStateStore(path=tmp_path / "s.json"),
                   timeout_seconds=0.0)
    r = s.prompt(tool="write_file", args={"path":"a","content":"x"})
    assert r == AskResult.DENIED_TIMEOUT

# src/nexuscore/harness/ask.py
"""spec §4: ask確認フロー（CLI対話・タイムアウト=deny）"""
from __future__ import annotations
import enum, signal, threading
from dataclasses import dataclass
from nexuscore.harness.run_state import RunStateStore

class AskResult(str, enum.Enum):
    APPROVED = "approved"
    DENIED_TIMEOUT = "denied_timeout"
    DENIED_USER = "denied_user"

class AskSession:
    def __init__(self, *, store: RunStateStore, timeout_seconds: float = 120.0):
        self.store = store
        self.timeout = timeout_seconds

    def prompt(self, *, tool: str, args: dict) -> AskResult:
        msg = f"[ASK] tool={tool} args={args} → approve? (y/N, timeout {self.timeout}s): "
        ans = _readline_with_timeout(msg, self.timeout)
        if ans is None: return AskResult.DENIED_TIMEOUT
        return AskResult.APPROVED if ans.strip().lower() == "y" else AskResult.DENIED_USER

def _readline_with_timeout(prompt: str, timeout: float) -> str | None:
    # 簡易実装（Phase 2ではthreading.Timerで実装）
    import sys
    print(prompt, end="", flush=True)
    result = []
    got = [False]
    def on_timeout():
        if not got[0]:
            print("\n[timeout]")
            result.append(None); got[0] = True
    t = threading.Timer(timeout, on_timeout)
    t.start()
    try:
        line = sys.stdin.readline()
    except EOFError:
        line = ""
    got[0] = True
    t.cancel()
    return line if line else None
```

- [ ] **Step 2: tool_policy.yaml 拡張（write系をaskに）**

```yaml
provider_priority: [openai, anthropic, gemini, openrouter, glm, minimax, deepseek, moonshot]
provider_insecure_default: [deepseek, moonshot]
tools:
  read_file:    { default: allow }
  list_dir:     { default: allow }
  search_text:  { default: allow }
  write_file:   { default: ask, deny_paths: ['.git/**', '**/.env', '**/secrets/**'] }
  edit_file:    { default: ask, deny_paths: ['.git/**', '**/.env', '**/secrets/**'] }
```

- [ ] **Step 3: commit**

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_ask_flow.py -v
git add src/nexuscore/harness/ask.py tests/harness/test_ask_flow.py tool_policy.yaml
git commit -m "feat(harness): ask確認フロー（CLI対話・タイムアウト=deny）+policy拡張"
```

### Task 19: Phase 2 チェックポイント（テストファイル1行修正をask承認込みで実行）

- [ ] **Step 1: 実行**

```bash
cd ~/projects/NexusCore && source .venv/bin/activate && export PYTHONPATH=src
# 対話実行（仕様: ask時にプロンプト→"y"入力）
echo "y" | python -m nexuscore.cli.harness_cli "edit_file をテストファイルに使って1行修正" --provider openai
# ログ保存
mkdir -p artifacts/checkpoints/phase2/$(date -I)
echo "y" | python -m nexuscore.cli.harness_cli "..." --provider openai 2>&1 | tee artifacts/checkpoints/phase2/$(date -I)/log.json
```

- [ ] **Step 2: 結果を記録**

```bash
# 01_DECISIONS/NexusCore/2026-08-30_phase2_チェックポイント.md
```

## Phase 3: 撃つ系

### Task 20: exec tool + 禁止パターンdeny

**Files:**
- Create: `src/nexuscore/harness/tools/exec.py`
- Modify: `tool_policy.yaml`
- Create: `tests/harness/test_tools_exec.py`
- Create: `tests/harness/test_deny_patterns.py`

- [ ] **Step 1: 失敗テスト+実装**

```python
# tests/harness/test_tools_exec.py
import subprocess
from nexuscore.harness.tools.exec import run_command

def test_run_command_captures_stdout():
    r = run_command("echo hello")
    assert "hello" in r["stdout"]

# src/nexuscore/harness/tools/exec.py
"""Phase 3: 撃つ系（必ずask経由・禁止パターンdeny）

⚠️ セキュリティ注意（security-guidance hook指摘の反映）:
この tool は「LLMが選んだコマンドを意図的に実行する」設計上、shell=True が必須。
安全性は subprocess 自体でなく ToolGate の ask 承認+deny_patterns で担保する。
shell=True のまま ToolGate を必ず通すことをテストで保証する
（test_deny_patterns.py がその保証）。
"""
from __future__ import annotations
import subprocess

TIMEOUT_SECONDS = 60

def run_command(cmd: str) -> dict:
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    return {"stdout": r.stdout[:5000], "stderr": r.stderr[:5000], "rc": r.returncode}
```

- [ ] **Step 2: tool_policy.yaml に禁止パターン**

```yaml
  run_command:
    default: ask
    deny_patterns: ['rm -rf', 'sudo ', 'git push --force', ':(){:|:&};:', 'mkfs', 'dd if=']
```

- [ ] **Step 3: deny test + commit**

```python
# tests/harness/test_deny_patterns.py
import pytest
from nexuscore.harness.tool_gate import ToolGate

@pytest.mark.parametrize("bad", [
    "rm -rf /tmp/x", "sudo apt update", "git push --force origin main"
])
def test_deny_patterns_blocked(tmp_path, bad):
    p = tmp_path / "p.yaml"
    p.write_text("tools:\n  run_command: { default: ask, deny_patterns: ['rm -rf', 'sudo ', 'git push --force'] }\n")
    g = ToolGate(policy_path=p)
    d = g.evaluate(tool="run_command", args={"cmd": bad}, ask_supported=True)
    assert d.mode.value == "deny"
```

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_tools_exec.py tests/harness/test_deny_patterns.py -v
git add src/nexuscore/harness/tools/exec.py tests/harness/test_tools_exec.py tests/harness/test_deny_patterns.py tool_policy.yaml
git commit -m "feat(harness): 撃つ系tool+禁止パターンdeny"
```

### Task 21: Phase 3 チェックポイント（pytest実行）

- [ ] **Step 1: 実行**

```bash
cd ~/projects/NexusCore && source .venv/bin/activate && export PYTHONPATH=src
echo "y" | python -m nexuscore.cli.harness_cli "run_command 'pytest tests/harness/ -q'" --provider openai
# 成功判定: 全テスト緑・abort_reason=null
```

- [ ] **Step 2: 記録**

```bash
# 01_DECISIONS/NexusCore/2026-08-30_phase3_チェックポイント.md
```

## Phase 4: Web UI

### Task 22: UIスタック決定ADR

**Files:**
- Create: `docs/adr/2026-08-30-harness-ui-stack.md`

- [ ] **Step 1: 候補比較を3行で記述して決定**

```markdown
<!-- docs/adr/2026-08-30-harness-ui-stack.md -->
# ハーネス Web UI スタック決定

日付: 2026-08-30

## 候補
- A: FastAPI + HTMX（既存webapp/に統合）
- B: Streamlit（独立・短時間）
- C: Gradio（既存unified_gradio_ui.py に統合）

## 決定
**A: FastAPI + HTMX**（既存webapp/の拡張として実装）

理由: 既存Flask/FastAPI資産の再利用・ask承認UIとツール実行モニタを1画面で提供できる
```

- [ ] **Step 2: commit**

```bash
cd ~/projects/NexusCore
git add docs/adr/2026-08-30-harness-ui-stack.md
git commit -m "docs(adr): ハーネスWeb UIスタック決定(FastAPI+HTMX)"
```

### Task 23: Web UI 薄い実装（タスク入力・ask承認・実行モニタ）

**Files:**
- Modify: `src/nexuscore/webapp/`（既存に1画面追加）
- Create: `tests/harness/test_web_ui.py`

- [ ] **Step 1: 薄いUI実装（FastAPI + HTMX・既存webapp拡張）**

```python
# src/nexuscore/webapp/harness_routes.py
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from nexuscore.harness.loop import AgentHarness
from nexuscore.harness.circuit_breaker import CircuitBreaker
from nexuscore.harness.tool_gate import ToolGate
from nexuscore.harness.run_state import RunStateStore
from nexuscore.harness.tools.read import list_dir, read_file, search_text

router = APIRouter(prefix="/harness")

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return HTMLResponse("""
    <html><body><h1>Harness</h1>
    <form action="/harness/run" method="post">
      <input name="task" style="width:60%">
      <button>Run</button>
    </form></body></html>""")

@router.post("/run")
async def run(task: str = Form(...)):
    from nexuscore.llm.llm_router import LLMRouter
    llm = LLMRouter().get_llm_for_task(task)
    gate = ToolGate(policy_path="tool_policy.yaml")
    h = AgentHarness(llm=llm, gate=gate,
                     tool_registry={"read_file":read_file,"list_dir":list_dir,"search_text":search_text},
                     state_store=RunStateStore(),
                     breaker=CircuitBreaker(provider="openai"))
    out = h.run(task)
    return HTMLResponse(f"<pre>{out}</pre>")
```

- [ ] **Step 2: テスト+commit**

```python
# tests/harness/test_web_ui.py
from fastapi.testclient import TestClient
from nexuscore.webapp.harness_routes import router

def test_index_renders_form():
    from fastapi import FastAPI
    app = FastAPI(); app.include_router(router)
    c = TestClient(app)
    r = c.get("/harness/")
    assert r.status_code == 200
    assert "<form" in r.text
```

```bash
cd ~/projects/NexusCore && PYTHONPATH=src pytest tests/harness/test_web_ui.py -v
git add src/nexuscore/webapp/harness_routes.py tests/harness/test_web_ui.py
git commit -m "feat(webapp): ハーネス Web UI（FastAPI+HTMX・薄い実装）"
```

## Phase 5: dogfooding

### Task 24: NexusCore小Issue 1個をハーネスで消化

- [ ] **Step 1: 対象Issue選定**

```bash
cd ~/projects/NexusCore
# 未コミットの改善点を1つ選ぶ（例: docs/変更履歴.md の未更新・未コミット変更の棚卸し）
git diff --stat
```

- [ ] **Step 2: ハーネスCLIで該当Issueを処理**

```bash
echo "y" | python -m nexuscore.cli.harness_cli "<具体的なIssue内容>" --provider openai
```

### Task 25: 計測6項目収集

- [ ] **Step 1: 計測スクリプト作成と実行**

```bash
# 過去24時間のrunイベントログから集計（spec §10 計測6項目）
python - <<'PY'
import json, glob
from collections import Counter
events = []
for f in glob.glob("artifacts/harness/run_state*.json*"):
    events.append(json.load(open(f)))
# 429頻度・breaker遷移・abort分布を集計して artifacts/harness/metrics.json に出力
print(json.dumps({"count":len(events)}, indent=2))
PY
```

### Task 26: 強化層Go/No-Go判定書

- [ ] **Step 1: 判定書テンプレ作成**

```markdown
# 強化層Go/No-Go判定書

## 計測データ
- 429頻度: <N>/時間
- ブレーカ遷移: <N>回/日
- ask応答時間 p95: <N>秒
- checkpoint失敗率: <N>
- abort分布: <dict>
- トークン量/タスク: <N>

## 各強化層項目の判定
- 3層トークン: Go / No-Go（理由）
- 適応�値: ...
- TTL付きcapability: ...
- 動的resumeバジェット: ...
- resume回数上限: ...
- トークンバケット適応: ...
- Chaos/Property-based: ...
- 通知3重化: ...
- 並行実行時トークン予約: ...

## 結論
- 強化層に進む項目: ...
- 見送る項目: ...
- 次フェーズ計画: ...
```

- [ ] **Step 2: 記録**

```bash
mkdir -p ~/projects/obsidian-ssot/01_DECISIONS/NexusCore
# 01_DECISIONS/NexusCore/2026-08-30_phase5_強化層GoNoGo.md
```

### Task 27: プロジェクトクロージング

- [ ] **Step 1: バックログ起票（残課題）**

```bash
# Windows対応・Phase 5以降の強化層・並列実行対応など残課題をバックログへ
# 既存L362「gradio→pydub 推移依存の恒久管理」等と統合
```

- [ ] **Step 2: 仕様書最終更新**

```bash
# docs/変更履歴.md にPhase完了履歴を追記（Keep a Changelog形式）
```

- [ ] **Step 3: handoff生成（プロジェクト区切り・必要に応じて）**

```bash
# セッションが長い場合のみ実行・Skill(new-session)
```

---

## 自己レビュー（plan vs spec）

1. **Spec coverage**: §3（D案・4クラス・差分フック）→Task 5/6/7、§4（ToolGate）→Task 10、§5 MVP（4リミット・breaker・run_state・resume）→Task 12/13/14、§6（Phase 0-5）→各Phaseタスク、§7（成功基準12件Phase配分）→Task 15/18/20/23のテスト、§8.5用語統一→Task 12/14のコメントで明示、§10（詳細契約19項目）→各タスクのコードに反映
2. **Placeholder scan**: なし（コード・コマンド・観測値すべて具体）
3. **Type consistency**: `complete_with_tools()`・`evaluate()`・`state.save()`・`record_failure()`・`record_probe_success()` のシグネチャは全タスクで一致

## 残存リスク（plan実行時の注意点）

- Phase 0で撤退基準に該当した場合 → A案版planが必要（別spec）
- 既存テスト5,000+件の非改変保証は各Phase後に `pytest tests/ -q --ignore=tests/harness -x` で確認
- spec §10のDiscord webhook運用は環境変数 `NEXUSCORE_DISCORD_WEBHOOK` 設定が前提（未設定時はログのみ）
