from app import create_app
from app.extensions import celery_init_app

flask_app = create_app()
celery = celery_init_app(flask_app)     # celery インスタンス

# 例：タスク定義
@celery.task
def ping():
    print("pong")
