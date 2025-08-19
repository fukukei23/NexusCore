from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')
    
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    from app.routes.image_crawler_route import bp as image_crawler_bp
    app.register_blueprint(image_crawler_bp)
    
    return app
