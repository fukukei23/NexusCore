# ==============================================================================
# ファイル名: policy_console.py
# レジストリ: src/nexuscore/gradio_app/
# 日付: 2025-09-08
# バージョン: 1.0 (Enterprise Policy Console)
#
# 概要:
#  - 企業ごとの「憲法（安全・準拠ポリシー）」をGUIで作成・保存・読み込み
#  - テンプレ(金融/医療/教育/一般)からの生成
#  - ConstitutionalCouncilAgent による即席チェック (モックにフォールバック)
#  - ルールJSONは policies/{profile}.json に保存
#
# 使い方:
#   (.venv) PS C:\...\NexusCore> python -m src.nexuscore.gradio_app.policy_console
#   ブラウザで http://127.0.0.1:7863/ を開く
# ==============================================================================

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr

# --- パス設定 ---------------------------------------------------------------
HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[3]
POLICY_DIR = PROJECT_ROOT / "policies"
POLICY_DIR.mkdir(parents=True, exist_ok=True)

# --- ConstitutionalCouncilAgent を試しに import。失敗すればモック ----------
USE_MOCK = False
CouncilCls = None
try:
    # 例: src/constitutional_council_agent.py の想定
    from constitutional_council_agent import ConstitutionalCouncilAgent as _Agent  # type: ignore

    CouncilCls = _Agent
except Exception:
    USE_MOCK = True


# --- テンプレ定義 -----------------------------------------------------------
def _base_template(name: str, sector: str) -> dict[str, Any]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "profile_name": name,
        "sector": sector,
        "version": "1.0",
        "updated_at": now,
        "owner": "security@your-org.example.com",
        "rules": [],
        "enforcement": {
            "mask_pii": True,
            "block_disallowed": True,
            "severity_threshold": "medium",  # low/medium/high
        },
        "guidance": {
            "on_violation": "違反箇所を説明し、安全な代替表現を出力。必要に応じてマスキング。",
            "disclaimer": "",
        },
    }


def template_finance(name="enterprise_finance") -> dict[str, Any]:
    t = _base_template(name, "finance")
    t["rules"] = [
        {"id": "PII", "desc": "個人特定情報(氏名・住所・電話・口座)の露出禁止", "severity": "high"},
        {
            "id": "ACCOUNT",
            "desc": "銀行口座/カード番号の取扱い禁止または必須マスキング",
            "severity": "high",
        },
        {
            "id": "ADVICE",
            "desc": "特定銘柄の推奨/断定的助言の禁止。一般的情報提供に留める",
            "severity": "medium",
        },
        {"id": "INSIDER", "desc": "未公開情報・内部情報の共有禁止", "severity": "high"},
    ]
    t["guidance"][
        "disclaimer"
    ] = "本出力は一般的情報であり、投資助言ではありません。最終判断は自己責任です。"
    return t


def template_healthcare(name="enterprise_healthcare") -> dict[str, Any]:
    t = _base_template(name, "healthcare")
    t["rules"] = [
        {"id": "PII", "desc": "患者の個人情報・受診情報を匿名化(必須)", "severity": "high"},
        {
            "id": "DIAGNOSIS",
            "desc": "診断の断定・処方指示の禁止。一般的注意喚起のみ",
            "severity": "high",
        },
        {"id": "EMERGENCY", "desc": "緊急時は直ちに医療機関へ誘導", "severity": "medium"},
        {"id": "SENSITIVE", "desc": "健康・遺伝情報等の取り扱い注意", "severity": "high"},
    ]
    t["guidance"][
        "disclaimer"
    ] = "本出力は医療アドバイスではありません。緊急時は医療機関へ連絡してください。"
    return t


def template_education(name="enterprise_education") -> dict[str, Any]:
    t = _base_template(name, "education")
    t["rules"] = [
        {"id": "MINOR", "desc": "児童・学生の個人情報・成績・評価の秘匿", "severity": "high"},
        {"id": "HARASS", "desc": "差別・ハラスメントに該当する表現禁止", "severity": "high"},
        {"id": "COPYRIGHT", "desc": "著作権侵害(課題の丸写し等)の支援禁止", "severity": "medium"},
    ]
    t["guidance"]["disclaimer"] = "学習支援用途です。提出物は本人のオリジナルで作成してください。"
    return t


def template_general(name="enterprise_general") -> dict[str, Any]:
    t = _base_template(name, "general")
    t["rules"] = [
        {"id": "PII", "desc": "PII(個人特定情報)の露出禁止/マスキング", "severity": "high"},
        {"id": "DEFAM", "desc": "誹謗中傷・差別・ハラスメント表現の禁止", "severity": "high"},
        {"id": "SAFETY", "desc": "危険行為の助長/手順提供の禁止", "severity": "high"},
    ]
    return t


TEMPLATES: dict[str, Any] = {
    "finance": template_finance,
    "healthcare": template_healthcare,
    "education": template_education,
    "general": template_general,
}


def render_template_profile(name: str, template_key: str = "general") -> tuple[str, str]:
    """
    Returns a tuple of (json_text, status_message) for the requested template.
    Raises ValueError when name is empty so UI側で明示エラーにできる。
    """
    if not name:
        raise ValueError("プロファイル名を入力してください")
    tmpl_fn = TEMPLATES.get(template_key, template_general)
    obj = tmpl_fn(name=name)
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    msg = f"テンプレ '{template_key}' から作成。まだ保存していません。"
    return text, msg


# --- ストレージ操作 ---------------------------------------------------------
def list_profiles() -> list[str]:
    return sorted([p.stem for p in POLICY_DIR.glob("*.json")])


def load_profile(name: str) -> str:
    path = POLICY_DIR / f"{name}.json"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def save_profile(name: str, json_text: str) -> tuple[bool, str]:
    try:
        obj = json.loads(json_text)
    except Exception as e:
        return False, f"JSONとして読み取れません: {e}"
    path = POLICY_DIR / f"{name}.json"
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return True, f"保存しました: {path}"


def delete_profile(name: str) -> str:
    path = POLICY_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
        return f"削除しました: {path}"
    return "対象が見つかりません"


# --- モック評価器 -----------------------------------------------------------
def _mock_evaluate(rules: dict[str, Any], text: str) -> dict[str, Any]:
    violations = []
    # 簡易PII
    if re.search(r"\b\d{10,16}\b", text) or re.search(r"(住所|電話|口座|クレジット)", text):
        violations.append({"rule_id": "PII", "severity": "high", "evidence": "PIIらしき数値/語句"})
    # 医療
    if re.search(r"(診断|処方|薬を飲み|この薬|確実に治る)", text):
        violations.append(
            {"rule_id": "DIAGNOSIS", "severity": "high", "evidence": "医療助言の断定"}
        )
    # 金融
    if re.search(r"(この株.*必ず上がる|絶対に儲かる)", text):
        violations.append({"rule_id": "ADVICE", "severity": "medium", "evidence": "断定的投資助言"})

    guidance = text
    if any(v["rule_id"] == "PII" for v in violations):
        guidance = re.sub(r"\b(\d{10,16})\b", "[MASKED]", guidance)
        guidance = re.sub(r"(住所|電話|口座|クレジット)", "[REDACTED]", guidance)

    return {
        "ok": len(violations) == 0,
        "violations": violations,
        "redacted_suggestion": guidance,
    }


# --- エンジン初期化 ---------------------------------------------------------
def _init_engine(policy_json: str):
    if USE_MOCK or CouncilCls is None:
        return "mock", None
    try:
        obj = json.loads(policy_json)
        engine = CouncilCls(obj)  # type: ignore
        return "real", engine
    except Exception:
        return "mock", None


# --- 評価ロジック -----------------------------------------------------------
def evaluate_text(policy_json: str, text: str) -> tuple[str, list[list[Any]], str]:
    """
    returns:
      status_msg, violations_table, suggestion_text
    """
    mode, engine = _init_engine(policy_json)
    try:
        if mode == "real" and engine is not None:
            # 想定: engine.evaluate(text) -> {"ok": bool, "violations": [...], "redacted_suggestion": "..."}
            result = engine.evaluate(text)  # type: ignore
        else:
            # モック
            result = _mock_evaluate(json.loads(policy_json), text)
    except Exception as e:
        return f"評価中にエラー: {e}", [], ""

    vrows = []
    for v in result.get("violations", []):
        vrows.append([v.get("rule_id", ""), v.get("severity", ""), v.get("evidence", "")])

    status = "✅ 準拠 (違反なし)" if result.get("ok", False) else f"❌ 違反 {len(vrows)} 件"
    return status, vrows, result.get("redacted_suggestion", "")


# --- UI 構築 ---------------------------------------------------------------
def build_ui():
    with gr.Blocks(title="Enterprise Policy Console", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🛡️ Enterprise Policy Console — 憲法エージェント設定")
        gr.Markdown("各社ポリシーをGUIで編集し、テスト文を即時チェックできます。")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### プロファイル")
                profile_list = gr.Dropdown(
                    choices=list_profiles(), label="既存プロファイル", value=None
                )
                new_name = gr.Textbox(
                    label="新規/名前を付けて保存", placeholder="my_enterprise_policy"
                )
                tmpl = gr.Radio(
                    choices=["finance", "healthcare", "education", "general"],
                    value="general",
                    label="テンプレート",
                )

                btn_new_from_tmpl = gr.Button("テンプレから新規作成")
                btn_load = gr.Button("読込")
                btn_save = gr.Button("保存")
                btn_delete = gr.Button("削除")
                profile_msg = gr.Markdown("")

                gr.Markdown("### ルールJSON")
                policy_json = gr.Code(
                    label="policy.json",
                    language="json",
                    lines=22,
                    value=json.dumps(template_general(), ensure_ascii=False, indent=2),
                )

            with gr.Column(scale=1):
                gr.Markdown("### テストベッド")
                test_input = gr.Textbox(
                    label="評価したいテキスト",
                    lines=8,
                    placeholder="ここに社内想定の入力やモデル出力を貼る",
                )
                btn_eval = gr.Button("このポリシーで評価")
                status_out = gr.Markdown("—")
                violations = gr.Dataframe(
                    headers=["RuleID", "Severity", "Evidence"],
                    datatype=["str", "str", "str"],
                    row_count=(0, "dynamic"),
                )
                redacted = gr.Textbox(label="安全な代替案（自動サジェスト）", lines=8)

        # --- コールバック定義 ---
        def _reload_profiles():
            return gr.update(choices=list_profiles())

        def _new_from_template(name: str, template_key: str):
            if not name:
                return gr.update(), gr.update(value="プロファイル名を入力してください")
            try:
                text, msg = render_template_profile(name, template_key)
            except ValueError as exc:
                return gr.update(), gr.update(value=str(exc)), gr.update(), gr.update()
            return (
                gr.update(value=text),
                gr.update(value=msg),
                gr.update(choices=list_profiles()),
                gr.update(value=name),
            )

        def _load(name: str | None):
            if not name:
                return gr.update(), "プロファイル名を選択してください"
            text = load_profile(name)
            if not text:
                return gr.update(), f"見つかりません: {name}"
            return gr.update(value=text), f"読込完了: {name}.json"

        def _save(name: str, text: str):
            if not name:
                return gr.update(), "保存名を入力してください"
            ok, msg = save_profile(name, text)
            return (
                (
                    gr.update(value=text),
                    msg,
                    gr.update(choices=list_profiles()),
                    gr.update(value=name),
                )
                if ok
                else (gr.update(), msg, gr.update(), gr.update())
            )

        def _delete(name: str | None):
            if not name:
                return "削除対象を選択してください", gr.update(choices=list_profiles())
            msg = delete_profile(name)
            return msg, gr.update(choices=list_profiles())

        def _evaluate(text_json: str, t: str):
            return evaluate_text(text_json, t)

        # --- イベント配線 ---
        btn_new_from_tmpl.click(
            _new_from_template,
            inputs=[new_name, tmpl],
            outputs=[policy_json, profile_msg, profile_list, profile_list],
        )
        btn_load.click(_load, inputs=[profile_list], outputs=[policy_json, profile_msg])
        btn_save.click(
            _save,
            inputs=[new_name, policy_json],
            outputs=[policy_json, profile_msg, profile_list, profile_list],
        )
        btn_delete.click(_delete, inputs=[profile_list], outputs=[profile_msg, profile_list])

        btn_eval.click(
            _evaluate, inputs=[policy_json, test_input], outputs=[status_out, violations, redacted]
        )

        # 起動時にドロップダウンを更新
        demo.load(lambda: gr.update(choices=list_profiles()), outputs=[profile_list])

    return demo


def launch_ui():
    demo = build_ui()
    # デフォルト7863。埋まっていたらGradioが自動案内
    demo.queue().launch(server_name="127.0.0.1", server_port=7863, share=False)


if __name__ == "__main__":
    launch_ui()
