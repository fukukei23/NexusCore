# ファイル: src/nexuscore/config/config.py

class AppConfig:
    """
    アプリ全体の静的な構成（秘密鍵除く）を管理
    """
    FLASK_SECRET_KEY = "a-very-secret-key-for-dev"
    DATABASE_URI = "sqlite:///db.sqlite3"
    CELERY_BROKER_URL = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
