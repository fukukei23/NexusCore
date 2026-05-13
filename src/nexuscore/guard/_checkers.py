from __future__ import annotations

import re
from collections.abc import Sequence

from nexuscore.guard._models import FileChange, ProjectType, ReviewIssue


# ── Pattern constants ──────────────────────────────────────────────────────

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


# ── Helper ─────────────────────────────────────────────────────────────────


def _severity_to_level(severity: str) -> str:
    mapping = {"CRITICAL": "error", "MAJOR": "warning", "MINOR": "info"}
    return mapping.get(severity, "warning")


# ── Checkers ───────────────────────────────────────────────────────────────


def check_sandbox_violations(files: Sequence[FileChange]) -> list[ReviewIssue]:
    issues: list[ReviewIssue] = []

    for fc in files:
        for p in SYSTEM_PATH_PATTERNS:
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
                for pattern in DANGEROUS_COMMAND_PATTERNS:
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


def check_testing_rules(files: Sequence[FileChange]) -> list[ReviewIssue]:
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
                    for pattern in MEANINGLESS_ASSERT_PATTERNS:
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


def check_code_safety_rules(files: Sequence[FileChange]) -> list[ReviewIssue]:
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


def check_nexuscore_specific(files: Sequence[FileChange]) -> list[ReviewIssue]:
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


def check_atelier_specific(files: Sequence[FileChange]) -> list[ReviewIssue]:
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

                for pattern in DOMESTIC_DOMAIN_PATTERNS:
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


def check_policy_rules(
    files: Sequence[FileChange],
    policy_rules: list[dict],
) -> list[ReviewIssue]:
    """policy_rules.json のルールをdiff追加行に対して適用"""
    issues: list[ReviewIssue] = []

    for rule in policy_rules:
        detection = rule.get("detection_pattern")
        if not detection:
            continue
        target_pattern = rule.get("target_file_pattern", ".*")
        exception_rules = rule.get("exception_rules", {})
        level = _severity_to_level(rule.get("severity", "MAJOR"))

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
