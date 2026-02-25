# ==============================================================================
# ファイル: src/nexuscore/agents/mutation_tester_agent.py
# 目的  : Tier 2品質ゲート - テストの質をミューテーションテストで検証
# ==============================================================================
"""
MutationTesterAgent: Tier 2品質ゲートの実装

ミューテーションテストを実行してテストの質を検証します。
"""
# from __future__ import annotations  # mutmut パーサーとの互換性のためコメントアウト

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from nexuscore.agents.base_agent import BaseAgent


# ==================== カスタム例外 ====================
class MutationTestError(Exception):
    """ミューテーションテスト実行時の基底エラー"""


class MutationTestTimeoutError(MutationTestError):
    """ミューテーションテストのタイムアウトエラー"""


# ==================== データクラス ====================
@dataclass
class Mutant:
    """生き残ったミュータント（バグ）の情報"""

    file_path: str
    line_number: int
    mutator: str  # 変異の種類 (例: "BinaryOperator", "ConditionalOperator")
    original_code: str
    mutated_code: str
    status: str  # "survived", "killed", "timeout", "suspicious"


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
        constitution: dict[str, Any],
        timeout_per_test: int = 10,
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

        self.logger.info("Tier 2品質ゲート開始: MutationScore≥%s%%", min_mutation_score)

        # Step 1: mutmut実行
        self.logger.info("mutmut実行中: %s", source_path)
        try:
            mutmut_result = self._run_mutmut(source_path, test_path, timeout_per_test)
        except MutationTestTimeoutError as e:
            # タイムアウト時の処理
            self.logger.error("ミューテーションテストがタイムアウトしました: %s", e)
            return MutationReport(
                passed=False,
                mutation_score=0.0,
                total_mutants=0,
                killed=0,
                survived=0,
                timeout=0,
                suspicious=0,
                survived_mutants=[],
                feedback="❌ Tier 2品質ゲート実行エラー\n\n"
                "ミューテーションテストがタイムアウトしました (600秒)。\n"
                "テスト実行時間が長すぎる可能性があります。\n"
                "- テストの実行時間を確認してください\n"
                "- 無限ループや遅い処理がないか確認してください",
            )
        except MutationTestError as e:
            # その他のエラー時の処理
            self.logger.error("ミューテーションテストの実行に失敗しました: %s", e)
            return MutationReport(
                passed=False,
                mutation_score=0.0,
                total_mutants=0,
                killed=0,
                survived=0,
                timeout=0,
                suspicious=0,
                survived_mutants=[],
                feedback=f"❌ Tier 2品質ゲート実行エラー\n\n"
                f"ミューテーションテストの実行に失敗しました。\n"
                f"エラー詳細: {str(e)}\n\n"
                f"考えられる原因:\n"
                f"- mutmutがインストールされていない\n"
                f"- テストパスが正しくない\n"
                f"- ソースコードに構文エラーがある",
            )

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
        feedback = self._generate_feedback(survived_mutants, mutation_score, min_mutation_score)

        return MutationReport(
            passed=passed,
            mutation_score=mutation_score,
            total_mutants=total,
            killed=killed,
            survived=survived,
            timeout=timeout,
            suspicious=suspicious,
            survived_mutants=survived_mutants,
            feedback=feedback,
        )

    def _run_mutmut(self, source_path: str, test_path: str, timeout: int) -> dict[str, int]:
        """
        mutmut v3.4.0を実行して結果を取得

        Returns:
            dict: {"total": X, "killed": Y, "survived": Z, ...}

        Raises:
            MutationTestTimeoutError: タイムアウト時
            MutationTestError: その他のエラー時
        """
        # 一時ディレクトリで実行
        temp_dir = tempfile.mkdtemp(prefix="mutmut_")

        try:
            # pyproject.toml生成
            pyproject_path = Path(temp_dir) / "pyproject.toml"

            with open(pyproject_path, "w", encoding="utf-8") as f:
                # TOMLフォーマットで書き込み
                f.write("[tool.mutmut]\n")
                f.write(f'paths_to_mutate = ["{source_path}"]\n')
                f.write(f'runner = "python -m pytest {test_path} -x --tb=no -q"\n')

            # mutmut実行（pyproject.tomlがあるディレクトリで実行）
            cmd = ["mutmut", "run", "--max-children", "1"]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 全体のタイムアウト: 10分
                check=False,
                cwd=temp_dir,
            )

            # 結果パース
            output = result.stdout + result.stderr
            parsed_result = self._parse_mutmut_output(output)

            # mutantsフォルダからJSON統計を読み取り
            stats_file = Path(temp_dir) / "mutants" / "mutmut-stats.json"
            if stats_file.exists():
                self.logger.info("mutmut統計ファイル発見: %s", stats_file)

            return parsed_result

        except subprocess.TimeoutExpired as e:
            self.logger.error("mutmut実行がタイムアウトしました")
            raise MutationTestTimeoutError("mutmut execution timed out after 600 seconds") from e
        except Exception as e:
            self.logger.error("mutmut実行エラー: %s", e, exc_info=True)
            raise MutationTestError(f"mutmut execution failed: {e}") from e
        finally:
            # 一時ディレクトリをクリーンアップ
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:  # pylint: disable=broad-exception-caught
                self.logger.warning("一時ディレクトリ削除失敗: %s", e)

    def _parse_mutmut_output(self, output: str) -> dict[str, int]:
        """
        mutmut の出力をパース（v2.x/v3.x 両対応）

        v3.x 出力例（絵文字ベース）:
            ⠧ 2/2  🎉 2 🫥 0  ⏰ 0  🤔 0  🙁 0  🔇 0

        v2.x 出力例（テキストベース）:
            Total mutants: 20
            Killed: 17 (85.0%)
            Survived: 3 (15.0%)

        絵文字の意味:
            🎉 = killed
            🙁 = survived
            ⏰ = timeout
            🤔 = suspicious
            🫥 = skipped
            🔇 = muted
        """
        result = {"total": 0, "killed": 0, "survived": 0, "timeout": 0, "suspicious": 0}

        # まず v3.x の絵文字ベースのパターンを試す
        emoji_patterns = {
            "total": r"(\d+)/\d+",  # "2/2" の最初の数字
            "killed": r"🎉\s*(\d+)",
            "survived": r"🙁\s*(\d+)",
            "timeout": r"⏰\s*(\d+)",
            "suspicious": r"🤔\s*(\d+)",
        }

        emoji_found = False
        for key, pattern in emoji_patterns.items():
            match = re.search(pattern, output)
            if match:
                result[key] = int(match.group(1))
                emoji_found = True

        # 絵文字形式が見つからない場合、v2.x のテキスト形式を試す
        if not emoji_found:
            text_patterns = {
                "total": r"Total mutants:\s*(\d+)",
                "killed": r"Killed:\s*(\d+)",
                "survived": r"Survived:\s*(\d+)",
                "timeout": r"Timeout:\s*(\d+)",
                "suspicious": r"Suspicious:\s*(\d+)",
            }

            for key, pattern in text_patterns.items():
                match = re.search(pattern, output)
                if match:
                    result[key] = int(match.group(1))

        # totalが見つからない場合、killed + survived + timeout + suspicious
        if result["total"] == 0:
            result["total"] = (
                result["killed"] + result["survived"] + result["timeout"] + result["suspicious"]
            )

        return result

    def _get_survived_mutants(self) -> list[Mutant]:
        """
        生き残ったミュータントの詳細を取得

        mutmut results コマンドを使用
        """
        try:
            result = subprocess.run(
                ["mutmut", "results"], capture_output=True, text=True, check=False
            )

            return self._parse_survived_mutants(result.stdout)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("ミュータント詳細取得エラー: %s", e)
            return []

    def _parse_survived_mutants(self, output: str) -> list[Mutant]:
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
        lines = output.split("\n")
        current_mutant = None

        for line in lines:
            # ファイル:行番号のパターン
            match = re.match(r"(\d+)\.\s+(.+?):(\d+)", line)
            if match:
                if current_mutant:
                    mutants.append(current_mutant)

                current_mutant = Mutant(
                    file_path=match.group(2),
                    line_number=int(match.group(3)),
                    mutator="Unknown",
                    original_code="",
                    mutated_code="",
                    status="survived",
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
        self, survived_mutants: list[Mutant], mutation_score: float, min_score: float
    ) -> str:
        """
        TesterAgentへの具体的なフィードバックを生成
        """
        if mutation_score >= min_score:
            return f"✅ ミューテーションスコア {mutation_score:.1f}% - 基準をクリアしました。"

        feedback_lines = [
            "❌ Tier 2品質ゲート不合格",
            f"ミューテーションスコア: {mutation_score:.1f}% < {min_score}% (最低基準)\n",
            f"以下の{len(survived_mutants)}個のミュータントが生き残りました。",
            "テストを追加してバグ検出能力を向上させてください。\n",
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
