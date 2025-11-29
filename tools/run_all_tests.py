#!/usr/bin/env python3
"""
全体のテストを実行し、結果レポートを生成するスクリプト
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "test_results"
RESULTS_DIR.mkdir(exist_ok=True)

def run_tests():
    """pytest を実行して結果を返す"""
    print("🧪 全体のテストを実行中...")
    print("=" * 80)

    # pytest を実行
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "-q",  # 最後にサマリーを表示
    ]

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=600,  # 10分でタイムアウト
    )

    return result

def generate_summary(result: subprocess.CompletedProcess) -> dict:
    """テスト結果からサマリーを生成"""
    output = result.stdout + result.stderr

    # サマリー行を探す
    lines = output.split('\n')
    summary = {
        'total': 0,
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'duration': None,
    }

    for line in lines:
        if 'passed' in line and 'failed' in line:
            # pytest のサマリー行をパース
            parts = line.split()
            for part in parts:
                if part.isdigit():
                    if 'passed' in line and summary['passed'] == 0:
                        summary['passed'] = int(part)
                    elif 'failed' in line and summary['failed'] == 0:
                        summary['failed'] = int(part)
                    elif 'skipped' in line:
                        summary['skipped'] = int(part)
                    elif 'error' in line.lower():
                        summary['errors'] = int(part)

        if 'in ' in line and 's' in line and summary['duration'] is None:
            # 実行時間を抽出
            try:
                import re
                match = re.search(r'in (\d+\.?\d*)s', line)
                if match:
                    summary['duration'] = float(match.group(1))
            except:
                pass

    # 失敗したテストを抽出
    failed_tests = []
    in_failure = False
    current_test = None

    for line in lines:
        if 'FAILED' in line or 'ERROR' in line:
            # テスト名を抽出
            parts = line.split()
            for i, part in enumerate(parts):
                if 'FAILED' in part or 'ERROR' in part:
                    if i > 0:
                        current_test = parts[i-1]
                        break
            if current_test:
                failed_tests.append(current_test)

    summary['failed_tests'] = failed_tests
    summary['return_code'] = result.returncode
    summary['success'] = result.returncode == 0

    return summary

def main():
    """メイン処理"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = RESULTS_DIR / f"TEST_RESULT_{timestamp}.md"
    json_file = RESULTS_DIR / f"TEST_RESULT_{timestamp}.json"

    # テスト実行
    result = run_tests()

    # サマリー生成
    summary = generate_summary(result)
    summary['output'] = result.stdout + result.stderr

    # JSON レポート
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Markdown レポート
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(f"# テスト結果レポート\n\n")
        f.write(f"**実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## サマリー\n\n")
        f.write(f"- **合計テスト数**: {summary.get('total', 'N/A')}\n")
        f.write(f"- **成功**: {summary['passed']}\n")
        f.write(f"- **失敗**: {summary['failed']}\n")
        f.write(f"- **スキップ**: {summary['skipped']}\n")
        f.write(f"- **エラー**: {summary['errors']}\n")
        if summary['duration']:
            f.write(f"- **実行時間**: {summary['duration']:.2f}秒\n")
        f.write(f"- **成功率**: {(summary['passed'] / (summary['passed'] + summary['failed'] + summary['errors']) * 100) if (summary['passed'] + summary['failed'] + summary['errors']) > 0 else 0:.1f}%\n\n")

        if summary['failed_tests']:
            f.write(f"## 失敗したテスト\n\n")
            for test in summary['failed_tests']:
                f.write(f"- {test}\n")
            f.write(f"\n")

        f.write(f"## 詳細出力\n\n")
        f.write(f"```\n")
        f.write(result.stdout)
        f.write(result.stderr)
        f.write(f"\n```\n")

    # サマリーを表示
    print("\n" + "=" * 80)
    print("📊 テスト結果サマリー")
    print("=" * 80)
    print(f"成功: {summary['passed']}")
    print(f"失敗: {summary['failed']}")
    print(f"スキップ: {summary['skipped']}")
    print(f"エラー: {summary['errors']}")
    if summary['duration']:
        print(f"実行時間: {summary['duration']:.2f}秒")
    print(f"\n📄 レポートファイル: {report_file}")
    print(f"📄 JSONファイル: {json_file}")

    if summary['failed_tests']:
        print(f"\n⚠️  失敗したテスト:")
        for test in summary['failed_tests'][:10]:  # 最初の10件だけ表示
            print(f"  - {test}")
        if len(summary['failed_tests']) > 10:
            print(f"  ... 他 {len(summary['failed_tests']) - 10} 件")

    return result.returncode

if __name__ == '__main__':
    sys.exit(main())

