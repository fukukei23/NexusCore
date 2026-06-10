from __future__ import annotations

import logging
import os

import gradio as gr

from ._state import AppState

logger = logging.getLogger(__name__)

# APIキー環境変数名 → 表示名
_PROVIDER_KEY_MAP: dict[str, str] = {
    "OPENAI_API_KEY": "OpenAI",
    "ANTHROPIC_API_KEY": "Anthropic",
    "GEMINI_API_KEY": "Google Gemini",
    "GLM_API_KEY": "GLM (Zhipu AI)",
    "MINIMAX_API_KEY": "MiniMax",
    "DEEPSEEK_API_KEY": "DeepSeek",
    "MOONSHOT_API_KEY": "Moonshot",
}


def _provider_status_table() -> str:
    """プロバイダーごとの API キー有無を Markdown テーブルで返す。"""
    rows = ["| プロバイダー | API キー |", "|---|---|"]
    for env_var, display_name in _PROVIDER_KEY_MAP.items():
        present = bool(os.getenv(env_var))
        status = "✅ 設定済み" if present else "❌ 未設定"
        rows.append(f"| {display_name} | {status} |")
    return "\n".join(rows)


def _profiles_table() -> str:
    """PROFILE_REGISTRY の内容を Markdown テーブルで返す。"""
    rows = ["| プロファイル | プロバイダー | モデル | 温度 | 説明 |", "|---|---|---|---|---|"]
    try:
        from nexuscore.llm.llm_profiles import PROFILE_REGISTRY

        for _name, p in PROFILE_REGISTRY.items():
            desc = (p.description or "").replace("|", "\\|")
            rows.append(f"| {p.name} | {p.provider} | {p.model} | {p.default_temperature} | {desc} |")
    except ImportError:
        rows.append("| - | - | - | - | プロファイル情報の取得に失敗 |")
    return "\n".join(rows)


def _task_map_summary() -> str:
    """TASK_MODEL_CONFIGS のサマリーを Markdown で返す。"""
    lines = []
    try:
        from nexuscore.llm.task_model_map import TASK_MODEL_CONFIGS

        current_tier: str | None = None
        for task_name, cfg in TASK_MODEL_CONFIGS.items():
            tier = "quality" if cfg.primary.startswith(("gpt_", "sonnet_")) else "lightweight"
            if tier != current_tier:
                tier_label = "Quality Tier" if tier == "quality" else "Lightweight Tier"
                lines.append(f"\n### {tier_label}\n")
                current_tier = tier
            secondary = ", ".join(cfg.secondary) if cfg.secondary else "-"
            temp = f"{cfg.temperature}" if cfg.temperature is not None else "-"
            lines.append(f"- **{task_name}**: primary=`{cfg.primary}`, fallback=`{cfg.fallback}`, secondary=[{secondary}], temp={temp}")
    except ImportError:
        lines.append("タスクマップ情報の取得に失敗")
    return "\n".join(lines)


def _runtime_status() -> str:
    """ランタイム状況（LLM Router・Whisper・SelfHealing）を返す。"""
    lines = []
    try:
        from ._llm_init import HAS_LLM, HAS_SELF_HEALING, HAS_WHISPER

        lines.append(f"- LLM Router: {'✅ 初期化済み' if HAS_LLM else '❌ 未初期化'}")
        lines.append(f"- Whisper: {'✅ 利用可能' if HAS_WHISPER else '❌ 未インストール'}")
        lines.append(f"- Self-Healing: {'✅ 利用可能' if HAS_SELF_HEALING else '❌ 未インストール'}")
    except ImportError:
        lines.append("ランタイム情報の取得に失敗")
    return "\n".join(lines)


# ---- OpenRouter BYOK helpers ----


def _openrouter_byok_status() -> str:
    """OpenRouter BYOK キーの状態を返す。"""
    try:
        from nexuscore.utils.key_store import has_key

        if has_key("openrouter"):
            return "✅ OpenRouter APIキー: 登録済み — 100+モデルに1キーでアクセス可能"
        return "❌ OpenRouter APIキー: 未登録"
    except Exception:
        return "⚠️ キー状態の取得に失敗"


def _save_openrouter_key(api_key: str) -> tuple[str, str]:
    """OpenRouterキーを暗号化保存 → (結果メッセージ, ステータス表示)."""
    if not api_key or not api_key.strip():
        return "⚠️ APIキーを入力してください", _openrouter_byok_status()
    try:
        from nexuscore.utils.key_store import save_key

        save_key("openrouter", api_key.strip())
        return "✅ OpenRouter APIキーを保存しました", _openrouter_byok_status()
    except Exception as e:
        return f"❌ 保存エラー: {e}", _openrouter_byok_status()


def _delete_openrouter_key() -> tuple[str, str]:
    """OpenRouterキーを削除 → (結果メッセージ, ステータス表示)."""
    try:
        from nexuscore.utils.key_store import delete_key

        existed = delete_key("openrouter")
        if existed:
            return "✅ OpenRouter APIキーを削除しました", _openrouter_byok_status()
        return "ℹ️ 保存済みのキーはありません", _openrouter_byok_status()
    except Exception as e:
        return f"❌ 削除エラー: {e}", _openrouter_byok_status()


def build_settings_tab(state: gr.State) -> None:
    with gr.Column():
        gr.Markdown("## Settings")
        gr.Markdown("LLM プロバイダー・プロファイル・タスクルーティングの読み取り専用ダッシュボードです。")

        with gr.Accordion("ランタイム状態", open=True):
            runtime_md = gr.Markdown(value=_runtime_status())

        with gr.Accordion("API キー状態", open=True):
            provider_md = gr.Markdown(value=_provider_status_table())

        # --- OpenRouter BYOK ---
        with gr.Accordion("🔑 OpenRouter BYOK", open=True):
            gr.Markdown(
                "OpenRouter APIキーを1つ登録するだけで、OpenAI / Anthropic / Google など "
                "100+モデルにアクセスできます。キーはAES-256-GCMで暗号化して保存されます。"
            )
            or_status = gr.Markdown(value=_openrouter_byok_status())
            or_key_input = gr.Textbox(
                label="OpenRouter APIキー",
                placeholder="sk-or-v1-...",
                type="password",
            )
            with gr.Row():
                or_save_btn = gr.Button("💾 保存", variant="primary")
                or_delete_btn = gr.Button("🗑️ 削除", variant="stop")

            or_result = gr.Markdown()

            or_save_btn.click(
                fn=_save_openrouter_key,
                inputs=[or_key_input],
                outputs=[or_result, or_status],
            )
            or_delete_btn.click(
                fn=_delete_openrouter_key,
                outputs=[or_result, or_status],
            )

        with gr.Accordion("LLM プロファイル一覧", open=False):
            profiles_md = gr.Markdown(value=_profiles_table())

        with gr.Accordion("タスクルーティングマップ", open=False):
            taskmap_md = gr.Markdown(value=_task_map_summary())
