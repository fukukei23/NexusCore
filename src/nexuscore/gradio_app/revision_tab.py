# ==============================================================================
# ファイル名: revision_tab.py
# レジストリ: src/nexuscore/gradio_app/
# 日付: 2025-09-07
# バージョン: 2.6 (GLM/MiniMax移行版)
#
# 概要:
#  - auto_revision_runner.py が import する関数群を提供（互換重視）。
#  - 旧来のテキスト履歴(save_patch_history)は維持しつつ、JSONも併記保存。
#  - run_pytest は (bool, str) を返す（Runner 側のラッパでも両対応にしているが本体も新式）。
#  - 単体でもタブUIとして動かせる最小UIを同梱（任意）。
# ==============================================================================

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from pathlib import Path

import gradio as gr

from nexuscore.gradio_app.llm_helper import call_llm_messages

logger = logging.getLogger(__name__)

# ---------- パス ----------
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[3]
SRC_ROOT = HERE.parents[2]

# サンドボックス候補
CANDIDATES = [SRC_ROOT / "sandbox_output", PROJECT_ROOT / "sandbox_output"]
for c in CANDIDATES:
    if c.exists():
        SANDBOX_DIR = c
        break
else:
    SANDBOX_DIR = SRC_ROOT / "sandbox_output"

SAMPLE_FILE = str(SANDBOX_DIR / "sample.py")
TEST_FILE = str(SANDBOX_DIR / "test_sample.py")
RESULT_LOG = str(SANDBOX_DIR / "test_result.log")

# 旧テキスト履歴（互換）
HISTORY_TXT = str(SANDBOX_DIR / "patch_history.txt")

# タイムライン用 JSON はプロジェクト直下（Runner と一致）
PATCH_HISTORY_DIR = PROJECT_ROOT / "patch_history"
os.makedirs(PATCH_HISTORY_DIR, exist_ok=True)


# ---------- LLM 呼び出し（llm_helper 経由） ----------


# ---------- 互換ユーティリティ ----------
def _now_tag() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d_%H%M%S")


def read_file(file_path: str) -> str:
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except Exception:
        return ""


def save_file(file_path: str, content: str):
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    Path(file_path).write_text(content, encoding="utf-8")


# 旧仕様: テキスト履歴に追記（Runner 互換のため関数名は固定）
def save_patch_history(code: str, reason: str, prompt: str):
    Path(HISTORY_TXT).parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_TXT, "a", encoding="utf-8") as f:
        f.write("\n=== 新しい修正案 ===\n")
        f.write("[📝 修正理由]:\n" + (reason or "") + "\n")
        f.write("[📤 GPTプロンプト]:\n" + (prompt or "") + "\n")
        f.write("[💻 修正コード]:\n" + (code or "") + "\n")


# 新仕様: タイムライン JSON を保存（Runner 側も自身で保存するが、ここでも呼べる）
def save_patch_history_json(code: str, reason: str, prompt: str) -> str:
    ts = _now_tag()
    data = {
        "timestamp": ts,
        "status": "manual_save",
        "reason": reason or "",
        "prompt": prompt or "",
        "llm_prompt": prompt or "",
        "code": code or "",
        "full_code_after": code or "",
        "code_diff": "",  # 差分が欲しければ Runner 側で作る想定
        "test_log": read_file(RESULT_LOG),
    }
    out = PATCH_HISTORY_DIR / f"patch_{ts}.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out)


# ---------- pytest 実行 ----------
def run_pytest() -> tuple[bool, str]:
    """
    新式: (ok, output) を返す。
    互換: Runner 側は古い実装（文字列のみ）にも耐えるラッパを持つ。
    """
    try:
        result = subprocess.run(
            ["pytest", TEST_FILE],
            capture_output=True,
            text=True,
            cwd=str(SANDBOX_DIR),
        )
        output = result.stdout + ("\n" + result.stderr if result.stderr else "")
        # 保存（Timeline JSON が拾う）
        save_file(RESULT_LOG, output)
        ok = (result.returncode == 0) and ("failed" not in output.lower())
        return ok, output
    except Exception as e:
        output = f"❌ pytest 実行エラー: {e}"
        save_file(RESULT_LOG, output)
        return False, output


# ---------- プロンプト生成 ----------
def generate_prompt(
    sample_path: str, test_path: str, summary: str, history: str, error_log: str, user_note: str
) -> str:
    sample_code = read_file(sample_path)
    test_code = read_file(test_path)
    return f"""# Context
以下は Python 関数（sample.py）と対応するテスト（test_sample.py）です。

# sample.py
{sample_code}

# test_sample.py
{test_code}

# ユーザーの目的
{user_note}

# バージョン要約（最新版）
{summary}

# 修正履歴（直近）
{history}

# テスト結果
{error_log}

# 指示
上記情報を踏まえて、ユーザーが意図した動作を達成できるように `sample.py` の修正コードを提案してください。

- コードのみを返してください
- 余計な説明文、Markdown記法、```python や ``` は不要です
- すべてのコードは sample.py に直接書き込める内容にしてください
- コメントは歓迎します
- 差分ではなく、完全な最新コードを提示してください
"""


# ---------- LLM応答の抽出 ----------
def extract_code_and_reason(response: str) -> tuple[str, str]:
    """
    - JSON形式 {"code": "...", "reason": "..."} を優先
    - それ以外は ```...``` の fenced code から抽出、残りを理由扱い
    """
    try:
        data = json.loads(response)
        return data.get("code", "").strip(), data.get("reason", "").strip()
    except Exception:
        pass
    m = re.search(r"```(?:python)?\n(.*?)```", response, re.DOTALL)
    code = m.group(1).strip() if m else ""
    # コードを除いた残りを理由として扱う簡易フォールバック
    reason = re.sub(r"```(?:python)?\n.*?```", "", response, flags=re.DOTALL).strip()
    if not reason:
        reason = "（理由を抽出できませんでした）"
    return code, reason


# ---------- LLM 呼び出し（安全フォールバック付き） ----------
def call_gpt(prompt: str) -> str:
    """
    - MINIMAX_API_KEY があれば MiniMax API を使う
    - 無ければ簡易フォールバックの修正案を返す（is_prime の 2 対応など）
    """
    try:
        return call_llm_messages([{"role": "user", "content": prompt}], temperature=0.2)
    except Exception:
            # API失敗時はフォールバック
            logger.warning("MiniMax API failed, using fallback", exc_info=True)

    # フォールバック出力（is_prime の典型修正）
    fallback_code = """def is_prime(n):
    if n < 2:
        return False
    if n in (2, 3):
        return True
    if n % 2 == 0:
        return False
    i = 3
    while i * i <= n:
        if n % i == 0:
            return False
        i += 2
    return True
"""
    return json.dumps(
        {"code": fallback_code, "reason": "Handle n=2 and even numbers; standard primality check."}
    )


# ---------- 最小タブ UI（任意で利用可） ----------
def tab_revision() -> gr.Blocks:
    with gr.Blocks() as tab:
        gr.Markdown("## 🔁 Auto Revision（最小デモ）")
        code_input = gr.Code(
            label="📝 対象コード (sample.py)", language="python", value=read_file(SAMPLE_FILE)
        )
        user_instruction = gr.Textbox(
            label="💡 補足/指示", placeholder="例: 2 を素数として扱って", lines=2
        )
        test_failures = gr.Textbox(label="❌ 失敗ログ", value=read_file(RESULT_LOG), lines=6)

        generated_code = gr.Code(label="✅ 生成コード", language="python")
        explanation = gr.Textbox(label="📄 修正理由", lines=4)
        test_result = gr.Textbox(label="🧪 pytest 結果", lines=12)
        last_json_path = gr.Textbox(label="🗂 JSON履歴ファイル", interactive=False)

        def do_generate(user_code: str, note: str, fail_log: str):
            save_file(SAMPLE_FILE, user_code)
            prompt = generate_prompt(SAMPLE_FILE, TEST_FILE, "現行", "—", fail_log, note)
            gpt_response = call_gpt(prompt)
            code, reason = extract_code_and_reason(gpt_response)
            return code, reason, prompt

        def do_apply(code: str, reason: str, prompt: str):
            save_file(SAMPLE_FILE, code)
            save_patch_history(code, reason, prompt)  # 旧テキスト
            ok, out = run_pytest()  # (bool, str)
            json_path = save_patch_history_json(code, reason, prompt)  # 新JSON
            return out, json_path

        revise_btn = gr.Button("🔁 修正案を生成")
        apply_btn = gr.Button("✅ 修正案を適用してテスト")

        revise_btn.click(
            do_generate,
            [code_input, user_instruction, test_failures],
            [generated_code, explanation, user_instruction],
        )
        apply_btn.click(
            do_apply, [generated_code, explanation, user_instruction], [test_result, last_json_path]
        )
    return tab
