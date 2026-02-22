# ==============================================================================
# 操作するソフト: VSCode (または任意のテキストエディタ)
# フォルダ: src/nexuscore/agents/
# ファイル名: policy_agent.py
# 日付: 2025/09/03 22:45
#
# 使用方法:
#   この内容で既存のファイルを上書きしてください。
#   BaseAgentの近代化された__init__契約に完全に準拠させるための最終FIX版です。
#
# 改修内容:
#   - __init__メソッドを他の近代化されたエージェントと統一し、
#     引数を受け取らないように変更しました。
#   - super().__init__()を、引数なしで呼び出すように修正しました。
# ==============================================================================

import json
import re

from .base_agent import BaseAgent


class PolicyAgent(BaseAgent):
    """
    コードが事前に定義されたポリシー（規約）に準拠しているかを監査するエージェント。
    LLMを呼び出さず、設定ファイルに基づいて機械的にチェックを行う。
    """

    # ▼▼▼【アーキテクチャ統一】ここから▼▼▼
    def __init__(self, policy_rules_path: str = "config/policy_rules.json"):
        """
        PolicyAgentを初期化する。
        """
        super().__init__()  # 引数なしで呼び出すのが正しい作法
        # ▲▲▲【アーキテク-チャ統一】ここまで▲▲▲

        try:
            with open(policy_rules_path, encoding="utf-8") as f:
                self.policies = json.load(f)
            self.logger.info(f"Loaded {len(self.policies)} policies from {policy_rules_path}")
        except FileNotFoundError:
            self.logger.error(
                f"Policy rules file not found at: {policy_rules_path}. No policies will be enforced."
            )
            self.policies = []
        except json.JSONDecodeError:
            self.logger.error(
                f"Failed to parse JSON from {policy_rules_path}. Check for syntax errors."
            )
            self.policies = []

    def audit(self, files_to_check: list) -> dict:
        """
        与えられたファイル群を監査し、監査結果を返す。
        """
        all_violations = []
        self.logger.info(f"Starting policy audit for {len(files_to_check)} file(s)...")

        if not self.policies:
            self.logger.warning("No policies loaded. Skipping audit and approving by default.")
            return {"result": "APPROVED", "violations": []}

        for file_info in files_to_check:
            file_path = file_info.get("path")
            content = file_info.get("content")
            if not file_path or content is None:
                continue

            for policy in self.policies:
                if not all(
                    k in policy
                    for k in ["policy_id", "detection_pattern", "severity", "description"]
                ):
                    self.logger.warning(
                        f"Skipping malformed policy: {policy.get('policy_id', 'N/A')}"
                    )
                    continue

                if re.search(policy.get("target_file_pattern", ".*"), file_path):
                    for i, line in enumerate(content.splitlines()):
                        if re.search(policy["detection_pattern"], line):
                            violation = {
                                "file_path": file_path,
                                "line_number": i + 1,
                                "policy_id": policy["policy_id"],
                                "severity": policy["severity"],
                                "description": policy["description"],
                                "suggestion": policy.get("suggestion", "No specific suggestion."),
                            }
                            all_violations.append(violation)
                            self.logger.warning(f"Policy violation found: {violation}")

        result = "APPROVED" if not all_violations else "REJECTED"
        self.logger.info(
            f"Policy audit finished. Result: {result}, Violations: {len(all_violations)}"
        )

        return {"result": result, "violations": all_violations}
