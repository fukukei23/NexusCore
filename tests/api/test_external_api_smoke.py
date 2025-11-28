"""
API スモークテスト

外部統合 API（/api/v1/*）の HTTP ステータスと最低限の JSON キーを検証する軽量テスト。

UI スモークテストと同様、「壊れていないこと」を保証する用途に留める。
"""

from __future__ import annotations

import json
import pytest

from tests.api.helpers_api import assert_json_keys


def test_get_projects_requires_api_key(client, app):
    """API キーなしでプロジェクト一覧を取得すると 401 が返る"""
    resp = client.get("/api/v1/projects")
    assert resp.status_code in (401, 403)


def test_get_projects_with_api_key(client, app, test_user, test_project, test_api_key):
    """有効な API キーでプロジェクト一覧を取得できる"""
    with app.app_context():
        raw_token, _ = test_api_key
        headers = {"X-Api-Key": raw_token}
        resp = client.get("/api/v1/projects", headers=headers)

        assert resp.status_code == 200

        data = resp.get_json()
        assert "projects" in data
        assert isinstance(data["projects"], list)

        if data["projects"]:
            project = data["projects"][0]
            assert_json_keys(project, ["id", "name"])


def test_post_run_requires_api_key(client, app, test_project):
    """API キーなしで Run を実行すると 401 が返る"""
    url = f"/api/v1/projects/{test_project.id}/run"
    resp = client.post(url, json={"requirement": "Test run"})
    assert resp.status_code in (401, 403)


def test_post_run_with_api_key(client, app, test_user, test_project, test_api_key):
    """有効な API キーで Run を実行できる"""
    with app.app_context():
        raw_token, _ = test_api_key
        url = f"/api/v1/projects/{test_project.id}/run"
        headers = {"X-Api-Key": raw_token}
        payload = {
            "requirement": "Smoke test self-healing run",
            "autonomy_level": 1,
            "fast_lane": True,
        }

        resp = client.post(url, headers=headers, json=payload)

        # 非同期 = 202 / 同期 = 200 を許容
        assert resp.status_code in (200, 202)

        data = resp.get_json()
        assert_json_keys(data, ["run_id", "project_id", "status"])


def test_get_latest_run_requires_api_key(client, app, test_project):
    """API キーなしで最新 Run を取得すると 401 が返る"""
    url = f"/api/v1/projects/{test_project.id}/runs/latest"
    resp = client.get(url)
    assert resp.status_code in (401, 403)


def test_get_latest_run_with_api_key(client, app, test_user, test_project, test_api_key, test_run_with_metrics):
    """有効な API キーで最新 Run を取得できる"""
    with app.app_context():
        raw_token, _ = test_api_key
        url = f"/api/v1/projects/{test_project.id}/runs/latest"
        headers = {"X-Api-Key": raw_token}

        resp = client.get(url, headers=headers)

        assert resp.status_code == 200

        data = resp.get_json()
        # {"run": {...}} 形式を想定
        assert "run" in data

        if data["run"] is not None:
            run_obj = data["run"]
            assert_json_keys(run_obj, ["id", "run_id", "status"])


def test_get_latest_run_without_runs(client, app, test_user, test_project, test_api_key):
    """Run がない場合でも最新 Run 取得が 200 を返す"""
    with app.app_context():
        raw_token, _ = test_api_key
        url = f"/api/v1/projects/{test_project.id}/runs/latest"
        headers = {"X-Api-Key": raw_token}

        resp = client.get(url, headers=headers)

        assert resp.status_code == 200

        data = resp.get_json()
        assert "run" in data
        # Run がない場合は null を許容
        assert data["run"] is None or isinstance(data["run"], dict)

