from celery import Celery, Task

def celery_init_app(app):
    class ContextTask(Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery = Celery(app.import_name)
    celery.config_from_object(app.config["CELERY"])
    celery.Task = ContextTask
    app.celery = celery            # ← 外部から参照できるよう保持
    return celery
