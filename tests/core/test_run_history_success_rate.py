"""
test_run_history_success_rate.py

RunHistoryLogger の成功率計算機能のテスト。
"""

from __future__ import annotations

import tempfile

from nexuscore.core.run_history import RunHistoryLogger, RunRecord


class TestRunHistorySuccessRate:
    """成功率計算機能のテスト"""

    def test_calculate_success_rate_empty(self):
        """履歴が空の場合"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(project_root=tmpdir)
            rate, success, total = logger.calculate_success_rate(limit=30)

            assert rate == 0.0
            assert success == 0
            assert total == 0

    def test_calculate_success_rate_single_fixed(self):
        """1件の fixed レコード"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(project_root=tmpdir)

            # 1件の fixed レコードを追加
            record = RunRecord(
                run_id="test-1",
                session_id="session-1",
                kind="self_healing",
                status="fixed",
                started_at=1000.0,
                finished_at=1003.0,
            )
            logger.log_run(record)

            rate, success, total = logger.calculate_success_rate(limit=30)

            assert rate == 100.0
            assert success == 1
            assert total == 1

    def test_calculate_success_rate_mixed(self):
        """複数の mixed レコード"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(project_root=tmpdir)

            # 3件の fixed と 2件の not_fixed を追加
            for i, status in enumerate(["fixed", "fixed", "fixed", "not_fixed", "not_fixed"]):
                record = RunRecord(
                    run_id=f"test-{i}",
                    session_id=f"session-{i}",
                    kind="self_healing",
                    status=status,
                    started_at=1000.0 + i,
                    finished_at=1003.0 + i,
                )
                logger.log_run(record)

            rate, success, total = logger.calculate_success_rate(limit=30)

            assert rate == 60.0  # 3/5 = 60%
            assert success == 3
            assert total == 5

    def test_calculate_success_rate_limit(self):
        """limit を超える場合、最新の limit 件のみを対象"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(project_root=tmpdir)

            # 40件のレコードを追加（古い順に not_fixed, 新しい順に fixed）
            for i in range(40):
                status = "fixed" if i >= 10 else "not_fixed"  # 最初の10件は not_fixed
                record = RunRecord(
                    run_id=f"test-{i}",
                    session_id=f"session-{i}",
                    kind="self_healing",
                    status=status,
                    started_at=1000.0 + i,
                    finished_at=1003.0 + i,
                )
                logger.log_run(record)

            # limit=30 の場合、最新30件（すべて fixed）が対象
            rate, success, total = logger.calculate_success_rate(limit=30)

            assert rate == 100.0  # 最新30件はすべて fixed
            assert success == 30
            assert total == 30

    def test_get_last_self_healing_runs(self):
        """直近の実行履歴を取得"""
        with tempfile.TemporaryDirectory() as tmpdir:
            logger = RunHistoryLogger(project_root=tmpdir)

            # 5件のレコードを追加
            for i in range(5):
                record = RunRecord(
                    run_id=f"test-{i}",
                    session_id=f"session-{i}",
                    kind="self_healing",
                    status="fixed" if i % 2 == 0 else "not_fixed",
                    started_at=1000.0 + i,
                    finished_at=1003.0 + i,
                )
                logger.log_run(record)

            runs = logger.get_last_self_healing_runs(limit=3)

            assert len(runs) == 3
            # 新しい順に並んでいることを確認
            assert runs[0]["run_id"] == "test-4"
            assert runs[1]["run_id"] == "test-3"
            assert runs[2]["run_id"] == "test-2"
