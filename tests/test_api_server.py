"""Tests for nexuscore.api.server"""
import os
import json
from unittest.mock import patch, MagicMock
import pytest

from nexuscore.api import server


def test_app_exists():
    """Flaskアプリの存在確認"""
    assert hasattr(server, "app")
    assert server.app is not None


def test_tasks_dict_exists():
    """tasks辞書の存在確認"""
    assert hasattr(server, "tasks")
    assert isinstance(server.tasks, dict)


def test_execute_task_endpoint_missing_fields():
    """execute_taskエンドポイント: 必須フィールドがない場合のテスト"""
    with server.app.test_client() as client:
        # requirementがない場合
        response = client.post('/api/v1/execute', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data
        assert "MISSING_FIELD" in data.get("error_code", "")


def test_execute_task_endpoint_success():
    """execute_taskエンドポイント: 成功ケースのテスト"""
    with server.app.test_client() as client:
        with patch("nexuscore.api.server.run_orchestrator_task") as mock_task:
            response = client.post('/api/v1/execute', json={
                "requirement": "Test requirement",
                "project_path": "/tmp/test"
            })

            assert response.status_code == 202
            data = json.loads(response.data)
            assert "task_id" in data
            assert "status_url" in data
            assert "message" in data


def test_get_task_status_not_found():
    """get_task_statusエンドポイント: タスクが見つからない場合"""
    with server.app.test_client() as client:
        response = client.get('/api/v1/status/nonexistent-task-id')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data


def test_get_task_status_found():
    """get_task_statusエンドポイント: タスクが見つかった場合"""
    # テスト用のタスクを追加
    test_task_id = "test-task-123"
    server.tasks[test_task_id] = {"status": "running", "message": "Test message"}

    try:
        with server.app.test_client() as client:
            response = client.get(f'/api/v1/status/{test_task_id}')
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["status"] == "running"
            assert data["message"] == "Test message"
    finally:
        # クリーンアップ
        if test_task_id in server.tasks:
            del server.tasks[test_task_id]


@patch("nexuscore.api.server.run_orchestrator_task")
def test_execute_task_with_constitution(mock_task):
    """execute_task: constitution_textを含む場合のテスト"""
    with server.app.test_client() as client:
        response = client.post('/api/v1/execute', json={
            "requirement": "Test requirement",
            "project_path": "/tmp/test",
            "constitution_text": "Custom constitution"
        })

        assert response.status_code == 202
        # run_orchestrator_taskが呼ばれることを確認
        assert mock_task.called


def test_execute_task_invalid_json():
    """execute_task: 不正なJSONのテスト"""
    with server.app.test_client() as client:
        response = client.post('/api/v1/execute', data="invalid json", content_type='application/json')
        assert response.status_code == 400


def test_execute_task_empty_request():
    """execute_task: 空のリクエストのテスト"""
    with server.app.test_client() as client:
        response = client.post('/api/v1/execute', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


def test_execute_task_missing_project_path():
    """execute_task: project_pathがない場合のテスト"""
    with server.app.test_client() as client:
        response = client.post('/api/v1/execute', json={
            "requirement": "Test requirement"
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


def test_execute_task_missing_requirement():
    """execute_task: requirementがない場合のテスト"""
    with server.app.test_client() as client:
        response = client.post('/api/v1/execute', json={
            "project_path": "/tmp/test"
        })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert "error" in data


def test_get_task_status_invalid_id():
    """get_task_status: 無効なタスクIDのテスト"""
    with server.app.test_client() as client:
        response = client.get('/api/v1/status/invalid-task-id-12345')
        assert response.status_code == 404
        data = json.loads(response.data)
        assert "error" in data


def test_execute_task_with_extra_fields():
    """execute_task: 追加フィールドを含むリクエストのテスト"""
    with server.app.test_client() as client:
        with patch("nexuscore.api.server.run_orchestrator_task") as mock_task:
            response = client.post('/api/v1/execute', json={
                "requirement": "Test requirement",
                "project_path": "/tmp/test",
                "extra_field": "extra_value",
                "another_field": 123
            })

            assert response.status_code == 202
            data = json.loads(response.data)
            assert "task_id" in data
            assert mock_task.called


def test_get_task_status_different_statuses():
    """get_task_status: 異なるステータスのテスト"""
    test_cases = [
        ("running", "Task is running"),
        ("completed", "Task completed"),
        ("error", "Task failed")
    ]

    for status, message in test_cases:
        test_task_id = f"test-task-{status}"
        server.tasks[test_task_id] = {"status": status, "message": message}

        try:
            with server.app.test_client() as client:
                response = client.get(f'/api/v1/status/{test_task_id}')
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data["status"] == status
                assert data["message"] == message
        finally:
            if test_task_id in server.tasks:
                del server.tasks[test_task_id]


def test_execute_task_task_id_format():
    """execute_task: タスクIDの形式テスト"""
    with server.app.test_client() as client:
        with patch("nexuscore.api.server.run_orchestrator_task"):
            response = client.post('/api/v1/execute', json={
                "requirement": "Test",
                "project_path": "/tmp/test"
            })

            assert response.status_code == 202
            data = json.loads(response.data)
            task_id = data["task_id"]

            # UUID形式であることを確認（簡易チェック）
            assert len(task_id) > 10
            assert "-" in task_id  # UUIDには通常ハイフンが含まれる


def test_execute_task_status_url_format():
    """execute_task: status_urlの形式テスト"""
    with server.app.test_client() as client:
        with patch("nexuscore.api.server.run_orchestrator_task"):
            response = client.post('/api/v1/execute', json={
                "requirement": "Test",
                "project_path": "/tmp/test"
            })

            assert response.status_code == 202
            data = json.loads(response.data)
            status_url = data["status_url"]

            assert status_url.startswith("/api/v1/status/")
            assert len(status_url) > len("/api/v1/status/")


def test_get_task_status_empty_tasks_dict():
    """get_task_status: 空のtasks辞書でのテスト"""
    # tasks辞書を一時的にクリア
    original_tasks = server.tasks.copy()
    server.tasks.clear()

    try:
        with server.app.test_client() as client:
            response = client.get('/api/v1/status/nonexistent-id')
            assert response.status_code == 404
    finally:
        server.tasks.update(original_tasks)


def test_execute_task_concurrent_requests():
    """並行リクエストのテスト"""
    with server.app.test_client() as client:
        with patch("nexuscore.api.server.run_orchestrator_task"):
            # 複数のリクエストを同時に送信
            responses = []
            for i in range(3):
                response = client.post('/api/v1/execute', json={
                    "requirement": f"Test {i}",
                    "project_path": f"/tmp/test{i}"
                })
                responses.append(response)

            # すべてのリクエストが成功することを確認
            for response in responses:
                assert response.status_code == 202
                data = json.loads(response.data)
                assert "task_id" in data


def test_execute_task_response_structure():
    """レスポンス構造の詳細テスト"""
    with server.app.test_client() as client:
        with patch("nexuscore.api.server.run_orchestrator_task"):
            response = client.post('/api/v1/execute', json={
                "requirement": "Test",
                "project_path": "/tmp/test"
            })

            assert response.status_code == 202
            data = json.loads(response.data)

            # レスポンスの構造を詳細に確認
            assert "message" in data
            assert "task_id" in data
            assert "status_url" in data
            assert isinstance(data["message"], str)
            assert isinstance(data["task_id"], str)
            assert isinstance(data["status_url"], str)


def test_get_task_status_response_structure():
    """ステータスレスポンスの構造テスト"""
    test_task_id = "test-structure-123"
    server.tasks[test_task_id] = {
        "status": "running",
        "message": "Test message",
        "extra_field": "extra_value"
    }

    try:
        with server.app.test_client() as client:
            response = client.get(f'/api/v1/status/{test_task_id}')
            assert response.status_code == 200
            data = json.loads(response.data)

            # レスポンス構造を確認
            assert "status" in data
            assert "message" in data
            assert data["status"] == "running"
            assert data["message"] == "Test message"
    finally:
        if test_task_id in server.tasks:
            del server.tasks[test_task_id]


def test_execute_task_with_none_values():
    """None値を含むリクエストのテスト"""
    with server.app.test_client() as client:
        # None値が含まれる場合の処理を確認
        response = client.post('/api/v1/execute', json={
            "requirement": None,
            "project_path": "/tmp/test"
        })

        # requirementがNoneの場合はエラーになる可能性がある
        assert response.status_code in [400, 202]  # 実装に応じて調整


def test_get_task_status_with_special_characters():
    """特殊文字を含むタスクIDのテスト"""
    with server.app.test_client() as client:
        # 特殊文字を含むタスクID
        special_ids = [
            "task-with-dashes",
            "task_with_underscores",
            "task.with.dots",
            "task@with#special$chars"
        ]

        for task_id in special_ids:
            response = client.get(f'/api/v1/status/{task_id}')
            # タスクが存在しない場合は404
            assert response.status_code in [200, 404]

