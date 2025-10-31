# フォルダ: app
# ファイル名: __init__.py
# メモ: FlaskのSECRET_KEYをハードコーディングから環境変数読み込みに変更し、セキュリティを向上させました。
#      他の設定値も併せて環境変数から読み込めるように改良しています。

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
# これにより、.envファイルに記述した設定がos.getenv()で利用可能になります。
load_dotenv()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # --- 基本設定 ---
    # ◀️ ハードコーディングされた秘密鍵を環境変数から読み込むように修正
    #    os.getenvの第2引数は、環境変数が設定されていない場合のデフォルト値です。
    #    本番環境では必ず強固なキーを環境変数に設定してください。
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "a-very-secret-key-for-development-only")
    
    # データベースのURIも環境変数から取得するように変更
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URI", "sqlite:///db.sqlite3")

    # --- Celery 用設定 ---
    # Celeryの接続情報も環境変数から取得するように変更
    app.config.from_mapping(
        CELERY=dict(
            broker_url=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
            result_backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
            task_ignore_result=True,
        )
    )

    # --- 拡張機能の初期化 ---
    db.init_app(app)

    # Blueprint の登録（ここで１回だけ）
    from .routes import bp as main_bp
    app.register_blueprint(main_bp)

    # Celery を紐付け
    from .extensions import celery_init_app
    celery_init_app(app)

    return app
