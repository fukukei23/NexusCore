# ==============================================================================
# フォルダ: src/core
# ファイル名: orchestrator.py
# メモ: 【知識伝達強化版】自己学習サイクルで新しい知識が検証された後、
#      ファイルに書き込むだけでなく、DebuggerAgentインスタンスに直接
#      その知識を記憶させる(`add_knowledge`)ように修正。
# ==============================================================================
import os
import json
import re
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Dict
from pathlib import Path

# 依存エージェントとユーティリティをインポート
from src.agents.planner_agent import PlannerAgent
from src.agents.coder_agent import CoderAgent
from src.agents.tester_agent import TesterAgent
from src.agents.guardian_agent import GuardianAgent
from src.agents.architect_agent import ArchitectAgent
from src.agents.debugger_agent import DebuggerAgent
from src.agents.postmortem_agent import PostmortemAgent
from src.agents.knowledge_curator_agent import KnowledgeCuratorAgent
from src.agents.patch_applier import PatchApplier
from src.agents.policy_agent import PolicyAgent
from src.utils import code_analyzer

def clean_llm_output(text: str) -> str:
    # (この関数は変更なし)
    if not text:
        return ""
    match = re.search(r"```(?:python\n)?(.*)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

@dataclass
class Orchestrator:
    # (クラス属性は変更なし)
    project_path: str
    constitution: Dict
    architect: ArchitectAgent
    planner: PlannerAgent
    coder: CoderAgent
    tester: TesterAgent
    debugger: DebuggerAgent
    guardian: GuardianAgent
    policy_agent: PolicyAgent
    postmortem_agent: PostmortemAgent
    knowledge_curator_agent: KnowledgeCuratorAgent
    max_retries: int = 5
    max_quality_retries: int = 3
    logger: logging.Logger = field(init=False)
    log_dir: str = field(init=False)

    def __post_init__(self):
        # (このメソッドは変更なし)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.log_dir = os.path.join(self.project_path, ".nexus_logs")
        os.makedirs(self.log_dir, exist_ok=True)
        self.logger.info(f"Production Orchestrator initialized for project: {self.project_path}")
        self.logger.info(f"Logging to: {self.log_dir}")

    def run_tests(self, test_file_path):
        # (このメソッドは変更なし)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", os.path.relpath(test_file_path, self.project_path)],
                cwd=self.project_path,
                capture_output=True, text=True, encoding='utf-8', errors='replace', check=False
            )
            return result.returncode == 0, result.stdout + "\n" + result.stderr
        except Exception as e:
            self.logger.error(f"An error occurred while running tests: {e}", exc_info=True)
            return False, str(e)

    def self_healing_cycle(self, test_file_path: str, source_file_path: str) -> bool:
        self.logger.info(f"Starting self-healing cycle for '{os.path.basename(test_file_path)}'")
        
        for attempt in range(self.max_retries):
            self.logger.info(f"--- Self-Healing Attempt {attempt + 1}/{self.max_retries} ---")
            tests_passed, test_output = self.run_tests(test_file_path)

            if tests_passed:
                self.logger.info("✅ Tests passed. Self-healing cycle successful.")
                return True

            self.logger.warning("Tests failed. DebuggerAgent invoked.")
            
            files_context = {"source_file": source_file_path, "test_file": test_file_path}
            debug_result = self.debugger.debug(test_output, files_context)

            if debug_result and "patch" in debug_result:
                patch_str = debug_result["patch"]
                patcher = PatchApplier()
                was_applied = patcher.apply(patch_str, self.project_path)
                if was_applied:
                    self.logger.info("Patch applied successfully. Retrying tests...")
                    continue
                self.logger.error("PatchApplier failed. Continuing to learning phase.")

            self.logger.warning("No applicable solution found in FKB. Initiating learning cycle.")
            fkb_suggestion = self.postmortem_agent.analyze_failure_and_suggest_fkb_entry(
                error_log=test_output,
                source_code=Path(source_file_path).read_text(encoding='utf-8'),
                test_code=Path(test_file_path).read_text(encoding='utf-8'),
                source_file_path=os.path.relpath(source_file_path, self.project_path),
                test_file_path=os.path.relpath(test_file_path, self.project_path)
            )

            if not isinstance(fkb_suggestion, dict):
                self.logger.error("PostmortemAgent failed to generate a valid suggestion. Aborting.")
                return False

            is_valid_knowledge = self.knowledge_curator_agent.validate_fkb_suggestion(
                suggestion=fkb_suggestion,
                original_project_path=self.project_path,
                failed_test_path=test_file_path,
                related_source_path=source_file_path,
                original_test_output=test_output
            )

            if is_valid_knowledge:
                self.logger.info("Knowledge validation successful. Updating FKB automatically.")
                fkb_path = os.path.join(self.project_path, "fkb_local.json")
                try:
                    with open(fkb_path, 'r+', encoding='utf-8') as f:
                        fkb_data = json.load(f)
                        fkb_data.append(fkb_suggestion)
                        f.seek(0)
                        json.dump(fkb_data, f, ensure_ascii=False, indent=2)
                        f.truncate()
                    self.logger.info("✅ fkb_local.json has been automatically updated.")
                    
                    # ▼▼▼▼▼ ここからが最重要修正点 ▼▼▼▼▼
                    # DebuggerAgentインスタンスに、新しい知識を直接記憶させる
                    self.debugger.add_knowledge(fkb_suggestion)
                    # ▲▲▲▲▲ ここまでが最重要修正点 ▲▲▲▲▲
                    
                    self.logger.info("Retrying self-healing cycle with new knowledge.")
                    continue
                except (IOError, json.JSONDecodeError) as e:
                    self.logger.error(f"Failed to auto-update FKB: {e}", exc_info=True)
            else:
                self.logger.error("Knowledge validation failed. The suggestion will be logged but not applied.")
                suggestion_log_path = os.path.join(self.log_dir, "fkb_suggestions_rejected.jsonl")
                with open(suggestion_log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(fkb_suggestion, ensure_ascii=False) + '\n')

            self.logger.error("Could not repair the code in this attempt.")
            return False

        self.logger.error(f"Self-healing cycle failed after {self.max_retries} attempts.")
        return False
    
    # (以降のメソッド _create_project_structure, design_phase, development_cycle, _run_quality_gate, execute_task, _create_feedback_for_coder は変更なし)
    def _create_project_structure(self, files: list):
        root = Path(self.project_path)
        self.logger.info(f"Creating project structure at: {root}")
        root.mkdir(parents=True, exist_ok=True)
        if not isinstance(files, list):
            self.logger.error(f"Invalid 'files' format. Expected a list, but got {type(files)}")
            return
        for item in files:
            item_path_str = item.get("name")
            item_type = item.get("type")
            if not item_path_str or not item_type:
                self.logger.warning(f"Skipping invalid item in design data: {item}")
                continue
            normalized_path = item_path_str.replace("\\", "/").lstrip("/")
            full_path = root / normalized_path
            try:
                if item_type == 'folder':
                    full_path.mkdir(parents=True, exist_ok=True)
                elif item_type == 'file':
                    full_path.parent.mkdir(parents=True, exist_ok=True)
                    content = item.get("content", "")
                    full_path.write_text(content, encoding='utf-8')
            except IOError as e:
                self.logger.error(f"Failed to create {item_type} at {full_path}: {e}", exc_info=True)

    def design_phase(self, user_requirement: str):
        self.logger.info("--- 📐 Architect Phase ---")
        try:
            design_json_str = self.architect.design_project_structure(user_requirement)
            design_data = json.loads(design_json_str)
            self._create_project_structure(design_data.get("project", {}).get("files", []))
            self.logger.info(f"Project structure created at {self.project_path}")
        except json.JSONDecodeError:
            self.logger.error("ArchitectAgent did not return valid JSON. Skipping structure creation.")
        except Exception as e:
            self.logger.error(f"An error occurred during the design phase: {e}", exc_info=True)

    def development_cycle(self, user_requirement: str):
        self.logger.info("--- 🔄 Development Cycle ---")
        self.logger.info("--- 📝 Planner Phase ---")
        try:
            plan_json_str = self.planner.create_plan(user_requirement)
            plan = json.loads(plan_json_str)
            tasks = plan.get("functions_to_implement", [])
            self.logger.info(f"Plan created with {len(tasks)} tasks.")
            for i, task in enumerate(tasks):
                self.logger.info(f"\n{'='*20} Task {i+1}/{len(tasks)} {'='*20}")
                self.execute_task(task)
        except json.JSONDecodeError:
            self.logger.error("PlannerAgent did not return valid JSON. Cannot proceed.")
        except Exception as e:
            self.logger.error(f"An error occurred during the development cycle: {e}", exc_info=True)

    def _run_quality_gate(self, source_file_path: str) -> tuple[bool, str]:
        self.logger.info("---  GATE: Running Quality Gate ---")
        gate_config = self.constitution.get("quality_gate", {})
        min_coverage = gate_config.get("MIN_COVERAGE", 90)
        min_pylint_score = gate_config.get("MIN_PYLINT_SCORE", 8.0)
        violations = []
        self.logger.info(f"Checking test coverage (min: {min_coverage}%)")
        coverage = code_analyzer.run_pytest_cov(self.project_path)
        if coverage < min_coverage:
            msg = f"Test coverage is {coverage}%, which is below the required {min_coverage}%."
            violations.append(msg)
            self.logger.warning(f"QUALITY GATE VIOLATION: {msg}")
        self.logger.info(f"Checking Pylint score (min: {min_pylint_score}/10)")
        pylint_score = code_analyzer.run_pylint(source_file_path)
        if pylint_score < min_pylint_score:
            msg = f"Pylint score is {pylint_score}/10, which is below the required {min_pylint_score}/10."
            violations.append(msg)
            self.logger.warning(f"QUALITY GATE VIOLATION: {msg}")
        self.logger.info("Checking MyPy for type errors...")
        mypy_ok, mypy_errors = code_analyzer.run_mypy(source_file_path)
        if not mypy_ok:
            msg = f"MyPy found type errors:\n{mypy_errors}"
            violations.append(msg)
            self.logger.warning(f"QUALITY GATE VIOLATION: {msg}")
        if not violations:
            self.logger.info("✅✅ Quality Gate PASSED!")
            return True, "All quality checks passed."
        feedback = "The code is functionally correct but failed the quality gate. Please fix the following issues:\n- " + "\n- ".join(violations)
        return False, feedback

    def execute_task(self, task: Dict):
        task_name = task.get('name', 'Unnamed Task')
        self.logger.info(f"--- 🧑‍💻 Executing Task: {task_name} ---")
        module_name = task.get('module', 'main')
        source_file_rel_path = f"app/{module_name}.py"
        test_file_rel_path = f"tests/test_{module_name}.py"
        source_file_abs_path = os.path.join(self.project_path, source_file_rel_path)
        test_file_abs_path = os.path.join(self.project_path, test_file_rel_path)
        current_task_description = json.dumps(task, ensure_ascii=False)
        for attempt in range(self.max_quality_retries):
            self.logger.info(f"--- Quality Improvement Loop: Attempt {attempt + 1}/{self.max_quality_retries} ---")
            try:
                self.logger.info(f"1. CoderAgent is working on '{task_name}'...")
                existing_code = Path(source_file_abs_path).read_text(encoding='utf-8') if Path(source_file_abs_path).exists() else ""
                implemented_code_raw = self.coder.implement_code(current_task_description, existing_code)
                implemented_code = clean_llm_output(implemented_code_raw)
                Path(source_file_abs_path).parent.mkdir(parents=True, exist_ok=True)
                Path(source_file_abs_path).write_text(implemented_code, encoding='utf-8')
                self.logger.info(f"Code implemented and saved to '{source_file_rel_path}'.")
                self.logger.info("2. TesterAgent is generating tests...")
                module_path = source_file_rel_path.replace(os.path.sep, '.').removesuffix('.py')
                test_gen_raw = self.tester.generate_tests_from_plan(task, module_path)
                test_gen_data = json.loads(test_gen_raw)
                test_code = clean_llm_output(test_gen_data.get("test_code", ""))
                testimony = test_gen_data.get("testimony", "No testimony provided.")
                Path(test_file_abs_path).parent.mkdir(parents=True, exist_ok=True)
                Path(test_file_abs_path).write_text(test_code, encoding='utf-8')
                self.logger.info(f"Tests generated and saved to '{test_file_rel_path}'.")
                self.logger.info("3. Initiating functional validation and self-healing cycle...")
                if not self.self_healing_cycle(test_file_abs_path, source_file_abs_path):
                     self.logger.error("Functional tests failed and could not be self-healed. Aborting task.")
                     return
                self.logger.info("4. PolicyAgent is auditing the code...")
                final_code_for_audit = Path(source_file_abs_path).read_text(encoding='utf-8')
                files_for_audit = [{"path": source_file_rel_path, "content": final_code_for_audit}]
                policy_result = self.policy_agent.audit(files_for_audit)
                if policy_result.get("result") == "REJECTED":
                    self.logger.warning("❌ Policy check REJECTED. Looping back to CoderAgent...")
                    feedback = self._create_feedback_for_coder(policy_result.get("violations", []))
                    current_task_description = f"{json.dumps(task, ensure_ascii=False)}\n\n[Orchestratorからの具体的指示]:\n前回の試行は以下のポリシー違反により失敗しました。これらの問題をすべて修正してください。\n{feedback}"
                    if attempt + 1 >= self.max_quality_retries:
                        self.logger.error("Max quality retries reached for policy violations. Aborting task.")
                        return
                    continue
                self.logger.info("✅ Policy check passed.")
                quality_gate_passed, feedback = self._run_quality_gate(source_file_abs_path)
                if quality_gate_passed:
                    self.logger.info("✅✅✅ All checks passed! Proceeding to Guardian review.")
                    break
                self.logger.warning("❌ Quality Gate FAILED. Looping back to CoderAgent...")
                current_task_description = f"{json.dumps(task, ensure_ascii=False)}\n\n[Orchestratorからの具体的指示]:\n{feedback}"
                if attempt + 1 >= self.max_quality_retries:
                    self.logger.error("Max quality retries reached for quality gate. Aborting task.")
                    return
            except (IOError, json.JSONDecodeError) as e:
                self.logger.error(f"An error occurred during task execution loop: {e}", exc_info=True)
                return
        else: 
            self.logger.error("Could not satisfy requirements after all attempts.")
            return
        self.logger.info("6. GuardianAgent is reviewing the final changes...")
        final_code = Path(source_file_abs_path).read_text(encoding='utf-8')
        final_test_code = Path(test_file_abs_path).read_text(encoding='utf-8')
        _, final_test_output = self.run_tests(test_file_abs_path)
        constitution_text = self.constitution.get("description", "")
        review_result = self.guardian.review_and_commit(
            code_draft=final_code, test_code=final_test_code, test_result=final_test_output,
            testimony=testimony, constitution=constitution_text,
            task_description=json.dumps(task, ensure_ascii=False),
            changed_files=[source_file_abs_path, test_file_abs_path], debug_info={}
        )
        if review_result.get("decision") == "APPROVE":
            self.logger.info(f"✅✅✅ Task '{task_name}' APPROVED and committed!")
        else:
            self.logger.warning(f"❌ Task '{task_name}' REJECTED by GuardianAgent.")

    def _create_feedback_for_coder(self, violations: list) -> str:
        feedback_lines = [
            f"- ファイル '{v.get('file_path')}' の {v.get('line_number')}行目: {v.get('description')} (ルール: {v.get('policy_id')}). 提案: {v.get('suggestion')}"
            for v in violations
        ]
        return "\n".join(feedback_lines)

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
