# ==============================================================================
# フォルダ: src/agents
# ファイル名: policy_agent.py
# メモ: テスト成功後、Guardianのレビュー前に介入する品質ゲート。
#      BaseAgentを継承し、既存アーキテクチャに準拠。
# ==============================================================================

import json
import re
from .base_agent import BaseAgent

class PolicyAgent(BaseAgent):
    """
    コードが事前に定義されたポリシー（規約）に準拠しているかを監査するエージェント。
    LLMを呼び出さず、設定ファイルに基づいて機械的にチェックを行う。
    """
    def __init__(self, api_key: str, model: str, policy_rules_path: str = "config/policy_rules.json"):
        """
        PolicyAgentを初期化する。
        LLMは使用しないが、BaseAgentのインターフェースに合わせるため引数を受け取る。
        """
        # BaseAgentの初期化を呼び出し、主にロガーをセットアップ
        super().__init__(api_key, model)
        
        try:
            with open(policy_rules_path, 'r', encoding='utf-8') as f:
                self.policies = json.load(f)
            self.logger.info(f"Loaded {len(self.policies)} policies from {policy_rules_path}")
        except FileNotFoundError:
            self.logger.error(f"Policy rules file not found at: {policy_rules_path}. No policies will be enforced.")
            self.policies = []
        except json.JSONDecodeError:
            self.logger.error(f"Failed to parse JSON from {policy_rules_path}. Check for syntax errors.")
            self.policies = []


    def audit(self, files_to_check: list) -> dict:
        """
        与えられたファイル群を監査し、監査結果を返す。

        Args:
            files_to_check (list): ファイルパスとコンテンツを含む辞書のリスト。
                                  例: [{"path": "app/main.py", "content": "..."}]

        Returns:
            dict: 監査結果。'result'キーに'APPROVED'または'REJECTED'、
                  'violations'キーに違反リストが含まれる。
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
                # ポリシーに必要なキーが存在するかチェック
                if not all(k in policy for k in ["policy_id", "detection_pattern", "severity", "description"]):
                    self.logger.warning(f"Skipping malformed policy: {policy.get('policy_id', 'N/A')}")
                    continue

                # ターゲットファイルパターンに一致するかチェック
                if re.search(policy.get("target_file_pattern", ".*"), file_path):
                    for i, line in enumerate(content.splitlines()):
                        if re.search(policy["detection_pattern"], line):
                            violation = {
                                "file_path": file_path,
                                "line_number": i + 1,
                                "policy_id": policy["policy_id"],
                                "severity": policy["severity"],
                                "description": policy["description"],
                                "suggestion": policy.get("suggestion", "No specific suggestion.")
                            }
                            all_violations.append(violation)
                            self.logger.warning(f"Policy violation found: {violation}")

        result = "APPROVED" if not all_violations else "REJECTED"
        self.logger.info(f"Policy audit finished. Result: {result}, Violations: {len(all_violations)}")
        
        return {
            "result": result,
            "violations": all_violations
        }
