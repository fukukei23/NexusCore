# ==============================================================================
# ファイル: src/nexuscore/agents/mutation_tester_agent.py
# 目的  : Tier 2品質ゲート - テストの質をミューテーションテストで検証
# ==============================================================================
from __future__ import annotations

import subprocess
import re
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from nexuscore.agents.base_agent import BaseAgent


@dataclass
class Mutant:
    """生き残ったミュータント（バグ）の情報"""
    file_path: str
    line_number: int
    mutator: str          # 変異の種類 (例: "BinaryOperator", "ConditionalOperator")
    original_code: str
    mutated_code: str
    status: str           # "survived", "killed", "timeout", "suspicious"


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

    survived_mutants: List[Mutant] = field(default_factory=list)
    feedback: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "passed": self.passed,
            "mutation_score": self.mutation_score,
            "total_mutants": self.total_mutants,
            "killed": self.killed,
            "survived": self.survived,
            "timeout": self.timeout,
            "suspicious": self.suspicious,
            "survived_count": len(self.survived_mutants)
        }


class MutationTesterAgent(BaseAgent):
    """
    Tier 2品質ゲート: ミューテーションテストでテストの質を検証

    役割:
        - mutmutを使用してミュータントを生成
        - テストスイートを実行してバグ検出能力を測定
        - 生き残ったミュータントを分析してフィードバック生成
    """

    SYSTEM_PROMPT = (
        "You are a mutation testing expert. "
        "Analyze survived mutants and provide actionable feedback "
        "to improve test quality."
    )

    def __init__(self):
        super().__init__()
        self.logger.info("MutationTesterAgent initialized")

    def run_mutation_testing(
        self,
        source_path: str,
        test_path: str,
        constitution: Dict[str, Any],
        timeout_per_test: int = 10
    ) -> MutationReport:
        """
        ミューテーションテストを実行

        Args:
            source_path: ミュータント生成対象のソースコード
            test_path: テストコードのパス
            constitution: 憲法（品質基準）
            timeout_per_test: 各テストのタイムアウト（秒）

        Returns:
            MutationReport: 詳細なレポート
        """
        tier2_config = constitution.get("quality_gates", {}).get("tier2", {})
        min_mutation_score = tier2_config.get("mutation_score_min", 80)

        self.logger.info(f"Tier 2品質ゲート開始: MutationScore≥{min_mutation_score}%")

        # Step 1: mutmut実行
        self.logger.info(f"mutmut実行中: {source_path}")
        mutmut_result = self._run_mutmut(source_path, test_path, timeout_per_test)

        # Step 2: 結果パース
        total = mutmut_result["total"]
        killed = mutmut_result["killed"]
        survived = mutmut_result["survived"]
        timeout = mutmut_result["timeout"]
        suspicious = mutmut_result["suspicious"]

        mutation_score = (killed / total * 100) if total > 0 else 0.0
        passed = mutation_score >= min_mutation_score

        # Step 3: 生き残ったミュータントの詳細取得
        survived_mutants = self._get_survived_mutants() if survived > 0 else []

        # Step 4: フィードバック生成
        feedback = self._generate_feedback(
            survived_mutants,
            mutation_score,
            min_mutation_score
        )

        return MutationReport(
            passed=passed,
            mutation_score=mutation_score,
            total_mutants=total,
            killed=killed,
            survived=survived,
            timeout=timeout,
            suspicious=suspicious,
            survived_mutants=survived_mutants,
            feedback=feedback
        )

    def _run_mutmut(
        self,
        source_path: str,
        test_path: str,
        timeout: int
    ) -> Dict[str, int]:
        """
        mutmutを実行して結果を取得

        Returns:
            dict: {"total": X, "killed": Y, "survived": Z, ...}
        """
        # mutmutキャッシュをクリア
        subprocess.run(["mutmut", "run", "--rerun-all"], capture_output=True)

        # mutmut実行
        cmd = [
            "mutmut",
            "run",
            "--paths-to-mutate", source_path,
            "--tests-dir", test_path,
            "--runner", "python -m pytest",
            "--timeout", str(timeout)
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 全体のタイムアウト: 10分
            )

            # 結果パース
            output = result.stdout + result.stderr
            return self._parse_mutmut_output(output)

        except subprocess.TimeoutExpired:
            self.logger.error("mutmut実行がタイムアウトしました")
            return {"total": 0, "killed": 0, "survived": 0, "timeout": 0, "suspicious": 0}
        except Exception as e:
            self.logger.error(f"mutmut実行エラー: {e}", exc_info=True)
            return {"total": 0, "killed": 0, "survived": 0, "timeout": 0, "suspicious": 0}

    def _parse_mutmut_output(self, output: str) -> Dict[str, int]:
        """
        mutmutの出力をパース

        出力例:
            Total mutants: 120
            Killed: 96 (80.0%)
            Survived: 18 (15.0%)
            Timeout: 4 (3.3%)
            Suspicious: 2 (1.7%)
        """
        result = {
            "total": 0,
            "killed": 0,
            "survived": 0,
            "timeout": 0,
            "suspicious": 0
        }

        patterns = {
            "total": r"Total mutants:\s*(\d+)",
            "killed": r"Killed:\s*(\d+)",
            "survived": r"Survived:\s*(\d+)",
            "timeout": r"Timeout:\s*(\d+)",
            "suspicious": r"Suspicious:\s*(\d+)"
        }

        for key, pattern in patterns.items():
            match = re.search(pattern, output)
            if match:
                result[key] = int(match.group(1))

        return result

    def _get_survived_mutants(self) -> List[Mutant]:
        """
        生き残ったミュータントの詳細を取得

        mutmut results コマンドを使用
        """
        try:
            result = subprocess.run(
                ["mutmut", "results"],
                capture_output=True,
                text=True
            )

            return self._parse_survived_mutants(result.stdout)

        except Exception as e:
            self.logger.error(f"ミュータント詳細取得エラー: {e}")
            return []

    def _parse_survived_mutants(self, output: str) -> List[Mutant]:
        """
        mutmut resultsの出力をパース

        出力例:
            To apply a mutant on disk:
                mutmut apply <id>

            Survived 🙁

            1. src/calculator.py:15
               - from: result = a + b
               - to:   result = a - b
        """
        mutants = []

        # 簡易実装: 実際のmutmut出力に合わせて調整が必要
        lines = output.split('\n')
        current_mutant = None

        for line in lines:
            # ファイル:行番号のパターン
            match = re.match(r'(\d+)\.\s+(.+?):(\d+)', line)
            if match:
                if current_mutant:
                    mutants.append(current_mutant)

                current_mutant = Mutant(
                    file_path=match.group(2),
                    line_number=int(match.group(3)),
                    mutator="Unknown",
                    original_code="",
                    mutated_code="",
                    status="survived"
                )

            # from/toのパターン
            elif current_mutant and "- from:" in line:
                current_mutant.original_code = line.split("from:")[1].strip()
            elif current_mutant and "- to:" in line:
                current_mutant.mutated_code = line.split("to:")[1].strip()

        if current_mutant:
            mutants.append(current_mutant)

        return mutants

    def _generate_feedback(
        self,
        survived_mutants: List[Mutant],
        mutation_score: float,
        min_score: float
    ) -> str:
        """
        TesterAgentへの具体的なフィードバックを生成
        """
        if mutation_score >= min_score:
            return f"✅ ミューテーションスコア {mutation_score:.1f}% - 基準をクリアしました。"

        feedback_lines = [
            f"❌ Tier 2品質ゲート不合格",
            f"ミューテーションスコア: {mutation_score:.1f}% < {min_score}% (最低基準)\n",
            f"以下の{len(survived_mutants)}個のミュータントが生き残りました。",
            "テストを追加してバグ検出能力を向上させてください。\n"
        ]

        for i, mutant in enumerate(survived_mutants[:10], 1):  # 最初の10個のみ
            feedback_lines.append(f"{i}. ファイル: {mutant.file_path}:{mutant.line_number}")
            feedback_lines.append(f"   変更前: {mutant.original_code}")
            feedback_lines.append(f"   変更後: {mutant.mutated_code}")

            # 変異の種類から推奨テストを提案
            suggestion = self._suggest_test_for_mutant(mutant)
            if suggestion:
                feedback_lines.append(f"   💡 提案: {suggestion}")

            feedback_lines.append("")

        if len(survived_mutants) > 10:
            feedback_lines.append(f"... 他 {len(survived_mutants) - 10}個のミュータント")

        return "\n".join(feedback_lines)

    def _suggest_test_for_mutant(self, mutant: Mutant) -> str:
        """
        ミュータントの種類から、必要なテストケースを提案
        """
        original = mutant.original_code.lower()
        mutated = mutant.mutated_code.lower()

        # 演算子の変更
        if "+" in original and "-" in mutated:
            return "加算と減算の境界テストを追加してください。"
        elif "-" in original and "+" in mutated:
            return "減算と加算の境界テストを追加してください。"
        elif "*" in original and "/" in mutated:
            return "乗算と除算のテストケースを追加してください。"

        # 比較演算子の変更
        elif ">" in original and ">=" in mutated:
            return "境界値（等号を含む条件）のテストを追加してください。"
        elif ">=" in original and ">" in mutated:
            return "境界値（等号の有無）のテストを追加してください。"
        elif "<" in original and "<=" in mutated:
            return "境界値（等号を含む条件）のテストを追加してください。"

        # 論理演算子の変更
        elif "and" in original and "or" in mutated:
            return "論理演算子の真偽値テーブルを網羅するテストを追加してください。"
        elif "or" in original and "and" in mutated:
            return "論理演算子の真偽値テーブルを網羅するテストを追加してください。"

        # デフォルト
        return "この変更を検出できるテストケースを追加してください。"
