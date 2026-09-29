from flask import Flask
import os

def create_app():
    # Get the absolute path to the project root
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    app = Flask(__name__,
                template_folder=os.path.join(project_root, 'templates'),
                static_folder=os.path.join(project_root, 'static'))
    app.secret_key = "secret123"

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.main import main_bp
    from .routes.recommendations import rec_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(rec_bp)

    # Initialize database
    from .models.database import init_db
    init_db()

    return app