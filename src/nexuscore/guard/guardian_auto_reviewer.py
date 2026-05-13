"""Guardian auto-reviewer — models extracted, class remains here."""

from __future__ import annotations

import json
import re
from pathlib import Path

from nexuscore.guard._checkers import (  # noqa: F401 — legacy re-exports
    DOMESTIC_DOMAIN_PATTERNS,
    DANGEROUS_COMMAND_PATTERNS,
    MEANINGLESS_ASSERT_PATTERNS,
    SYSTEM_PATH_PATTERNS,
    check_atelier_specific,
    check_code_safety_rules,
    check_nexuscore_specific,
    check_policy_rules,
    check_sandbox_violations,
    check_testing_rules,
)
from nexuscore.guard._models import (  # noqa: F401 — legacy re-exports
    FileChange,
    Hunk,
    ProjectType,
    ReviewDecision,
    ReviewIssue,
    ReviewResult,
)


class GuardianAutoReviewer:
    """
    GuardianAgent 用の自動レビューロジック本体。

    想定ユースケース:
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff_text)
    """

    SYSTEM_PATH_PATTERNS = SYSTEM_PATH_PATTERNS
    DANGEROUS_COMMAND_PATTERNS = DANGEROUS_COMMAND_PATTERNS
    MEANINGLESS_ASSERT_PATTERNS = MEANINGLESS_ASSERT_PATTERNS
    DOMESTIC_DOMAIN_PATTERNS = DOMESTIC_DOMAIN_PATTERNS

    def __init__(self, project_name: str, policy_rules_path: str = "config/policy_rules.json"):
        self.project_type = self._detect_project_type(project_name)
        self.policy_rules: list[dict] = []
        self._load_policy_rules(policy_rules_path)

    def _load_policy_rules(self, path: str) -> None:
        """policy_rules.jsonを読み込み、enabled=trueのルールのみ保持"""
        try:
            p = Path(path)
            if not p.exists():
                return
            with p.open("r", encoding="utf-8") as f:
                all_rules = json.load(f)
            self.policy_rules = [
                r for r in all_rules if r.get("enabled", True)
            ]
        except Exception:
            self.policy_rules = []

    @staticmethod
    def _detect_project_type(project_name: str) -> ProjectType:
        name = project_name.lower()
        if "nexuscore" in name:
            return ProjectType.NEXUSCORE
        if "atelier" in name or "buyma" in name:
            return ProjectType.ATELIER
        return ProjectType.OTHER

    def review_unified_diff(self, diff_text: str) -> ReviewResult:
        """unified diff テキストを入力に、自動レビュー結果を返す。"""
        files = self._parse_unified_diff(diff_text)
        issues: list[ReviewIssue] = []

        issues.extend(check_sandbox_violations(files))
        issues.extend(check_testing_rules(files))
        issues.extend(check_code_safety_rules(files))
        issues.extend(check_policy_rules(files, self.policy_rules))

        if self.project_type == ProjectType.NEXUSCORE:
            issues.extend(check_nexuscore_specific(files))
        elif self.project_type == ProjectType.ATELIER:
            issues.extend(check_atelier_specific(files))

        if any(i.level == "error" for i in issues):
            decision = ReviewDecision.REJECT
        elif any(i.level == "warning" for i in issues):
            decision = ReviewDecision.MANUAL_REVIEW
        else:
            decision = ReviewDecision.APPROVE

        return ReviewResult(decision=decision, issues=issues)

    def _parse_unified_diff(self, diff_text: str) -> list[FileChange]:
        """ざっくりした unified diff パーサ。"""
        lines = diff_text.splitlines()
        files: list[FileChange] = []
        current_file: FileChange | None = None
        current_hunk: Hunk | None = None

        file_header_re = re.compile(r"^\+\+\+\s+b/(.+)$")
        hunk_header_re = re.compile(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@")

        for line in lines:
            m_file = file_header_re.match(line)
            if m_file:
                if current_file and current_hunk:
                    current_file.hunks.append(current_hunk)
                    current_hunk = None
                if current_file:
                    files.append(current_file)

                path = m_file.group(1)
                current_file = FileChange(path=path, hunks=[])
                current_hunk = None
                continue

            m_hunk = hunk_header_re.match(line)
            if m_hunk:
                if current_file is None:
                    continue
                if current_hunk:
                    current_file.hunks.append(current_hunk)
                old_start = int(m_hunk.group(1))
                old_lines = int(m_hunk.group(2) or 0)
                new_start = int(m_hunk.group(3))
                new_lines = int(m_hunk.group(4) or 0)
                current_hunk = Hunk(
                    old_start=old_start, old_lines=old_lines,
                    new_start=new_start, new_lines=new_lines, lines=[],
                )
                continue

            if current_hunk is not None:
                current_hunk.lines.append(line)

        if current_file:
            if current_hunk:
                current_file.hunks.append(current_hunk)
            files.append(current_file)

        return files

    # Legacy instance-method delegates (backward compat)
    def _check_sandbox_violations(self, files):
        return check_sandbox_violations(files)

    def _check_testing_rules(self, files):
        return check_testing_rules(files)

    def _check_code_safety_rules(self, files):
        return check_code_safety_rules(files)

    def _check_nexuscore_specific(self, files):
        return check_nexuscore_specific(files)

    def _check_atelier_specific(self, files):
        return check_atelier_specific(files)

    def _check_policy_rules(self, files):
        return check_policy_rules(files, self.policy_rules)

    @staticmethod
    def _severity_to_level(severity: str) -> str:
        from nexuscore.guard._checkers import _severity_to_level

        return _severity_to_level(severity)
