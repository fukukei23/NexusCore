"""
============================================================================
Comprehensive Tests for test_metrics.py
============================================================================
高品質テストの原則:
- 外部依存（ファイルシステム、TestStrategyManager）をモック
- 実際のメトリクス記録・取得ロジックをテスト
- エッジケースとエラー条件をカバー
============================================================================
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from nexuscore.core.test_metrics import (
    TestGenerationRecord,
    TestMetrics,
    TestMetricsCollector,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_project():
    """一時プロジェクトディレクトリ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def collector(temp_project):
    """TestMetricsCollector インスタンス"""
    return TestMetricsCollector(temp_project)


# ============================================================================
# Tests: TestGenerationRecord dataclass
# ============================================================================


class TestTestGenerationRecord:
    def test_create_record_minimal(self):
        """最小限のパラメータでレコード作成"""
        record = TestGenerationRecord(
            timestamp="2025-12-31T10:00:00Z",
            module_name="example.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test_example.py",
            test_count=10,
            generated_by="ai",
        )

        assert record.module_name == "example.py"
        assert record.risk_level == "A"
        assert record.test_count == 10
        assert record.generated_by == "ai"
        assert record.deleted is False

    def test_create_record_full(self):
        """全パラメータでレコード作成"""
        record = TestGenerationRecord(
            timestamp="2025-12-31T10:00:00Z",
            module_name="example.py",
            risk_level="S",
            strategy="mutation",
            test_file_path="tests/test_example.py",
            test_count=25,
            generated_by="ai+human",
            coverage_before=60.5,
            coverage_after=85.3,
            bugs_found=3,
            deleted=True,
            deleted_reason="Low quality",
        )

        assert record.coverage_before == 60.5
        assert record.coverage_after == 85.3
        assert record.bugs_found == 3
        assert record.deleted is True
        assert record.deleted_reason == "Low quality"


# ============================================================================
# Tests: TestMetrics dataclass
# ============================================================================


class TestTestMetrics:
    def test_create_metrics(self):
        """TestMetrics 作成"""
        metrics = TestMetrics(
            module_name="example.py",
            risk_level="A",
            total_tests_generated=50,
            tests_deleted=5,
            bugs_found=10,
            coverage_current=85.5,
            coverage_target=80,
            ai_generation_count=40,
            human_generation_count=10,
            effectiveness_score=0.2,
        )

        assert metrics.module_name == "example.py"
        assert metrics.total_tests_generated == 50
        assert metrics.effectiveness_score == 0.2


# ============================================================================
# Tests: TestMetricsCollector initialization
# ============================================================================


class TestTestMetricsCollectorInit:
    def test_init_creates_metrics_dir(self, temp_project):
        """初期化時にメトリクスディレクトリが作成される"""
        collector = TestMetricsCollector(temp_project)

        assert collector.metrics_dir.exists()
        assert collector.metrics_dir.is_dir()
        assert collector.metrics_dir == Path(temp_project) / ".nexus" / "test_metrics"

    def test_init_creates_history_file_path(self, collector):
        """履歴ファイルパスが設定される"""
        assert collector.history_file.name == "test_generation_history.jsonl"

    def test_init_with_existing_dir(self, temp_project):
        """既存のディレクトリで初期化"""
        # 先にディレクトリを作成
        metrics_dir = Path(temp_project) / ".nexus" / "test_metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # 例外が発生しないことを確認
        collector = TestMetricsCollector(temp_project)
        assert collector.metrics_dir.exists()


# ============================================================================
# Tests: record_test_generation
# ============================================================================


class TestRecordTestGeneration:
    def test_record_generation_minimal(self, collector):
        """最小限のパラメータでテスト生成を記録"""
        collector.record_test_generation(
            module_name="example.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test_example.py",
            test_count=10,
        )

        # 履歴ファイルが作成される
        assert collector.history_file.exists()

        # ファイルの内容を確認
        with collector.history_file.open("r") as f:
            line = f.readline()
            record = json.loads(line)

        assert record["module_name"] == "example.py"
        assert record["risk_level"] == "A"
        assert record["test_count"] == 10
        assert record["generated_by"] == "ai"  # デフォルト

    def test_record_generation_full(self, collector):
        """全パラメータでテスト生成を記録"""
        collector.record_test_generation(
            module_name="complex.py",
            risk_level="S",
            strategy="mutation",
            test_file_path="tests/test_complex.py",
            test_count=25,
            generated_by="ai+human",
            coverage_before=60.5,
            coverage_after=85.3,
        )

        with collector.history_file.open("r") as f:
            record = json.loads(f.readline())

        assert record["generated_by"] == "ai+human"
        assert record["coverage_before"] == 60.5
        assert record["coverage_after"] == 85.3

    def test_record_multiple_generations(self, collector):
        """複数のテスト生成を記録"""
        for i in range(5):
            collector.record_test_generation(
                module_name=f"module{i}.py",
                risk_level="B",
                strategy="unit",
                test_file_path=f"tests/test_module{i}.py",
                test_count=i * 10,
            )

        # 5行記録される
        with collector.history_file.open("r") as f:
            lines = f.readlines()

        assert len(lines) == 5

    def test_record_generation_timestamp(self, collector):
        """タイムスタンプが記録される"""
        collector.record_test_generation(
            module_name="example.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test_example.py",
            test_count=10,
        )

        with collector.history_file.open("r") as f:
            record = json.loads(f.readline())

        # ISO 8601 フォーマットのタイムスタンプ
        timestamp = record["timestamp"]
        assert "T" in timestamp
        assert ":" in timestamp


# ============================================================================
# Tests: record_bug_found
# ============================================================================


class TestRecordBugFound:
    def test_record_bug_found_single(self, collector):
        """バグ発見を記録"""
        # まずテスト生成を記録
        collector.record_test_generation(
            module_name="buggy.py",
            risk_level="A",
            strategy="mutation",
            test_file_path="tests/test_buggy.py",
            test_count=20,
        )

        # バグ発見を記録
        collector.record_bug_found("tests/test_buggy.py", bug_count=2)

        # 履歴を確認
        records = collector._load_history()
        assert records[0]["bugs_found"] == 2

    def test_record_bug_found_multiple_times(self, collector):
        """同じテストファイルで複数回バグ発見"""
        collector.record_test_generation(
            module_name="buggy.py",
            risk_level="S",
            strategy="mutation",
            test_file_path="tests/test_buggy.py",
            test_count=30,
        )

        # 3回バグを発見
        collector.record_bug_found("tests/test_buggy.py", bug_count=1)
        collector.record_bug_found("tests/test_buggy.py", bug_count=2)
        collector.record_bug_found("tests/test_buggy.py", bug_count=3)

        records = collector._load_history()
        # 最後の更新が反映される（合計6）
        assert records[0]["bugs_found"] == 6

    def test_record_bug_found_nonexistent_file(self, collector):
        """存在しないテストファイルでバグ発見を記録しても例外なし"""
        collector.record_bug_found("tests/nonexistent.py", bug_count=1)
        # 例外が発生しないことを確認


# ============================================================================
# Tests: record_test_deletion
# ============================================================================


class TestRecordTestDeletion:
    def test_record_deletion(self, collector):
        """テスト削除を記録"""
        collector.record_test_generation(
            module_name="bad_test.py",
            risk_level="B",
            strategy="unit",
            test_file_path="tests/test_bad.py",
            test_count=5,
        )

        collector.record_test_deletion(
            test_file_path="tests/test_bad.py", reason="Too many false positives"
        )

        records = collector._load_history()
        assert records[0]["deleted"] is True
        assert records[0]["deleted_reason"] == "Too many false positives"

    def test_record_deletion_nonexistent(self, collector):
        """存在しないテストの削除を記録しても例外なし"""
        collector.record_test_deletion(test_file_path="tests/nonexistent.py", reason="Not found")
        # 例外が発生しないことを確認


# ============================================================================
# Tests: get_metrics
# ============================================================================


class TestGetMetrics:
    def test_get_metrics_simple(self, collector, monkeypatch):
        """シンプルなメトリクス取得"""
        # TestStrategyManager をモック
        mock_strategy_class = MagicMock()
        mock_manager = MagicMock()
        mock_manager.get_min_coverage.return_value = 80
        mock_strategy_class.return_value = mock_manager

        # インポート時にモックを使用
        def mock_import(name, *args, **kwargs):
            if "test_strategy" in name:
                mock_module = MagicMock()
                mock_module.TestStrategyManager = mock_strategy_class
                return mock_module
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # テスト生成を記録
        collector.record_test_generation(
            module_name="example.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test_example.py",
            test_count=20,
            coverage_after=85.5,
        )

        metrics = collector.get_metrics("example.py")

        assert metrics is not None
        assert metrics.module_name == "example.py"
        assert metrics.risk_level == "A"
        assert metrics.total_tests_generated == 1
        assert metrics.tests_deleted == 0
        assert metrics.bugs_found == 0
        assert metrics.coverage_current == 85.5
        assert metrics.coverage_target == 80
        assert metrics.ai_generation_count == 1
        assert metrics.human_generation_count == 0
        assert metrics.effectiveness_score == 0.0

    def test_get_metrics_with_bugs(self, collector, monkeypatch):
        """バグを発見したテストのメトリクス"""
        mock_strategy_class = MagicMock()
        mock_manager = MagicMock()
        mock_manager.get_min_coverage.return_value = 80
        mock_strategy_class.return_value = mock_manager

        def mock_import(name, *args, **kwargs):
            if "test_strategy" in name:
                mock_module = MagicMock()
                mock_module.TestStrategyManager = mock_strategy_class
                return mock_module
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        collector.record_test_generation(
            module_name="buggy.py",
            risk_level="S",
            strategy="mutation",
            test_file_path="tests/test_buggy.py",
            test_count=30,
            coverage_after=90.0,
        )

        collector.record_bug_found("tests/test_buggy.py", bug_count=5)

        metrics = collector.get_metrics("buggy.py")

        assert metrics.bugs_found == 5
        assert metrics.effectiveness_score == 5 / 1  # 5 bugs / 1 generation

    def test_get_metrics_with_deletions(self, collector, monkeypatch):
        """削除されたテストを含むメトリクス"""
        mock_strategy_class = MagicMock()
        mock_manager = MagicMock()
        mock_manager.get_min_coverage.return_value = 80
        mock_strategy_class.return_value = mock_manager

        def mock_import(name, *args, **kwargs):
            if "test_strategy" in name:
                mock_module = MagicMock()
                mock_module.TestStrategyManager = mock_strategy_class
                return mock_module
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # 3つのテストを生成
        for i in range(3):
            collector.record_test_generation(
                module_name="test_module.py",
                risk_level="B",
                strategy="unit",
                test_file_path=f"tests/test_{i}.py",
                test_count=10,
            )

        # 1つを削除
        collector.record_test_deletion("tests/test_0.py", reason="Low quality")

        metrics = collector.get_metrics("test_module.py")

        assert metrics.total_tests_generated == 3
        assert metrics.tests_deleted == 1

    def test_get_metrics_mixed_generators(self, collector, monkeypatch):
        """AI と人間の混在テスト"""
        mock_strategy_class = MagicMock()
        mock_manager = MagicMock()
        mock_manager.get_min_coverage.return_value = 80
        mock_strategy_class.return_value = mock_manager

        def mock_import(name, *args, **kwargs):
            if "test_strategy" in name:
                mock_module = MagicMock()
                mock_module.TestStrategyManager = mock_strategy_class
                return mock_module
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        # AI 生成
        collector.record_test_generation(
            module_name="mixed.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test_mixed_ai.py",
            test_count=20,
            generated_by="ai",
        )

        # 人間が作成
        collector.record_test_generation(
            module_name="mixed.py",
            risk_level="A",
            strategy="manual",
            test_file_path="tests/test_mixed_human.py",
            test_count=10,
            generated_by="human",
        )

        # AI+人間の協働
        collector.record_test_generation(
            module_name="mixed.py",
            risk_level="A",
            strategy="hybrid",
            test_file_path="tests/test_mixed_hybrid.py",
            test_count=15,
            generated_by="ai+human",
        )

        metrics = collector.get_metrics("mixed.py")

        assert metrics.total_tests_generated == 3
        assert metrics.ai_generation_count == 1
        assert metrics.human_generation_count == 1

    def test_get_metrics_nonexistent_module(self, collector):
        """存在しないモジュールのメトリクス"""
        metrics = collector.get_metrics("nonexistent.py")
        assert metrics is None


# ============================================================================
# Tests: get_ai_effectiveness_by_risk
# ============================================================================


class TestGetAIEffectivenessByRisk:
    def test_effectiveness_by_risk_simple(self, collector):
        """リスクランク別の効果測定"""
        # リスクS
        collector.record_test_generation(
            module_name="critical.py",
            risk_level="S",
            strategy="mutation",
            test_file_path="tests/test_critical.py",
            test_count=30,
            generated_by="ai",
        )
        collector.record_bug_found("tests/test_critical.py", bug_count=5)

        # リスクA
        collector.record_test_generation(
            module_name="important.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test_important.py",
            test_count=20,
            generated_by="ai",
        )
        collector.record_bug_found("tests/test_important.py", bug_count=2)

        results = collector.get_ai_effectiveness_by_risk()

        assert "S" in results
        assert "A" in results

        assert results["S"]["total_generated"] == 1
        assert results["S"]["bugs_found"] == 5
        assert results["S"]["effectiveness_score"] == 5.0

        assert results["A"]["total_generated"] == 1
        assert results["A"]["bugs_found"] == 2
        assert results["A"]["effectiveness_score"] == 2.0

    def test_effectiveness_by_risk_filters_ai_only(self, collector):
        """AI生成のみをカウント"""
        # AI 生成
        collector.record_test_generation(
            module_name="ai_test.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test_ai.py",
            test_count=20,
            generated_by="ai",
        )

        # 人間が作成（カウントされない）
        collector.record_test_generation(
            module_name="human_test.py",
            risk_level="A",
            strategy="manual",
            test_file_path="tests/test_human.py",
            test_count=10,
            generated_by="human",
        )

        results = collector.get_ai_effectiveness_by_risk()

        assert results["A"]["total_generated"] == 1

    def test_effectiveness_by_risk_includes_deletions(self, collector):
        """削除されたテストもカウント"""
        collector.record_test_generation(
            module_name="deleted_test.py",
            risk_level="B",
            strategy="unit",
            test_file_path="tests/test_deleted.py",
            test_count=10,
            generated_by="ai",
        )

        collector.record_test_deletion("tests/test_deleted.py", reason="Low quality")

        results = collector.get_ai_effectiveness_by_risk()

        assert results["B"]["deleted"] == 1

    def test_effectiveness_by_risk_module_count(self, collector):
        """モジュール数のカウント"""
        # リスクAで3つのモジュール
        for i in range(3):
            collector.record_test_generation(
                module_name=f"module{i}.py",
                risk_level="A",
                strategy="property_based",
                test_file_path=f"tests/test_module{i}.py",
                test_count=20,
                generated_by="ai",
            )

        results = collector.get_ai_effectiveness_by_risk()

        assert results["A"]["module_count"] == 3
        assert len(results["A"]["modules"]) == 3


# ============================================================================
# Tests: _load_history and _rewrite_history
# ============================================================================


class TestHistoryManagement:
    def test_load_empty_history(self, collector):
        """空の履歴ファイル"""
        records = collector._load_history()
        assert records == []

    def test_load_history_with_records(self, collector):
        """レコードを含む履歴ファイル"""
        # いくつかレコードを書き込む
        collector.record_test_generation(
            module_name="test1.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test1.py",
            test_count=10,
        )
        collector.record_test_generation(
            module_name="test2.py",
            risk_level="B",
            strategy="unit",
            test_file_path="tests/test2.py",
            test_count=5,
        )

        records = collector._load_history()
        assert len(records) == 2

    def test_load_history_with_invalid_json(self, collector, temp_project):
        """無効なJSON行があっても処理を継続"""
        # 有効なレコードと無効なJSONを混在させる
        collector.record_test_generation(
            module_name="test1.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test1.py",
            test_count=10,
        )

        # 無効なJSON行を追加
        with collector.history_file.open("a") as f:
            f.write("invalid json line\n")

        collector.record_test_generation(
            module_name="test2.py",
            risk_level="B",
            strategy="unit",
            test_file_path="tests/test2.py",
            test_count=5,
        )

        records = collector._load_history()
        # 無効な行はスキップされる
        assert len(records) == 2

    def test_rewrite_history(self, collector):
        """履歴ファイルの再書き込み"""
        # 初期レコード
        collector.record_test_generation(
            module_name="test1.py",
            risk_level="A",
            strategy="property_based",
            test_file_path="tests/test1.py",
            test_count=10,
        )

        # レコードを読み込み、変更して再書き込み
        records = collector._load_history()
        records[0]["test_count"] = 20
        collector._rewrite_history(records)

        # 再読み込みして確認
        new_records = collector._load_history()
        assert new_records[0]["test_count"] == 20


# ============================================================================
# Tests: Edge cases
# ============================================================================


class TestEdgeCases:
    def test_collector_with_nonexistent_project(self):
        """存在しないプロジェクトパスでも動作"""
        collector = TestMetricsCollector("/nonexistent/path")
        # ディレクトリが作成される
        assert collector.metrics_dir.exists()

    def test_record_generation_with_zero_test_count(self, collector):
        """テスト数0でも記録"""
        collector.record_test_generation(
            module_name="empty.py",
            risk_level="B",
            strategy="unit",
            test_file_path="tests/test_empty.py",
            test_count=0,
        )

        records = collector._load_history()
        assert records[0]["test_count"] == 0

    def test_record_generation_with_negative_coverage(self, collector):
        """負のカバレッジ値"""
        collector.record_test_generation(
            module_name="weird.py",
            risk_level="B",
            strategy="unit",
            test_file_path="tests/test_weird.py",
            test_count=10,
            coverage_before=-1.0,
            coverage_after=50.0,
        )

        records = collector._load_history()
        assert records[0]["coverage_before"] == -1.0

    def test_get_metrics_with_no_coverage_data(self, collector, monkeypatch):
        """カバレッジデータなしのメトリクス"""
        mock_strategy_class = MagicMock()
        mock_manager = MagicMock()
        mock_manager.get_min_coverage.return_value = 80
        mock_strategy_class.return_value = mock_manager

        def mock_import(name, *args, **kwargs):
            if "test_strategy" in name:
                mock_module = MagicMock()
                mock_module.TestStrategyManager = mock_strategy_class
                return mock_module
            return __import__(name, *args, **kwargs)

        monkeypatch.setattr("builtins.__import__", mock_import)

        collector.record_test_generation(
            module_name="no_coverage.py",
            risk_level="B",
            strategy="unit",
            test_file_path="tests/test_no_coverage.py",
            test_count=10,
        )

        metrics = collector.get_metrics("no_coverage.py")
        assert metrics.coverage_current == 0.0
