"""
NexusCore テスト結果レポート生成ツール

pytest の実行結果を解析し、構造化されたMarkdownレポートを作成する。

使用方法:
    python -m dev_tools.test_result_reporter [pytest結果JSONファイル] [出力ディレクトリ]
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from _pytest.terminal import TerminalReporter
import pytest


def parse_pytest_output(output: str) -> Dict[str, Any]:
    """
    pytest の標準出力から結果を解析する。

    Args:
        output: pytest の標準出力文字列

    Returns:
        解析結果の辞書
    """
    result: Dict[str, Any] = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "errors": 0,
        "failed_tests": [],
        "error_tests": [],
        "execution_time": None,
    }

    # 合計テスト数の抽出
    total_match = re.search(r"(\d+)\s+(?:passed|failed|error|skipped)", output)
    if total_match:
        result["total"] = int(total_match.group(1))

    # passed/failed/skipped/error の抽出
    passed_match = re.search(r"(\d+)\s+passed", output)
    if passed_match:
        result["passed"] = int(passed_match.group(1))

    failed_match = re.search(r"(\d+)\s+failed", output)
    if failed_match:
        result["failed"] = int(failed_match.group(1))

    skipped_match = re.search(r"(\d+)\s+skipped", output)
    if skipped_match:
        result["skipped"] = int(skipped_match.group(1))

    error_match = re.search(r"(\d+)\s+error", output)
    if error_match:
        result["errors"] = int(error_match.group(1))

    # 実行時間の抽出
    time_match = re.search(r"in\s+([\d.]+)\s*(?:s|seconds)", output)
    if time_match:
        result["execution_time"] = float(time_match.group(1))

    # 失敗したテストの抽出
    failed_test_pattern = r"FAILED\s+(.+?)(?=\n|$)"
    failed_tests = re.findall(failed_test_pattern, output)
    result["failed_tests"] = [test.strip() for test in failed_tests]

    # エラーテストの抽出
    error_test_pattern = r"ERROR\s+(.+?)(?=\n|$)"
    error_tests = re.findall(error_test_pattern, output)
    result["error_tests"] = [test.strip() for test in error_tests]

    return result


def generate_test_result_report(
    result_data: Dict[str, Any],
    test_target: str,
    output_dir: Path,
    timestamp: str,
) -> Path:
    """
    テスト結果レポート（Markdown）を生成する。

    Args:
        result_data: テスト結果データ
        test_target: 実行したテストターゲット（例: "tests/", "tests/core/"）
        output_dir: 出力ディレクトリ
        timestamp: タイムスタンプ（YYYYMMDD_HHMMSS形式）

    Returns:
        生成されたレポートファイルのパス
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    report_file = output_dir / f"TEST_RESULT_{timestamp}.md"

    # ステータス判定
    if result_data["failed"] > 0 or result_data["errors"] > 0:
        status_emoji = "❌"
        status_text = "失敗"
    elif result_data["skipped"] == result_data["total"]:
        status_emoji = "⚠️"
        status_text = "スキップのみ"
    else:
        status_emoji = "✅"
        status_text = "成功"

    # 成功率計算
    if result_data["total"] > 0:
        success_rate = (result_data["passed"] / result_data["total"]) * 100
    else:
        success_rate = 0.0

    # Markdownレポート生成
    lines = [
        f"# テスト実行結果レポート",
        "",
        f"**実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**テストターゲット**: `{test_target}`",
        f"**ステータス**: {status_emoji} {status_text}",
        "",
        "## サマリー",
        "",
        "| 項目 | 値 |",
        "|------|-----|",
        f"| 合計テスト数 | {result_data['total']} |",
        f"| ✅ 成功 | {result_data['passed']} |",
        f"| ❌ 失敗 | {result_data['failed']} |",
        f"| ⚠️ スキップ | {result_data['skipped']} |",
        f"| 🚫 エラー | {result_data['errors']} |",
        f"| 成功率 | {success_rate:.1f}% |",
    ]

    if result_data.get("execution_time"):
        lines.append(f"| 実行時間 | {result_data['execution_time']:.2f}秒 |")

    lines.extend(["", "## 詳細", ""])

    # 失敗したテスト
    if result_data["failed_tests"]:
        lines.append("### ❌ 失敗したテスト")
        lines.append("")
        for test in result_data["failed_tests"]:
            lines.append(f"- `{test}`")
        lines.append("")

    # エラーテスト
    if result_data["error_tests"]:
        lines.append("### 🚫 エラーテスト")
        lines.append("")
        for test in result_data["error_tests"]:
            lines.append(f"- `{test}`")
        lines.append("")

    # すべて成功の場合
    if result_data["failed"] == 0 and result_data["errors"] == 0:
        lines.append("🎉 すべてのテストが成功しました！")
        lines.append("")

    lines.extend([
        "---",
        f"*このレポートは自動生成されました（{timestamp}）*",
    ])

    report_file.write_text("\n".join(lines), encoding="utf-8")
    return report_file


def generate_json_report(
    result_data: Dict[str, Any],
    test_target: str,
    output_dir: Path,
    timestamp: str,
) -> Path:
    """
    テスト結果レポート（JSON）を生成する。

    Args:
        result_data: テスト結果データ
        test_target: 実行したテストターゲット
        output_dir: 出力ディレクトリ
        timestamp: タイムスタンプ

    Returns:
        生成されたJSONファイルのパス
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    json_file = output_dir / f"TEST_RESULT_{timestamp}.json"

    report_data = {
        "timestamp": timestamp,
        "executed_at": datetime.now().isoformat(),
        "test_target": test_target,
        "result": result_data,
    }

    json_file.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return json_file


def main() -> int:
    """
    メイン関数。

    pytest の結果を読み取り、レポートを生成する。
    """
    if len(sys.argv) < 3:
        print("Usage: python -m dev_tools.test_result_reporter <pytest_output_file> <output_dir> [test_target]")
        return 1

    pytest_output_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    test_target = sys.argv[3] if len(sys.argv) > 3 else "tests/"

    if not pytest_output_file.exists():
        print(f"Error: pytest output file not found: {pytest_output_file}")
        return 1

    # pytest の出力を読み取り
    output = pytest_output_file.read_text(encoding="utf-8")

    # 結果を解析
    result_data = parse_pytest_output(output)

    # タイムスタンプ生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # レポート生成
    md_report = generate_test_result_report(result_data, test_target, output_dir, timestamp)
    json_report = generate_json_report(result_data, test_target, output_dir, timestamp)

    print(f"✅ テスト結果レポートを生成しました:")
    print(f"   - Markdown: {md_report}")
    print(f"   - JSON: {json_report}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

