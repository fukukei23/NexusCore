import json
import git
from .base_agent import BaseAgent
from src.utils.vcs import GitController

class GuardianAgent(BaseAgent):
    """
    コードの品質、セキュリティ、憲法への準拠をレビューし、
    承認された変更をGitに記録するCTOエージェント。
    """
    # ★★★★★ 修正点1: 他のエージェントと共通のSYSTEM_PROMPTを定義 ★★★★★
    SYSTEM_PROMPT = """
あなたはCTO（最高技術責任者）です。
開発チームから提出されたコード、テスト結果、その他の情報を総合的にレビューし、
その変更を承認（APPROVE）するか、修正のために差し戻す（REJECT）かを判断してください。
判断は、プロジェクトの憲法と、提示された技術的証拠に厳密に基づいてください。
"""

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        try:
            self.vcs = GitController()
        except git.InvalidGitRepositoryError:
            self.vcs = None
            print("⚠️ GuardianAgent: Gitリポジトリが見つからないため、コミット機能は無効です。")

    def review_and_commit(self, code_draft: str, test_code: str, test_result: str, testimony: str, constitution: str, task_description: str, changed_files: list, debug_info: dict = None):
        """
        コードをレビューし、承認された場合にのみコミットを実行する。
        """
        print("\n--- GuardianAgent (CTO): 最終レビューとコミット判断を開始 ---")

        # ★★★★★ 修正点2: プロンプトの構造をSYSTEM_PROMPTと分離 ★★★★★
        prompt = f"""
# レビュー対象の情報
- **プロジェクト憲法**: {constitution}
- **元のタスク**: {task_description}
- **提出コード**:
```python
{code_draft}
```
- **テストコード**:
```python
{test_code}
```
- **テスト結果**:
```
{test_result}
```
- **開発者の証言**: {testimony}

# あなたへの指示
上記の情報に基づき、このコード変更を承認するかを判断してください。

# 出力要件
- 必ず `decision` (`APPROVE`または`REJECT`) と `reason` (判断理由) を含むJSON形式で出力してください。
- REJECTする場合、`feedback_for_coder` キーに具体的な修正指示を含めてください。
"""
        # ★★★★★ 修正点3: 'invoke' を正しい '_call_llm' に修正し、JSON出力を指定 ★★★★★
        review_result_json = self._call_llm(prompt, self.SYSTEM_PROMPT, as_json=True)
        
        try:
            review_data = json.loads(review_result_json)
        except json.JSONDecodeError:
            print("❌ GuardianAgentのレビュー出力が不正なJSONでした。")
            return {"decision": "REJECT", "reason": "Invalid JSON response from Guardian."}

        decision = review_data.get("decision", "REJECT")
        reason = review_data.get("reason", "理由不明。")
        print(f"判断: {decision}")
        print(f"理由: {reason}")
        
        if decision == "REJECT":
            review_data["feedback_for_coder"] = review_data.get("feedback_for_coder", reason)
            return review_data

        if self.vcs:
            commit_message = self._generate_commit_message(review_data, changed_files, debug_info)
            commit_hash = self.vcs.commit_changes(changed_files, commit_message)
            
            if commit_hash:
                review_data["commit"] = commit_hash
            else:
                review_data["commit"] = "Commit failed or no changes detected."
        else:
            review_data["commit"] = "Git repository not available."
            
        return review_data


    def _generate_commit_message(self, review_data: dict, changed_files: list, debug_info: dict = None) -> str:
        """
        Conventional Commits形式に準拠したコミットメッセージを生成する。
        """
        scope = "auto"
        body = f"Reviewed by: GuardianAgent (Model: {self.model})\n"
        body += f"Reason for approval: {review_data.get('reason', 'N/A')}\n"

        if debug_info:
            commit_type = "fix"
            header = f"{commit_type}({scope}): Self-healed by DebuggerAgent"
            body += f"\n[DEBUGGER ACTIVITY]\n"
            body += f"Error Signature: {debug_info.get('error_signature', 'N/A')}\n"
            solution_type = debug_info.get('solution_pattern', {}).get('type', 'N/A')
            body += f"Applied Solution Type: {solution_type}\n"
        else:
            commit_type = "feat"
            header = f"{commit_type}({scope}): Implemented new functionality via CoderAgent"
        
        return f"{header}\n\n{body}"
