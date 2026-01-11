"""
Phase3（解析系）専用カバレッジ計測スクリプト

Phase3 対象モジュールのカバレッジを計測し、Markdown レポートを自動生成します。

使用方法:
    python -m tools.coverage_phase3_report
    または
    make coverage-phase3
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path
from typing import List, Tuple

try:
    import coverage
except ImportError:
    print("ERROR: coverage package is not installed.")
    print("Please install it with: pip install coverage")
    sys.exit(1)

try:
    import pytest
except ImportError:
    print("ERROR: pytest package is not installed.")
    print("Please install it with: pip install pytest")
    sys.exit(1)

# プロジェクトルートを基準にパスを解決
ROOT = Path(__file__).resolve().parents[1]

# Phase3 対象モジュール
PHASE3_SOURCES = [
    ROOT / "src" / "nexuscore" / "analyzer" / "graph_builder.py",
    ROOT / "src" / "nexuscore" / "analyzer" / "unified_analyzer.py",
    ROOT / "src" / "nexuscore" / "utils" / "test_generator.py",
    ROOT / "src" / "nexuscore" / "utils" / "tree_sitter_checker.py",
]

# Phase3 用テストターゲット（存在しないファイルは無視するよう実装）
PHASE3_TEST_TARGETS = [
    "tests/analyzer/",
    "tests/utils/test_tree_sitter_checker_optimized.py",
    "tests/analyzer/test_test_generator_stable.py",
]

# 将来の拡張候補（コメントで残しておく）
# PHASE3_SOURCES_CANDIDATES = [
#     ROOT / "src" / "nexuscore" / "analyzer" / "test_generator_integration.py",
#     # その他 Phase3 関連ユーティリティ（ファイル名次第）
# ]


def run_phase3_coverage() -> Tuple[coverage.Coverage, int]:
    """
    Phase3 対象モジュールのカバレッジを計測して Coverage オブジェクトと pytest の終了コードを返す。

    Returns:
        (Coverage オブジェクト, pytest の終了コード)
    """
    cov = coverage.Coverage(
        data_file=str(ROOT / ".coverage-phase3"),
        source=[
            str(ROOT / "src" / "nexuscore" / "analyzer"),
            str(ROOT / "src" / "nexuscore" / "utils"),
        ],
    )

    # 存在するテストパスだけに絞る（ファイルがない場合にエラーにならないように）
    existing_targets: List[str] = []
    for target in PHASE3_TEST_TARGETS:
        target_path = ROOT / target
        if target_path.exists():
            existing_targets.append(str(target_path))
        elif target.startswith("tests/"):
            # tests/ で始まるパスは、存在しなくても pytest に渡してみる（pytest が処理する）
            existing_targets.append(target)

    if not existing_targets:
        # 最低限のフェイルセーフ
        print("WARNING: No Phase3 test targets found.")
        print("Available test targets:", PHASE3_TEST_TARGETS)
        return cov, 0

    print(f"[coverage-phase3] Running pytest on: {', '.join(existing_targets)}")

    cov.start()
    try:
        exit_code = pytest.main(existing_targets + ["-v", "--tb=short"])
    finally:
        cov.stop()
        cov.save()

    return cov, exit_code


def collect_phase3_metrics(cov: coverage.Coverage) -> List[Tuple[str, int, int, float]]:
    """
    Coverage データから Phase3 モジュールの (モジュール名, stmts, missed, percent) のリストを返す。

    Args:
        cov: Coverage オブジェクト

    Returns:
        [(モジュール名, ステートメント数, ミス数, カバレッジ%), ...] のリスト
    """
    results: List[Tuple[str, int, int, float]] = []

    for path in PHASE3_SOURCES:
        if not path.exists():
            print(f"WARNING: Phase3 source file not found: {path}")
            continue

        # coverage.py の analysis API でステートメント数とミス数を取得
        try:
            filename = str(path)
            _, stmts, _, missing, _ = cov.analysis2(filename)
        except coverage.CoverageException as e:
            print(f"WARNING: Failed to analyze {path}: {e}")
            continue

        # stmts はステートメント行番号のリストなので、len() でカウント
        stmt_count = len(stmts)
        missed = len(missing)
        covered = max(stmt_count - missed, 0)
        percent = 0.0 if stmt_count == 0 else (covered / stmt_count) * 100.0

        # 表示用モジュール名は "analyzer.unified_analyzer" のように揃える
        rel = path.relative_to(ROOT / "src" / "nexuscore")
        module_label = ".".join(rel.with_suffix("").parts)

        results.append((module_label, stmt_count, missed, percent))

    # カバレッジ降順で並べる
    results.sort(key=lambda x: x[3], reverse=True)

    return results


def render_markdown(results: List[Tuple[str, int, int, float]]) -> str:
    """
    Phase3 カバレッジ結果の Markdown 文字列を生成する。

    Args:
        results: collect_phase3_metrics の戻り値

    Returns:
        Markdown 文字列
    """
    now = datetime.datetime.now().astimezone()
    timestamp = now.isoformat(timespec="seconds")

    header = f"""<!-- 本ファイルは tools/coverage_phase3_report.py により自動生成されます -->

# Phase 3 Coverage Summary

- **Last updated**: {timestamp}
- **Target modules**: graph_builder / unified_analyzer / test_generator / tree_sitter_checker

"""

    if not results:
        return header + "_No coverage data available. Please run `make coverage-phase3`._\n"

    table_header = "| Module | Stmts | Miss | Coverage |\n|--------|-------|------|----------|\n"

    rows = []
    for module, stmts, missed, percent in results:
        rows.append(f"| `{module}` | {stmts} | {missed} | {percent:.1f}% |")

    # 合計行を追加
    total_stmts = sum(r[1] for r in results)
    total_missed = sum(r[2] for r in results)
    total_covered = total_stmts - total_missed
    total_percent = 0.0 if total_stmts == 0 else (total_covered / total_stmts) * 100.0
    rows.append(f"| **Total** | **{total_stmts}** | **{total_missed}** | **{total_percent:.1f}%** |")

    return header + table_header + "\n".join(rows) + "\n"


def render_markdown_ci(results: List[Tuple[str, int, int, float]]) -> str:
    """
    CI の PR コメント用の簡易 Markdown レポートを生成する。
    ヘッダーとテーブルのみ（余計な説明を省略）。

    Args:
        results: collect_phase3_metrics の戻り値

    Returns:
        Markdown 文字列（CI コメント用）
    """
    lines = []
    lines.append("## Phase3 Coverage (graph_builder / unified_analyzer / test_generator / tree_sitter_checker)")
    lines.append("")

    if not results:
        lines.append("_No coverage data available._")
        return "\n".join(lines) + "\n"

    lines.append("| Module | Stmts | Miss | Coverage |")
    lines.append("|--------|-------|------|----------|")

    for module, stmts, missed, percent in results:
        lines.append(f"| `{module}` | {stmts} | {missed} | {percent:.1f}% |")

    # 合計行を追加
    total_stmts = sum(r[1] for r in results)
    total_missed = sum(r[2] for r in results)
    total_covered = total_stmts - total_missed
    total_percent = 0.0 if total_stmts == 0 else (total_covered / total_stmts) * 100.0
    lines.append(f"| **TOTAL** | {total_stmts} | {total_missed} | **{total_percent:.1f}%** |")
    lines.append("")

    return "\n".join(lines) + "\n"


def write_markdown_report(md_text: str) -> Path:
    """
    docs/coverage_phase3_summary.md を上書き生成する。

    Args:
        md_text: Markdown 文字列

    Returns:
        生成されたファイルのパス
    """
    docs_dir = ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    out_path = docs_dir / "coverage_phase3_summary.md"
    tmp_path = out_path.with_suffix(".tmp")

    # tmp に書いてから replace で atomic-ish に更新
    tmp_path.write_text(md_text, encoding="utf-8")
    tmp_path.replace(out_path)

    return out_path


def write_ci_report(md_text: str) -> Path:
    """
    docs/coverage_phase3_summary_ci.md を上書き生成する（CI 用の短いレポート）。

    Args:
        md_text: Markdown 文字列（CI 用）

    Returns:
        生成されたファイルのパス
    """
    docs_dir = ROOT / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)

    out_path = docs_dir / "coverage_phase3_summary_ci.md"
    tmp_path = out_path.with_suffix(".tmp")

    # tmp に書いてから replace で atomic-ish に更新
    tmp_path.write_text(md_text, encoding="utf-8")
    tmp_path.replace(out_path)

    return out_path


def main() -> None:
    """メイン処理"""
    print("[coverage-phase3] Starting Phase3 coverage measurement...")

    cov, exit_code = run_phase3_coverage()

    print("[coverage-phase3] Collecting metrics...")
    results = collect_phase3_metrics(cov)

    print("[coverage-phase3] Generating Markdown report...")
    md = render_markdown(results)

    out_path = write_markdown_report(md)

    # CI 用の短いレポートも生成
    print("[coverage-phase3] Generating CI Markdown report...")
    ci_md = render_markdown_ci(results)
    ci_path = write_ci_report(ci_md)

    print(f"[coverage-phase3] Report written to {out_path}")
    print(f"[coverage-phase3] CI report written to {ci_path}")
    print(f"[coverage-phase3] Coverage data saved to {ROOT / '.coverage-phase3'}")

    if exit_code != 0:
        print(f"[coverage-phase3] WARNING: pytest exited with code {exit_code}")
        print("[coverage-phase3] Coverage report generated, but some tests may have failed.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

