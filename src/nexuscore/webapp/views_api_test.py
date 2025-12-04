"""
4.5: External API テスト UI

E-1/E-2 で実装した /api/v1/projects / /api/v1/projects/<id>/run を、
Web UI 上から簡易的に試せるフォームを提供する。
"""

from __future__ import annotations

import json
from flask import Blueprint, request, jsonify, url_for
from typing import Optional

from nexuscore.webapp.models import Project, ApiKey
from nexuscore.webapp.auth import require_auth, get_current_user
from nexuscore.webapp import db

bp = Blueprint("views_api_test", __name__, url_prefix="/api-test")


@bp.route("/", methods=["GET", "POST"])
@require_auth
def api_test():
    """
    API Test ページ
    GET /api-test/ - フォーム表示
    POST /api-test/ - API を実行して結果を表示
    """
    user = get_current_user()

    # 現在ログイン中ユーザーの API Key 一覧を取得
    api_keys = ApiKey.query.filter_by(user_id=user.id).all()
    api_key_options_html = ""
    for ak in api_keys:
        api_key_options_html += f'<option value="{ak.id}">{ak.name} (ID: {ak.id})</option>'

    # プロジェクト一覧を取得
    projects = Project.query.filter_by(owner_id=user.id).all()
    project_options_html = ""
    for p in projects:
        project_options_html += f'<option value="{p.id}">{p.name} (ID: {p.id})</option>'

    error_msg = ""
    result_html = ""

    if request.method == "POST":
        # API を実行
        project_id = request.form.get("project_id", type=int)
        requirement = request.form.get("requirement", "")
        api_key_id = request.form.get("api_key_id", type=int)

        if not project_id or not requirement:
            error_msg = "Project ID and requirement are required."
        else:
            # API を実行（内部的に現在ユーザーの API Key を自動付与）
            try:
                # 注意: api_external は CR-FASTAPI-010 で削除済み（FastAPI に移行済み）
                # 実際の API 呼び出しは FastAPI エンドポイントを使用してください
                result_data = {
                    "status_code": 200,
                    "message": "API call simulated. Use curl or VSCode extension for actual API calls.",
                    "note": "This is a UI test page. For actual API calls, use the FastAPI endpoint (/api/v1/projects/{id}/run) with X-API-Key header.",
                }
                result_html = f"""
                <div style="background-color: #f0f9ff; padding: 16px; border-radius: 8px; margin-top: 16px;">
                    <h3>API Call Result</h3>
                    <pre style="background-color: #ffffff; padding: 12px; border-radius: 4px; overflow-x: auto;">{json.dumps(result_data, indent=2, ensure_ascii=False)}</pre>
                </div>
                """
            except Exception as e:
                error_msg = f"API execution failed: {e}"

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>NexusCore - API Test</title>
        <style>
            body {{
                font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                margin: 0;
                padding: 16px;
                background-color: #f3f4f6;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background-color: #ffffff;
                padding: 24px;
                border-radius: 12px;
                box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
            }}
            h1 {{
                margin-top: 0;
            }}
            .form-group {{
                margin-bottom: 16px;
            }}
            label {{
                display: block;
                margin-bottom: 4px;
                font-weight: 600;
                color: #374151;
            }}
            select, textarea {{
                width: 100%;
                padding: 8px;
                border: 1px solid #d1d5db;
                border-radius: 6px;
                font-size: 0.9rem;
            }}
            textarea {{
                min-height: 100px;
                font-family: monospace;
            }}
            button {{
                background-color: #2563eb;
                color: #ffffff;
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 0.9rem;
                font-weight: 600;
                cursor: pointer;
            }}
            button:hover {{
                background-color: #1d4ed8;
            }}
            .error {{
                background-color: #fee2e2;
                color: #991b1b;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 16px;
            }}
            pre {{
                background-color: #f9fafb;
                padding: 12px;
                border-radius: 4px;
                overflow-x: auto;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>API Test</h1>
            <p>Logged in as: {user.github_login}</p>
            <p>Test the external API endpoints from this UI.</p>
            <hr>

            {f'<div class="error">{error_msg}</div>' if error_msg else ''}

            <form method="POST">
                <div class="form-group">
                    <label for="project_id">Project ID:</label>
                    <select name="project_id" id="project_id" required>
                        <option value="">Select a project</option>
                        {project_options_html}
                    </select>
                </div>

                <div class="form-group">
                    <label for="api_key_id">API Key (Optional):</label>
                    <select name="api_key_id" id="api_key_id">
                        <option value="">None (use session auth)</option>
                        {api_key_options_html}
                    </select>
                </div>

                <div class="form-group">
                    <label for="requirement">Requirement:</label>
                    <textarea name="requirement" id="requirement" required placeholder="例: Run self-healing for this repo"></textarea>
                </div>

                <button type="submit">Execute API Call</button>
            </form>

            {result_html}

            <hr>
            <p>
                <strong>Note:</strong> This is a UI test page. For actual API calls from external clients,
                use the API endpoint with X-Api-Key header:
            </p>
            <pre>curl -X POST "http://localhost:5000/api/v1/projects/&lt;project_id&gt;/run" \\
  -H "X-Api-Key: your-api-key" \\
  -H "Content-Type: application/json" \\
  -d '{{"requirement": "..."}}'</pre>

            <p>
                <a href="/projects/">Back to Projects</a>
            </p>
        </div>
    </body>
    </html>
    """
    return html

