from flask import Flask
from app.routes import main_blueprint
from app.redis_client import init_redis

def create_app():
    app = Flask(__name__)
    init_redis()
    app.register_blueprint(main_blueprint)
    return app
