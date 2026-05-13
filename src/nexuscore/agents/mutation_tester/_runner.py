from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from nexuscore.agents.mutation_tester._models import Mutant, MutationTestError, MutationTestTimeoutError


def run_mutmut(source_path: str, test_path: str, timeout: int, logger) -> dict[str, int]:
    """
    mutmut v3.4.0を実行して結果を取得。

    Raises:
        MutationTestTimeoutError: タイムアウト時
        MutationTestError: その他のエラー時
    """
    temp_dir = tempfile.mkdtemp(prefix="mutmut_")

    try:
        pyproject_path = Path(temp_dir) / "pyproject.toml"

        with open(pyproject_path, "w", encoding="utf-8") as f:
            f.write("[tool.mutmut]\n")
            f.write(f'paths_to_mutate = ["{source_path}"]\n')
            f.write(f'runner = "python -m pytest {test_path} -x --tb=no -q"\n')

        cmd = ["mutmut", "run", "--max-children", "1"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
            cwd=temp_dir,
        )

        output = result.stdout + result.stderr
        parsed_result = parse_mutmut_output(output)

        stats_file = Path(temp_dir) / "mutants" / "mutmut-stats.json"
        if stats_file.exists():
            logger.info("mutmut統計ファイル発見: %s", stats_file)

        return parsed_result

    except subprocess.TimeoutExpired as e:
        logger.error("mutmut実行がタイムアウトしました")
        raise MutationTestTimeoutError("mutmut execution timed out after 600 seconds") from e
    except Exception as e:
        logger.error("mutmut実行エラー: %s", e, exc_info=True)
        raise MutationTestError(f"mutmut execution failed: {e}") from e
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning("一時ディレクトリ削除失敗: %s", e)


def parse_mutmut_output(output: str) -> dict[str, int]:
    """mutmut の出力をパース（v2.x/v3.x 両対応）。"""
    result: dict[str, int] = {"total": 0, "killed": 0, "survived": 0, "timeout": 0, "suspicious": 0}

    emoji_patterns = {
        "total": r"(\d+)/\d+",
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

    if result["total"] == 0:
        result["total"] = (
            result["killed"] + result["survived"] + result["timeout"] + result["suspicious"]
        )

    return result


def get_survived_mutants(logger) -> list[Mutant]:
    """生き残ったミュータントの詳細を取得。"""
    try:
        result = subprocess.run(
            ["mutmut", "results"], capture_output=True, text=True, check=False
        )

        return parse_survived_mutants(result.stdout)

    except Exception as e:
        logger.error("ミュータント詳細取得エラー: %s", e)
        return []


def parse_survived_mutants(output: str) -> list[Mutant]:
    """mutmut resultsの出力をパース。"""
    mutants: list[Mutant] = []
    lines = output.split("\n")
    current_mutant: Mutant | None = None

    for line in lines:
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

        elif current_mutant and "- from:" in line:
            current_mutant.original_code = line.split("from:")[1].strip()
        elif current_mutant and "- to:" in line:
            current_mutant.mutated_code = line.split("to:")[1].strip()

    if current_mutant:
        mutants.append(current_mutant)

    return mutants
