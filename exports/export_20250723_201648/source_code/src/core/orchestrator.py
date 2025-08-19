# ==============================================================================
# フォルダ: src/core
# ファイル名: orchestrator.py
# メモ: DebuggerAgentとPatchApplierの最終仕様に合わせて、
#      呼び出し方を調整した最終版。
# ==============================================================================
import os
import json
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict

# 依存エージェントとユーティリティをインポート
from src.agents.planner_agent import PlannerAgent
from src.agents.coder_agent import CoderAgent
from src.agents.tester_agent import TesterAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.architect_agent import ArchitectAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.patch_applier import PatchApplier
from src.agents.policy_agent import PolicyAgent
from src.utils.file_utils import create_project_structure

# テスト環境で開発したMixinをインポート
from src.agents.orchestrator import SelfHealingMixin, StructuredLoggingMixin

def clean_llm_output(text: str) -> str:
    """LLMの出力からコードブロックを抽出する"""
    if not text: return ""
    match = re.search(r"```(?:python\n)?(.*)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

@dataclass
class Orchestrator(SelfHealingMixin, StructuredLoggingMixin):
    # --- 構成部品 (DI) ---
    project_path: str
    constitution: str
    architect: ArchitectAgent
    planner: PlannerAgent
    coder: CoderAgent
    tester: TesterAgent
    debugger: DebuggerAgent
    guardian: GuardianAgent
    policy_agent: PolicyAgent
    
    # --- ループ制御 ---
    max_retries: int = 5
    max_quality_retries: int = 3

    # --- 自己修復サイクルに必要な部品 ---
    patch_applier: PatchApplier = field(default_factory=PatchApplier)

    # --- 内部属性 ---
    logger: logging.Logger = field(init=False)
    log_dir: str = field(init=False)

    def __post_init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.log_dir = os.path.join(self.project_path, ".nexus_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.logger.info(f"Production Orchestrator initialized for project: {self.project_path}")
        self.logger.info(f"Logging to: {self.log_dir}")
        # ★ SelfHealingMixinに、新しいPatchApplierの呼び出し方を教える
        self.debugger_agent = self.debugger
        self.patch_applier_func = lambda patch_str: self.patch_applier.apply(patch_str, self.project_path)


    def design_phase(self, user_requirement: str):
        # (変更なし)
        self.logger.info("--- 📐 Architect Phase ---")
        design_json_str = self.architect.design_project_structure(user_requirement)
        try:
            design_data = json.loads(design_json_str)
            create_project_structure(self.project_path, design_data.get("files", []))
            self.logger.info(f"Project structure created at {self.project_path}")
        except json.JSONDecodeError:
            self.logger.error("ArchitectAgent did not return valid JSON. Skipping structure creation.")

    def development_cycle(self, user_requirement: str):
        # (変更なし)
        self.logger.info("--- 🔄 Development Cycle ---")
        self.logger.info("--- 📝 Planner Phase ---")
        plan_json_str = self.planner.create_plan(user_requirement)
        try:
            plan = json.loads(plan_json_str)
            tasks = plan.get("functions_to_implement", [])
            self.logger.info(f"Plan created with {len(tasks)} tasks.")
            for i, task in enumerate(tasks):
                self.logger.info(f"\n{'='*20} Task {i+1}/{len(tasks)} {'='*20}")
                self.execute_task(task)
        except json.JSONDecodeError:
            self.logger.error("PlannerAgent did not return valid JSON. Cannot proceed.")

    def execute_task(self, task: Dict):
        """単一のタスクを実装、テスト、監査、自己修正するループを実行する"""
        task_name = task.get('name', 'Unnamed Task')
        self.logger.info(f"--- 🧑‍💻 Executing Task: {task_name} ---")

        source_file_rel_path = f"app/{task.get('module', 'main')}.py"
        test_file_rel_path = f"tests/test_{task.get('module', 'main')}.py"
        source_file_abs_path = os.path.join(self.project_path, source_file_rel_path)
        test_file_abs_path = os.path.join(self.project_path, test_file_rel_path)
        
        current_task_description = json.dumps(task, ensure_ascii=False)
        
        for attempt in range(self.max_quality_retries):
            self.logger.info(f"--- Quality Improvement Loop: Attempt {attempt + 1}/{self.max_quality_retries} ---")

            # 1. 実装 (CoderAgent)
            self.logger.info(f"1. CoderAgent is working on '{task_name}'...")
            try:
                with open(source_file_abs_path, 'r', encoding='utf-8') as f:
                    existing_code = f.read()
            except FileNotFoundError:
                existing_code = ""
            
            implemented_code_raw = self.coder.implement_code(current_task_description, existing_code)
            implemented_code = clean_llm_output(implemented_code_raw)
            
            os.makedirs(os.path.dirname(source_file_abs_path), exist_ok=True)
            with open(source_file_abs_path, 'w', encoding='utf-8') as f:
                f.write(implemented_code)
            self.logger.info(f"Code implemented and saved to '{source_file_rel_path}'.")

            # 2. テスト生成 (TesterAgent)
            self.logger.info(f"2. TesterAgent is generating tests...")
            module_path = source_file_rel_path.replace(os.path.sep, '.').removesuffix('.py')
            test_gen_raw = self.tester.generate_tests_from_plan(task, module_path)
            
            try:
                test_gen_data = json.loads(test_gen_raw)
                test_code = clean_llm_output(test_gen_data.get("test_code", ""))
                testimony = test_gen_data.get("testimony", "No testimony provided.")
                os.makedirs(os.path.dirname(test_file_abs_path), exist_ok=True)
                with open(test_file_abs_path, 'w', encoding='utf-8') as f: f.write(test_code)
                self.logger.info(f"Tests generated and saved to '{test_file_rel_path}'.")
            except json.JSONDecodeError:
                self.logger.error("TesterAgent did not return valid JSON. Aborting task.")
                return

            # 3. 機能テスト & 自己修復
            self.logger.info(f"3. Initiating functional validation and self-healing cycle...")
            self.self_healing_cycle(test_file_abs_path, source_file_abs_path)
            tests_passed, final_test_output = self.run_tests(test_file_abs_path)
            if not tests_passed:
                self.logger.error("Functional tests failed and could not be self-healed. Aborting task.")
                return

            # 4. 品質監査 (PolicyAgent)
            self.logger.info(f"4. PolicyAgent is auditing the code...")
            with open(source_file_abs_path, 'r', encoding='utf-8') as f: final_code_for_audit = f.read()
            files_for_audit = [
                {"path": source_file_rel_path, "content": final_code_for_audit},
                {"path": test_file_rel_path, "content": test_code}
            ]
            policy_result = self.policy_agent.audit(files_for_audit)

            if policy_result.get("result") == "APPROVED":
                self.logger.info("✅✅ Policy check passed! Proceeding to Guardian review.")
                break
            else:
                self.logger.warning(f"❌ Policy check REJECTED. Generating feedback for CoderAgent...")
                feedback = self._create_feedback_for_coder(policy_result["violations"])
                current_task_description = f"{json.dumps(task, ensure_ascii=False)}\n\n[Orchestratorからの具体的指示]:\n前回の試行は以下のポリシー違反により失敗しました。これらの問題をすべて修正してください。\n{feedback}"
                
                if attempt + 1 == self.max_quality_retries:
                    self.logger.error("Max quality retries reached. Aborting task.")
                    return
        else: 
            self.logger.error("Could not satisfy policy requirements after all attempts.")
            return
        
        # 5. 最終レビュー (GuardianAgent)
        self.logger.info(f"5. GuardianAgent is reviewing the final changes...")
        with open(source_file_abs_path, 'r', encoding='utf-8') as f: final_code = f.read()
        review_result = self.guardian.review_and_commit(
            code_draft=final_code, test_code=test_code, test_result=final_test_output,
            testimony=testimony, constitution=self.constitution,
            task_description=json.dumps(task, ensure_ascii=False),
            changed_files=[source_file_abs_path, test_file_abs_path], debug_info={}
        )
        
        if review_result.get("decision") == "APPROVE":
            self.logger.info(f"✅✅✅ Task '{task_name}' APPROVED and committed!")
        else:
            self.logger.warning(f"❌ Task '{task_name}' REJECTED by GuardianAgent.")

    def _create_feedback_for_coder(self, violations: list) -> str:
        """ポリシー違反リストからCoderAgent向けのフィードバック文字列を生成する"""
        feedback_lines = []
        for v in violations:
            line = f"- ファイル '{v['file_path']}' の {v['line_number']}行目: {v['description']} (ルール: {v['policy_id']}). 提案: {v['suggestion']}"
            feedback_lines.append(line)
        return "\n".join(feedback_lines)
