"""
Comprehensive tests for ui/self_healing_dashboard.py

Self-Healing Dashboard の関数とロジックのテスト
"""

import json
import sys
from unittest.mock import MagicMock, patch

# Streamlitのモック化
sys.modules["streamlit"] = MagicMock()

from nexuscore.ui.self_healing_dashboard import _parse_args, load_history, main


# ============================================================================
# load_history テスト
# ============================================================================
class TestLoadHistory:
    def test_load_history_file_not_exists(self, tmp_path):
        """ファイルが存在しない場合は空リストを返す"""
        project_root = str(tmp_path / "nonexistent")

        result = load_history(project_root)

        assert result == []

    def test_load_history_empty_file(self, tmp_path):
        """空ファイルの場合は空リストを返す"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"
        log_file.write_text("")

        result = load_history(str(project_root))

        assert result == []

    def test_load_history_single_record(self, tmp_path):
        """単一レコードを正しく読み込む"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        record = {"status": "success", "run_id": "123"}
        log_file.write_text(json.dumps(record) + "\n")

        result = load_history(str(project_root))

        assert len(result) == 1
        assert result[0]["status"] == "success"
        assert result[0]["run_id"] == "123"

    def test_load_history_multiple_records(self, tmp_path):
        """複数レコードを正しく読み込む"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        records = [
            {"status": "success", "run_id": "1"},
            {"status": "failed", "run_id": "2"},
            {"status": "pending", "run_id": "3"},
        ]
        content = "\n".join(json.dumps(r) for r in records) + "\n"
        log_file.write_text(content)

        result = load_history(str(project_root))

        assert len(result) == 3
        assert result[0]["run_id"] == "1"
        assert result[1]["run_id"] == "2"
        assert result[2]["run_id"] == "3"

    def test_load_history_skips_empty_lines(self, tmp_path):
        """空行をスキップする"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        content = (
            json.dumps({"status": "success"}) + "\n\n\n" + json.dumps({"status": "failed"}) + "\n"
        )
        log_file.write_text(content)

        result = load_history(str(project_root))

        assert len(result) == 2

    def test_load_history_skips_invalid_json(self, tmp_path):
        """無効なJSONをスキップする"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        content = (
            json.dumps({"status": "success"})
            + "\n"
            + "invalid json line\n"
            + json.dumps({"status": "failed"})
            + "\n"
        )
        log_file.write_text(content)

        result = load_history(str(project_root))

        # 有効な2レコードのみ
        assert len(result) == 2
        assert result[0]["status"] == "success"
        assert result[1]["status"] == "failed"

    def test_load_history_with_nested_data(self, tmp_path):
        """ネストされたデータを含むレコード"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        record = {
            "status": "success",
            "details": {"patch_preview": "diff content", "files_changed": ["file1.py", "file2.py"]},
        }
        log_file.write_text(json.dumps(record) + "\n")

        result = load_history(str(project_root))

        assert len(result) == 1
        assert result[0]["details"]["patch_preview"] == "diff content"
        assert len(result[0]["details"]["files_changed"]) == 2

    def test_load_history_unicode_content(self, tmp_path):
        """Unicode文字を含むコンテンツ"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        record = {"status": "成功", "summary": "日本語のサマリー"}
        log_file.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

        result = load_history(str(project_root))

        assert len(result) == 1
        assert result[0]["status"] == "成功"
        assert result[0]["summary"] == "日本語のサマリー"


# ============================================================================
# main 関数テスト（Streamlit モック）
# ============================================================================
class TestMain:
    @patch("nexuscore.ui.self_healing_dashboard.st")
    @patch("nexuscore.ui.self_healing_dashboard.load_history")
    def test_main_no_records(self, mock_load_history, mock_st, tmp_path):
        """レコードがない場合"""
        mock_load_history.return_value = []

        main(str(tmp_path))

        # 情報メッセージが表示される
        mock_st.info.assert_called_once()

    @patch("nexuscore.ui.self_healing_dashboard.st")
    @patch("nexuscore.ui.self_healing_dashboard.load_history")
    def test_main_with_records(self, mock_load_history, mock_st, tmp_path):
        """レコードがある場合"""
        mock_load_history.return_value = [
            {"status": "success", "run_id": "1"},
            {"status": "failed", "run_id": "2"},
        ]

        # サイドバーのモック設定
        mock_st.sidebar.multiselect.side_effect = [
            ["success", "failed"],  # selected_statuses
            [],  # selected_repos（空リスト）
        ]

        # columnsのモック設定
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_st.columns.return_value = [mock_col1, mock_col2]

        main(str(tmp_path))

        # ページ設定が呼ばれる
        mock_st.set_page_config.assert_called_once()

        # タイトルが設定される
        mock_st.title.assert_called_once()

    @patch("nexuscore.ui.self_healing_dashboard.st")
    @patch("nexuscore.ui.self_healing_dashboard.load_history")
    def test_main_displays_total_count(self, mock_load_history, mock_st, tmp_path):
        """総レコード数を表示"""
        records = [{"status": "success", "run_id": str(i)} for i in range(10)]
        mock_load_history.return_value = records

        mock_st.sidebar.multiselect.side_effect = [["success"], []]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        main(str(tmp_path))

        # writeメソッドが呼ばれる（総数表示）
        assert mock_st.write.called

    @patch("nexuscore.ui.self_healing_dashboard.st")
    @patch("nexuscore.ui.self_healing_dashboard.load_history")
    def test_main_filters_by_status(self, mock_load_history, mock_st, tmp_path):
        """ステータスでフィルタリング"""
        records = [
            {"status": "success", "run_id": "1"},
            {"status": "failed", "run_id": "2"},
            {"status": "success", "run_id": "3"},
        ]
        mock_load_history.return_value = records

        # "success" のみ選択
        mock_st.sidebar.multiselect.side_effect = [["success"], []]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        main(str(tmp_path))

        # フィルタリング結果が表示される
        assert mock_st.write.called

    @patch("nexuscore.ui.self_healing_dashboard.st")
    @patch("nexuscore.ui.self_healing_dashboard.load_history")
    def test_main_displays_status_summary(self, mock_load_history, mock_st, tmp_path):
        """ステータスサマリーを表示"""
        records = [
            {"status": "success", "run_id": "1"},
            {"status": "success", "run_id": "2"},
            {"status": "failed", "run_id": "3"},
        ]
        mock_load_history.return_value = records

        mock_st.sidebar.multiselect.side_effect = [["success", "failed"], []]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        main(str(tmp_path))

        # サブヘッダーが設定される
        assert mock_st.subheader.called

    @patch("nexuscore.ui.self_healing_dashboard.st")
    @patch("nexuscore.ui.self_healing_dashboard.load_history")
    def test_main_displays_recent_runs(self, mock_load_history, mock_st, tmp_path):
        """最近の実行を表示"""
        records = [
            {
                "status": "success",
                "run_id": "1",
                "repo_full_name": "user/repo",
                "pr_number": 123,
                "summary": "Test summary",
            }
        ]
        mock_load_history.return_value = records

        mock_st.sidebar.multiselect.side_effect = [["success"], ["user/repo"]]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        main(str(tmp_path))

        # expanderが使われる
        assert mock_st.expander.called


# ============================================================================
# _parse_args テスト
# ============================================================================
class TestParseArgs:
    @patch("sys.argv", ["script.py", "--project-root", "/custom/path"])
    def test_parse_args_with_project_root(self):
        """--project-root 引数のパース"""
        args = _parse_args()

        assert args.project_root == "/custom/path"

    @patch("sys.argv", ["script.py"])
    def test_parse_args_default_project_root(self):
        """デフォルトのproject_root"""
        args = _parse_args()

        assert args.project_root == "."

    @patch("sys.argv", ["script.py", "--project-root", "."])
    def test_parse_args_current_directory(self):
        """カレントディレクトリ指定"""
        args = _parse_args()

        assert args.project_root == "."


# ============================================================================
# 統合テスト
# ============================================================================
class TestSelfHealingDashboardIntegration:
    def test_load_history_and_filter_integration(self, tmp_path):
        """load_history → フィルタリングの統合テスト"""
        # ヒストリーファイルを作成
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        records = [
            {"status": "success", "repo_full_name": "repo1", "run_id": "1"},
            {"status": "failed", "repo_full_name": "repo2", "run_id": "2"},
            {"status": "success", "repo_full_name": "repo1", "run_id": "3"},
        ]
        content = "\n".join(json.dumps(r) for r in records) + "\n"
        log_file.write_text(content)

        # ロード
        loaded = load_history(str(project_root))

        # フィルタリング（main関数内のロジックをシミュレート）
        selected_statuses = ["success"]
        selected_repos = ["repo1"]

        filtered = [
            r
            for r in loaded
            if r.get("status") in selected_statuses and r.get("repo_full_name") in selected_repos
        ]

        assert len(filtered) == 2
        assert all(r["status"] == "success" for r in filtered)
        assert all(r["repo_full_name"] == "repo1" for r in filtered)

    @patch("nexuscore.ui.self_healing_dashboard.st")
    def test_main_full_workflow(self, mock_st, tmp_path):
        """main関数の完全ワークフロー"""
        # ヒストリーファイルを作成
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        records = [
            {
                "status": "success",
                "repo_full_name": "test/repo",
                "pr_number": 1,
                "run_id": "run1",
                "summary": "Fixed bug",
                "session_id": "session1",
                "head_sha": "abc123",
                "started_at": "2024-01-01T00:00:00",
                "finished_at": "2024-01-01T01:00:00",
                "details": {"patch_preview": "diff content"},
            }
        ]
        content = "\n".join(json.dumps(r) for r in records) + "\n"
        log_file.write_text(content)

        # サイドバーのモック
        mock_st.sidebar.multiselect.side_effect = [["success"], ["test/repo"]]
        mock_st.columns.return_value = [MagicMock(), MagicMock()]

        # 実行
        main(str(project_root))

        # ページ設定が呼ばれる
        mock_st.set_page_config.assert_called_once()

        # タイトルが設定される
        mock_st.title.assert_called_once()

    def test_empty_and_non_empty_workflow(self, tmp_path):
        """空→非空のワークフローテスト"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        # 最初は空
        log_file.write_text("")
        result1 = load_history(str(project_root))
        assert len(result1) == 0

        # レコード追加
        log_file.write_text(json.dumps({"status": "success", "run_id": "1"}) + "\n")
        result2 = load_history(str(project_root))
        assert len(result2) == 1

        # さらに追加
        with log_file.open("a") as f:
            f.write(json.dumps({"status": "failed", "run_id": "2"}) + "\n")
        result3 = load_history(str(project_root))
        assert len(result3) == 2


# ============================================================================
# エッジケーステスト
# ============================================================================
class TestEdgeCases:
    def test_load_history_with_large_file(self, tmp_path):
        """大量のレコードを含むファイル"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        # 1000レコード作成
        records = [{"status": "success", "run_id": str(i)} for i in range(1000)]
        content = "\n".join(json.dumps(r) for r in records) + "\n"
        log_file.write_text(content)

        result = load_history(str(project_root))

        assert len(result) == 1000

    def test_load_history_malformed_but_valid_json(self, tmp_path):
        """構造が異なるが有効なJSON"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        # 構造が異なるレコード
        records = [
            {"status": "success"},
            {"different_field": "value"},
            {"status": "failed", "extra": {"nested": "data"}},
        ]
        content = "\n".join(json.dumps(r) for r in records) + "\n"
        log_file.write_text(content)

        result = load_history(str(project_root))

        # 全て読み込まれる
        assert len(result) == 3

    def test_load_history_with_special_characters(self, tmp_path):
        """特殊文字を含むレコード"""
        project_root = tmp_path
        history_dir = project_root / ".nexus" / "history"
        history_dir.mkdir(parents=True)
        log_file = history_dir / "self_healing.log.jsonl"

        record = {"status": "success", "summary": "Fixed: 'quotes' and \"double\" and \n newline"}
        log_file.write_text(json.dumps(record) + "\n")

        result = load_history(str(project_root))

        assert len(result) == 1
        assert "quotes" in result[0]["summary"]
