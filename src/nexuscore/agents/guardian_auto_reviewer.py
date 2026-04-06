from __future__ import annotations

import enum
import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path


class ReviewDecision(enum.StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    MANUAL_REVIEW = "manual_review"


@dataclass
class ReviewIssue:
    """
    個別の指摘事項。
    """

    level: str  # "error" | "warning" | "info"
    code: str  # 例: "SEC-001", "TEST-003", etc.
    message: str
    file_path: str | None = None
    line_no: int | None = None


@dataclass
class ReviewResult:
    """
    GuardianAgent が使うレビュー結果の構造。
    """

    decision: ReviewDecision
    issues: list[ReviewIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.level == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.level == "warning" for i in self.issues)

    def summary(self) -> str:
        lines = [f"decision={self.decision.value}"]
        for issue in self.issues:
            loc = ""
            if issue.file_path:
                loc += issue.file_path
                if issue.line_no is not None:
                    loc += f":{issue.line_no}"
            prefix = f"[{issue.level.upper()}][{issue.code}]"
            if loc:
                lines.append(f"{prefix} {loc} - {issue.message}")
            else:
                lines.append(f"{prefix} {issue.message}")
        return "\n".join(lines)


class ProjectType(enum.StrEnum):
    NEXUSCORE = "nexuscore"
    ATELIER = "atelier-kyo-manager"
    OTHER = "other"


@dataclass
class FileChange:
    """
    diff解析済みの1ファイル分の変更情報（最低限）。
    """

    path: str
    hunks: list[Hunk]


@dataclass
class Hunk:
    """
    unified diff の hunk 情報。
    """

    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    lines: list[str]  # "+...", "-...", " ..." の行


class GuardianAutoReviewer:
    """
    GuardianAgent 用の自動レビューロジック本体。

    想定ユースケース:
        reviewer = GuardianAutoReviewer(project_name="nexuscore")
        result = reviewer.review_unified_diff(diff_text)

    GuardianAgent 側では、result.decision を見て approve/reject、
    result.summary() をそのままコメントに貼る、などで使える。
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

    # テスト系で禁止したいパターン
    MEANINGLESS_ASSERT_PATTERNS = [
        re.compile(r"assert\s+True\b"),
        re.compile(r"self\.assertTrue\(True\)"),
        re.compile(r"self\.assertIsNotNone\(\s*\w+\s*\)"),
    ]

    # 国内サイト例（atelier-kyo-manager用）
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

    # =============================
    # パブリックAPI
    # =============================

    def review_unified_diff(self, diff_text: str) -> ReviewResult:
        """
        git diff --unified=0 のような unified diff テキストを入力に、
        自動レビュー結果を返す。
        """
        files = self._parse_unified_diff(diff_text)
        issues: list[ReviewIssue] = []

        # 各チェックを実行
        issues.extend(self._check_sandbox_violations(files))
        issues.extend(self._check_testing_rules(files))
        issues.extend(self._check_code_safety_rules(files))
        issues.extend(self._check_policy_rules(files))

        if self.project_type == ProjectType.NEXUSCORE:
            issues.extend(self._check_nexuscore_specific(files))
        elif self.project_type == ProjectType.ATELIER:
            issues.extend(self._check_atelier_specific(files))

        # 決定ロジック
        if any(i.level == "error" for i in issues):
            decision = ReviewDecision.REJECT
        elif any(i.level == "warning" for i in issues):
            decision = ReviewDecision.MANUAL_REVIEW
        else:
            decision = ReviewDecision.APPROVE

        return ReviewResult(decision=decision, issues=issues)

    # =============================
    # diff パーサ（簡易版）
    # =============================

    def _parse_unified_diff(self, diff_text: str) -> list[FileChange]:
        """
        ざっくりした unified diff パーサ。
        精密さよりも「パターン検出用に最低限」が目的。
        """
        lines = diff_text.splitlines()
        files: list[FileChange] = []
        current_file: FileChange | None = None
        current_hunk: Hunk | None = None

        file_header_re = re.compile(r"^\+\+\+\s+b/(.+)$")
        hunk_header_re = re.compile(r"^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@")

        for line in lines:
            m_file = file_header_re.match(line)
            if m_file:
                # ファイル切り替え
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
                    old_start=old_start,
                    old_lines=old_lines,
                    new_start=new_start,
                    new_lines=new_lines,
                    lines=[],
                )
                continue

            if current_hunk is not None:
                current_hunk.lines.append(line)

        if current_file:
            if current_hunk:
                current_file.hunks.append(current_hunk)
            files.append(current_file)

        return files

    # =============================
    # 共通チェック
    # =============================

    def _check_sandbox_violations(self, files: Sequence[FileChange]) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []

        for fc in files:
            # 危険なパス
            for p in self.SYSTEM_PATH_PATTERNS:
                if p.search(fc.path):
                    issues.append(
                        ReviewIssue(
                            level="error",
                            code="SEC-001",
                            message=f"危険なパスへの変更が含まれています: {fc.path}",
                            file_path=fc.path,
                        )
                    )

            # 危険コマンド
            for h in fc.hunks:
                line_no = h.new_start
                for line in h.lines:
                    if not line.startswith("+"):
                        # 追加行のみチェック
                        if line.startswith("-"):
                            line_no += 1
                        continue
                    content = line[1:]
                    for pattern in self.DANGEROUS_COMMAND_PATTERNS:
                        if pattern.search(content):
                            issues.append(
                                ReviewIssue(
                                    level="error",
                                    code="SEC-002",
                                    message=f"破壊的なコマンドが追加されています: {content.strip()[:100]}",
                                    file_path=fc.path,
                                    line_no=line_no,
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

                    # 意味のないアサーション
                    if is_test_file:
                        for pattern in self.MEANINGLESS_ASSERT_PATTERNS:
                            if pattern.search(content):
                                issues.append(
                                    ReviewIssue(
                                        level="warning",
                                        code="TEST-001",
                                        message="意味の弱いアサーションが検出されました。仕様ベースの期待値で検証してください。",
                                        file_path=fc.path,
                                        line_no=line_no,
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

                    # 例外握りつぶし
                    if try_except_pass_re.search(content):
                        pass

                    if except_pass_re.search(content):
                        issues.append(
                            ReviewIssue(
                                level="error",
                                code="SAFE-001",
                                message="例外を pass で握りつぶすコードは追加禁止です。",
                                file_path=fc.path,
                                line_no=line_no,
                            )
                        )

                    # 素の except / except Exception も src では警告
                    if is_src and (
                        except_bare_re.search(content) or except_exception_re.search(content)
                    ):
                        issues.append(
                            ReviewIssue(
                                level="warning",
                                code="SAFE-002",
                                message="bare except / except Exception は運用上リスクが高いです。対象例外を絞ってください。",
                                file_path=fc.path,
                                line_no=line_no,
                            )
                        )

                    # test 用 debug フラグっぽい追加
                    if is_src and "debug=" in content and "def " in content:
                        issues.append(
                            ReviewIssue(
                                level="warning",
                                code="SAFE-003",
                                message="本番コードに debug フラグを追加していませんか？テスト専用フラグであれば _for_testing などにしてください。",
                                file_path=fc.path,
                                line_no=line_no,
                            )
                        )

                    line_no += 1

        return issues

    # =============================
    # NexusCore 専用チェック
    # =============================

    def _check_nexuscore_specific(self, files: Sequence[FileChange]) -> list[ReviewIssue]:
        issues: list[ReviewIssue] = []

        for fc in files:
            # Orchestrator のステージ順序破壊チェック（簡易）
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
                            # 削除されている場合は要注意
                            issues.append(
                                ReviewIssue(
                                    level="warning",
                                    code="NC-001",
                                    message="Orchestrator のフェーズに関わる変更があります。フェーズ順序を壊していないか確認してください。",
                                    file_path=fc.path,
                                    line_no=line_no,
                                )
                            )
                        line_no += 1

            # fkb / self-healing 周りの削除禁止（簡易）
            if "fkb" in fc.path or "failure_knowledge" in fc.path:
                for h in fc.hunks:
                    line_no = h.old_start
                    for line in h.lines:
                        if line.startswith("-"):
                            issues.append(
                                ReviewIssue(
                                    level="warning",
                                    code="NC-002",
                                    message="Failure Knowledge Base に関する削除があります。自己修復ループに影響しないか確認してください。",
                                    file_path=fc.path,
                                    line_no=line_no,
                                )
                            )
                        if line.startswith("-") or line.startswith(" "):
                            line_no += 1

        return issues

    # =============================
    # atelier-kyo-manager 専用チェック
    # =============================

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

                    # 国内サイトドメインの検出
                    for pattern in self.DOMESTIC_DOMAIN_PATTERNS:
                        if pattern.search(content):
                            issues.append(
                                ReviewIssue(
                                    level="error",
                                    code="AT-001",
                                    message="国内ECサイトURLが追加されています。BUYMA規約違反の可能性があるため禁止です。",
                                    file_path=fc.path,
                                    line_no=line_no,
                                )
                            )

                    # 利益計算ロジック周辺の変更検出（簡易）
                    if "profit" in content or "margin" in content or "利益" in content:
                        issues.append(
                            ReviewIssue(
                                level="warning",
                                code="AT-002",
                                message="利益計算ロジック周辺の変更です。ビジネス上の影響が大きいため人間レビュー推奨です。",
                                file_path=fc.path,
                                line_no=line_no,
                            )
                        )

                    line_no += 1

        return issues

    # =============================
    # policy_rules.json 連動チェック（新スキーマ対応）
    # =============================

    @staticmethod
    def _severity_to_level(severity: str) -> str:
        """policy severity → ReviewIssue level マッピング"""
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
                # allowlisted_files 除外
                file_excluded = False
                for pat in exception_rules.get("allowlisted_files", []):
                    if re.search(pat, fc.path):
                        file_excluded = True
                        break
                if file_excluded:
                    continue

                # target_file_pattern チェック
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
                            # allowed_patterns 除外
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
                                    file_path=fc.path,
                                    line_no=line_no,
                                )
                            )
                        line_no += 1

        return issues
