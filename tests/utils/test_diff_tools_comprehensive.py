"""
diff_tools.py の包括的テスト

カバレッジ:
- generate_diff_report: unified diff レポート生成
- score_code_improvement: コード改善スコア計算

エッジケース:
- 空文字列、単一行、複数行
- 追加のみ、削除のみ、変更
- 同一コード、完全に異なるコード
- Unicode文字、特殊文字
"""

import pytest
from nexuscore.utils.diff_tools import (
    generate_diff_report,
    score_code_improvement,
)


class TestGenerateDiffReport:
    """generate_diff_report() のテスト"""

    def test_generate_diff_report_no_changes(self):
        """変更なしの場合は空のdiffを返す"""
        original = "line1\nline2\nline3"
        modified = "line1\nline2\nline3"

        result = generate_diff_report(original, modified)

        # 変更がない場合、ヘッダーのみ
        assert "---" not in result or "+++" not in result or len(result.split("\n")) <= 2

    def test_generate_diff_report_single_line_added(self):
        """1行追加された場合"""
        original = "line1\nline2"
        modified = "line1\nline2\nline3"

        result = generate_diff_report(original, modified)

        # 追加された行が + で始まる
        assert "+line3" in result
        assert "Original" in result
        assert "Modified" in result

    def test_generate_diff_report_single_line_removed(self):
        """1行削除された場合"""
        original = "line1\nline2\nline3"
        modified = "line1\nline2"

        result = generate_diff_report(original, modified)

        # 削除された行が - で始まる
        assert "-line3" in result

    def test_generate_diff_report_single_line_modified(self):
        """1行変更された場合"""
        original = "line1\nline2\nline3"
        modified = "line1\nLINE2_MODIFIED\nline3"

        result = generate_diff_report(original, modified)

        # 古い行が削除され、新しい行が追加される
        assert "-line2" in result
        assert "+LINE2_MODIFIED" in result

    def test_generate_diff_report_multiple_changes(self):
        """複数行の変更"""
        original = "line1\nline2\nline3\nline4"
        modified = "line1\nMODIFIED2\nline3\nline5"

        result = generate_diff_report(original, modified)

        # 複数の変更が含まれる
        assert "-line2" in result or "-line4" in result
        assert "+MODIFIED2" in result or "+line5" in result

    def test_generate_diff_report_empty_original(self):
        """元のコードが空の場合（全て追加）"""
        original = ""
        modified = "line1\nline2\nline3"

        result = generate_diff_report(original, modified)

        # 全ての行が追加される
        assert "+line1" in result
        assert "+line2" in result
        assert "+line3" in result

    def test_generate_diff_report_empty_modified(self):
        """変更後のコードが空の場合（全て削除）"""
        original = "line1\nline2\nline3"
        modified = ""

        result = generate_diff_report(original, modified)

        # 全ての行が削除される
        assert "-line1" in result
        assert "-line2" in result
        assert "-line3" in result

    def test_generate_diff_report_both_empty(self):
        """両方とも空の場合"""
        original = ""
        modified = ""

        result = generate_diff_report(original, modified)

        # 空のdiff（ヘッダーのみまたは完全に空）
        assert len(result) == 0 or "Original" in result

    def test_generate_diff_report_unicode_characters(self):
        """Unicode文字を含むdiff"""
        original = "日本語\n中文"
        modified = "日本語\n한국어"

        result = generate_diff_report(original, modified)

        # Unicode文字が正しく処理される
        assert "-中文" in result
        assert "+한국어" in result

    def test_generate_diff_report_special_characters(self):
        """特殊文字を含むdiff"""
        original = "def foo():\n    return 'hello'"
        modified = "def foo():\n    return \"world\""

        result = generate_diff_report(original, modified)

        # 特殊文字（クォート）が正しく処理される
        assert "-" in result and "'" in result
        assert "+" in result and '"' in result

    def test_generate_diff_report_whitespace_changes(self):
        """空白の変更を検出"""
        original = "line1\nline2"
        modified = "line1\n  line2"  # インデント追加

        result = generate_diff_report(original, modified)

        # 空白の変更が検出される
        assert "-line2" in result
        assert "+  line2" in result

    def test_generate_diff_report_fromfile_tofile_headers(self):
        """ファイル名ヘッダーが含まれる"""
        original = "test"
        modified = "test2"

        result = generate_diff_report(original, modified)

        # ファイル名ヘッダーが含まれる
        assert "Original" in result
        assert "Modified" in result


class TestScoreCodeImprovement:
    """score_code_improvement() のテスト"""

    def test_score_code_improvement_no_change(self):
        """変更なしの場合はスコア0.0"""
        original = "line1\nline2\nline3"
        modified = "line1\nline2\nline3"

        score = score_code_improvement(original, modified)

        assert score == 0.0

    def test_score_code_improvement_one_line_added(self):
        """1行追加された場合（3行→4行）"""
        original = "line1\nline2\nline3"
        modified = "line1\nline2\nline3\nline4"

        score = score_code_improvement(original, modified)

        # (4-3)/3 = 0.33
        assert score == 0.33

    def test_score_code_improvement_one_line_removed(self):
        """1行削除された場合（3行→2行）"""
        original = "line1\nline2\nline3"
        modified = "line1\nline2"

        score = score_code_improvement(original, modified)

        # (2-3)/3 = -0.33
        assert score == -0.33

    def test_score_code_improvement_doubled_lines(self):
        """行数が2倍になった場合"""
        original = "line1\nline2"
        modified = "line1\nline2\nline3\nline4"

        score = score_code_improvement(original, modified)

        # (4-2)/2 = 1.0
        assert score == 1.0

    def test_score_code_improvement_halved_lines(self):
        """行数が半分になった場合"""
        original = "line1\nline2\nline3\nline4"
        modified = "line1\nline2"

        score = score_code_improvement(original, modified)

        # (2-4)/4 = -0.5
        assert score == -0.5

    def test_score_code_improvement_empty_original(self):
        """元のコードが空の場合（division by zero対策）"""
        original = ""
        modified = "line1\nline2\nline3"

        score = score_code_improvement(original, modified)

        # (3-0)/max(0,1) = 3.0
        assert score == 3.0

    def test_score_code_improvement_empty_modified(self):
        """変更後のコードが空の場合"""
        original = "line1\nline2\nline3"
        modified = ""

        score = score_code_improvement(original, modified)

        # (0-3)/3 = -1.0
        assert score == -1.0

    def test_score_code_improvement_both_empty(self):
        """両方とも空の場合"""
        original = ""
        modified = ""

        score = score_code_improvement(original, modified)

        # (0-0)/max(0,1) = 0.0
        assert score == 0.0

    def test_score_code_improvement_whitespace_stripped(self):
        """前後の空白は除去される"""
        original = "\n\nline1\nline2\n\n"
        modified = "\n\nline1\nline2\nline3\n\n"

        score = score_code_improvement(original, modified)

        # strip()後: 2行→3行 なので (3-2)/2 = 0.5
        assert score == 0.5

    def test_score_code_improvement_single_line_to_multiline(self):
        """1行→複数行"""
        original = "single line"
        modified = "line1\nline2\nline3"

        score = score_code_improvement(original, modified)

        # (3-1)/1 = 2.0
        assert score == 2.0

    def test_score_code_improvement_multiline_to_single_line(self):
        """複数行→1行（コード圧縮）"""
        original = "line1\nline2\nline3"
        modified = "compressed"

        score = score_code_improvement(original, modified)

        # (1-3)/3 = -0.67
        assert score == -0.67

    def test_score_code_improvement_large_addition(self):
        """大量の行を追加"""
        original = "line1"
        modified = "\n".join([f"line{i}" for i in range(1, 101)])  # 100行

        score = score_code_improvement(original, modified)

        # (100-1)/1 = 99.0
        assert score == 99.0

    def test_score_code_improvement_large_deletion(self):
        """大量の行を削除"""
        original = "\n".join([f"line{i}" for i in range(1, 101)])  # 100行
        modified = "line1"

        score = score_code_improvement(original, modified)

        # (1-100)/100 = -0.99
        assert score == -0.99

    def test_score_code_improvement_rounding_precision(self):
        """スコアが2桁に丸められる"""
        original = "1\n2\n3"
        modified = "1\n2\n3\n4\n5\n6\n7"

        score = score_code_improvement(original, modified)

        # (7-3)/3 = 1.333... → 1.33
        assert score == 1.33
        assert isinstance(score, float)


class TestEdgeCases:
    """エッジケースのテスト"""

    def test_generate_diff_report_very_long_lines(self):
        """非常に長い行を含むdiff"""
        original = "short"
        modified = "a" * 10000  # 10000文字の行

        result = generate_diff_report(original, modified)

        # 長い行も処理される
        assert "-short" in result
        assert "+" in result
        assert len(result) > 100

    def test_generate_diff_report_many_lines(self):
        """多数の行を含むdiff"""
        original = "\n".join([f"line{i}" for i in range(1000)])
        modified = "\n".join([f"line{i}" for i in range(1, 1001)])  # 1行シフト

        result = generate_diff_report(original, modified)

        # diffが生成される
        assert len(result) > 0

    def test_score_code_improvement_only_whitespace_original(self):
        """元のコードが空白のみの場合"""
        original = "   \n  \n   "
        modified = "line1\nline2"

        # strip()で空になる
        score = score_code_improvement(original, modified)

        # 空→2行 = (2-0)/max(0,1) = 2.0
        assert score == 2.0

    def test_score_code_improvement_only_whitespace_modified(self):
        """変更後のコードが空白のみの場合"""
        original = "line1\nline2"
        modified = "   \n  \n   "

        # strip()で空になる
        score = score_code_improvement(original, modified)

        # 2行→0行 = (0-2)/2 = -1.0
        assert score == -1.0

    def test_generate_diff_report_newline_at_end(self):
        """末尾の改行の扱い"""
        original = "line1\nline2\n"
        modified = "line1\nline2"

        result = generate_diff_report(original, modified)

        # 差分が検出される（または検出されない）
        assert isinstance(result, str)

    def test_score_code_improvement_negative_to_positive(self):
        """マイナスからプラスへの変化"""
        # 削除: -0.5
        original1 = "1\n2\n3\n4"
        modified1 = "1\n2"
        score1 = score_code_improvement(original1, modified1)
        assert score1 < 0

        # 追加: +1.0
        original2 = "1\n2"
        modified2 = "1\n2\n3\n4"
        score2 = score_code_improvement(original2, modified2)
        assert score2 > 0

    def test_generate_diff_report_tabs_vs_spaces(self):
        """タブとスペースの違いを検出"""
        original = "\tindented"
        modified = "    indented"  # 4スペース

        result = generate_diff_report(original, modified)

        # 差分が検出される
        assert "-" in result
        assert "+" in result

    def test_score_code_improvement_unicode_line_count(self):
        """Unicode文字でも行数カウントが正確"""
        original = "日本語1\n日本語2\n日本語3"
        modified = "日本語1\n日本語2\n日本語3\n日本語4\n日本語5"

        score = score_code_improvement(original, modified)

        # (5-3)/3 = 0.67
        assert score == 0.67
