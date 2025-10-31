# ==============================================================================
# ファイル: src/nexuscore/agents/requirement_agent.py
# 版数  : v.fix-28 + budget-hook
# 変更点:
#   - Step2: 予算フック on_budget_tick を追加し、LLM実行直前に1行呼ぶ
#     * interpret_user_input / _generate_suggestions / generate_intermediate_spec
# 他は既存仕様（FSM, UI, JSONサニタイズ等）を維持
# ==============================================================================

from __future__ import annotations
import os
import re
import json
import uuid
import gradio as gr
from typing import Dict, List, Optional, Any, Set, Callable
from datetime import datetime

# --- 依存（BaseAgent / json_sanitizer） ---
try:
    from .base_agent import BaseAgent
    from ..utils.json_sanitizer import sanitize_json_like
except ImportError:
    # --- フォールバック定義 ---
    def sanitize_json_like(payload: Any) -> Any: return payload
    class BaseAgent:
        def __init__(self, *args, **kwargs): print("警告: BaseAgentが見つかりません。（フォールバック）")
        def execute_llm_task(self, prompt: str, as_json: bool = False) -> str:
            return "{}"
        def _call_llm(self, prompt: str, system_prompt: str, as_json: bool = False) -> str:
            return self.execute_llm_task(prompt, as_json)

# --- 定数/ディレクトリ ---
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'requirement_sessions')
os.makedirs(SESSIONS_DIR, exist_ok=True)

SUPPORTED_LANGS = {"ja": "日本語", "en": "English"}

# --- UIテキスト ---
UI_TEXT = {
    "ja": {
        "title": "Requirement Agent",
        "send": "送信",
        "finish": "この内容で仕様書を作成",
        "mid_draft_btn": "中間仕様書を作成",
        "draft_label": "中間仕様書（Draft）",
        "final_spec": "最終要求仕様書",
        "hearing_intro": "承知いたしました。では、要求を具体化するためにいくつか質問させてください。",
        "first_ai_done": "ありがとうございます。すべての基本項目についてお伺いしました。ここからは内容を洗練させていきましょう。追加や変更、提案依頼など、ご自由にお申し付けください。",
        "acknowledge_addition": "承知いたしました。ご要望を反映しました。他に何かございますか？",
        "suggestion_intro": "承知いたしました。現在の要件に基づき、以下の拡張案を提案します。",
        "gen_fail": "仕様書の生成に失敗しました。",
        "status_label": "状態",
        "chat_label": "対話履歴",
        "input_label": "要求入力",
        "input_ph": "具体的な機能・非機能・方針などをご自由に入力してください…",
        "thanks_and_wait": "ありがとうございます。仕様書を作成します…",
        "ask_to_type": "入力をお願いします。",
        "boot_msg": "Gradio UIを起動します。ブラウザで対話を行ってください。",
        "progress_label": "進捗",
        "lang_select": "UI言語",
        # ワンクリックボタン
        "yes_btn": "はい",
        "no_btn": "いいえ",
        "suggest_btn": "提案して",
    },
    "en": {
        "title": "Requirement Agent",
        "send": "Send",
        "finish": "Generate Final Spec",
        "mid_draft_btn": "Create Draft Spec",
        "draft_label": "Draft Requirements",
        "final_spec": "Final Requirements",
        "hearing_intro": "Understood. Let me ask a few questions.",
        "first_ai_done": "Thanks. We covered the basics. Feel free to ask for additions, changes, or suggestions.",
        "acknowledge_addition": "Acknowledged. Your request has been reflected. Anything else?",
        "suggestion_intro": "Based on the current requirements, I suggest the following extensions:",
        "gen_fail": "Failed to generate the specification.",
        "status_label": "Status",
        "chat_label": "Conversation",
        "input_label": "Requirement input",
        "input_ph": "Describe features / NFRs / policies…",
        "thanks_and_wait": "Thanks. Generating the specification…",
        "ask_to_type": "Please type something.",
        "boot_msg": "Launching Gradio UI. Please use your browser.",
        "progress_label": "Progress",
        "lang_select": "UI Language",
        # Quick buttons
        "yes_btn": "Yes",
        "no_btn": "No",
        "suggest_btn": "Suggest",
    }
}

SYSTEM_PROMPTS = {
    "ja": {
        "interpretation": "# 命令: ユーザーの意図を抽出し、JSONで出力。コードフェンス禁止。",
        "spec": "# 命令: スロット情報と対話履歴を基に、要求仕様書(JSON)を生成。未定は'tbd'。",
        "suggest": "# 命令: 既存の要求仕様に基づき、革新的な拡張案を3つ提案。JSONで出力。"
    },
    "en": {
        "interpretation": "# Instruction: Extract user intent and output as JSON. No code fences.",
        "spec": "# Instruction: Generate a requirements spec (JSON) from slots and history. Use 'tbd' for undefined items.",
        "suggest": "# Instruction: Suggest 3 innovative extensions based on current specs. Output as JSON."
    }
}

# --- 人間仕様言語マッピング ---
ANSWER_MAP = {
    "ja": {
        "persona": {
            "1": "個人バイヤー", "１": "個人バイヤー", "個人バイヤー": "個人バイヤー",
            "2": "小規模事業者", "２": "小規模事業者", "小規模事業者": "小規模事業者",
            "3": "企業内担当者", "３": "企業内担当者", "企業内担当者": "企業内担当者",
            "4": "その他",       "４": "その他",       "その他": "その他"
        },
        "data_acquisition_policy": {
            "1": "保守的", "１": "保守的", "保守的": "保守的",
            "2": "標準",   "２": "標準",   "標準": "標準",
            "3": "積極的", "３": "積極的", "積極的": "積極的"
        },
        "non_functional_defaults": {
            "1": "はい", "１": "はい", "はい": "はい",
            "2": "いいえ（後で個別設定）", "２": "いいえ（後で個別設定）", "いいえ": "いいえ（後で個別設定）"
        },
        "risk_policy": {
            "1": "はい", "１": "はい", "はい": "はい",
            "2": "いいえ（個別指定）", "２": "いいえ（個別指定）", "いいえ": "いいえ（個別指定）"
        },
        "core_features": {
            "1": "product_harvesting",  "１": "product_harvesting",
            "2": "competitor_analysis", "２": "competitor_analysis",
            "3": "recommendation",      "３": "recommendation",
            "4": "email_generation",    "４": "email_generation",
            "5": "price_stock_tracking","５": "price_stock_tracking",
            "商品収集": "product_harvesting",
            "競合分析": "competitor_analysis",
            "レコメンド": "recommendation",
            "メール生成": "email_generation",
            "価格/在庫トラッキング": "price_stock_tracking",
            "価格在庫トラッキング": "price_stock_tracking"
        }
    },
    "en": {
        "persona": {
            "1": "Individual Buyer", "Individual Buyer": "Individual Buyer",
            "2": "Small Business",   "Small Business":   "Small Business",
            "3": "Enterprise Staff", "Enterprise Staff": "Enterprise Staff",
            "4": "Other",            "Other":            "Other"
        },
        "data_acquisition_policy": {
            "1": "Conservative", "Conservative": "Conservative",
            "2": "Standard",     "Standard":     "Standard",
            "3": "Aggressive",   "Aggressive":   "Aggressive"
        },
        "non_functional_defaults": {
            "1": "Yes", "Yes": "Yes",
            "2": "No (configure later)", "No": "No (configure later)"
        },
        "risk_policy": {
            "1": "Yes", "Yes": "Yes",
            "2": "No (specify later)", "No": "No (specify later)"
        },
        "core_features": {
            "1": "product_harvesting",
            "2": "competitor_analysis",
            "3": "recommendation",
            "4": "email_generation",
            "5": "price_stock_tracking",
            "Product Harvesting": "product_harvesting",
            "Competitor Analysis": "competitor_analysis",
            "Recommendations": "recommendation",
            "Email Generation": "email_generation",
            "Price/Stock Tracking": "price_stock_tracking"
        }
    }
}

def _to_half_width_digits(s: str) -> str:
    trans = str.maketrans("０１２３４５６７８９", "0123456789")
    return s.translate(trans)

class RequirementAgent(BaseAgent):
    # Orchestrator から注入可能な予算フック
    on_budget_tick: Optional[Callable[[str], None]] = None

    def __init__(self, api_key: str = None, model: str = None, session_id: Optional[str] = None, language: str = "ja"):
        super().__init__(api_key, model)
        self.set_language(language)
        # --- フェーズFSM ---
        self.dialogue_phase: str = "GATHERING"  # GATHERING → VALIDATION → REFINEMENT → FINALIZING
        self.phase_history: List[str] = [self.dialogue_phase]
        self.hearing_completed: bool = False
        self.last_question_text: str = ""
        self.asked_slots: Set[str] = set()

        # --- 進行状態 ---
        self.conversation_history: List[Dict[str, str]] = []
        self.final_requirements: Optional[Dict] = None
        self.session_id = session_id or (datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8])
        self.session_path: str = os.path.join(SESSIONS_DIR, f"session_{self.session_id}.jsonl")

        # --- スロット ---
        self.slots: Dict[str, Any] = {
            "persona": None,
            "core_features": [],
            "data_acquisition_policy": None,
            "non_functional_defaults": None,
            "risk_policy": None,
        }
        self._load_session()

    # ---------------- 言語/UI ----------------
    def set_language(self, language: str = "ja"):
        if language not in SUPPORTED_LANGS:
            language = "ja"
        self.lang = language
        self.text = UI_TEXT.get(language, UI_TEXT["ja"])
        self.system_prompt = SYSTEM_PROMPTS.get(language, SYSTEM_PROMPTS["ja"])

    # ---------------- 予算フック ----------------
    def _budget(self, step: str) -> None:
        try:
            if callable(self.on_budget_tick):
                self.on_budget_tick(step)
        except Exception:
            pass

    # ---------------- ログ永続化 ----------------
    def _save_log(self, role: str, content: str):
        entry = {"timestamp": datetime.now().isoformat(), "role": role, "content": content}
        try:
            with open(self.session_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception:
            pass

    def _load_session(self):
        if not os.path.exists(self.session_path):
            return
        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                for line in f:
                    obj = json.loads(line)
                    if obj.get("role") in ("user", "assistant"):
                        self.conversation_history.append({"role": obj["role"], "content": obj.get("content", "")})
        except Exception:
            pass

    # ---------------- FSMユーティリティ ----------------
    def _transition(self, to_phase: str):
        allowed = {
            "GATHERING": {"GATHERING", "VALIDATION"},
            "VALIDATION": {"REFINEMENT", "GATHERING"},
            "REFINEMENT": {"REFINEMENT", "FINALIZING"},
            "FINALIZING": {"FINALIZING"},
        }
        cur = self.dialogue_phase
        if to_phase in allowed.get(cur, set()):
            self.dialogue_phase = to_phase
            self.phase_history.append(self.dialogue_phase)

    def _needs_more_hearing(self) -> bool:
        return any(v is None or (isinstance(v, list) and not v) for v in self.slots.values())

    def _mark_asked_slot(self, q_text: str):
        for key, hint in {
            "persona": "想定ユーザー",
            "core_features": "中心となる機能",
            "data_acquisition_policy": "データ取得",
            "non_functional_defaults": "性能やセキュリティ",
            "risk_policy": "リスク対策",
        }.items():
            if hint in q_text:
                self.asked_slots.add(key)

    def _next_question(self) -> Optional[str]:
        missing = [k for k, v in self.slots.items() if v is None or (isinstance(v, list) and not v)]
        order = ["persona", "core_features", "data_acquisition_policy", "non_functional_defaults", "risk_policy"]
        ordered = [k for k in order if k in missing and k not in self.asked_slots] + \
                  [k for k in order if k in missing and k in self.asked_slots]
        if not ordered:
            return None
        q = self._generate_user_friendly_questions()
        if q and q == self.last_question_text:
            return None
        return q

    # ---------------- LLM呼び出し ----------------
    def _get_last_ai_message(self) -> str:
        for item in reversed(self.conversation_history):
            if item.get("role") == "assistant":
                return item.get("content", "")
        return ""

    def interpret_user_input(self, user_message: str, last_question: str) -> Dict:
        prompt = f"""
{self.system_prompt['interpretation']}
# 対話の文脈:
- 現在の対話フェーズ: {self.dialogue_phase}
- システムからの直前の質問/発言: {last_question}
- ユーザーの最新の入力: {user_message}
- 現在のスロットの状態: {json.dumps(self.slots, ensure_ascii=False)}
"""
        # Step2: 予算カウント
        self._budget("requirement:interpret")
        response = self._call_llm(prompt, self.system_prompt['interpretation'], as_json=True)
        interpretation = sanitize_json_like(response)
        return interpretation.get("interpretation", {}) if isinstance(interpretation, dict) else {}

    def _apply_interpretation(self, interpretation: Dict):
        updates = interpretation.get("slot_updates", {})
        if not isinstance(updates, dict):
            return
        for k, v in updates.items():
            if k not in self.slots:
                continue
            if isinstance(self.slots[k], list):
                new_items = v if isinstance(v, list) else [v]
                self.slots[k] = sorted(list(set(self.slots[k] + [x for x in new_items if x])))
            else:
                self.slots[k] = v

    # ---------------- ユーザー入力→スロット反映（人間仕様言語） ----------------
    def _apply_human_answer_mapping(self, message: str):
        msg_raw = message.strip()
        msg = _to_half_width_digits(msg_raw)

        # ---- まず core_features を“常に”加算判定 ----
        cf_map = ANSWER_MAP.get(self.lang, {}).get("core_features", {})
        digits = re.findall(r"[0-9]", msg)
        cf_values: List[str] = []

        for d in digits:
            val = cf_map.get(d)
            if val:
                cf_values.append(val)

        tokenized = re.split(r"[,\s、，]+", msg)
        for tk in tokenized:
            tk = tk.strip()
            if not tk:
                continue
            val = cf_map.get(tk)
            if not val:
                if tk in {"product_harvesting","competitor_analysis","recommendation","email_generation","price_stock_tracking"}:
                    val = tk
            if val:
                cf_values.append(val)

        if cf_values:
            merged = sorted(list(set(self.slots.get("core_features", []) + cf_values)))
            self.slots["core_features"] = merged

        # ---- 単一選択スロット ----
        missing = [k for k, v in self.slots.items() if v is None or (isinstance(v, list) and not v)]
        if not missing:
            return
        current_slot = missing[0]
        if current_slot == "core_features":
            return
        single_map = ANSWER_MAP.get(self.lang, {}).get(current_slot, {})
        mapped = single_map.get(msg) or single_map.get(msg_raw)
        if mapped:
            self.slots[current_slot] = mapped

    # ---------------- 人間可読サマリ + 選択肢提示 ----------------
    def _summarize_slots_to_confirm(self) -> str:
        summary = {
            "persona": self.slots.get("persona"),
            "core_features": self.slots.get("core_features"),
            "data_acquisition_policy": self.slots.get("data_acquisition_policy"),
            "non_functional_defaults": self.slots.get("non_functional_defaults"),
            "risk_policy": self.slots.get("risk_policy"),
        }
        human = []
        if self.lang == "ja":
            human.append("■ 確認内容")
            human.append(f"- 想定ユーザー: {summary['persona'] or '未設定'}")
            cf = summary['core_features'] or []
            cf_map = {
                "product_harvesting": "商品収集",
                "competitor_analysis": "競合分析",
                "recommendation": "レコメンド",
                "email_generation": "メール生成",
                "price_stock_tracking": "価格・在庫トラッキング",
            }
            cf_human = "、".join([cf_map.get(x, x) for x in cf]) or "未設定"
            human.append(f"- コア機能: {cf_human}")
            human.append(f"- データ取得ポリシー: {summary['data_acquisition_policy'] or '未設定'}")
            human.append(f"- 非機能（推奨初期値）: {summary['non_functional_defaults'] or '未設定'}")
            human.append(f"- リスク対策テンプレート: {summary['risk_policy'] or '未設定'}")
            human.append("")
            human.append("この内容でよろしいですか？（選択肢: **はい**／**いいえ**／**提案して**）")
            human.append("※ 修正がある場合は、例: 「core_features=5 追加」「data_acquisition_policy=標準」など具体的に入力してください。")
        else:
            human.append("■ Confirmation")
            human.append(f"- Persona: {summary['persona'] or 'unset'}")
            cf = summary['core_features'] or []
            cf_human = ", ".join(cf) or "unset"
            human.append(f"- Core features: {cf_human}")
            human.append(f"- Data acquisition policy: {summary['data_acquisition_policy'] or 'unset'}")
            human.append(f"- Non-functional defaults: {summary['non_functional_defaults'] or 'unset'}")
            human.append(f"- Risk-mitigation template: {summary['risk_policy'] or 'unset'}")
            human.append("")
            human.append("Proceed with this? (Options: **yes** / **no** / **suggest**)")
        human.append("\n---\n参考(JSON): " + json.dumps(summary, ensure_ascii=False))
        return "\n".join(human)

    # ---------------- AI提案（不足穴埋め + 拡張案） ----------------
    def _compose_ai_proposals(self) -> str:
        suggestions_text = self._generate_suggestions()
        if self.lang == "ja":
            recs = []
            if not self.slots.get("data_acquisition_policy"):
                recs.append("- データ取得ポリシー案: **標準**（初期は標準、後に積極的へ段階移行）")
            if not self.slots.get("non_functional_defaults"):
                recs.append("- 非機能の初期値: **はい（推奨初期設定を適用）**")
            if not self.slots.get("risk_policy"):
                recs.append("- リスク対策テンプレ: **はい（一般的対策を適用）**")
            head = "■ 改善提案（不足の穴埋め＋拡張案）"
            tail = "\n".join(recs) if recs else "（主要スロットは概ね充足しています）"
            return f"{head}\n{tail}\n\n{suggestions_text}"
        else:
            recs = []
            if not self.slots.get("data_acquisition_policy"):
                recs.append("- Data policy: **Standard** (start standard, ramp up later)")
            if not self.slots.get("non_functional_defaults"):
                recs.append("- Non-functional defaults: **Yes (apply recommended)**")
            if not self.slots.get("risk_policy"):
                recs.append("- Risk template: **Yes (apply common mitigations)**")
            head = "■ Proposals (fill gaps + extensions)"
            tail = "\n".join(recs) if recs else "(Key slots are mostly filled.)"
            return f"{head}\n{tail}\n\n{suggestions_text}"

    def _generate_user_friendly_questions(self) -> Optional[str]:
        missing = [k for k, v in self.slots.items() if v is None or (isinstance(v, list) and not v)]
        if not missing:
            return None
        order = ["persona", "core_features", "data_acquisition_policy", "non_functional_defaults", "risk_policy"]
        next_slot = sorted(missing, key=lambda x: order.index(x) if x in order else len(order))[0]
        q_bank = {
            "ja": {
                "persona": "まず、このシステムの主な想定ユーザーを教えてください: 1) 個人バイヤー 2) 小規模事業者 3) 企業内担当者 4) その他",
                "core_features": "次に、中心となる機能を教えてください（複数可。番号/名称で入力可）: [1 商品収集, 2 競合分析, 3 レコメンド, 4 メール生成, 5 価格/在庫トラッキング]",
                "data_acquisition_policy": "ECサイトからのデータ取得ポリシーは？: 1) 保守的 2) 標準 3) 積極的",
                "non_functional_defaults": "非機能（性能/セキュリティ等）は推奨初期値で開始しますか？ 1) はい 2) いいえ（後で個別設定）",
                "risk_policy": "一般的なリスク対策テンプレートを適用しますか？ 1) はい 2) いいえ（個別指定）",
            },
            "en": {
                "persona": "Primary user persona? 1) Individual Buyer 2) Small Business 3) Enterprise Staff 4) Other",
                "core_features": "Core features (multi; number/name accepted): [1 Product Harvesting, 2 Competitor Analysis, 3 Recommendations, 4 Email Generation, 5 Price/Stock Tracking]",
                "data_acquisition_policy": "Data acquisition policy? 1) Conservative 2) Standard 3) Aggressive",
                "non_functional_defaults": "Start with recommended defaults for NFRs? 1) Yes 2) No (configure later)",
                "risk_policy": "Apply common risk-mitigation template? 1) Yes 2) No (specify later)",
            }
        }
        return q_bank[self.lang].get(next_slot, self.text["hearing_intro"])

    def _generate_suggestions(self) -> str:
        prompt = f"{self.system_prompt['suggest']}\n# 既存の要求仕様:\n{json.dumps(self.slots, ensure_ascii=False)}"
        # Step2: 予算カウント
        self._budget("requirement:suggest")
        response = self._call_llm(prompt, self.system_prompt['suggest'], as_json=True)
        data = sanitize_json_like(response)
        suggestions = data.get("suggestions", []) if isinstance(data, dict) else []
        if not suggestions:
            return self.text["acknowledge_addition"]
        return self.text["suggestion_intro"] + "\n- " + "\n- ".join(suggestions)

    # ---------------- 仕様生成（フォールバック内蔵） ----------------
    def _build_spec_fallback(self) -> Dict:
        return {
            "requirements_specification": {
                "slots": self.slots,
                "history": self.conversation_history
            }
        }

    def generate_intermediate_spec(self) -> Dict:
        if not any(v is not None for v in self.slots.values()):
            return {"error": self.text["gen_fail"]}
        prompt = (
            f"{self.system_prompt['spec']}\n"
            f"# 確定スロット情報:\n{json.dumps(self.slots, ensure_ascii=False)}\n"
            f"# 対話履歴:\n{json.dumps(self.conversation_history, ensure_ascii=False)}"
        )
        # Step2: 予算カウント
        self._budget("requirement:spec")
        response = self._call_llm(prompt, self.system_prompt['spec'], as_json=True)
        data = sanitize_json_like(response)
        if isinstance(data, dict) and "requirements_specification" in data:
            return data
        return self._build_spec_fallback()

    def generate_spec(self) -> Dict:
        return self.generate_intermediate_spec()

    # ---------------- セッション制御 ----------------
    def start_session(self, user_initial_request: str):
        self.conversation_history.clear()
        self.dialogue_phase = "GATHERING"
        self.phase_history = [self.dialogue_phase]
        self.hearing_completed = False
        self.last_question_text = ""
        self.asked_slots.clear()
        self.slots.update({k: ([] if isinstance(v, list) else None) for k, v in self.slots.items()})
        if user_initial_request:
            self.process_user_message(user_initial_request)

    # ---------------- 対話処理（FSM＋マッピング） ----------------
    def process_user_message(self, message: str) -> str:
        if not message or not message.strip():
            return self.text["ask_to_type"]

        self._apply_human_answer_mapping(message)

        self.conversation_history.append({"role": "user", "content": message})
        self._save_log("user", message)
        last_ai_q = self._get_last_ai_message()

        interpretation = self.interpret_user_input(message, last_ai_q)
        self._apply_interpretation(interpretation)
        intent = interpretation.get("user_intent", "")

        phase = self.dialogue_phase
        ai_response = ""

        if phase == "GATHERING":
            if self._needs_more_hearing():
                q = self._next_question()
                if q:
                    ai_response = q
                    self.last_question_text = q
                    self._mark_asked_slot(q)
                else:
                    self.hearing_completed = True
                    self._transition("VALIDATION")
                    ai_response = self._summarize_slots_to_confirm()
            else:
                self.hearing_completed = True
                self._transition("VALIDATION")
                ai_response = self._summarize_slots_to_confirm()

        elif phase == "VALIDATION":
            normalized = _to_half_width_digits(message.strip()).lower()
            is_yes = normalized in {"はい", "ok", "yes", "y", "了解", "問題ない", "そのまま"} or ("承認" in normalized)
            is_no  = normalized in {"いいえ", "no", "n", "だめ", "不可", "いや"}
            want_suggest = ("提案" in message) or ("suggest" in normalized)
            is_fix = ("修正" in message) or ("変更" in message) or ("追加" in message) or ("違う" in message)

            if is_yes or intent in {"confirm_selection", "accept"}:
                if self._needs_more_hearing():
                    self._transition("GATHERING")
                    q = self._next_question()
                    if q:
                        ai_response = q
                        self.last_question_text = q
                        self._mark_asked_slot(q)
                    else:
                        ai_response = self._summarize_slots_to_confirm()
                else:
                    self._transition("REFINEMENT")
                    ai_response = self.text["first_ai_done"]

            elif is_no or want_suggest:
                ai_response = self._compose_ai_proposals()

            elif is_fix or intent in {"modify_slot", "add_feature"}:
                if self._needs_more_hearing():
                    self._transition("GATHERING")
                    q = self._next_question()
                    if q:
                        ai_response = q
                        self.last_question_text = q
                        self._mark_asked_slot(q)
                    else:
                        ai_response = "どの項目を修正・追加しますか？（例：persona=小規模事業者、core_features=5 追加）"
                else:
                    ai_response = self._summarize_slots_to_confirm()
            else:
                ai_response = self._summarize_slots_to_confirm()

        elif phase == "REFINEMENT":
            if intent in {"add_feature", "modify_slot"}:
                ai_response = self.text["acknowledge_addition"]
            elif intent in {"ask_for_suggestion", "suggest"} or ("提案" in message):
                ai_response = self._generate_suggestions()
            else:
                ai_response = self.text["acknowledge_addition"]

        elif phase == "FINALIZING":
            ai_response = "最終仕様を生成中です。UIの『この内容で仕様書を作成』をご使用ください。"

        else:
            self._transition("GATHERING")
            q = self._next_question()
            ai_response = q or self.text["hearing_intro"]

        self.conversation_history.append({"role": "assistant", "content": ai_response})
        self._save_log("assistant", ai_response)
        return ai_response

    # ---------------- UI ----------------
    def launch_ui(self, user_initial_request: str, share: bool = False):
        with gr.Blocks(theme=gr.themes.Soft(), title=self.text["title"]) as demo:
            gr.Markdown(f"# 🤖 {self.text['title']}")

            with gr.Row():
                lang_radio = gr.Radio(
                    choices=[SUPPORTED_LANGS["ja"], SUPPORTED_LANGS["en"]],
                    value=SUPPORTED_LANGS[self.lang],
                    label=self.text["lang_select"]
                )
                status_bar = gr.Markdown(f"{self.text['status_label']}: INITIALIZING")

            chatbot = gr.Chatbot(label=self.text["chat_label"], height=460, type="messages")
            msg_input = gr.Textbox(label=self.text["input_label"], placeholder=self.text["input_ph"])

            with gr.Row():
                send_button = gr.Button(self.text["send"], variant="primary")
                mid_draft_btn = gr.Button(self.text["mid_draft_btn"])
                finish_button = gr.Button(self.text["finish"], variant="stop")

            with gr.Row():
                yes_btn = gr.Button(self.text["yes_btn"], visible=False)
                no_btn = gr.Button(self.text["no_btn"], visible=False)
                suggest_btn = gr.Button(self.text["suggest_btn"], visible=False)

            draft_output = gr.JSON(label=self.text["draft_label"], visible=True)
            final_output = gr.JSON(label=self.text["final_spec"], visible=False)

            def reflect_state_and_quickops():
                status = gr.update(value=f"{self.text['status_label']}: {self.dialogue_phase}")
                vis = (self.dialogue_phase == "VALIDATION")
                yes_u = gr.update(visible=vis, value=self.text["yes_btn"])
                no_u = gr.update(visible=vis, value=self.text["no_btn"])
                sug_u = gr.update(visible=vis, value=self.text["suggest_btn"])
                return status, yes_u, no_u, sug_u

            def on_ui_load():
                self.start_session(user_initial_request)
                status_u, yes_u, no_u, sug_u = reflect_state_and_quickops()
                return (self.conversation_history, status_u,
                        gr.update(label=self.text["chat_label"]),
                        gr.update(label=self.text["input_label"], placeholder=self.text["input_ph"]),
                        gr.update(value=self.text["send"]),
                        gr.update(value=self.text["mid_draft_btn"]),
                        gr.update(value=self.text["finish"]),
                        gr.update(label=self.text["draft_label"]),
                        gr.update(label=self.text["final_spec"]),
                        gr.update(label=self.text["lang_select"]),
                        yes_u, no_u, sug_u)

            def on_user_submit(message, history):
                self.process_user_message(message)
                status_u, yes_u, no_u, sug_u = reflect_state_and_quickops()
                return "", self.conversation_history, status_u, yes_u, no_u, sug_u

            def on_mid_draft_click():
                draft = self.generate_intermediate_spec()
                return gr.update(value=draft, visible=True)

            def on_finish_click(history):
                self._transition("FINALIZING")
                self.conversation_history.append({"role": "assistant", "content": self.text["thanks_and_wait"]})
                final_specs = self.generate_spec()
                self.final_requirements = final_specs
                return (
                    self.conversation_history,
                    gr.update(value=final_specs, visible=True),
                    gr.update(interactive=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(visible=False),
                )

            def on_lang_change(display_value: str):
                code = "ja" if display_value == SUPPORTED_LANGS["ja"] else "en"
                self.set_language(code)
                status_u, yes_u, no_u, sug_u = reflect_state_and_quickops()
                return (
                    gr.update(label=self.text["lang_select"]),
                    status_u,
                    gr.update(label=self.text["chat_label"]),
                    gr.update(label=self.text["input_label"], placeholder=self.text["input_ph"]),
                    gr.update(value=self.text["send"]),
                    gr.update(value=self.text["mid_draft_btn"]),
                    gr.update(value=self.text["finish"]),
                    gr.update(label=self.text["draft_label"]),
                    gr.update(label=self.text["final_spec"]),
                    yes_u, no_u, sug_u
                )

            def on_yes_click():
                self.process_user_message(self.text["yes_btn"])
                status_u, yes_u, no_u, sug_u = reflect_state_and_quickops()
                return self.conversation_history, status_u, yes_u, no_u, sug_u

            def on_no_click():
                self.process_user_message(self.text["no_btn"])
                status_u, yes_u, no_u, sug_u = reflect_state_and_quickops()
                return self.conversation_history, status_u, yes_u, no_u, sug_u

            def on_suggest_click():
                token = "提案して" if self.lang == "ja" else "suggest"
                self.process_user_message(token)
                status_u, yes_u, no_u, sug_u = reflect_state_and_quickops()
                return self.conversation_history, status_u, yes_u, no_u, sug_u

            demo.load(
                on_ui_load,
                outputs=[
                    chatbot, status_bar,
                    chatbot, msg_input, send_button, mid_draft_btn, finish_button,
                    draft_output, final_output, lang_radio,
                    yes_btn, no_btn, suggest_btn
                ]
            )

            send_button.click(
                on_user_submit, [msg_input, chatbot],
                [msg_input, chatbot, status_bar, yes_btn, no_btn, suggest_btn]
            )
            msg_input.submit(
                on_user_submit, [msg_input, chatbot],
                [msg_input, chatbot, status_bar, yes_btn, no_btn, suggest_btn]
            )

            mid_draft_btn.click(on_mid_draft_click, outputs=[draft_output])

            finish_button.click(
                on_finish_click, [chatbot],
                [chatbot, final_output, finish_button, yes_btn, no_btn, suggest_btn]
            )

            lang_radio.change(
                on_lang_change, [lang_radio],
                [lang_radio, status_bar, chatbot, msg_input, send_button, mid_draft_btn, finish_button, draft_output, final_output,
                 yes_btn, no_btn, suggest_btn]
            )

            yes_btn.click(on_yes_click, outputs=[chatbot, status_bar, yes_btn, no_btn, suggest_btn])
            no_btn.click(on_no_click, outputs=[chatbot, status_bar, yes_btn, no_btn, suggest_btn])
            suggest_btn.click(on_suggest_click, outputs=[chatbot, status_bar, yes_btn, no_btn, suggest_btn])

        print(self.text["boot_msg"])
        demo.queue().launch(share=share)
        return self.final_requirements or {}

# ---------------- 直接実行 ----------------
if __name__ == "__main__":
    # Gradio UIを起動するためのAPIキーとモデルは、環境変数などから取得する想定です
    agent = RequirementAgent(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        language="ja"
    )
    initial_request = "BUYMA無在庫転売の売上最大化・業務効率化・規約遵守・リスク低減を目的に、AIで業務を自動化・最適化したい。素人でも使いやすい直感的なUI/UXで。"
    final_specs = agent.launch_ui(initial_request, share=False)
    if final_specs:
        print("\n" + "="*50)
        print("Final Spec:")
        print(json.dumps(final_specs, indent=2, ensure_ascii=False))
        print("="*50)