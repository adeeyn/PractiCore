from flask import Flask

from .cli import register_commands
from .config import Config
from .routes import ALL_BLUEPRINTS
from .services import ResumeParser


def create_app(config_class=Config):
    """Application factory: builds and wires up the Flask app."""
    app = Flask(
        __name__,
        template_folder=config_class.TEMPLATE_FOLDER,
        static_folder=config_class.STATIC_FOLDER,
    )
    app.config.from_object(config_class)

    # Load SpaCy model once at application startup
    app.extensions["resume_parser"] = ResumeParser()

    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)

    register_commands(app)

    return app
