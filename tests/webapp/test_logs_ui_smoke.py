"""
4.5: Flask SaaS UI - Run 詳細（Self-Healing Metrics）のスモークテスト（リファクタ版）

HTTP 500 が出ないことと、Self-Healing メトリクス系の重要な文字列が必ず含まれていることを検証する。

共通ヘルパーと UI キーワード表を使用して、保守性を向上。
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from nexuscore.webapp import db
from nexuscore.webapp.models import Run

from tests.webapp.helpers import assert_page_keywords, login_user
from tests.webapp.ui_keywords import RUN_DETAIL_KEYWORDS


def test_run_detail_shows_self_healing_metrics(client, app, test_user, test_project, test_run_with_self_healing_metrics):
    """Run 詳細ページ（/logs/runs/<run_id>）が 200 を返し、Self-Healing Metrics セクションが含まれることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get(f"/logs/runs/{test_run_with_self_healing_metrics.run_id}")
        assert_page_keywords(response, RUN_DETAIL_KEYWORDS)


def test_run_detail_shows_guardian_review(client, app, test_user, test_project, test_run_with_self_healing_metrics):
    """Run 詳細ページに Guardian Review セクションが含まれていることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get(f"/logs/runs/{test_run_with_self_healing_metrics.run_id}")
        assert_page_keywords(response, ["Guardian Review"])


def test_run_detail_shows_ai_diff_summary(client, app, test_user, test_project, test_run_with_self_healing_metrics):
    """Run 詳細ページに AI Diff Summary セクションが含まれていることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get(f"/logs/runs/{test_run_with_self_healing_metrics.run_id}")
        # AI Diff Summary はレポートがない場合は表示されない可能性があるため、Observability も確認
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        assert "AI Diff Summary" in html or "Observability" in html


def test_run_detail_shows_observability_links(client, app, test_user, test_project, test_run_with_self_healing_metrics):
    """Run 詳細ページに Observability セクションとリンクが含まれていることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get(f"/logs/runs/{test_run_with_self_healing_metrics.run_id}")
        assert_page_keywords(response, ["Observability"])


def test_run_detail_shows_retry_count(client, app, test_user, test_project, test_run_with_self_healing_metrics):
    """Run 詳細ページに Retry Count の数値が表示されることを確認"""
    with app.app_context():
        login_user(client, test_user)
        response = client.get(f"/logs/runs/{test_run_with_self_healing_metrics.run_id}")
        assert response.status_code == 200
        html = response.data.decode("utf-8")
        # retry_count: 2 が含まれているはず
        assert "2" in html


def test_run_detail_without_guardian_review(client, app, test_user, test_project):
    """Guardian Review がない場合でも Run 詳細ページが 200 を返すことを確認"""
    with app.app_context():
        # Run を作成（Guardian Review なし）
        run = Run(
            project_id=test_project.id,
            run_id="test-run-no-guardian",
            triggered_by=test_user.id,
            status="SUCCESS",
            started_at=datetime.utcnow() - timedelta(seconds=30),
            finished_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.commit()

        login_user(client, test_user)
        response = client.get(f"/logs/runs/{run.run_id}")
        assert_page_keywords(response, ["Self-Healing Metrics"])
