"""Guardian auto-reviewer — models extracted, class remains here."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from pathlib import Path

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

    SYSTEM_PATH_PATTERNS = [
        re.compile(r"(^|/)\.git(/|$)"),
        re.compile(r"(^|/)\.venv(/|$)"),
        re.compile(r"^/etc(/|$)"),
        re.compile(r"^/usr(/|$)"),
        re.compile(r"^C:\\Windows", re.IGNORECASE),
    ]

    DANGEROUS_COMMAND_PATTERNS = [
        re.compile(r"\brm\s+-rf\b"),
        re.compile(r"\bgit\s+clean\b"),
        re.compile(r"rm\s+-rf\s+/\b"),
    ]

    MEANINGLESS_ASSERT_PATTERNS = [
        re.compile(r"assert\s+True\b"),
        re.compile(r"self\.assertTrue\(True\)"),
        re.compile(r"self\.assertIsNotNone\(\s*\w+\s*\)"),
    ]

    DOMESTIC_DOMAIN_PATTERNS = [
        re.compile(r'"https?://(?:www\.)?rakuten\.co\.jp'),
        re.compile(r'"https?://(?:www\.)?amazon\.co\.jp'),
        re.compile(r'"https?://(?:www\.)?zozo\.jp'),
        re.compile(r'"https?://(?:www\.)?yahoo\.co\.jp'),
    ]

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

        issues.extend(self._check_sandbox_violations(files))
        issues.extend(self._check_testing_rules(files))
        issues.extend(self._check_code_safety_rules(files))
        issues.extend(self._check_policy_rules(files))

        if self.project_type == ProjectType.NEXUSCORE:
            issues.extend(self._check_nexuscore_specific(files))
        elif self.project_type == ProjectType.ATELIER:
            issues.extend(self._check_atelier_specific(files))

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

    def _check_sandbox_violations(self, files: Sequence[FileChange]) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []

        for fc in files:
            for p in self.SYSTEM_PATH_PATTERNS:
                if p.search(fc.path):
                    issues.append(
                        ReviewIssue(
                            level="error", code="SEC-001",
                            message=f"危険なパスへの変更が含まれています: {fc.path}",
                            file_path=fc.path,
                        )
                    )

            for h in fc.hunks:
                line_no = h.new_start
                for line in h.lines:
                    if not line.startswith("+"):
                        if line.startswith("-"):
                            line_no += 1
                        continue
                    content = line[1:]
                    for pattern in self.DANGEROUS_COMMAND_PATTERNS:
                        if pattern.search(content):
                            issues.append(
                                ReviewIssue(
                                    level="error", code="SEC-002",
                                    message=f"破壊的なコマンドが追加されています: {content.strip()[:100]}",
                                    file_path=fc.path, line_no=line_no,
                                )
                            )
                    line_no += 1

        return issues

    def _check_testing_rules(self, files: Sequence[FileChange]) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []
        for fc in files:
            is_test_file = fc.path.startswith("tests/") or fc.path.endswith("_test.py")
            for h in fc.hunks:
                line_no = h.new_start
                for line in h.lines:
                    if not line.startswith("+"):
                        if line.startswith("-"):
                            line_no += 1
                        continue
                    content = line[1:]

                    if is_test_file:
                        for pattern in self.MEANINGLESS_ASSERT_PATTERNS:
                            if pattern.search(content):
                                issues.append(
                                    ReviewIssue(
                                        level="warning", code="TEST-001",
                                        message="意味の弱いアサーションが検出されました。仕様ベースの期待値で検証してください。",
                                        file_path=fc.path, line_no=line_no,
                                    )
                                )

                    line_no += 1
        return issues

    def _check_code_safety_rules(self, files: Sequence[FileChange]) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []

        try_except_pass_re = re.compile(r"try\s*:\s*$")
        except_pass_re = re.compile(r"except(?:\s+\w+)?\s*:\s*pass\b")
        except_bare_re = re.compile(r"except\s*:\s*$")
        except_exception_re = re.compile(r"except\s+Exception\s*:")

        for fc in files:
            is_src = fc.path.startswith("src/")
            for h in fc.hunks:
                line_no = h.new_start
                for line in h.lines:
                    if not line.startswith("+"):
                        if line.startswith("-"):
                            line_no += 1
                        continue
                    content = line[1:].rstrip()

                    if try_except_pass_re.search(content):
                        pass

                    if except_pass_re.search(content):
                        issues.append(
                            ReviewIssue(
                                level="error", code="SAFE-001",
                                message="例外を pass で握りつぶすコードは追加禁止です。",
                                file_path=fc.path, line_no=line_no,
                            )
                        )

                    if is_src and (
                        except_bare_re.search(content) or except_exception_re.search(content)
                    ):
                        issues.append(
                            ReviewIssue(
                                level="warning", code="SAFE-002",
                                message="bare except / except Exception は運用上リスクが高いです。対象例外を絞ってください。",
                                file_path=fc.path, line_no=line_no,
                            )
                        )

                    if is_src and "debug=" in content and "def " in content:
                        issues.append(
                            ReviewIssue(
                                level="warning", code="SAFE-003",
                                message="本番コードに debug フラグを追加していませんか？テスト専用フラグであれば _for_testing などにしてください。",
                                file_path=fc.path, line_no=line_no,
                            )
                        )

                    line_no += 1

        return issues

    def _check_nexuscore_specific(self, files: Sequence[FileChange]) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []

        for fc in files:
            if "orchestrator" in fc.path and fc.path.endswith(".py"):
                for h in fc.hunks:
                    line_no = h.new_start
                    for line in h.lines:
                        if not line.startswith("+") and not line.startswith("-"):
                            if line.startswith("-"):
                                line_no += 1
                            continue
                        content = line[1:]
                        if "Requirement" in content and "Plan" in content and "-" in line:
                            issues.append(
                                ReviewIssue(
                                    level="warning", code="NC-001",
                                    message="Orchestrator のフェーズに関わる変更があります。フェーズ順序を壊していないか確認してください。",
                                    file_path=fc.path, line_no=line_no,
                                )
                            )
                        line_no += 1

            if "fkb" in fc.path or "failure_knowledge" in fc.path:
                for h in fc.hunks:
                    line_no = h.old_start
                    for line in h.lines:
                        if line.startswith("-"):
                            issues.append(
                                ReviewIssue(
                                    level="warning", code="NC-002",
                                    message="Failure Knowledge Base に関する削除があります。自己修復ループに影響しないか確認してください。",
                                    file_path=fc.path, line_no=line_no,
                                )
                            )
                        if line.startswith("-") or line.startswith(" "):
                            line_no += 1

        return issues

    def _check_atelier_specific(self, files: Sequence[FileChange]) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []

        for fc in files:
            for h in fc.hunks:
                line_no = h.new_start
                for line in h.lines:
                    if not line.startswith("+"):
                        if line.startswith("-"):
                            line_no += 1
                        continue
                    content = line[1:]

                    for pattern in self.DOMESTIC_DOMAIN_PATTERNS:
                        if pattern.search(content):
                            issues.append(
                                ReviewIssue(
                                    level="error", code="AT-001",
                                    message="国内ECサイトURLが追加されています。BUYMA規約違反の可能性があるため禁止です。",
                                    file_path=fc.path, line_no=line_no,
                                )
                            )

                    if "profit" in content or "margin" in content or "利益" in content:
                        issues.append(
                            ReviewIssue(
                                level="warning", code="AT-002",
                                message="利益計算ロジック周辺の変更です。ビジネス上の影響が大きいため人間レビュー推奨です。",
                                file_path=fc.path, line_no=line_no,
                            )
                        )

                    line_no += 1

        return issues

    @staticmethod
    def _severity_to_level(severity: str) -> str:
        mapping = {"CRITICAL": "error", "MAJOR": "warning", "MINOR": "info"}
        return mapping.get(severity, "warning")

    def _check_policy_rules(self, files: Sequence[FileChange]) -> list[ReviewIssue]:
        """policy_rules.json のルールをdiff追加行に対して適用"""
        issues: list[ReviewIssue] = []

        for rule in self.policy_rules:
            detection = rule.get("detection_pattern")
            if not detection:
                continue
            target_pattern = rule.get("target_file_pattern", ".*")
            exception_rules = rule.get("exception_rules", {})
            level = self._severity_to_level(rule.get("severity", "MAJOR"))

            for fc in files:
                file_excluded = False
                for pat in exception_rules.get("allowlisted_files", []):
                    if re.search(pat, fc.path):
                        file_excluded = True
                        break
                if file_excluded:
                    continue

                if not re.search(target_pattern, fc.path):
                    continue

                for h in fc.hunks:
                    line_no = h.new_start
                    for line in h.lines:
                        if not line.startswith("+"):
                            if line.startswith("-"):
                                line_no += 1
                            continue
                        content = line[1:]

                        if re.search(detection, content):
                            line_excluded = False
                            for allowed in exception_rules.get("allowed_patterns", []):
                                if allowed in content:
                                    line_excluded = True
                                    break
                            if line_excluded:
                                line_no += 1
                                continue

                            issues.append(
                                ReviewIssue(
                                    level=level,
                                    code=rule.get("policy_id", "POLICY-???"),
                                    message=rule.get(
                                        "description",
                                        f"ポリシー違反: {rule.get('policy_id', 'N/A')}",
                                    ),
                                    file_path=fc.path, line_no=line_no,
                                )
                            )
                        line_no += 1

        return issues
