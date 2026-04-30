"""
Run 完了時 Markdown レポート自動生成モジュール

Run 完了時に、Self-Healing Summary・LLMコスト・テスト結果・ログリンクを
1枚の Markdown レポートにまとめて保存する。
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Webapp モデルはオプショナルインポート
try:
    from nexuscore.webapp import db
    from nexuscore.webapp.models import ExecutionLog, PatchRecord, Project, Run

    HAS_WEBAPP = True
except ImportError:
    HAS_WEBAPP = False
    Run = None
    Project = None
    PatchRecord = None
    ExecutionLog = None
    db = None

# Config は必須
try:
    from nexuscore.config.config import AppConfig
except ImportError:
    import os

    class AppConfig:  # type: ignore
        WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "http://localhost:5000")


def _format_duration(run: Run) -> str:
    """実行時間をフォーマットする"""
    if not run.started_at or not run.finished_at:
        return "N/A"

    delta = run.finished_at - run.started_at
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return f"{total_seconds}s"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}m {seconds}s"
    else:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"


def _estimate_diff_lines(diff_text: str) -> int:
    """diff テキストから変更行数を推定（簡易版）"""
    if not diff_text:
        return 0

    lines = diff_text.splitlines()
    count = 0
    for line in lines:
        if line.startswith("+") or line.startswith("-"):
            if not line.startswith("+++") and not line.startswith("---"):
                count += 1
    return count


def _collect_run_metrics(run: Run) -> dict[str, Any]:
    """Run からメトリクスを収集する（github_pr_comment.py の関数を再利用）"""
    try:
        from nexuscore.integration.github_pr_comment import _collect_run_metrics as _collect_metrics

        return _collect_metrics(run)
    except ImportError:
        # フォールバック: 自前で実装
        if not HAS_WEBAPP:
            return {
                "duration_str": "N/A",
                "patch_files_count": 0,
                "patch_lines": 0,
                "model_call_counts": {},
                "estimated_cost_jpy": 0.0,
            }

        # パッチ情報
        patch_files = set()
        total_patch_lines = 0

        try:
            patches = PatchRecord.query.filter_by(run_id=run.id).all()
            for p in patches:
                patch_files.add(p.file_path)
                total_patch_lines += _estimate_diff_lines(p.diff_text or "")
        except Exception as e:
            logger.warning(f"Failed to collect patch metrics: {e}", exc_info=True)

        # LLMログ (NPE)
        models: defaultdict[str, int] = defaultdict(int)
        total_cost = 0.0

        try:
            logs = ExecutionLog.query.filter_by(run_id=run.id, source="NPE").all()
            for lg in logs:
                payload = lg.payload_json or {}
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = {}

                model = payload.get("model") or payload.get("model_name") or "unknown"
                models[model] += 1

                cost = (
                    payload.get("estimated_cost")
                    or payload.get("cost_jpy")
                    or payload.get("usage", {}).get("cost_jpy", 0.0)
                )
                try:
                    total_cost += float(cost)
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Failed to collect LLM metrics: {e}", exc_info=True)

        return {
            "duration_str": _format_duration(run),
            "patch_files_count": len(patch_files),
            "patch_lines": total_patch_lines,
            "model_call_counts": dict(models),
            "estimated_cost_jpy": total_cost,
        }


def _compute_recent_success_rate(project_id: int, limit: int = 30) -> float:
    """過去N回の成功率を計算する（github_pr_comment.py の関数を再利用）"""
    try:
        from nexuscore.integration.github_pr_comment import (
            _compute_recent_success_rate as _compute_rate,
        )

        return _compute_rate(project_id, limit)
    except ImportError:
        # フォールバック: 自前で実装
        if not HAS_WEBAPP or not Run:
            return 0.0

        try:
            from sqlalchemy import desc

            q = (
                Run.query.filter(Run.project_id == project_id)
                .order_by(desc(Run.started_at))
                .limit(limit)
            )
            runs = q.all()

            if not runs:
                return 0.0

            success = sum(1 for r in runs if r.status == "SUCCESS")
            return success / len(runs)
        except Exception as e:
            logger.warning(f"Failed to compute success rate: {e}", exc_info=True)
            return 0.0


def _collect_test_results(run: Run) -> dict[str, Any]:
    """テスト結果を収集する"""
    if not HAS_WEBAPP or not ExecutionLog:
        return {
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "test_output": "",
        }

    try:
        logs = ExecutionLog.query.filter_by(run_id=run.id).all()

        error_count = sum(1 for lg in logs if lg.level == "ERROR")
        warning_count = sum(1 for lg in logs if lg.level == "WARNING")
        info_count = sum(1 for lg in logs if lg.level == "INFO")

        # テスト出力を集約（SANDBOX / ORCHESTRATOR のログから）
        test_outputs = []
        for lg in logs:
            if lg.source in ("SANDBOX", "ORCHESTRATOR") and lg.level in ("ERROR", "WARNING"):
                test_outputs.append(f"[{lg.level}] {lg.message}")

        return {
            "error_count": error_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "test_output": "\n".join(test_outputs[:20]),  # 最大20件
        }
    except Exception as e:
        logger.warning(f"Failed to collect test results: {e}", exc_info=True)
        return {
            "error_count": 0,
            "warning_count": 0,
            "info_count": 0,
            "test_output": "",
        }


def generate_run_report_markdown(run_db_id: int) -> str:
    """
    単一 Run 向けの Markdown レポート本文を返す。

    Args:
        run_db_id: Run.id（DB上のID）

    Returns:
        Markdown 形式のレポート本文
    """
    if not HAS_WEBAPP:
        return "# Run Report\n\nWebapp models not available.\n"

    try:
        run: Run | None = Run.query.get(run_db_id)
        if not run:
            return f"# Run Report\n\nRun not found: ID={run_db_id}\n"

        project: Project | None = run.project
        if not project:
            return f"# Run Report\n\nProject not found for Run ID={run_db_id}\n"

        # メトリクス収集
        metrics = _collect_run_metrics(run)
        test_results = _collect_test_results(run)
        success_rate = _compute_recent_success_rate(project.id, limit=30)

        # URL生成
        base_url = AppConfig.WEBAPP_BASE_URL.rstrip("/")
        run_logs_url = f"{base_url}/logs/runs/{run.run_id}"
        project_logs_url = f"{base_url}/logs/projects/{project.id}"
        project_dashboard_url = f"{base_url}/dashboard/projects/{project.id}"

        # モデル一覧をフォーマット
        models_str_lines = []
        for model, count in metrics["model_call_counts"].items():
            models_str_lines.append(f"- `{model}`: {count} calls")
        models_str = (
            "\n".join(models_str_lines) if models_str_lines else "- (no LLM calls recorded)"
        )

        # パッチファイル一覧
        patch_files_list = []
        try:
            patches = PatchRecord.query.filter_by(run_id=run.id).all()
            for p in patches:
                patch_files_list.append(
                    f"- `{p.file_path}` ({'applied' if p.applied else 'not applied'})"
                )
        except Exception:
            pass

        patch_files_str = "\n".join(patch_files_list[:10]) if patch_files_list else "- (no patches)"
        if len(patch_files_list) > 10:
            patch_files_str += f"\n- ... and {len(patch_files_list) - 10} more files"

        # Markdown 生成
        report = f"""# Run Report: {run.run_id}

**Generated at:** {datetime.now(UTC).isoformat()} UTC

---

## Project Information

- **Project Name:** {project.name}
- **Repository:** {project.repo_url or 'N/A'}
- **Local Path:** {project.local_path}

---

## Run Summary

- **Run ID:** `{run.run_id}`
- **Status:** `{run.status or 'UNKNOWN'}`
- **Started At:** {run.started_at.isoformat() if run.started_at else 'N/A'}
- **Finished At:** {run.finished_at.isoformat() if run.finished_at else 'N/A'}
- **Duration:** {metrics["duration_str"]}
- **Autonomy Level:** {run.autonomy_level or 1}

---

## Self-Healing Metrics

- **Patches Applied:** {metrics["patch_files_count"]} files, {metrics["patch_lines"]} lines changed
- **LLM Models Used:**
{models_str}
- **Estimated Cost:** ~{metrics["estimated_cost_jpy"]:.2f} JPY
- **Recent Success Rate (last 30 runs):** {success_rate * 100:.1f}%

### Patched Files

{patch_files_str}

---

## Test Results

- **Errors:** {test_results["error_count"]}
- **Warnings:** {test_results["warning_count"]}
- **Info Messages:** {test_results["info_count"]}

### Test Output (Recent Errors/Warnings)

```
{test_results["test_output"] or "(no errors or warnings)"}
```

---

## Observability Links

- **Run Logs:** {run_logs_url}
- **Project Logs:** {project_logs_url}
- **Project Dashboard:** {project_dashboard_url}

---

*This report was automatically generated by NexusCore.*
"""
        return report

    except Exception as e:
        logger.error(f"Failed to generate run report: {e}", exc_info=True)
        return f"# Run Report\n\nError generating report: {e}\n"


def write_run_report_file(run_db_id: int, base_dir: Path | None = None) -> Path:
    """
    docs/run_reports/RUN_{run_id}.md に Markdown を書き出し、ファイルパスを返す。

    Args:
        run_db_id: Run.id（DB上のID）
        base_dir: ベースディレクトリ（デフォルトはプロジェクトルート）

    Returns:
        生成されたレポートファイルのパス
    """
    if not HAS_WEBAPP:
        raise RuntimeError("Webapp models not available")

    try:
        run: Run | None = Run.query.get(run_db_id)
        if not run:
            raise ValueError(f"Run not found: ID={run_db_id}")

        # ベースディレクトリの決定
        if base_dir is None:
            # プロジェクトルートを取得（このファイルの位置から推定）
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent.parent
            base_dir = project_root

        # レポートディレクトリを作成
        reports_dir = base_dir / "docs" / "run_reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # ファイル名
        filename = f"RUN_{run.run_id}.md"
        report_path = reports_dir / filename

        # Markdown を生成して書き出し
        markdown = generate_run_report_markdown(run_db_id)
        report_path.write_text(markdown, encoding="utf-8")

        logger.info(f"Run report written to: {report_path}")
        return report_path

    except Exception as e:
        logger.error(f"Failed to write run report file: {e}", exc_info=True)
        raise


def get_markdown_report_path(run_id: str, base_dir: Path | None = None) -> Path:
    """
    Run レポートの Markdown ファイルパスを返す。

    Args:
        run_id: Run.run_id（文字列）
        base_dir: ベースディレクトリ（デフォルトはプロジェクトルート）

    Returns:
        レポートファイルのパス（存在しない場合でもパスは返す）
    """
    if base_dir is None:
        # プロジェクトルートを取得（このファイルの位置から推定）
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent.parent
        base_dir = project_root

    # レポートディレクトリ
    reports_dir = base_dir / "docs" / "run_reports"

    # ファイル名
    filename = f"RUN_{run_id}.md"
    return reports_dir / filename
