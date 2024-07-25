from flask import Flask
from config import Config
from .extensions import db 


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    
    with app.app_context():
        from .models import User, Token, RefreshToken
        db.create_all()

    # Import and register the Blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
