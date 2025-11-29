#!/usr/bin/env python3
"""
pytest を実行し、結果レポートを生成するスクリプト
"""

import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_ROOT / "test_results"
RESULTS_DIR.mkdir(exist_ok=True)
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = LOGS_DIR / f"pytest_output_{timestamp}.txt"
    json_file = RESULTS_DIR / f"TEST_RESULT_{timestamp}.json"
    md_file = RESULTS_DIR / f"TEST_RESULT_{timestamp}.md"

    print(f"🧪 pytest を実行中... (結果を {output_file} に保存)")

    # pytest を実行
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]

    with open(output_file, 'w', encoding='utf-8') as f:
        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=f,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=600,
        )

    # 出力を読み込む
    output = output_file.read_text(encoding='utf-8')

    # 簡単なサマリー生成
    passed = output.count(' PASSED')
    failed = output.count(' FAILED')
    skipped = output.count(' SKIPPED')
    error = output.count(' ERROR')
    total = passed + failed + skipped + error

    # 実行時間を抽出
    import re
    time_match = re.search(r'in (\d+\.?\d*)s', output)
    duration = float(time_match.group(1)) if time_match else None

    # JSON レポート
    summary = {
        'timestamp': timestamp,
        'total': total,
        'passed': passed,
        'failed': failed,
        'skipped': skipped,
        'errors': error,
        'duration': duration,
        'success': result.returncode == 0,
        'output_file': str(output_file),
    }

    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Markdown レポート
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# テスト結果レポート\n\n")
        f.write(f"**実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"## サマリー\n\n")
        f.write(f"- **合計テスト数**: {total}\n")
        f.write(f"- **成功**: {passed}\n")
        f.write(f"- **失敗**: {failed}\n")
        f.write(f"- **スキップ**: {skipped}\n")
        f.write(f"- **エラー**: {error}\n")
        if duration:
            f.write(f"- **実行時間**: {duration:.2f}秒\n")
        if total > 0:
            success_rate = (passed / total * 100)
            f.write(f"- **成功率**: {success_rate:.1f}%\n")
        f.write(f"\n")

        f.write(f"## 詳細出力\n\n")
        f.write(f"```\n")
        f.write(output)
        f.write(f"\n```\n")

    # サマリーを表示
    print(f"\n{'='*80}")
    print(f"📊 テスト結果サマリー")
    print(f"{'='*80}")
    print(f"合計: {total}")
    print(f"成功: {passed}")
    print(f"失敗: {failed}")
    print(f"スキップ: {skipped}")
    print(f"エラー: {error}")
    if duration:
        print(f"実行時間: {duration:.2f}秒")
    if total > 0:
        print(f"成功率: {(passed / total * 100):.1f}%")
    print(f"\n📄 レポートファイル: {md_file}")
    print(f"📄 JSONファイル: {json_file}")
    print(f"📄 出力ファイル: {output_file}")

    return result.returncode

if __name__ == '__main__':
    sys.exit(main())

