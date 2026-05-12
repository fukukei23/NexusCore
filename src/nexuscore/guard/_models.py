"""Guardian auto-reviewer data models and enums."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class ReviewDecision(enum.StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    MANUAL_REVIEW = "manual_review"


@dataclass
class ReviewIssue:
    """個別の指摘事項。"""

    level: str  # "error" | "warning" | "info"
    code: str  # 例: "SEC-001", "TEST-003", etc.
    message: str
    file_path: str | None = None
    line_no: int | None = None


@dataclass
class ReviewResult:
    """GuardianAgent が使うレビュー結果の構造。"""

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
    """diff解析済みの1ファイル分の変更情報。"""

    path: str
    hunks: list[Hunk]


@dataclass
class Hunk:
    """unified diff の hunk 情報。"""

    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    lines: list[str]
