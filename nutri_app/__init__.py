"""
Application initialization functions and logging configuration.
"""
import os
import logging
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv
from flask import Flask
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from werkzeug.exceptions import HTTPException

# Load environment variables from .env file
load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
mail = Mail()
login_manager = LoginManager()
csrf = CSRFProtect()



def configure_logging(app):
    """
    Configure logging for the Flask application.
    Args:
        app (Flask): The Flask application instance.
    """
    # Set up logging to a file
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = RotatingFileHandler(
        f"{log_dir}/app.log", maxBytes=1_000_000, backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Clear existing handlers if running in debug/reload mode
    if app.logger.hasHandlers():
        app.logger.handlers.clear()

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)

    # Log unhandled exceptions
    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return e
        
        app.logger.exception("Unhandled Exception: %s", e)
        return "An internal error occurred.", 500


def register_blueprints(app):
    """
    Register all blueprints for the Flask application.
    Args:
        app (Flask): The Flask application instance.
    """
    from nutri_app.routes.auth import bp as auth_bp
    from nutri_app.routes.recipes import bp as recipes_bp
    from nutri_app.routes.menus import bp as menus_bp
    from nutri_app.routes.account import bp as profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(recipes_bp)
    app.register_blueprint(menus_bp)
    app.register_blueprint(profile_bp)

def create_app():
    """
    Create and configure the Flask application.
    Returns:
        Flask app: The configured Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration from environment variables
    config_name = os.getenv("FLASK_CONFIG", "config.DevelopmentConfig")
    app.config.from_object(config_name)
    print(app.config)
    app.logger.info(f"Starting app in {config_name} mode.")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)
    from nutri_app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    configure_logging(app)
    register_blueprints(app)

    return app