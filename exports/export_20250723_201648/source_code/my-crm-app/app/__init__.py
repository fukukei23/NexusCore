# TODO: Initialize Flask app and configure database

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///customers.db'
    db.init_app(app)
    
    # TODO: Register blueprints
    
    return app
