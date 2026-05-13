from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class MutationTestError(Exception):
    """ミューテーションテスト実行時の基底エラー"""


class MutationTestTimeoutError(MutationTestError):
    """ミューテーションテストのタイムアウトエラー"""


@dataclass
class Mutant:
    """生き残ったミュータント（バグ）の情報"""

    file_path: str
    line_number: int
    mutator: str
    original_code: str
    mutated_code: str
    status: str


@dataclass
class MutationReport:
    """Tier 2 品質ゲートの結果レポート"""

    passed: bool
    mutation_score: float
    total_mutants: int
    killed: int
    survived: int
    timeout: int
    suspicious: int
    survived_mutants: list[Mutant] = field(default_factory=list)
    feedback: str = ""

    def to_dict(self) -> dict[str, Any]:
        """MutationReportを辞書形式に変換"""
        return {
            "passed": self.passed,
            "mutation_score": self.mutation_score,
            "total_mutants": self.total_mutants,
            "killed": self.killed,
            "survived": self.survived,
            "timeout": self.timeout,
            "suspicious": self.suspicious,
            "survived_count": len(self.survived_mutants),
        }
