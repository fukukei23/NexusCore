from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .mutation_tester._models import (  # noqa: F401 — legacy re-exports
    Mutant,
    MutationReport,
    MutationTestError,
    MutationTestTimeoutError,
)
from .mutation_tester._runner import (
    get_survived_mutants as _get_survived_mutants,
    parse_mutmut_output as _parse_mutmut_output,
    parse_survived_mutants as _parse_survived_mutants,
    run_mutmut as _run_mutmut,
)


class MutationTesterAgent(BaseAgent):
    """Tier 2品質ゲート: ミューテーションテストでテストの質を検証"""

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
        constitution: dict[str, Any],
        timeout_per_test: int = 10,
    ) -> MutationReport:
        """ミューテーションテストを実行"""
        tier2_config = constitution.get("quality_gates", {}).get("tier2", {})
        min_mutation_score = tier2_config.get("mutation_score_min", 80)

        self.logger.info("Tier 2品質ゲート開始: MutationScore≥%s%%", min_mutation_score)

        self.logger.info("mutmut実行中: %s", source_path)
        try:
            mutmut_result = self._run_mutmut(source_path, test_path, timeout_per_test)
        except MutationTestTimeoutError as e:
            self.logger.error("ミューテーションテストがタイムアウトしました: %s", e)
            return MutationReport(
                passed=False, mutation_score=0.0, total_mutants=0, killed=0, survived=0,
                timeout=0, suspicious=0, survived_mutants=[],
                feedback="❌ Tier 2品質ゲート実行エラー\n\n"
                "ミューテーションテストがタイムアウトしました (600秒)。\n"
                "テスト実行時間が長すぎる可能性があります。\n"
                "- テストの実行時間を確認してください\n"
                "- 無限ループや遅い処理がないか確認してください",
            )
        except MutationTestError as e:
            self.logger.error("ミューテーションテストの実行に失敗しました: %s", e)
            return MutationReport(
                passed=False, mutation_score=0.0, total_mutants=0, killed=0, survived=0,
                timeout=0, suspicious=0, survived_mutants=[],
                feedback=f"❌ Tier 2品質ゲート実行エラー\n\n"
                f"ミューテーションテストの実行に失敗しました。\n"
                f"エラー詳細: {str(e)}\n\n"
                f"考えられる原因:\n"
                f"- mutmutがインストールされていない\n"
                f"- テストパスが正しくない\n"
                f"- ソースコードに構文エラーがある",
            )

        total = mutmut_result["total"]
        killed = mutmut_result["killed"]
        survived = mutmut_result["survived"]
        timeout = mutmut_result["timeout"]
        suspicious = mutmut_result["suspicious"]

        mutation_score = (killed / total * 100) if total > 0 else 0.0
        passed = mutation_score >= min_mutation_score

        survived_mutants = self._get_survived_mutants() if survived > 0 else []
        feedback = self._generate_feedback(survived_mutants, mutation_score, min_mutation_score)

        return MutationReport(
            passed=passed, mutation_score=mutation_score, total_mutants=total,
            killed=killed, survived=survived, timeout=timeout, suspicious=suspicious,
            survived_mutants=survived_mutants, feedback=feedback,
        )

    def _generate_feedback(
        self, survived_mutants: list[Mutant], mutation_score: float, min_score: float
    ) -> str:
        """TesterAgentへの具体的なフィードバックを生成"""
        if mutation_score >= min_score:
            return f"✅ ミューテーションスコア {mutation_score:.1f}% - 基準をクリアしました。"

        feedback_lines = [
            "❌ Tier 2品質ゲート不合格",
            f"ミューテーションスコア: {mutation_score:.1f}% < {min_score}% (最低基準)\n",
            f"以下の{len(survived_mutants)}個のミュータントが生き残りました。",
            "テストを追加してバグ検出能力を向上させてください。\n",
        ]

        for i, mutant in enumerate(survived_mutants[:10], 1):
            feedback_lines.append(f"{i}. ファイル: {mutant.file_path}:{mutant.line_number}")
            feedback_lines.append(f"   変更前: {mutant.original_code}")
            feedback_lines.append(f"   変更後: {mutant.mutated_code}")

            suggestion = self._suggest_test_for_mutant(mutant)
            if suggestion:
                feedback_lines.append(f"   💡 提案: {suggestion}")

            feedback_lines.append("")

        if len(survived_mutants) > 10:
            feedback_lines.append(f"... 他 {len(survived_mutants) - 10}個のミュータント")

        return "\n".join(feedback_lines)

    def _suggest_test_for_mutant(self, mutant: Mutant) -> str:
        """ミュータントの種類から、必要なテストケースを提案"""
        original = mutant.original_code.lower()
        mutated = mutant.mutated_code.lower()

        if "+" in original and "-" in mutated:
            return "加算と減算の境界テストを追加してください。"
        elif "-" in original and "+" in mutated:
            return "減算と加算の境界テストを追加してください。"
        elif "*" in original and "/" in mutated:
            return "乗算と除算のテストケースを追加してください。"
        elif ">" in original and ">=" in mutated:
            return "境界値（等号を含む条件）のテストを追加してください。"
        elif ">=" in original and ">" in mutated:
            return "境界値（等号の有無）のテストを追加してください。"
        elif "<" in original and "<=" in mutated:
            return "境界値（等号を含む条件）のテストを追加してください。"
        elif "and" in original and "or" in mutated:
            return "論理演算子の真偽値テーブルを網羅するテストを追加してください。"
        elif "or" in original and "and" in mutated:
            return "論理演算子の真偽値テーブルを網羅するテストを追加してください。"

        return "この変更を検出できるテストケースを追加してください。"

    # Legacy method aliases for backward compatibility with tests
    def _run_mutmut(self, source_path: str, test_path: str, timeout: int) -> dict[str, int]:
        return _run_mutmut(source_path, test_path, timeout, self.logger)

    def _parse_mutmut_output(self, output: str) -> dict[str, int]:
        return _parse_mutmut_output(output)

    def _get_survived_mutants(self) -> list[Mutant]:
        return _get_survived_mutants(self.logger)

    def _parse_survived_mutants(self, output: str) -> list[Mutant]:
        return _parse_survived_mutants(output)
