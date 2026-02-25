"""
test_metrics.py

テストメトリクスの収集と分析。

NexusCore のテスト戦略の効果を測定し、
フィードバックループを構築するためのメトリクスを提供します。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TestGenerationRecord:
    """テスト生成の記録"""

    timestamp: str
    module_name: str
    risk_level: str
    strategy: str
    test_file_path: str
    test_count: int
    generated_by: str  # "ai" | "human" | "ai+human"
    coverage_before: float | None = None
    coverage_after: float | None = None
    bugs_found: int = 0
    deleted: bool = False
    deleted_reason: str | None = None


@dataclass
class TestMetrics:
    """テストメトリクスの集計結果"""

    module_name: str
    risk_level: str
    total_tests_generated: int
    tests_deleted: int
    bugs_found: int
    coverage_current: float
    coverage_target: int
    ai_generation_count: int
    human_generation_count: int
    effectiveness_score: float  # バグ検出数 / 生成テスト数


class TestMetricsCollector:
    """
    テストメトリクスを収集・分析するクラス。

    テスト生成履歴を記録し、AI生成テストの効果を測定します。
    """

    def __init__(self, project_root: str) -> None:
        """
        :param project_root: プロジェクトルート
        """
        self.project_root = Path(project_root)
        self.metrics_dir = self.project_root / ".nexus" / "test_metrics"
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.metrics_dir / "test_generation_history.jsonl"

    def record_test_generation(
        self,
        module_name: str,
        risk_level: str,
        strategy: str,
        test_file_path: str,
        test_count: int,
        generated_by: str = "ai",
        coverage_before: float | None = None,
        coverage_after: float | None = None,
    ) -> None:
        """
        テスト生成を記録する。

        :param module_name: モジュール名
        :param risk_level: リスクランク（"S" | "A" | "B"）
        :param strategy: テスト生成戦略
        :param test_file_path: 生成されたテストファイルのパス
        :param test_count: 生成されたテスト数
        :param generated_by: 生成者（"ai" | "human" | "ai+human"）
        :param coverage_before: 生成前のカバレッジ（%）
        :param coverage_after: 生成後のカバレッジ（%）
        """
        record = TestGenerationRecord(
            timestamp=datetime.now(UTC).isoformat(),
            module_name=module_name,
            risk_level=risk_level,
            strategy=strategy,
            test_file_path=test_file_path,
            test_count=test_count,
            generated_by=generated_by,
            coverage_before=coverage_before,
            coverage_after=coverage_after,
        )

        try:
            with self.history_file.open("a", encoding="utf-8") as f:
                json.dump(asdict(record), f, ensure_ascii=False)
                f.write("\n")
        except Exception as e:
            logger.error(f"Failed to record test generation: {e}", exc_info=True)

    def record_bug_found(
        self,
        test_file_path: str,
        bug_count: int = 1,
    ) -> None:
        """
        テストがバグを発見したことを記録する。

        :param test_file_path: テストファイルのパス
        :param bug_count: 発見したバグ数
        """
        # 履歴ファイルから該当レコードを探して更新
        # 簡易実装: 最新の該当レコードを更新
        try:
            records = self._load_history()
            for record in reversed(records):
                if record.get("test_file_path") == test_file_path:
                    record["bugs_found"] = record.get("bugs_found", 0) + bug_count
                    # 履歴ファイルを再書き込み（簡易実装）
                    self._rewrite_history(records)
                    break
        except Exception as e:
            logger.error(f"Failed to record bug found: {e}", exc_info=True)

    def record_test_deletion(
        self,
        test_file_path: str,
        reason: str,
    ) -> None:
        """
        テストが削除されたことを記録する。

        :param test_file_path: テストファイルのパス
        :param reason: 削除理由
        """
        try:
            records = self._load_history()
            for record in reversed(records):
                if record.get("test_file_path") == test_file_path:
                    record["deleted"] = True
                    record["deleted_reason"] = reason
                    self._rewrite_history(records)
                    break
        except Exception as e:
            logger.error(f"Failed to record test deletion: {e}", exc_info=True)

    def get_metrics(self, module_name: str) -> TestMetrics | None:
        """
        モジュールのテストメトリクスを取得する。

        :param module_name: モジュール名
        :return: テストメトリクス（見つからない場合は None）
        """
        records = self._load_history()
        module_records = [r for r in records if r.get("module_name") == module_name]

        if not module_records:
            return None

        total_generated = len(module_records)
        deleted = sum(1 for r in module_records if r.get("deleted", False))
        bugs_found = sum(r.get("bugs_found", 0) for r in module_records)
        ai_count = sum(1 for r in module_records if r.get("generated_by") == "ai")
        human_count = sum(1 for r in module_records if r.get("generated_by") == "human")

        # 最新のカバレッジを取得
        latest_record = max(module_records, key=lambda r: r.get("timestamp", ""))
        coverage_current = latest_record.get("coverage_after") or 0.0

        # リスクランクと目標カバレッジを取得
        risk_level = latest_record.get("risk_level", "B")
        from nexuscore.agents.test_strategy import TestStrategyManager

        strategy_manager = TestStrategyManager()
        coverage_target = strategy_manager.get_min_coverage(module_name)

        # 効果スコア（バグ検出数 / 生成テスト数）
        effectiveness_score = bugs_found / total_generated if total_generated > 0 else 0.0

        return TestMetrics(
            module_name=module_name,
            risk_level=risk_level,
            total_tests_generated=total_generated,
            tests_deleted=deleted,
            bugs_found=bugs_found,
            coverage_current=coverage_current,
            coverage_target=coverage_target,
            ai_generation_count=ai_count,
            human_generation_count=human_count,
            effectiveness_score=effectiveness_score,
        )

    def get_ai_effectiveness_by_risk(self) -> dict[str, dict[str, Any]]:
        """
        リスクランク別のAI生成テストの効果を集計する。

        Returns:
            リスクランク別の効果メトリクス
        """
        records = self._load_history()
        ai_records = [r for r in records if r.get("generated_by") == "ai"]

        by_risk: dict[str, dict[str, Any]] = {}

        for record in ai_records:
            risk = record.get("risk_level", "B")
            if risk not in by_risk:
                by_risk[risk] = {
                    "total_generated": 0,
                    "bugs_found": 0,
                    "deleted": 0,
                    "modules": set(),
                }

            by_risk[risk]["total_generated"] += 1
            by_risk[risk]["bugs_found"] += record.get("bugs_found", 0)
            if record.get("deleted", False):
                by_risk[risk]["deleted"] += 1
            by_risk[risk]["modules"].add(record.get("module_name", "unknown"))

        # 効果スコアを計算
        for _risk, data in by_risk.items():
            data["effectiveness_score"] = (
                data["bugs_found"] / data["total_generated"] if data["total_generated"] > 0 else 0.0
            )
            data["modules"] = list(data["modules"])
            data["module_count"] = len(data["modules"])

        return by_risk

    def _load_history(self) -> list[dict[str, Any]]:
        """履歴ファイルを読み込む"""
        if not self.history_file.exists():
            return []

        records = []
        try:
            with self.history_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        continue
        except Exception as e:
            logger.error(f"Failed to load test generation history: {e}", exc_info=True)

        return records

    def _rewrite_history(self, records: list[dict[str, Any]]) -> None:
        """履歴ファイルを再書き込み（簡易実装）"""
        try:
            with self.history_file.open("w", encoding="utf-8") as f:
                for record in records:
                    json.dump(record, f, ensure_ascii=False)
                    f.write("\n")
        except Exception as e:
            logger.error(f"Failed to rewrite history: {e}", exc_info=True)
