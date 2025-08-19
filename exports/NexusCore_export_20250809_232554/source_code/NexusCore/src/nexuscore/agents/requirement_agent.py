# ==============================================================================
# ファイル: src/nexuscore/agents/requirement_agent.py
# メモ: 完全版（中間仕様ボタン・状態/進捗・編集/再生成・多言語）
# ==============================================================================
import os
import json
import uuid
import gradio as gr
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

# --- 安全なインポート ---
try:
    from .base_agent import BaseAgent
except ImportError:
    # スクリプトとして直接実行する場合のフォールバック
    class BaseAgent:
        def __init__(self):
            print("警告: BaseAgentが見つかりません。ダミークラスを使用します。")
        def execute_llm_task(self, prompt, as_json=False):
            print(f"ダミーLLM実行: {prompt[:80]}...")
            if "JSON" in prompt:
                if "松・竹・梅" in prompt:
                    return json.dumps({
                        "proposals": [
                            {"plan_name": "梅プラン（最小構成）", "description": "必要最低限の機能に絞ったプランです。"},
                            {"plan_name": "竹プラン（標準構成）", "description": "基本的な機能を網羅したバランスの取れたプランです。"},
                            {"plan_name": "松プラン（高機能版）", "description": "全ての機能を利用できる最高位のプランです。"}
                        ]
                    })
                # ダミーの仕様書JSONを返す
                return json.dumps({
                    "requirements_specification": {
                        "project_overview": "ダミーのプロジェクト概要",
                        "user_stories": ["ダミーのユーザーストーリー1"],
                    }
                })
            if "HEARING" in prompt or "PROPOSAL" in prompt:
                return "HEARING"
            return "CONTINUE_HEARING"

# --- 定数 ---
SESSIONS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'logs', 'requirement_sessions')
os.makedirs(SESSIONS_DIR, exist_ok=True)

SUPPORTED_LANGS = {"ja": "日本語", "en": "English"}

UI_TEXT = {
    "ja": {
        "title": "Requirement Agent - 要求定義セッション",
        "session_id": "セッションID",
        "lang_select": "言語を選択",
        "chat_label": "対話履歴",
        "input_label": "あなたの要求を入力してください",
        "input_ph": "具体的な機能や改善点を自由に入力してください...",
        "send": "送信",
        "finish": "この内容で仕様書を作成",
        "final_spec": "最終要求仕様書",
        "boot_msg": "Gradio UIを起動します。ブラウザで対話を行ってください。",
        "pii_warn": "注意: 入力内容はログに保存されます（PII/機微情報を含めないようご注意ください）。",
        "resume_msg": "以前の続きから始めましょう。ご要望の追加や変更点はありますか？",
        "thanks_and_wait": "ありがとうございます。仕様書を作成しますので、少々お待ちください。",
        "ask_to_type": "何か入力してください。",
        "proposals_intro": "承知いたしました。一般的な構成プランを3つ提案します。どのプランがイメージに近いですか？",
        "hearing_intro": "承知いたしました。では、要求を具体化するためにいくつか質問させてください。",
        "first_ai_done": "ありがとうございます。頂いた情報で要求仕様書を作成しますので、少々お待ちください。",
        "gen_ok": "要求仕様書の生成が完了しました。",
        "gen_fail": "要求仕様書の生成に失敗しました。",
        "log_saved": "対話ログは次のパスに保存されています",
        "draft_intro": "ここまでの内容で中間たたき台を作りました。合っていますか？",
        "choose_one": "以下から選んでください。",
        "yes": "はい",
        "no": "いいえ（修正したい）",
        "ask_for_correction": "承知いたしました。どの部分を修正しますか？具体的に教えてください。",
        "acknowledge_correction": "修正内容を承知いたしました。反映して、再度ヒアリングを続けます。",
        "explain_nfr": "「非機能要件」とは、システムの性能（例：ページの表示速度）、セキュリティ、信頼性など、機能そのものではない品質に関する要求のことです。デフォルト案では、一般的なWebシステムの目標値を設定します。後で個別に調整も可能です。",
        "explain_risk": "「リスク対策テンプレート」とは、不正アクセスやデータ漏洩といった一般的なリスクを想定し、それらに対する基本的な防御策（例：ログイン試行回数制限、IPアドレスによるアクセス制限など）を予め仕様に組み込むことです。",
        "status_label": "状態",
        "progress_label": "進捗",
        "mid_draft_btn": "中間仕様書を作成",
        "edit_switch": "編集モード（JSONを手直し）",
        "apply_edit": "この編集内容を採用（保存）",
        "regen": "AIに再生成させる（編集を反映）",
        "processing": "⏳ 処理中…",
        "draft_label": "中間仕様書（Draft）",
    },
    "en": {
        "title": "Requirement Agent - Requirement Definition Session",
        "session_id": "Session ID",
        "lang_select": "Select Language",
        "chat_label": "Conversation",
        "input_label": "Enter your requirements",
        "input_ph": "Describe desired features or improvements...",
        "send": "Send",
        "finish": "Generate specification",
        "final_spec": "Final Requirements Specification",
        "boot_msg": "Launching Gradio UI. Please continue in your browser.",
        "pii_warn": "Note: Inputs are logged. Avoid entering PII or sensitive data.",
        "resume_msg": "Let's resume where we left off. Any additions or changes?",
        "thanks_and_wait": "Thanks. I will generate the specification now. Please wait a moment.",
        "ask_to_type": "Please type something.",
        "proposals_intro": "Understood. Here are three typical plan options. Which is closest to your image?",
        "hearing_intro": "Understood. Let me ask a few questions to clarify your requirements.",
        "first_ai_done": "Thanks. I have enough information to draft the specification. Please wait a moment.",
        "gen_ok": "Specification generation completed.",
        "gen_fail": "Failed to generate the specification.",
        "log_saved": "Conversation log saved at",
        "draft_intro": "Here is a draft based on your inputs so far. Does this look right?",
        "choose_one": "Please choose one.",
        "yes": "Yes",
        "no": "No (I want to edit)",
        "ask_for_correction": "Understood. Which part would you like to correct? Please be specific.",
        "acknowledge_correction": "Acknowledged your corrections. I will reflect them and continue the hearing.",
        "explain_nfr": "'Non-functional requirements' (NFRs) refer to quality aspects like system performance (e.g., page load speed), security, and reliability, rather than specific features. The default plan sets typical targets for a standard web system, which can be adjusted later.",
        "explain_risk": "The 'risk mitigation template' involves pre-emptively incorporating basic defenses against common risks like unauthorized access or data breaches into the specification, such as limiting login attempts or restricting access by IP address.",
        "status_label": "Status",
        "progress_label": "Progress",
        "mid_draft_btn": "Generate Draft Spec",
        "edit_switch": "Edit mode (tweak JSON)",
        "apply_edit": "Apply this edit (save)",
        "regen": "Regenerate with AI (reflect edits)",
        "processing": "⏳ Processing...",
        "draft_label": "Draft Specification",
    }
}

SYSTEM_PROMPTS = {
    "ja": """あなたは、経験豊富なビジネスアナリスト兼プロダクトマネージャーです。
あなたの役割は、ユーザーの曖昧な要求を聞き出し、対話を通じて
開発チームがすぐに作業に取り掛かれる具体的な「要求仕様書」を完成させることです。
ただ質問するだけでなく、ベストプラクティスに基づいた提案も行い、ユーザーの思考を導いてください。
対話の最終目的は、抜け漏れのない完璧なJSON仕様書を完成させることです。""",
    "en": """You are an experienced business analyst and product manager.
Your role is to elicit ambiguous user needs and, through dialogue,
produce a concrete JSON "requirements specification" that the development team can act on immediately.
Not only ask questions, but also provide best-practice proposals to guide the user.
The ultimate goal is to produce a complete, gap-free JSON specification."""
}

def _ensure_json_obj(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        s = value.strip()
        start_brace = s.find("{")
        start_bracket = s.find("[")
        if start_brace == -1 and start_bracket == -1:
            return value
        starts = [x for x in [start_brace, start_bracket] if x != -1]
        if not starts:
            return value
        start = min(starts)
        end = max(s.rfind("}"), s.rfind("]"))
        if end > start:
            try:
                return json.loads(s[start:end+1])
            except Exception:
                return value
    return value

def _limit_questions(items: List[str], max_q: int = 3) -> List[str]:
    return items[:max_q] if isinstance(items, list) else []

class RequirementAgent(BaseAgent):
    def __init__(self, session_id: Optional[str] = None, language: str = "ja"):
        super().__init__()
        self.set_language(language)

        self.state: str = "INITIALIZING"
        self.conversation_history: List[Dict[str, str]] = []
        self.final_requirements: Optional[Dict] = None
        self.session_id = session_id or (datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8])
        self.session_path: str = os.path.join(SESSIONS_DIR, f"session_{self.session_id}.jsonl")
        self._load_session()
        
        self.slots: Dict[str, Any] = {
            "persona": None,
            "core_features": None,
            "data_acquisition_policy": None,
            "non_functional_defaults": None,
            "risk_policy": None,
        }
        self.turn_counter: int = 0

    def set_language(self, language: str = "ja"):
        if language not in SUPPORTED_LANGS:
            language = "ja"
        self.lang = language
        self.text = UI_TEXT[self.lang]
        self.system_prompt = SYSTEM_PROMPTS[self.lang]

    def _save_log(self, role: str, content: str):
        entry = {"timestamp": datetime.now().isoformat(), "role": role, "content": content}
        with open(self.session_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def _load_session(self):
        if os.path.exists(self.session_path):
            with open(self.session_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        log_entry = json.loads(line)
                        self.conversation_history.append({"role": log_entry["role"], "content": log_entry["content"]})
                    except Exception:
                        continue
            if self.conversation_history:
                self.state = "GATHERING"

    def _determine_next_action(self) -> str:
        # この関数は、次に何をすべきか大まかな方針を決める
        # 全スロットが埋まったら仕様書生成を提案
        if all(v is not None for v in self.slots.values()):
            return "SYNTHESIZE_REQUIREMENTS"
        return "CONTINUE_HEARING"

    def _generate_user_friendly_questions(self) -> str:
        # 未入力のスロットに対する質問を生成する
        missing = [k for k, v in self.slots.items() if v is None]
        order = ["persona", "core_features", "data_acquisition_policy", "non_functional_defaults", "risk_policy"]
        missing_sorted = sorted(missing, key=lambda x: order.index(x) if x in order else len(order))
        
        if not missing_sorted:
            return self.text["first_ai_done"]

        next_slot = missing_sorted[0]
        
        if self.lang == "ja":
            bank = {
                "persona": "まず、このシステムの主な想定ユーザーを教えてください: 1) 個人バイヤー 2) 小規模事業者 3) 企業内担当者 4) その他",
                "core_features": "次に、中心となる機能を3つまで選んでください: [商品収集, 競合分析, レコメンド, メール生成, 価格/在庫トラッキング]",
                "data_acquisition_policy": "ECサイトからのデータ取得頻度や方法に関するポリシーをどうしますか？: 1) 保守的（規約を厳守し、低頻度） 2) 標準（規約に配慮しつつ、適度な頻度） 3) 積極的（高頻度で取得、ただし注意が必要）",
                "non_functional_defaults": "システムの性能やセキュリティなどの非機能要件は、一般的な推奨値（デフォルト案）で開始しますか？ 1) はい 2) いいえ（後で個別に設定）",
                "risk_policy": "一般的なリスク対策（不正ログイン防止など）のテンプレートを適用しますか？ 1) はい 2) いいえ（個別指定）",
            }
        else:
            bank = {
                "persona": "First, who are the primary users of this system?: 1) Individual Buyers 2) Small Businesses 3) Enterprise Users 4) Other",
                "core_features": "Next, pick up to 3 core features: [Product Harvesting, Competitor Analysis, Recommendations, Email Generation, Price/Stock Tracking]",
                "data_acquisition_policy": "What is your policy for data acquisition from e-commerce sites?: 1) Conservative (strict adherence to terms, low frequency) 2) Standard (respectful of terms, moderate frequency) 3) Aggressive (high frequency, requires caution)",
                "non_functional_defaults": "Shall we start with default targets for non-functional requirements like performance and security? 1) Yes 2) No (configure later)",
                "risk_policy": "Should we apply a template for common risk mitigation (e.g., preventing brute-force logins)? 1) Yes 2) No (specify individually)",
            }
        return bank.get(next_slot, self.text["hearing_intro"])

    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★★★★★★★★★★★★★★★ ここからが修正箇所です ★★★★★★★★★★★★★★★
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    def _generate_response(self, user_message: str) -> str:
        """ユーザーの入力に基づいて、文脈に応じた応答を生成する（新ロジック）"""
        
        last_ai_q = self.conversation_history[-2]['content'] if len(self.conversation_history) > 1 else ""
        user_msg_lower = user_message.lower()

        # 状態1: 修正内容の入力を待っている
        if self.state == "AWAITING_CORRECTION":
            self.state = "GATHERING"
            # ユーザーの修正内容を履歴に反映する（ここでは簡略化）
            self.conversation_history.append({"role": "user_correction", "content": user_message})
            return self.text["acknowledge_correction"] + "\n\n" + self._generate_user_friendly_questions()

        # 状態2: 中間仕様書の承認を待っている
        if self.text["draft_intro"] in last_ai_q:
            if "はい" in user_msg_lower or "yes" in user_msg_lower:
                self.state = "GATHERING"
                return self._generate_user_friendly_questions()
            if "いいえ" in user_msg_lower or "no" in user_msg_lower:
                self.state = "AWAITING_CORRECTION"
                return self.text["ask_for_correction"]
        
        # 状態3: 通常のヒアリング中
        # ユーザーが説明を求めてきた場合
        if "どういう意味" in user_message or "what does that mean" in user_msg_lower:
            if "非機能要件" in last_ai_q:
                return self.text["explain_nfr"]
            if "リスク対策" in last_ai_q:
                return self.text["explain_risk"]

        # スロットを埋めるための応答解釈
        self._ingest_user_signal_to_slots(user_message, last_ai_q)
        
        # 次の質問を生成
        return self._generate_user_friendly_questions()

    def process_user_message(self, message: str) -> str:
        if not message or not message.strip():
            return self.text["ask_to_type"]
        
        self.conversation_history.append({"role": "user", "content": message})
        self._save_log("user", message)
        
        if self.state != "AWAITING_CORRECTION":
            self.turn_counter += 1
        
        ai_response = self._generate_response(message)
        
        self.conversation_history.append({"role": "assistant", "content": ai_response})
        self._save_log("assistant", ai_response)
        
        # 特定の応答の場合、状態を変更
        if ai_response == self.text["draft_intro"]:
            self.state = "AWAITING_DRAFT_APPROVAL"
        elif ai_response == self.text["ask_for_correction"]:
             self.state = "AWAITING_CORRECTION"
        else:
             self.state = "GATHERING"
             
        return ai_response

    def _ingest_user_signal_to_slots(self, message: str, last_question: str):
        """最後の質問の文脈を考慮してスロットを埋める"""
        t = message.lower()
        
        # 回答の柔軟な解釈
        is_yes = "はい" in t or "yes" in t or t.strip().startswith("1")
        is_no = "いいえ" in t or "no" in t or t.strip().startswith("2")

        if "想定ユーザー" in last_question or "primary users" in last_question:
            if "個人" in t or "individual" in t: self.slots["persona"] = "individual"
            elif "小規模" in t or "small" in t: self.slots["persona"] = "small_business"
            elif "企業" in t or "enterprise" in t: self.slots["persona"] = "enterprise"
        
        elif "非機能要件" in last_question or "non-functional" in last_question:
            if is_yes: self.slots["non_functional_defaults"] = "default_ok"
            if is_no: self.slots["non_functional_defaults"] = "custom"
        
        elif "リスク対策" in last_question or "risk mitigation" in last_question:
            if is_yes: self.slots["risk_policy"] = "template_on"
            if is_no: self.slots["risk_policy"] = "custom"
        
        # キーワードベースのスロットフィリングも残す
        if "攻め" in t or "aggressive" in t: self.slots["data_acquisition_policy"] = "aggressive"
        
    def generate_intermediate_spec(self) -> Dict:
        history_str = json.dumps(self.conversation_history, ensure_ascii=False)
        lang_instruction = "日本語で" if self.lang == "ja" else "in English"
        
        prompt = f"""以下の対話履歴から現時点の暫定仕様JSONを{lang_instruction}出力。未確定はTBDで埋め、必須キーは保持。
ルート: requirements_specification
JSONのみ出力
対話履歴
{history_str}"""
        
        try:
            draft = _ensure_json_obj(self.execute_llm_task(prompt, as_json=True))
            if isinstance(draft, dict) and "requirements_specification" in draft:
                return draft
        except Exception:
            pass
        return {"error": "Draft generation failed."}

    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★★★★★★★★★★★★★★★ 修正箇所はここまでです ★★★★★★★★★★★★★★★
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

    def start_session(self, user_initial_request: str) -> List[Tuple[Optional[str], Optional[str]]]:
        if not self.conversation_history:
            self.state = "GATHERING"
            self.conversation_history.append({"role": "user", "content": user_initial_request})
            self._save_log("user", user_initial_request)
            ai_message = self._generate_user_friendly_questions()
            self.conversation_history.append({"role": "assistant", "content": ai_message})
            self._save_log("assistant", ai_message)
        
        history: List[Tuple[Optional[str], Optional[str]]] = []
        u: Optional[str] = None
        for m in self.conversation_history:
            if m["role"] == "user":
                u = m["content"]
            elif m["role"] == "assistant":
                history.append((u, m["content"]))
                u = None
        return history

    def finalize_session(self) -> Dict:
        self.state = "FINALIZING"
        history_str = json.dumps(self.conversation_history, ensure_ascii=False)
        lang_instruction = "日本語で" if self.lang == "ja" else "in English"
        prompt = f"""以下の対話履歴に基づき、要求仕様書を{lang_instruction}厳格に出力してください。
ルート: requirements_specification
JSONのみ出力
対話履歴
{history_str}"""
        try:
            final_obj = _ensure_json_obj(self.execute_llm_task(prompt, as_json=True))
            if not isinstance(final_obj, dict) or "requirements_specification" not in final_obj:
                raise ValueError("Missing 'requirements_specification'")
            self.final_requirements = final_obj
            self._save_log("system", f"spec_generated: {json.dumps(self.final_requirements, ensure_ascii=False)}")
            self.state = "DONE"
            return self.final_requirements
        except Exception as e:
            self.state = "ERROR"
            return {"error": self.text["gen_fail"], "details": str(e)}

    def regenerate_with_hint(self, edit_hint_json_text: str) -> Dict:
        hint = ""
        try:
            obj = json.loads(edit_hint_json_text)
            hint = json.dumps(obj, ensure_ascii=False)
        except Exception:
            pass
        self.state = "FINALIZING"
        history_str = json.dumps(self.conversation_history, ensure_ascii=False)
        lang_instruction = "日本語で" if self.lang == "ja" else "in English"
        prompt = f"""以下の対話履歴と編集ヒントを踏まえ、仕様JSONを{lang_instruction}再生成。
ルート: requirements_specification
JSONのみ出力
対話履歴
{history_str}
編集ヒント（優先）
{hint}"""
        obj = _ensure_json_obj(self.execute_llm_task(prompt, as_json=True))
        if isinstance(obj, dict) and "requirements_specification" in obj:
            self.final_requirements = obj
            self.state = "DONE"
            return obj
        self.state = "ERROR"
        return {"error": "Regeneration failed"}

    def launch_ui(self, user_initial_request: str, share: bool = False):
        with gr.Blocks(theme=gr.themes.Soft(), title=self.text["title"]) as demo:
            gr.Markdown(f"# 🤖 {self.text['title']}")
            with gr.Row():
                gr.Markdown(f"**{self.text['session_id']}:** `{self.session_id}`")
                lang_selector = gr.Radio(
                    list(SUPPORTED_LANGS.values()), 
                    value=SUPPORTED_LANGS[self.lang], 
                    label=self.text["lang_select"],
                    interactive=True
                )
            gr.Markdown(f"_{self.text['pii_warn']}_")
            status_bar = gr.Markdown(f"{self.text['status_label']}: INITIALIZING")
            progress = gr.Slider(minimum=0, maximum=100, value=5, step=1, label=self.text["progress_label"], interactive=False)
            spinner = gr.Markdown("")
            
            chatbot = gr.Chatbot(label=self.text["chat_label"], height=460, type="messages")

            with gr.Row():
                msg_input = gr.Textbox(label=self.text["input_label"], placeholder=self.text["input_ph"], scale=4)
                send_button = gr.Button(self.text["send"], variant="primary", scale=1)
            with gr.Row():
                mid_draft_btn = gr.Button(self.text["mid_draft_btn"], variant="secondary")
                finish_button = gr.Button(self.text["finish"], variant="stop")
            draft_output = gr.JSON(label=self.text["draft_label"], visible=False)
            final_output = gr.JSON(label=self.text["final_spec"], visible=False)
            edit_switch = gr.Checkbox(label=self.text["edit_switch"], value=False)
            draft_editor = gr.Code(label="編集用JSON（Draft/Final）", language="json", visible=False, lines=18)
            apply_edited_btn = gr.Button(self.text["apply_edit"], visible=False)
            regen_btn = gr.Button(self.text["regen"], visible=False)

            def on_lang_change(lang_value):
                lang_key = [k for k, v in SUPPORTED_LANGS.items() if v == lang_value][0]
                self.set_language(lang_key)
                # UIのテキストを更新するために、各コンポーネントのupdateを返す
                return {
                    demo: gr.update(title=self.text["title"]),
                    lang_selector: gr.update(label=self.text["lang_select"]),
                    # 他のUI要素も同様に更新
                }

            def reflect_state(custom: Optional[str] = None):
                label = custom or self.state
                user_messages = [m for m in self.conversation_history if m.get("role") == "user"]
                pairs = len(user_messages)
                base = 10 if label == "INITIALIZING" else 20
                prog = max(5, min(100, base + pairs * 12))
                return gr.update(value=f"{self.text['status_label']}: {label}"), gr.update(value=prog)

            def on_ui_load(progress=gr.Progress()):
                progress(0, desc="Initializing")
                history_tuples = self.start_session(user_initial_request)
                message_history = []
                for user, assistant in history_tuples:
                    if user:
                        message_history.append({"role": "user", "content": user})
                    if assistant:
                        message_history.append({"role": "assistant", "content": assistant})

                self.state = "GATHERING"
                st, pg = reflect_state("GATHERING")
                progress(1.0, desc="Ready")
                return message_history, st, pg
            
            def on_user_submit(message, history, progress=gr.Progress()):
                spinner_on = gr.update(value=self.text["processing"])
                st1, pg1 = reflect_state()
                progress(0.2, desc="Parsing input")
                ai_response = self.process_user_message(message)
                progress(0.7, desc="Generating reply")
                history.append({"role": "user", "content": message})
                history.append({"role": "assistant", "content": ai_response})
                st2, pg2 = reflect_state()
                spinner_off = gr.update(value="")
                progress(1.0, desc="Done")

                if self.text["draft_intro"] in ai_response:
                    progress(0.1, desc="Drafting spec...")
                    draft_spec = self.generate_intermediate_spec()
                    self.state = "AWAITING_DRAFT_APPROVAL"
                    st3, pg3 = reflect_state()
                    progress(1.0, desc="Draft ready")
                    return "", history, st3, pg3, spinner_off, gr.update(value=draft_spec, visible=True)
                
                return "", history, st2, pg2, spinner_off, gr.update(visible=False)

            def on_mid_draft_click(history, progress=gr.Progress()):
                self.state = "SYNTHESIZING"
                st1, pg1 = reflect_state()
                progress(0.3, desc="Drafting")
                draft = self.generate_intermediate_spec()
                progress(0.8, desc="Validating")
                self.state = "AWAITING_DRAFT_APPROVAL"
                st2, pg2 = reflect_state()
                progress(1.0, desc="Draft ready")
                return gr.update(value=draft, visible=True), st2, pg2

            def on_finish_click(history, progress=gr.Progress()):
                self.state = "FINALIZING"
                st1, pg1 = reflect_state()
                spinner_on = gr.update(value=self.text["processing"])
                final_message = self.text["thanks_and_wait"]
                self.conversation_history.append({"role": "assistant", "content": final_message})
                self._save_log("assistant", final_message)
                history.append({"role": "assistant", "content": final_message})
                progress(0.4, desc="Composing spec")
                final_specs = self.finalize_session()
                progress(1.0, desc="Spec ready")
                st2, pg2 = reflect_state()
                spinner_off = gr.update(value="")
                return {
                    chatbot: gr.update(value=history),
                    final_output: gr.update(value=final_specs, visible=True),
                    finish_button: gr.update(interactive=False),
                    msg_input: gr.update(interactive=False),
                    send_button: gr.update(interactive=False),
                    status_bar: st2,
                    progress: pg2,
                    spinner: spinner_off
                }

            def on_edit_toggle(flag, draft, final_):
                target = final_ if (isinstance(final_, dict) and final_) else (draft if isinstance(draft, dict) else {})
                editor_value = json.dumps(target, ensure_ascii=False, indent=2) if flag else ""
                return gr.update(visible=flag, value=editor_value), gr.update(visible=flag), gr.update(visible=flag)

            def on_apply_edit(code_text):
                try:
                    obj = json.loads(code_text)
                    if isinstance(obj, dict) and "requirements_specification" in obj:
                        self.final_requirements = obj
                        return gr.update(value=obj, visible=True)
                    return gr.update(value={"error": "Missing 'requirements_specification'"}, visible=True)
                except Exception as e:
                    return gr.update(value={"error": "JSON Parse Error", "details": str(e)}, visible=True)
            
            def on_regen(code_text, progress=gr.Progress()):
                self.state = "FINALIZING"
                st1, pg1 = reflect_state()
                spinner_on = gr.update(value=self.text["processing"])
                progress(0.3, desc="Regenerating")
                obj = self.regenerate_with_hint(code_text)
                progress(1.0, desc="Done")
                st2, pg2 = reflect_state()
                spinner_off = gr.update(value="")
                return gr.update(value=obj, visible=True), st2, pg2, spinner_off

            lang_selector.change(on_lang_change, [lang_selector], [demo, lang_selector])
            send_button.click(on_user_submit, [msg_input, chatbot], [msg_input, chatbot, status_bar, progress, spinner, draft_output])
            msg_input.submit(on_user_submit, [msg_input, chatbot], [msg_input, chatbot, status_bar, progress, spinner, draft_output])
            
            mid_draft_btn.click(
                on_mid_draft_click,
                inputs=[chatbot],
                outputs=[draft_output, status_bar, progress]
            )
            
            demo.load(on_ui_load, outputs=[chatbot, status_bar, progress])
            finish_button.click(on_finish_click, inputs=[chatbot], outputs=[chatbot, final_output, finish_button, msg_input, send_button, status_bar, progress, spinner])
            edit_switch.change(on_edit_toggle, [edit_switch, draft_output, final_output], [draft_editor, apply_edited_btn, regen_btn])
            apply_edited_btn.click(on_apply_edit, [draft_editor], [final_output])
            regen_btn.click(on_regen, [draft_editor], [final_output, status_bar, progress, spinner])

        print(self.text["boot_msg"])
        demo.queue().launch(share=share)
        return self.final_requirements or {}

# ----------------- 直接実行 -----------------
if __name__ == "__main__":
    agent = RequirementAgent(language="ja")
    initial_request = "AIで営業メールを自動生成する機能を作りたい。顧客リストをアップロードして、ターゲットごとに内容を少し変えたい。"
    final_specs = agent.launch_ui(initial_request, share=False)

    print("\n" + "="*50)
    print(f"{UI_TEXT[agent.lang]['session_id']}: {agent.session_id}")
    print(UI_TEXT[agent.lang]['log_saved'], agent.session_path)
    print("Final Spec:")
    if final_specs:
        print(json.dumps(final_specs, indent=2, ensure_ascii=False))
    else:
        print("N/A")
    print("="*50)
