"""
NexusCore SaaS基盤 - Flaskアプリファクトリ

既存の Orchestrator / NPE / Agents アーキテクチャを壊さずに、
Web UI と API を提供するための Flask アプリケーション。

既存の CLI 実行 (python orchestrator.py ...) は独立して動作し続ける。
"""
from __future__ import annotations

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from nexuscore.config.config import AppConfig

# グローバルなDBインスタンス（models.pyで使用）
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_overrides: dict | None = None) -> Flask:
    """
    Flaskアプリケーションのファクトリ関数。

    Args:
        config_overrides: 設定の上書き（テスト用など）

    Returns:
        初期化済みのFlaskアプリケーション
    """
    app = Flask(__name__)

    # 基本設定（AppConfigから読み込み）
    app.config["SECRET_KEY"] = AppConfig.FLASK_SECRET_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = AppConfig.DATABASE_URI
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # 設定の上書き（テスト用など）
    if config_overrides:
        app.config.update(config_overrides)

    # DB初期化
    db.init_app(app)
    migrate.init_app(app, db)

    # OAuth初期化
    from nexuscore.webapp import auth
    auth.init_oauth(app)

    # Celery 初期化（Flask アプリコンテキストで Celery を初期化）
    from nexuscore.webapp.celery_app import make_celery
    celery_instance = make_celery(app)  # Flask アプリと Celery を連携（タスクも自動登録される）

    # Blueprint登録
    from nexuscore.webapp import views_projects, views_logs, views_dashboard, api_badges, api_external, views_api_test

    app.register_blueprint(auth.bp)
    app.register_blueprint(views_projects.bp)
    app.register_blueprint(views_logs.bp)
    app.register_blueprint(views_dashboard.bp)
    app.register_blueprint(api_badges.bp)
    app.register_blueprint(api_external.external_api_bp)
    app.register_blueprint(views_api_test.bp)  # 4.5: API Test UI

    # CORS 対応（外部統合 API 用）
    try:
        from flask_cors import CORS
        # /api/v1/* に対して CORS を許可（開発フェーズでは "*"、本番はホスト制限を推奨）
        CORS(app, resources={r"/api/v1/*": {"origins": "*"}})
    except ImportError:
        # flask-cors がインストールされていない場合はスキップ
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            "flask-cors is not installed. CORS support for /api/v1/* is disabled. "
            "Install with: pip install flask-cors"
        )

    # ロギングプロバイダーの登録（Core層へのDB拡張ロガーの注入）
    from nexuscore.webapp.logging_provider import WebappLoggingProvider
    from nexuscore.core.logging_interface import register_logging_provider

    register_logging_provider(WebappLoggingProvider())
    # これにより、Core/NPE層がWebapp層に直接依存せずにDB logging機能を利用可能になる

    # ルートページ（リダイレクト）
    @app.route("/")
    def index():
        from flask import redirect, url_for
        return redirect(url_for("views_projects.list_projects"))

    return app

