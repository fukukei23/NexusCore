from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from flask import Flask, flash, redirect, render_template_string, url_for

if TYPE_CHECKING:
    from .constitutional_council_agent import ConstitutionalCouncilAgent

logger = logging.getLogger(__name__)

TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>憲法改正案管理 (Constitutional Amendment)</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js" defer></script>
<style>
  body { background-color: #f8f9fa; }
  .card-header { background-color: #e9ecef; }
  pre {
    white-space: pre-wrap;
    word-break: break-all;
    background-color: #fff;
    border: 1px solid #dee2e6;
    border-radius: 0.25rem;
  }
</style>
</head>
<body class="bg-light">
<div class="container py-4">
{% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
    {% for category, message in messages %}
      <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    {% endfor %}
  {% endif %}
{% endwith %}
<h1 class="mb-4">憲法改正案 管理画面</h1>
<h2 class="h5 mb-3 text-muted">Pending Amendments</h2>
{% if files %}
<div class="row">
{% for fname, content in files %}
  <div class="col-lg-6">
    <div class="card mb-4 shadow-sm">
      <div class="card-header"><strong>{{ fname }}</strong></div>
      <div class="card-body">
        <pre class="small p-3">{{ content }}</pre>
        <div class="d-flex justify-content-end gap-2 mt-3">
          <a class="btn btn-success" onclick="return confirm('本当に承認しますか？\\nApprove this amendment?')" href="{{ url_for('approve', filename=fname) }}">承認 (Approve)</a>
          <a class="btn btn-danger"  onclick="return confirm('本当に却下しますか？\\nReject this amendment?')"   href="{{ url_for('reject', filename=fname) }}">却下 (Reject)</a>
        </div>
      </div>
    </div>
  </div>
{% endfor %}
</div>
{% else %}
  <div class="alert alert-info shadow-sm">保留中の改正案はありません。(No pending amendments.)</div>
{% endif %}
</div>
</body></html>"""


def _is_safe_filename(filename: str) -> bool:
    if not filename:
        return False
    if ".." in filename or "/" in filename or "\\" in filename or filename.startswith("/"):
        return False
    if not (filename.startswith("pending_") and filename.endswith(".json")):
        logger.warning("[WEB-UI] Filename format mismatch: %s", filename)
        return False
    core = filename[len("pending_") : -len(".json")]
    if not core:
        logger.warning("[WEB-UI] Filename has empty core: %s", filename)
        return False
    if re.search(r"[^\w\-]", core):
        logger.warning("[WEB-UI] Filename core contains invalid characters: %s", filename)
        return False
    return True


def run_web_ui(agent: ConstitutionalCouncilAgent, host: str = "127.0.0.1", port: int = 5000) -> None:
    app = Flask(__name__)
    secret = os.getenv("FLASK_SECRET_KEY")
    if not secret:
        if os.getenv("ENV") == "production":
            raise RuntimeError("FLASK_SECRET_KEY must be set in production")
        logger.warning("FLASK_SECRET_KEY not set — using insecure dev-only fallback")
        secret = "dev_only_secret_key_DO_NOT_USE_IN_PRODUCTION"
    app.secret_key = secret

    @app.route("/")
    def index():
        files_data = []
        try:
            pending_files = sorted(
                agent.amendments_dir.glob("pending_*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )
        except Exception as e:
            logger.error("[WEB-UI] Error reading amendments directory: %s", e)
            flash(f"改正案ディレクトリの読み込みに失敗しました: {e}", "danger")
            pending_files = []

        for f in pending_files:
            try:
                with f.open("r", encoding="utf-8") as fp:
                    content = json.dumps(json.load(fp), ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error("[WEB-UI] Error reading file %s: %s", f, e)
                content = f"読み込みエラー (Error reading file: {e})"
            files_data.append((f.name, content))
        return render_template_string(TEMPLATE, files=files_data)

    @app.route("/approve/<path:filename>")
    def approve(filename: str):
        if not _is_safe_filename(filename):
            logger.warning("[WEB-UI] Invalid path/filename detected in approve: %s", filename)
            flash(f"無効なファイル名です: {filename}", "danger")
            return redirect(url_for("index"))
        try:
            file_path = agent.amendments_dir.joinpath(filename).resolve()
            if file_path.parent != agent.amendments_dir.resolve():
                logger.error("[WEB-UI] Resolved path mismatch: %s", file_path)
                flash("セキュリティ違反が検出されました。", "danger")
                return redirect(url_for("index"))

            ok = agent.approve_amendment(file_path)
            if ok:
                flash(f"改正案 '{filename}' は正常に承認されました。", "success")
            else:
                if (agent.amendments_dir / filename).exists():
                    flash(
                        f"改正案 '{filename}' のアーカイブに失敗しました。ポリシーは更新済みの可能性があります。手動確認を。",
                        "danger",
                    )
                else:
                    flash(
                        f"改正案 '{filename}' の承認に失敗しました。ログを確認してください。",
                        "danger",
                    )
        except Exception as e:
            logger.error("[WEB-UI] Error during approval of %s: %s", filename, e)
            flash(f"承認処理中に予期せぬエラー: {e}", "danger")
        return redirect(url_for("index"))

    @app.route("/reject/<path:filename>")
    def reject(filename: str):
        if not _is_safe_filename(filename):
            logger.warning("[WEB-UI] Invalid path/filename detected in reject: %s", filename)
            flash(f"無効なファイル名です: {filename}", "danger")
            return redirect(url_for("index"))
        try:
            file_path = agent.amendments_dir.joinpath(filename).resolve()
            if file_path.parent != agent.amendments_dir.resolve():
                logger.error("[WEB-UI] Resolved path mismatch: %s", file_path)
                flash("セキュリティ違反が検出されました。", "danger")
                return redirect(url_for("index"))

            if agent.reject_amendment(file_path):
                flash(f"改正案 '{filename}' は正常に却下されました。", "info")
            else:
                flash(
                    f"改正案 '{filename}' の却下（アーカイブ）に失敗しました。ログを確認してください。",
                    "danger",
                )
        except Exception as e:
            logger.error("[WEB-UI] Error during rejection of %s: %s", filename, e)
            flash(f"却下処理中に予期せぬエラー: {e}", "danger")
        return redirect(url_for("index"))

    logger.info("[Council] Starting Web UI at http://%s:%d", host, port)
    app.run(host=host, port=port)
