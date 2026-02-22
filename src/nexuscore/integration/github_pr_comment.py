"""
GitHub PR コメント組み立てモジュール

PR コメント本文を組み立てる責務を一箇所に集約する。
GuardianAgent の「コードレビュー本文」と、Self-Healing Summary、リンク、AI要約を統合する。
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence, Union, Dict, Any, List

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Webapp モデルはオプショナルインポート（webapp が利用可能な場合のみ）
try:
    from nexuscore.webapp.models import Run, Project, PatchRecord, ExecutionLog
    from nexuscore.webapp import db
    HAS_WEBAPP = True
except ImportError:
    HAS_WEBAPP = False
    Run = None  # type: ignore
    Project = None  # type: ignore
    PatchRecord = None  # type: ignore
    ExecutionLog = None  # type: ignore
    db = None  # type: ignore

# Config は必須
try:
    from nexuscore.config.config import AppConfig
except ImportError:
    # フォールバック
    import os
    class AppConfig:  # type: ignore
        WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "http://localhost:5000")


class PRCommentContext(BaseModel):
    """
    PR コメント組み立てに必要なコンテキスト情報
    """
    project: Optional[object] = None  # Project モデル（型チェック回避のため object）
    run: Optional[object] = None  # Run モデル
    guardian_review_markdown: str = ""  # 既存のGuardianAgentレビュー本文
    repo_full_name: Optional[str] = None  # "owner/repo"
    pr_number: Optional[int] = None
    branch_name: Optional[str] = None
    commit_sha: Optional[str] = None  # CR-E3: 対象コミットの SHA
    change_summary: Optional[str] = None  # AI生成の修正要約（B-3）
    diff_summary: Optional[Union[str, Dict[str, str]]] = None  # E-4/E-5: Before/After 差分サマリー（単一ファイル: str, 複数ファイル: dict）
    markdown_report: Optional[str] = None  # E-3: Run Markdown レポート全文
    details: Optional[Dict[str, Any]] = None  # E-5: Self-Healing 実行結果の details（メトリクス統合用）
    semantic_diffs: Optional[Dict[str, Dict[str, Any]]] = None  # Semantic Diff 情報


def _format_duration(run: object) -> str:
    """
    実行時間をフォーマットする
    """
    if not HAS_WEBAPP or not hasattr(run, "started_at") or not hasattr(run, "finished_at"):
        return "N/A"

    if not run.started_at or not run.finished_at:  # type: ignore
        return "N/A"

    delta = run.finished_at - run.started_at  # type: ignore
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
    """
    diff テキストから変更行数を推定（簡易版）
    """
    if not diff_text:
        return 0

    lines = diff_text.splitlines()
    count = 0
    for line in lines:
        # "+" または "-" で始まる行をカウント（ファイルヘッダー除く）
        if line.startswith("+") or line.startswith("-"):
            if not line.startswith("+++") and not line.startswith("---"):
                count += 1

    return count


def _estimate_diff_lines_separated(diff_text: str) -> tuple[int, int]:
    """
    diff テキストから追加行数と削除行数を分けて推定（CR-E3）

    Args:
        diff_text: diff テキスト

    Returns:
        (added_lines, removed_lines) のタプル
    """
    if not diff_text:
        return (0, 0)

    lines = diff_text.splitlines()
    added = 0
    removed = 0

    for line in lines:
        # "+" で始まる行は追加行（ファイルヘッダー除く）
        if line.startswith("+") and not line.startswith("+++"):
            added += 1
        # "-" で始まる行は削除行（ファイルヘッダー除く）
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1

    return (added, removed)


def _collect_run_metrics(run: object) -> dict:
    """
    Run からメトリクスを収集する（CR-E3: 追加行数/削除行数を分けて収集）

    Returns:
        dict に以下のキーを含む:
        - duration_str: 実行時間の文字列表現
        - patch_files_count: 変更ファイル数
        - patch_lines: 総変更行数（後方互換性のため残す）
        - added_lines: 追加行数（CR-E3）
        - removed_lines: 削除行数（CR-E3）
        - model_call_counts: モデルごとの呼び出し回数
        - estimated_cost_jpy: 推定コスト（JPY）
        - start_time: 開始時刻（datetime、CR-E3）
        - end_time: 終了時刻（datetime、CR-E3）
        - duration_seconds: 経過時間（秒、CR-E3）
    """
    if not HAS_WEBAPP:
        return {
            "duration_str": "N/A",
            "patch_files_count": 0,
            "patch_lines": 0,
            "added_lines": 0,
            "removed_lines": 0,
            "model_call_counts": {},
            "estimated_cost_jpy": 0.0,
            "start_time": None,
            "end_time": None,
            "duration_seconds": 0.0,
        }

    # パッチ情報
    patch_files = set()
    total_patch_lines = 0
    total_added_lines = 0
    total_removed_lines = 0

    try:
        if hasattr(run, "id") and PatchRecord:
            patches = PatchRecord.query.filter_by(run_id=run.id).all()  # type: ignore
            for p in patches:
                patch_files.add(p.file_path)  # type: ignore
                diff_text = p.diff_text or ""  # type: ignore
                total_patch_lines += _estimate_diff_lines(diff_text)
                # CR-E3: 追加行数と削除行数を分けて収集
                added, removed = _estimate_diff_lines_separated(diff_text)
                total_added_lines += added
                total_removed_lines += removed
    except Exception as e:
        logger.warning(f"Failed to collect patch metrics: {e}", exc_info=True)

    # LLMログ (NPE)
    models = defaultdict(int)
    total_cost = 0.0

    try:
        if hasattr(run, "id") and ExecutionLog:
            logs = ExecutionLog.query.filter_by(run_id=run.id, source="NPE").all()  # type: ignore
            for lg in logs:
                payload = lg.payload_json or {}  # type: ignore
                if isinstance(payload, str):
                    try:
                        payload = json.loads(payload)
                    except Exception:
                        payload = {}

                model = payload.get("model") or payload.get("model_name") or "unknown"
                models[model] += 1

                cost = payload.get("estimated_cost") or payload.get("cost_jpy") or payload.get("usage", {}).get("cost_jpy", 0.0)
                try:
                    total_cost += float(cost)
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Failed to collect LLM metrics: {e}", exc_info=True)

    # CR-E3: 実行時間の詳細を取得
    start_time = None
    end_time = None
    duration_seconds = 0.0

    if hasattr(run, "started_at") and run.started_at:  # type: ignore
        start_time = run.started_at  # type: ignore
    if hasattr(run, "finished_at") and run.finished_at:  # type: ignore
        end_time = run.finished_at  # type: ignore

    if start_time and end_time:
        delta = end_time - start_time  # type: ignore
        duration_seconds = delta.total_seconds()

    return {
        "duration_str": _format_duration(run),
        "patch_files_count": len(patch_files),
        "patch_lines": total_patch_lines,  # 後方互換性のため残す
        "added_lines": total_added_lines,  # CR-E3
        "removed_lines": total_removed_lines,  # CR-E3
        "model_call_counts": dict(models),
        "estimated_cost_jpy": total_cost,
        "start_time": start_time,  # CR-E3
        "end_time": end_time,  # CR-E3
        "duration_seconds": duration_seconds,  # CR-E3
    }


def _compute_recent_success_rate(project_id: int, limit: int = 30) -> float:
    """
    過去N回の成功率を計算する
    """
    if not HAS_WEBAPP or not Run:
        return 0.0

    try:
        q = (
            Run.query  # type: ignore
            .filter(Run.project_id == project_id)  # type: ignore
            .order_by(Run.started_at.desc().nullslast())  # type: ignore
            .limit(limit)
        )
        runs = q.all()

        if not runs:
            return 0.0

        success = sum(1 for r in runs if hasattr(r, "status") and r.status == "SUCCESS")  # type: ignore
        return success / len(runs)
    except Exception as e:
        logger.warning(f"Failed to compute success rate: {e}", exc_info=True)
        return 0.0


def build_run_logs_url(project_id: int, run: object) -> str:
    """
    Run ログの URL を構築する
    """
    base = AppConfig.WEBAPP_BASE_URL.rstrip("/")
    if hasattr(run, "run_id"):
        return f"{base}/logs/runs/{run.run_id}"  # type: ignore
    elif hasattr(run, "id"):
        return f"{base}/logs/runs/{run.id}"  # type: ignore
    else:
        return f"{base}/logs/runs/unknown"


def build_project_logs_url(project_id: int) -> str:
    """
    プロジェクトログの URL を構築する
    """
    base = AppConfig.WEBAPP_BASE_URL.rstrip("/")
    return f"{base}/logs/projects/{project_id}"


def build_project_dashboard_url(project_id: int) -> str:
    """
    プロジェクトダッシュボードの URL を構築する
    """
    base = AppConfig.WEBAPP_BASE_URL.rstrip("/")
    return f"{base}/dashboard/projects/{project_id}"


# ------------------------------------------------------------------ #
# E-3: Run Markdown レポート読み込み
# ------------------------------------------------------------------ #
def load_run_markdown(run_id: str) -> str:
    """
    docs/run_reports/<run_id>.md を読み込み文字列で返す。

    ファイルが存在しない場合は空文字を返す。

    Args:
        run_id: Run.run_id（文字列）

    Returns:
        Markdown レポートの本文（ファイルが存在しない場合は空文字）
    """
    try:
        from nexuscore.integration.run_report_generator import get_markdown_report_path

        report_path = get_markdown_report_path(run_id)
        if report_path.exists():
            return report_path.read_text(encoding="utf-8")
        else:
            logger.debug(f"Run report not found: {report_path}")
            return ""
    except Exception as e:
        logger.warning(f"Failed to load run markdown: {e}", exc_info=True)
        return ""


def format_markdown_report_block(md_text: str) -> str:
    """
    Markdown の <details><summary>Run Report</summary>...</details> を生成する。

    Args:
        md_text: Markdown レポートの本文

    Returns:
        <details> タグで囲まれた Markdown ブロック
    """
    if not md_text.strip():
        return ""

    return f"""<details>
<summary>📄 Run Report (Markdown)</summary>

{md_text}

</details>
"""


# ------------------------------------------------------------------ #
# E-4/E-5: Before/After 差分サマリーブロック（複数ファイル対応）
# ------------------------------------------------------------------ #
# ------------------------------------------------------------------ #
# E-5: カード形式 UI レンダリング関数
# ------------------------------------------------------------------ #
def render_summary_card(
    metrics: Dict[str, Any],
    details: Optional[Dict[str, Any]] = None,
) -> str:
    """
    実行メトリクスをカード形式（Markdown テーブル）でレンダリングする。

    Args:
        metrics: _collect_run_metrics() の戻り値
        details: Self-Healing 実行結果の details 辞書（E-5 メトリクス統合用）

    Returns:
        Markdown テーブル形式のカード
    """
    rows: list[str] = []

    # E-5: details から実行メトリクスを取得
    execution_ms = details.get("execution_ms") if details else None
    retry_count = details.get("retry_count", 0) if details else 0
    model_name = details.get("model") if details else None
    token_usage = details.get("token_usage") if details else None
    cost_usd = details.get("cost_usd") if details else None
    files_changed = details.get("files_changed") if details else None
    last_error_class = details.get("last_error_class") if details else None  # 4.4: エラー種別

    # モデル名（優先順位: details.model > metrics の最初のモデル）
    if model_name:
        model_display = model_name
    elif metrics.get("model_call_counts"):
        first_model = list(metrics["model_call_counts"].keys())[0]
        model_display = first_model
    else:
        model_display = "N/A"

    # 実行時間（優先順位: details.execution_ms > metrics.duration_str）
    if execution_ms is not None:
        if execution_ms < 1000:
            exec_time_display = f"{execution_ms:.0f}ms"
        elif execution_ms < 60000:
            exec_time_display = f"{execution_ms / 1000:.1f}s"
        else:
            exec_time_display = f"{execution_ms / 60000:.1f}m"
    else:
        exec_time_display = metrics.get("duration_str", "N/A")

    # コスト（優先順位: details.cost_usd > metrics.estimated_cost_jpy）
    if cost_usd is not None:
        cost_display = f"${cost_usd:.4f} USD"
    else:
        cost_jpy = metrics.get("estimated_cost_jpy", 0.0)
        if cost_jpy > 0:
            cost_display = f"~{cost_jpy:.2f} JPY"
        else:
            cost_display = "N/A"

    # ファイル変更数（優先順位: details.files_changed > metrics.patch_files_count）
    if files_changed is not None:
        files_display = str(files_changed)
    else:
        files_display = str(metrics.get("patch_files_count", 0))

    # テーブル行を構築
    rows.append(f"| Model | {model_display} |")
    rows.append(f"| Exec Time | {exec_time_display} |")
    if retry_count > 0:
        rows.append(f"| Retry | {retry_count} |")
    rows.append(f"| Files Changed | {files_display} |")
    if token_usage:
        rows.append(f"| Token Usage | {token_usage} |")
    rows.append(f"| Cost | {cost_display} |")
    # 4.4: エラー種別を表示（retry が発生した場合のみ）
    if last_error_class and retry_count > 0:
        rows.append(f"| Last Error | {last_error_class} |")

    return f"""## 🤖 Self-Healing Summary

| Metric | Value |
|--------|-------|
{chr(10).join(rows)}

"""


def format_diff_summary_block(
    summary_text: Optional[str] = None,
    file_summaries: Optional[Dict[str, str]] = None,
) -> str:
    """
    Before/After 差分の AI 要約を <details> に収める。

    Args:
        summary_text: AI 生成の差分要約（5行以内、単一ファイル用、後方互換性）
        file_summaries: ファイル名をキー、要約を値とする辞書（E-5 複数ファイル用）

    Returns:
        <details> タグで囲まれた差分サマリーブロック
    """
    # E-5: 複数ファイル対応
    if file_summaries:
        parts: list[str] = []
        parts.append("## 🔍 AI Diff Summary (Multiple Files)\n")
        for file_path, summary in file_summaries.items():
            if summary and summary.strip():
                parts.append(f"""<details>
<summary>{file_path}</summary>

{summary}

</details>
""")
        return "\n".join(parts) if parts else ""

    # E-4: 単一ファイル対応（後方互換性）
    if not summary_text or not summary_text.strip():
        return ""

    return f"""## 🤖 AI Diff Summary (Before → After)

<details>
<summary>差分要約（5行）</summary>

{summary_text}

</details>
"""


def format_semantic_diff_block(
    semantic_diffs: Optional[Dict[str, Dict[str, Any]]],
) -> str:
    """
    semantic_diffs を Markdown (<details>) でレンダリングする。

    Args:
        semantic_diffs: Semantic Diff 情報
            {
                "file.py": {
                    "functions": [...],
                    "behavior_hints": [...],
                }
            }

    Returns:
        Markdown 形式の <details> ブロック
    """
    if not semantic_diffs:
        return ""

    blocks: List[str] = []

    for rel_path, data in semantic_diffs.items():
        functions = data.get("functions") or []
        behavior_hints = data.get("behavior_hints") or []

        # 関数の追加/削除/変更のテーブル
        table_lines = [
            "| Function | Kind | Before | After |",
            "|----------|------|--------|-------|",
        ]

        for f in functions:
            name = f.get("name", "")
            kind = f.get("kind", "")
            sig_before = f.get("signature_before") or ""
            sig_after = f.get("signature_after") or ""

            # シグネチャが長すぎる場合は省略
            if len(sig_before) > 50:
                sig_before = sig_before[:47] + "..."
            if len(sig_after) > 50:
                sig_after = sig_after[:47] + "..."

            table_lines.append(
                f"| `{name}` | {kind} | `{sig_before}` | `{sig_after}` |"
            )

        behavior_lines = []
        for hint in behavior_hints:
            desc = hint.get("description") or ""
            risk = hint.get("risk_level") or "medium"
            risk_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(risk, "🟡")
            behavior_lines.append(f"- {risk_emoji} ({risk}) {desc}")

        block = f"""<details>

<summary>🧠 Semantic Diff: `{rel_path}`</summary>

### Functions

{chr(10).join(table_lines) if len(table_lines) > 2 else "_(no function changes)_"}

### Behavior Hints

{chr(10).join(behavior_lines) if behavior_lines else "_(no behavior hints)_"}

</details>"""
        blocks.append(block)

    return "\n\n".join(blocks)


def format_metadata_block(
    run_id: str,
    pr_number: Optional[int],
    commit_sha: Optional[str],
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    duration_seconds: float,
    primary_model: str,
    aux_models: list[str],
    changed_files: int,
    added_lines: int,
    removed_lines: int,
    success_rate_last_n: Optional[float] = None,
    recent_runs_window: int = 30,
) -> str:
    """
    CR-E3: Self-Healing メタ情報ブロックを生成する

    Args:
        run_id: Run ID
        pr_number: PR 番号
        commit_sha: 対象コミットの SHA（短縮形式）
        start_time: 開始時刻
        end_time: 終了時刻
        duration_seconds: 経過時間（秒）
        primary_model: メインで使用したモデル名
        aux_models: 補助的に使用したモデル名のリスト
        changed_files: 変更ファイル数
        added_lines: 追加行数
        removed_lines: 削除行数
        success_rate_last_n: 過去 N 回の成功率（0.0-1.0）
        recent_runs_window: 成功率計算の対象期間（デフォルト: 30）

    Returns:
        Markdown 形式のメタ情報ブロック
    """
    parts: list[str] = []

    # ヘッダー
    parts.append("### 🛠 Self-Healing Summary\n")

    # Run 識別情報
    parts.append(f"- Run ID: `{run_id}`")
    if pr_number:
        parts.append(f"- PR: #{pr_number}")
    if commit_sha:
        # 短縮形式（7文字）を表示
        short_sha = commit_sha[:7] if len(commit_sha) > 7 else commit_sha
        parts.append(f"- Commit: `{short_sha}`")
    parts.append("")

    # 実行時間
    parts.append("**Execution**")
    if start_time:
        parts.append(f"- Start: {start_time.isoformat()}Z")
    else:
        parts.append("- Start: N/A")
    if end_time:
        parts.append(f"- End:   {end_time.isoformat()}Z")
    else:
        parts.append("- End:   N/A")

    # 経過時間のフォーマット
    if duration_seconds > 0:
        if duration_seconds < 60:
            duration_str = f"{duration_seconds:.1f}s"
        elif duration_seconds < 3600:
            duration_str = f"{duration_seconds / 60:.1f}m"
        else:
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            duration_str = f"{hours}h {minutes}m"
    else:
        duration_str = "N/A"
    parts.append(f"- Duration: {duration_str}")

    # 使用モデル
    model_parts = [primary_model]
    if aux_models:
        model_parts.extend(aux_models)
    if len(model_parts) == 1:
        parts.append(f"- Model: {primary_model}")
    else:
        parts.append(f"- Model: {primary_model} (primary), {', '.join(aux_models)} (aux)")
    parts.append("")

    # 変更規模
    parts.append("**Effect**")
    parts.append(f"- Changed files: {changed_files}")
    parts.append(f"- +{added_lines} / -{removed_lines} lines")
    parts.append("")

    # 信頼性（成功率）
    parts.append("**Reliability**")
    if success_rate_last_n is not None:
        success_rate_percent = success_rate_last_n * 100
        parts.append(f"- Success rate (last {recent_runs_window} runs): {success_rate_percent:.1f}%")
    else:
        parts.append(f"- Success rate (last {recent_runs_window} runs): N/A")
    parts.append("")

    return "\n".join(parts)


def build_pr_comment(ctx: PRCommentContext) -> str:
    """
    PR コメント本文を組み立てる

    CR-NEXUS-039 Follow-up: 責務境界の明文化
    - この関数は Guardian/Diff/Links/MarkdownReport 等の付随セクションの組み立てに限定する
    - "## Self-Healing Result" 見出しは出さない（上位の format_pr_comment() が固定で付与する）
    - この関数が誤って Self-Healing Result を出すと二重化するため禁止

    Args:
        ctx: PR コメントコンテキスト

    Returns:
        Markdown 形式の PR コメント本文（Self-Healing Result 見出しを含まない）
    """
    parts: list[str] = []

    # === CR-E3: Self-Healing メタ情報ブロック ===
    if ctx.run is not None and ctx.project is not None:
        try:
            metrics = _collect_run_metrics(ctx.run)

            # プロジェクトIDを取得
            project_id = 0
            if hasattr(ctx.project, "id"):
                project_id = ctx.project.id  # type: ignore

            success_rate = None
            if project_id > 0:
                success_rate = _compute_recent_success_rate(project_id, limit=30)

            # Run ID を取得
            run_id = "unknown"
            if hasattr(ctx.run, "run_id"):
                run_id = ctx.run.run_id  # type: ignore

            # 実行時間を取得
            start_time = metrics.get("start_time")
            end_time = metrics.get("end_time")
            duration_seconds = metrics.get("duration_seconds", 0.0)

            # 使用モデルを取得
            model_call_counts = metrics.get("model_call_counts", {})
            primary_model = "N/A"
            aux_models: list[str] = []

            # details からモデル名を取得（優先）
            if ctx.details:
                model_name = ctx.details.get("model") or ctx.details.get("model_name")
                if model_name:
                    primary_model = str(model_name)

            # model_call_counts からモデルを取得（フォールバック）
            if primary_model == "N/A" and model_call_counts:
                # 呼び出し回数が多い順にソート
                sorted_models = sorted(
                    model_call_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
                if sorted_models:
                    primary_model = sorted_models[0][0]
                    # 2番目以降を aux_models に追加
                    aux_models = [model for model, _ in sorted_models[1:]]

            # 変更規模を取得
            changed_files = metrics.get("patch_files_count", 0)
            added_lines = metrics.get("added_lines", 0)
            removed_lines = metrics.get("removed_lines", 0)

            # CR-E3: メタ情報ブロックを生成
            metadata_block = format_metadata_block(
                run_id=run_id,
                pr_number=ctx.pr_number,
                commit_sha=ctx.commit_sha,
                start_time=start_time,
                end_time=end_time,
                duration_seconds=duration_seconds,
                primary_model=primary_model,
                aux_models=aux_models,
                changed_files=changed_files,
                added_lines=added_lines,
                removed_lines=removed_lines,
                success_rate_last_n=success_rate,
                recent_runs_window=30,
            )
            parts.append(metadata_block)
            parts.append("")  # 空行を追加

        except Exception as e:
            logger.warning(f"Failed to build Self-Healing metadata block: {e}", exc_info=True)

    # === E-5: Self-Healing Summary (カード形式) ===
    if ctx.run is not None and ctx.project is not None:
        try:
            metrics = _collect_run_metrics(ctx.run)

            # プロジェクトIDを取得
            project_id = 0
            if hasattr(ctx.project, "id"):
                project_id = ctx.project.id  # type: ignore

            success_rate = 0.0
            if project_id > 0:
                success_rate = _compute_recent_success_rate(project_id, limit=30)

            # プロジェクト名を取得
            project_name = "Unknown"
            if hasattr(ctx.project, "name"):
                project_name = ctx.project.name  # type: ignore

            # Run ID とステータスを取得
            run_id = "unknown"
            run_status = "UNKNOWN"
            if hasattr(ctx.run, "run_id"):
                run_id = ctx.run.run_id  # type: ignore
            if hasattr(ctx.run, "status"):
                run_status = ctx.run.status  # type: ignore

            # E-5: details から実行メトリクスを取得
            details_for_card = ctx.details

            # E-5: カード形式でレンダリング
            summary_card = render_summary_card(metrics, details_for_card)

            # 追加情報（プロジェクト、Run ID、成功率）
            additional_info = f"""
**Project:** `{project_name}` ({ctx.repo_full_name or '-'})
**Run ID:** `{run_id}` (status: `{run_status}`)
**Recent success rate (last 30 runs):** {success_rate * 100:.1f}%

"""
            parts.append(summary_card)
            parts.append(additional_info)
        except Exception as e:
            logger.warning(f"Failed to build Self-Healing Summary: {e}", exc_info=True)

    # === Guardian Review ===
    parts.append("## 🔍 Guardian Review\n\n")
    parts.append(ctx.guardian_review_markdown or "_(no review content)_\n")

    # === Change Summary (AI 要約) (B-3) ===
    if ctx.change_summary:
        parts.append("\n---\n\n")
        parts.append("## ✨ Change Summary (AI-generated)\n\n")
        parts.append(ctx.change_summary)
        parts.append("\n")

    # === E-4/E-5: AI Diff Summary (Before → After) ===
    if ctx.diff_summary:
        parts.append("\n---\n\n")
        # E-5: 複数ファイル対応（dict の場合は file_summaries として扱う）
        if isinstance(ctx.diff_summary, dict):
            parts.append(format_diff_summary_block(file_summaries=ctx.diff_summary))
        else:
            parts.append(format_diff_summary_block(summary_text=ctx.diff_summary))
        parts.append("\n")

    # === Semantic Diff ===
    if ctx.semantic_diffs:
        parts.append("\n---\n\n")
        parts.append("## 🧠 Semantic Diff\n\n")
        parts.append(format_semantic_diff_block(ctx.semantic_diffs))
        parts.append("\n")

    # === E-3: Run Markdown Report ===
    if ctx.markdown_report:
        parts.append("\n---\n\n")
        parts.append(format_markdown_report_block(ctx.markdown_report))
        parts.append("\n")
    elif ctx.run is not None:
        # run_id から自動的に読み込む
        try:
            if hasattr(ctx.run, "run_id"):
                run_id = ctx.run.run_id  # type: ignore
                markdown_content = load_run_markdown(run_id)
                if markdown_content:
                    parts.append("\n---\n\n")
                    parts.append(format_markdown_report_block(markdown_content))
                    parts.append("\n")
        except Exception as e:
            logger.warning(f"Failed to load run markdown: {e}", exc_info=True)

    # === Observability Links (B-2) ===
    if ctx.project is not None and ctx.run is not None:
        try:
            project_id = 0
            if hasattr(ctx.project, "id"):
                project_id = ctx.project.id  # type: ignore

            if project_id > 0:
                run_logs_url = build_run_logs_url(project_id, ctx.run)
                proj_logs_url = build_project_logs_url(project_id)
                proj_dash_url = build_project_dashboard_url(project_id)

                links_md = f"""---

## 📊 Observability Links

- Run logs: {run_logs_url}
- Project logs: {proj_logs_url}
- Project dashboard: {proj_dash_url}

"""
                parts.append(links_md)
        except Exception as e:
            logger.warning(f"Failed to build Observability Links: {e}", exc_info=True)

    return "\n".join(parts)

