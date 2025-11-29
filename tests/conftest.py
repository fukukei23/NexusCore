"""
Pytest 共通フィクスチャ

Flask SaaS UI のスモークテストで使用する共通フィクスチャを集約。
テスト結果自動保存機能も含む。
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
from typing import List, Dict, Any

# webapp 関連のインポートは条件付き（Gradio/analyzer テストでは不要）
try:
    from nexuscore.webapp import create_app, db
    from nexuscore.webapp.models import Project, Run, User, ExecutionLog, PatchRecord, ApiKey
    HAS_WEBAPP = True
except ImportError:
    HAS_WEBAPP = False
    create_app = None  # type: ignore
    db = None  # type: ignore
    Project = None  # type: ignore
    Run = None  # type: ignore
    User = None  # type: ignore
    ExecutionLog = None  # type: ignore
    PatchRecord = None  # type: ignore
    ApiKey = None  # type: ignore


@pytest.fixture
def app():
    """テスト用 Flask アプリ"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    app = create_app(config_overrides={
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
    })
    return app


@pytest.fixture
def client(app):
    """テスト用クライアント"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()


@pytest.fixture
def test_user(app):
    """テスト用ユーザー"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        user = User(
            github_id="123",
            github_login="test_user",
        )
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def test_project(app, test_user):
    """テスト用プロジェクト"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        project = Project(
            owner_id=test_user.id,
            name="Test Project",
            repo_url="https://github.com/example/repo",
            local_path="/tmp/test",
        )
        db.session.add(project)
        db.session.commit()
        return project


@pytest.fixture
def test_run_with_metrics(app, test_project, test_user):
    """テスト用 Run（メトリクス付き）"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        run = Run(
            project_id=test_project.id,
            run_id="test-run-123",
            triggered_by=test_user.id,
            status="SUCCESS",
            started_at=datetime.utcnow() - timedelta(seconds=30),
            finished_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.flush()

        # ExecutionLog に retry_count と last_error_class を含める
        log1 = ExecutionLog(
            run_id=run.id,
            source="NPE",
            level="INFO",
            message="Test log",
            payload_json=json.dumps({
                "model": "gpt-4.1",
                "retry_count": 2,
                "last_error_class": "rate_limit",
            }),
        )
        db.session.add(log1)

        log2 = ExecutionLog(
            run_id=run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Test log 2",
            payload_json=json.dumps({
                "execution_ms": 1234,
                "files_changed": 3,
            }),
        )
        db.session.add(log2)

        db.session.commit()
        return run


@pytest.fixture
def test_run_with_self_healing_metrics(app, test_project, test_user):
    """
    テスト用 Run（Self-Healing メトリクス付き）
    ExecutionLog に retry_count, last_error_class, model を含める
    """
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        run = Run(
            project_id=test_project.id,
            run_id="test-run-sh-123",
            triggered_by=test_user.id,
            status="SUCCESS",
            started_at=datetime.utcnow() - timedelta(seconds=30),
            finished_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.flush()

        # ExecutionLog に Self-Healing メトリクスを含める
        log1 = ExecutionLog(
            run_id=run.id,
            source="NPE",
            level="INFO",
            message="LLM call",
            payload_json=json.dumps({
                "model": "gpt-4.1",
                "retry_count": 2,
                "last_error_class": "rate_limit",
                "estimated_cost": 10.0,
            }),
        )
        db.session.add(log1)

        log2 = ExecutionLog(
            run_id=run.id,
            source="ORCHESTRATOR",
            level="INFO",
            message="Guardian review",
            payload_json=json.dumps({
                "guardian_review": {
                    "decision": "approved",
                    "reason": "Patch looks safe",
                },
            }),
        )
        db.session.add(log2)

        # PatchRecord を作成（files_changed を計算するため）
        patch1 = PatchRecord(
            run_id=run.id,
            file_path="src/test1.py",
            diff_text="--- a/src/test1.py\n+++ b/src/test1.py\n@@ -1,1 +1,2 @@\n+new line",
            applied=True,
        )
        db.session.add(patch1)

        patch2 = PatchRecord(
            run_id=run.id,
            file_path="src/test2.py",
            diff_text="--- a/src/test2.py\n+++ b/src/test2.py\n@@ -1,1 +1,2 @@\n+new line",
            applied=True,
        )
        db.session.add(patch2)

        db.session.commit()
        return run


@pytest.fixture
def test_api_key(app, test_user):
    """テスト用 API Key"""
    if not HAS_WEBAPP:
        pytest.skip("webapp modules not available")
    with app.app_context():
        raw_token = ApiKey.generate_token()
        token_hash = ApiKey.hash_token(raw_token)

        api_key = ApiKey(
            user_id=test_user.id,
            token_hash=token_hash,
            name="Test API Key",
        )
        db.session.add(api_key)
        db.session.commit()
        return raw_token, api_key


# ==============================================================================
# テスト結果自動保存機能
# ==============================================================================

# テスト結果を保存するためのグローバル変数
_test_results: List[Dict[str, Any]] = []
_result_file_path: Path | None = None


def pytest_configure(config):
    """
    テスト開始時に結果ファイルのパスを設定
    """
    global _result_file_path

    # プロジェクトルートを取得
    project_root = Path(__file__).resolve().parents[1]

    # docs/reports/ ディレクトリを作成
    reports_dir = project_root / "docs" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    # タイムスタンプ付きファイル名を生成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _result_file_path = reports_dir / f"TEST_RESULTS_{timestamp}.txt"


def pytest_runtest_logreport(report):
    """
    各テストの結果を収集
    """
    global _test_results

    # テスト実行時のみ記録（setup, call, teardown のうち call のみ）
    if report.when == "call":
        test_result = {
            "nodeid": report.nodeid,
            "outcome": report.outcome,  # "passed", "failed", "skipped"
            "duration": getattr(report, "duration", 0.0),
            "longrepr": str(report.longrepr) if hasattr(report, "longrepr") and report.longrepr else None,
        }
        _test_results.append(test_result)


def pytest_collectreport(report):
    """
    テスト収集時のエラーも記録
    """
    global _test_results

    # 収集エラーを記録
    if report.failed:
        test_result = {
            "nodeid": report.nodeid or "collection",
            "outcome": "error",
            "duration": 0.0,
            "longrepr": str(report.longrepr) if hasattr(report, "longrepr") and report.longrepr else None,
        }
        _test_results.append(test_result)


def pytest_collectreport(report):
    """
    テスト収集時のエラーも記録
    """
    global _test_results

    # 収集エラーを記録
    if report.failed:
        test_result = {
            "nodeid": report.nodeid or "collection",
            "outcome": "error",
            "duration": 0.0,
            "longrepr": str(report.longrepr) if hasattr(report, "longrepr") and report.longrepr else None,
        }
        _test_results.append(test_result)


def pytest_sessionfinish(session, exitstatus):
    """
    テスト終了時に結果ファイルに書き込み
    """
    global _test_results, _result_file_path

    if _result_file_path is None:
        return

    try:
        # テスト結果をテキスト形式で整形
        lines: List[str] = []
        lines.append("=" * 80)
        lines.append("NexusCore Test Results")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 80)
        lines.append("")

        # 統計情報
        total = len(_test_results)
        passed = sum(1 for r in _test_results if r["outcome"] == "passed")
        failed = sum(1 for r in _test_results if r["outcome"] == "failed")
        skipped = sum(1 for r in _test_results if r["outcome"] == "skipped")
        error = sum(1 for r in _test_results if r["outcome"] == "error")

        lines.append(f"Total tests: {total}")
        lines.append(f"Passed: {passed}")
        lines.append(f"Failed: {failed}")
        lines.append(f"Skipped: {skipped}")
        if error > 0:
            lines.append(f"Error: {error}")
        lines.append("")
        lines.append("=" * 80)
        lines.append("")

        # 各テストの詳細
        for result in _test_results:
            outcome_emoji = {
                "passed": "✅",
                "failed": "❌",
                "skipped": "⏭️",
                "error": "⚠️",
            }.get(result["outcome"], "❓")

            lines.append(f"{outcome_emoji} {result['nodeid']} ({result['outcome']})")
            if result["duration"]:
                lines.append(f"   Duration: {result['duration']:.3f}s")

            # 失敗したテストの詳細
            if result["outcome"] == "failed" and result["longrepr"]:
                lines.append("   Error details:")
                for line in result["longrepr"].split("\n"):
                    lines.append(f"   {line}")

            lines.append("")

        # ファイルに書き込み
        _result_file_path.write_text("\n".join(lines), encoding="utf-8")

        # ターミナルにメッセージを表示（1回のみ）
        import sys
        message = f"\n✅ テスト結果を保存しました: {_result_file_path}\n"
        # stderr に出力（pytest の出力と混ざらないように）
        sys.stderr.write(message)
        sys.stderr.flush()

    except Exception as e:
        import sys
        error_message = f"⚠️ テスト結果の保存に失敗しました: {e}\n"
        sys.stderr.write(error_message)
        sys.stderr.flush()

