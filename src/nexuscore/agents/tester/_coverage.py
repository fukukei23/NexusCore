# =============================================================================
# Coverage measurement and subprocess-based test execution
# =============================================================================

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def count_test_functions(test_code: str) -> int:
    pattern = r"^\s*def\s+test_\w+"
    return len(re.findall(pattern, test_code, re.MULTILINE))


def get_coverage_for_module(project_root: Path, module_name: str) -> float:
    coverage_file = project_root / ".coverage"
    if not coverage_file.exists():
        logger.debug("No coverage file found for module '%s'. Returning 0.0", module_name)
        return 0.0

    try:
        result = subprocess.run(
            ["coverage", "json", "-o", "-", "--include", f"*{module_name}*"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning("Coverage command failed: %s", result.stderr)
            return 0.0

        data = json.loads(result.stdout)
        for key, value in data.get("files", {}).items():
            if module_name in key:
                return value.get("summary", {}).get("percent_covered", 0.0)
        return 0.0
    except Exception as e:
        logger.debug("Failed to get coverage for module '%s': %s", module_name, e)
        return 0.0


def run_tests_and_get_coverage(
    project_root: Path,
    module_name: str,
    test_file_path: Path,
) -> float:
    try:
        result = subprocess.run(
            ["coverage", "run", "-m", "pytest", str(test_file_path), "-v", "--tb=short"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            logger.info("Tests passed for %s", test_file_path)
        else:
            logger.warning("Tests failed for %s: %s", test_file_path, result.stderr)

        coverage_result = subprocess.run(
            ["coverage", "json", "-o", "-"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if coverage_result.returncode != 0:
            logger.warning("Coverage json command failed: %s", coverage_result.stderr)
            return 0.0

        data = json.loads(coverage_result.stdout)
        total_coverage = data.get("totals", {}).get("percent_covered", 0.0)
        logger.info("Coverage after tests: %s%%", total_coverage)
        return total_coverage
    except subprocess.TimeoutExpired:
        logger.error("Test execution timeout for %s", test_file_path)
    except Exception as e:
        logger.error("Failed to run tests or get coverage: %s", e, exc_info=True)
    return 0.0
