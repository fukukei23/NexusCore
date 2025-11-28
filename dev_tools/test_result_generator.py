"""
NexusCore テスト結果自動生成ツール

pytest の実行結果を解析し、構造化されたMarkdownレポートを作成する。

使用方法:
    python -m dev_tools.test_result_generator [pytest標準出力ファイル] [テストターゲット] [出力ディレクトリ]
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


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

    # 合計テスト数の抽出（最後のサマリー行を探す）
    summary_match = re.search(
        r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+error|(\d+)\s+skipped", output
    )
    if summary_match:
        # 最後のサマリー行を探す
        summary_lines = re.findall(
            r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+error|(\d+)\s+skipped", output
        )
        if summary_lines:
            for line in summary_lines:
                if line[0]:
                    result["total"] = max(result["total"], int(line[0]))
                    result["passed"] = max(result["passed"], int(line[0]))
                if line[1]:
                    result["failed"] = max(result["failed"], int(line[1]))
                if line[2]:
                    result["errors"] = max(result["errors"], int(line[2]))
                if line[3]:
                    result["skipped"] = max(result["skipped"], int(line[3]))

    # より正確なパターンで抽出を試みる
    final_summary = re.search(
        r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+error|(\d+)\s+skipped", output
    )
    if not final_summary:
        # 別のパターンを試す
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

    # 合計を計算
    result["total"] = result["passed"] + result["failed"] + result["skipped"] + result["errors"]

    # 実行時間の抽出
    time_match = re.search(r"in\s+([\d.]+)\s*(?:s|seconds)", output)
    if time_match:
        result["execution_time"] = float(time_match.group(1))

    # 失敗したテストの抽出
    failed_test_pattern = r"FAILED\s+(.+?)(?=\n|$)"
    failed_tests = re.findall(failed_test_pattern, output)
    result["failed_tests"] = [test.strip() for test in failed_tests if test.strip()]

    # エラーテストの抽出
    error_test_pattern = r"ERROR\s+(.+?)(?=\n|$)"
    error_tests = re.findall(error_test_pattern, output)
    result["error_tests"] = [test.strip() for test in error_tests if test.strip()]

    return result


def generate_test_result_markdown(
    result_data: Dict[str, Any],
    test_target: str,
    output_dir: Path,
    timestamp: str,
    stdout: str = "",
) -> Path:
    """
    テスト結果レポート（Markdown）を生成する。

    Args:
        result_data: テスト結果データ
        test_target: 実行したテストターゲット（例: "tests/", "tests/core/"）
        output_dir: 出力ディレクトリ
        timestamp: タイムスタンプ（YYYYMMDD_HHMMSS形式）
        stdout: pytest の標準出力（詳細表示用）

    Returns:
        生成されたレポートファイルのパス
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    report_file = output_dir / f"TEST_RESULT_{timestamp}.md"

    # 結果データから値を抽出
    total = result_data.get("total", 0)
    passed = result_data.get("passed", 0)
    failed = result_data.get("failed", 0)
    skipped = result_data.get("skipped", 0)
    errors = result_data.get("errors", 0)
    execution_time = result_data.get("execution_time")

    # ステータス判定
    if failed > 0 or errors > 0:
        status_emoji = "❌"
        status_text = "失敗"
    elif skipped == total and total > 0:
        status_emoji = "⚠️"
        status_text = "スキップのみ"
    elif total == 0:
        status_emoji = "⚠️"
        status_text = "テストなし"
    else:
        status_emoji = "✅"
        status_text = "成功"

    # 成功率計算
    if total > 0:
        success_rate = (passed / total) * 100
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
        f"| 合計テスト数 | {total} |",
        f"| ✅ 成功 | {passed} |",
        f"| ❌ 失敗 | {failed} |",
        f"| ⚠️ スキップ | {skipped} |",
        f"| 🚫 エラー | {errors} |",
        f"| 成功率 | {success_rate:.1f}% |",
    ]

    if execution_time:
        lines.append(f"| 実行時間 | {execution_time:.2f}秒 |")

    lines.extend(["", "## 詳細", ""])

    # 失敗したテスト
    failed_tests = result_data.get("failed_tests", [])
    if failed_tests:
        lines.append("### ❌ 失敗したテスト")
        lines.append("")
        for test in failed_tests[:20]:  # 最大20件まで
            lines.append(f"- `{test}`")
        if len(failed_tests) > 20:
            lines.append(f"- ... 他 {len(failed_tests) - 20} 件")
        lines.append("")

    # エラーテスト
    error_tests = result_data.get("error_tests", [])
    if error_tests:
        lines.append("### 🚫 エラーテスト")
        lines.append("")
        for test in error_tests[:20]:
            lines.append(f"- `{test}`")
        if len(error_tests) > 20:
            lines.append(f"- ... 他 {len(error_tests) - 20} 件")
        lines.append("")

    # すべて成功の場合
    if failed == 0 and errors == 0 and total > 0:
        lines.append("🎉 すべてのテストが成功しました！")
        lines.append("")

    # 詳細出力（折りたたみ）
    if stdout:
        lines.extend([
            "<details>",
            "<summary>詳細出力（pytest標準出力）</summary>",
            "",
            "```",
            stdout[:5000] + ("..." if len(stdout) > 5000 else ""),  # 最大5000文字
            "```",
            "",
            "</details>",
            "",
        ])

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

    使用方法:
        python -m dev_tools.test_result_generator <pytest_output_file> <test_target> [output_dir]
    """
    if len(sys.argv) < 3:
        print("Usage: python -m dev_tools.test_result_generator <pytest_output_file> <test_target> [output_dir]")
        print("  pytest_output_file: pytest の標準出力が保存されたファイル")
        print("  test_target: 実行したテストターゲット（例: 'tests/', 'tests/core/'）")
        print("  output_dir: 出力ディレクトリ（省略時は 'test_results/'）")
        return 1

    pytest_output_file = Path(sys.argv[1])
    test_target = sys.argv[2]
    output_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("test_results")

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
    md_report = generate_test_result_markdown(result_data, test_target, output_dir, timestamp, output)
    json_report = generate_json_report(result_data, test_target, output_dir, timestamp)

    print(f"✅ テスト結果レポートを生成しました:")
    print(f"   - Markdown: {md_report}")
    print(f"   - JSON: {json_report}")

    # 結果のサマリーを表示
    total = result_data.get("total", 0)
    passed = result_data.get("passed", 0)
    failed = result_data.get("failed", 0)
    skipped = result_data.get("skipped", 0)
    errors = result_data.get("errors", 0)

    print(f"\n📊 テスト結果サマリー:")
    print(f"   合計: {total} / 成功: {passed} / 失敗: {failed} / スキップ: {skipped} / エラー: {errors}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
