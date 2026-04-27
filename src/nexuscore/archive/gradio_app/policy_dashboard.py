# ==============================================================================
# ファイル名: policy_dashboard.py
# レジストリ: src/nexuscore/gradio_app/
# 日付: 2025-09-08
# バージョン: 1.0 (Enterprise Policy UI)
#
# 概要:
#   - 企業ごとに「憲法（ポリシー）」を GUI で編集/検証/保存するダッシュボード
#   - タブ: ①基本/メタ ②禁止事項/レッドライン ③PII/データ取扱 ④出力ルール ⑤モデル/温度
#           ⑥検証ツール ⑦エクスポート
#   - constitution.json を PROJECT_ROOT/policies に保存（既存Agentから読み込みしやすい形）
#
# 使い方:
#   (.venv) PS C:\...\NexusCore> python -m src.nexuscore.gradio_app.policy_dashboard
# ==============================================================================

from __future__ import annotations

import json
import typing as t
from datetime import datetime
from pathlib import Path

import gradio as gr

HERE = Path(__file__).resolve()
PROJECT_ROOT = HERE.parents[3]
POLICY_DIR = PROJECT_ROOT / "policies"
POLICY_DIR.mkdir(parents=True, exist_ok=True)
POLICY_FILE = POLICY_DIR / "constitution.json"

# ---- 既存 ConstitutionalCouncilAgent があれば使う（任意） --------------------
# なくても動作するよう try/except で囲みます。
AGENT_AVAILABLE = False
try:
    # 例: from nexuscore.agents.constitutional_council_agent import ConstitutionalCouncilAgent
    from ..agents.constitutional_council_agent import ConstitutionalCouncilAgent

    AGENT_AVAILABLE = True
except Exception:
    ConstitutionalCouncilAgent = None  # type: ignore


def _load_policy() -> dict:
    if POLICY_FILE.exists():
        try:
            return json.loads(POLICY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    # デフォルト雛形
    return {
        "meta": {
            "org_name": "",
            "owner": "",
            "sector": "general",  # finance/healthcare/general/other
            "last_updated": None,
            "version": "1.0",
        },
        "redlines": [
            # { "id": "RL-001", "text": "金融アドバイスの提供禁止（免責案内必須）", "severity": "high" }
        ],
        "pii_policy": {
            "collect": False,
            "masking": True,
            "mask_style": "[REDACTED]",
            "storage": "forbidden",  # forbidden/ephemeral/encrypted
            "retention_days": 0,
        },
        "output_rules": {
            "language": "ja",
            "tone": "professional",
            "citations_required": False,
            "include_disclaimer": True,
            "disclaimer_text": "本出力は情報提供のみを目的とし、助言を構成するものではありません。",
        },
        "model_policy": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 2000,
        },
    }


def _save_policy(policy: dict) -> None:
    policy["meta"]["last_updated"] = datetime.now().isoformat()
    POLICY_FILE.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")


def _validate_policy(policy: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    # メタ
    if not policy["meta"].get("org_name"):
        errors.append("組織名（org_name）が空です。")
    # レッドライン最低1件推奨（金融/医療は強く推奨）
    if len(policy.get("redlines", [])) == 0 and policy["meta"].get("sector") in (
        "finance",
        "healthcare",
    ):
        errors.append("金融/医療セクターではレッドラインを最低1件以上設定してください。")
    # PIIポリシー
    pii = policy.get("pii_policy", {})
    if pii.get("storage") not in ("forbidden", "ephemeral", "encrypted"):
        errors.append("PIIのstorageは forbidden/ephemeral/encrypted のいずれかにしてください。")
    # 出力言語
    if policy["output_rules"].get("language") not in ("ja", "en"):
        errors.append("出力言語 language は 'ja' か 'en' のみをサポートします。")
    return (len(errors) == 0), errors


def _safe_int(value: t.Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: t.Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def assemble_policy_payload(
    org_name: str,
    owner: str,
    sector: str,
    version: str,
    redline_rows: t.Sequence[t.Sequence[t.Any]] | None,
    pii_collect: bool,
    pii_mask: bool,
    mask_style: str,
    storage: str,
    retention_days: t.Any,
    out_lang: str,
    tone: str,
    cite_req: bool,
    disclaimer_on: bool,
    disclaimer_text: str,
    provider: str,
    model_name: str,
    temp: t.Any,
    max_tokens: t.Any,
) -> tuple[dict, dict]:
    redlines = [
        {
            "id": row[0],
            "text": row[1],
            "severity": row[2] if len(row) > 2 and row[2] else "high",
        }
        for row in (redline_rows or [])
        if len(row) >= 2 and (row[0] or row[1])
    ]
    assembled = {
        "meta": {
            "org_name": org_name or "",
            "owner": owner or "",
            "sector": sector or "general",
            "last_updated": None,
            "version": version or "1.0",
        },
        "redlines": redlines,
        "pii_policy": {
            "collect": bool(pii_collect),
            "masking": bool(pii_mask),
            "mask_style": mask_style or "[REDACTED]",
            "storage": storage or "forbidden",
            "retention_days": _safe_int(retention_days, 0),
        },
        "output_rules": {
            "language": out_lang or "ja",
            "tone": tone or "professional",
            "citations_required": bool(cite_req),
            "include_disclaimer": bool(disclaimer_on),
            "disclaimer_text": disclaimer_text or "",
        },
        "model_policy": {
            "provider": provider or "openai",
            "model": model_name or "gpt-4o-mini",
            "temperature": _safe_float(temp, 0.2),
            "max_tokens": _safe_int(max_tokens, 2000),
        },
    }
    return assembled, assembled["meta"]  # type: ignore[return-value]


def validation_summary(policy: dict) -> str:
    ok, errs = _validate_policy(policy)
    if ok:
        return "✅ 検証OK（保存可能）"
    return "⚠️ 検証NG:\n- " + "\n- ".join(errs)


def build_ui():
    policy = _load_policy()

    with gr.Blocks(title="Enterprise Policy Dashboard", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🛡️ Enterprise Policy Dashboard（憲法エージェントUI）")
        gr.Markdown(
            "左のフォームで企業ごとのポリシーを定義し、右上の **検証/保存/エクスポート** を使って運用に反映します。"
            "<br>保存先: `policies/constitution.json`"
        )

        # =====================================================================
        # 上段: 操作ボタン & ステータス
        # =====================================================================
        with gr.Row():
            validate_btn = gr.Button("🔍 検証", variant="secondary")
            save_btn = gr.Button("💾 保存", variant="primary")
            export_btn = gr.Button("📦 エクスポート(JSON表示)")
            if AGENT_AVAILABLE:
                test_prompt = gr.Textbox(
                    label="ポリシー検証プロンプト（任意）",
                    placeholder="この質問/出力がポリシーに反していないかチェック...",
                    lines=2,
                )
                agent_btn = gr.Button(
                    "🧪 エージェントで検証（ConstitutionalCouncilAgent）", variant="secondary"
                )
            status_md = gr.Markdown("")

        # =====================================================================
        # 中段: 設定フォーム（タブ）
        # =====================================================================
        with gr.Tabs():
            with gr.TabItem("① 基本/メタ"):
                with gr.Row():
                    org_name = gr.Textbox(label="組織名", value=policy["meta"].get("org_name", ""))
                    owner = gr.Textbox(
                        label="オーナー/責任者", value=policy["meta"].get("owner", "")
                    )
                    sector = gr.Dropdown(
                        label="セクター",
                        choices=["general", "finance", "healthcare", "other"],
                        value=policy["meta"].get("sector", "general"),
                    )
                version = gr.Textbox(label="バージョン", value=policy["meta"].get("version", "1.0"))
                meta_preview = gr.JSON(label="メタ情報プレビュー", value=policy["meta"])

            with gr.TabItem("② 禁止事項/レッドライン"):
                rl_table = gr.Dataframe(
                    label="レッドライン（id / text / severity）",
                    headers=["id", "text", "severity"],
                    datatype=["str", "str", "str"],
                    value=[
                        [r.get("id", ""), r.get("text", ""), r.get("severity", "high")]
                        for r in policy.get("redlines", [])
                    ],
                    wrap=True,
                )
                gr.Markdown(
                    "例: `RL-FIN-001 | 無許可の投資助言の禁止（免責表記なし） | high`<br>"
                    "severity: low / medium / high"
                )

            with gr.TabItem("③ PII / データ取扱"):
                with gr.Row():
                    pii_collect = gr.Checkbox(
                        label="個人情報の収集を許可",
                        value=policy["pii_policy"].get("collect", False),
                    )
                    pii_mask = gr.Checkbox(
                        label="個人情報を必ずマスキング",
                        value=policy["pii_policy"].get("masking", True),
                    )
                mask_style = gr.Textbox(
                    label="マスク表記", value=policy["pii_policy"].get("mask_style", "[REDACTED]")
                )
                with gr.Row():
                    storage = gr.Dropdown(
                        label="保存方針",
                        choices=["forbidden", "ephemeral", "encrypted"],
                        value=policy["pii_policy"].get("storage", "forbidden"),
                    )
                    retention = gr.Number(
                        label="保存日数（0=保持禁止）",
                        value=policy["pii_policy"].get("retention_days", 0),
                        precision=0,
                    )

            with gr.TabItem("④ 出力ルール"):
                with gr.Row():
                    out_lang = gr.Dropdown(
                        label="出力言語",
                        choices=["ja", "en"],
                        value=policy["output_rules"].get("language", "ja"),
                    )
                    tone = gr.Dropdown(
                        label="口調/トーン",
                        choices=["professional", "friendly", "strict"],
                        value=policy["output_rules"].get("tone", "professional"),
                    )
                with gr.Row():
                    cite_req = gr.Checkbox(
                        label="引用(出典)必須",
                        value=policy["output_rules"].get("citations_required", False),
                    )
                    disclaimer = gr.Checkbox(
                        label="免責文を常に付与",
                        value=policy["output_rules"].get("include_disclaimer", True),
                    )
                disclaimer_text = gr.Textbox(
                    label="免責文（日本語/英語）",
                    value=policy["output_rules"].get("disclaimer_text", ""),
                    lines=3,
                )

            with gr.TabItem("⑤ モデル/温度"):
                provider = gr.Textbox(
                    label="プロバイダ", value=policy["model_policy"].get("provider", "openai")
                )
                model = gr.Textbox(
                    label="モデル名", value=policy["model_policy"].get("model", "gpt-4o-mini")
                )
                with gr.Row():
                    temp = gr.Slider(
                        label="temperature",
                        minimum=0.0,
                        maximum=1.0,
                        step=0.05,
                        value=float(policy["model_policy"].get("temperature", 0.2)),
                    )
                    max_tokens = gr.Number(
                        label="max_tokens",
                        value=int(policy["model_policy"].get("max_tokens", 2000)),
                        precision=0,
                    )

            with gr.TabItem("⑥ 検証ツール"):
                preview_json = gr.JSON(label="統合プレビュー", value=policy)

            with gr.TabItem("⑦ エクスポート"):
                export_json = gr.JSON(label="constitution.json", value=_load_policy())

        # =====================================================================
        # 変更 → プレビュー反映
        # =====================================================================
        inputs_all = [
            org_name,
            owner,
            sector,
            version,
            rl_table,
            pii_collect,
            pii_mask,
            mask_style,
            storage,
            retention,
            out_lang,
            tone,
            cite_req,
            disclaimer,
            disclaimer_text,
            provider,
            model,
            temp,
            max_tokens,
        ]

        def _assemble(*vals):
            return assemble_policy_payload(*vals)

        for comp in inputs_all:
            comp.change(_assemble, inputs=inputs_all, outputs=[preview_json, meta_preview])

        # =====================================================================
        # ボタン動作
        # =====================================================================
        validate_btn.click(
            fn=lambda *vals: validation_summary(_assemble(*vals)[0]),
            inputs=inputs_all,
            outputs=status_md,
        )

        save_btn.click(
            fn=lambda *vals: (
                _save_policy(_assemble(*vals)[0]) or "✅ 保存しました: policies/constitution.json"
            ),
            inputs=inputs_all,
            outputs=status_md,
        )

        export_btn.click(
            fn=lambda *vals: _assemble(*vals)[0], inputs=inputs_all, outputs=export_json
        )

        if AGENT_AVAILABLE:

            def _agent_check(prompt_text: str, *vals):
                policy = _assemble(*vals)[0]
                # Agent にポリシーを渡して評価（エージェントのAPI仕様に合わせて調整）
                try:
                    agent = ConstitutionalCouncilAgent(policy=policy)  # type: ignore[call-arg]
                    verdict = agent.evaluate_prompt(prompt_text)  # type: ignore[attr-defined]
                    return f"🧪 Agent verdict: {verdict}"
                except Exception as e:
                    return f"⚠️ Agent連携に失敗: {e}"

            agent_btn.click(fn=_agent_check, inputs=[test_prompt] + inputs_all, outputs=status_md)

    return demo


def launch_dashboard():
    demo = build_ui()
    demo.launch(server_name="127.0.0.1", server_port=7891, inbrowser=True, share=False)


if __name__ == "__main__":
    launch_dashboard()
