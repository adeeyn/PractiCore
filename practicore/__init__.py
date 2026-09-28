from flask import Flask, request

from .cli import register_commands
from .config import Config
from .routes import ALL_BLUEPRINTS
from .services import MatchingService, ResumeParser


def create_app(config_class=Config):
    """Application factory: builds and wires up the Flask app."""
    app = Flask(
        __name__,
        template_folder=config_class.TEMPLATE_FOLDER,
        static_folder=config_class.STATIC_FOLDER,
    )
    app.config.from_object(config_class)

    # Load SpaCy model once at application startup
    app.extensions["resume_parser"] = ResumeParser(config_class.SPACY_MODEL)

    # Load the Random Forest ranking model once at startup. Never fatal: without
    # the artifact or scikit-learn, MatchingService falls back to the weighted
    # content-based scorer and the UI says so.
    app.extensions["matching_service"] = MatchingService.load(
        app.config["RANKING_MODEL_PATH"],
        enabled=app.config["RANKING_MODEL_ENABLED"],
    )

    for blueprint in ALL_BLUEPRINTS:
        app.register_blueprint(blueprint)

    register_commands(app)

    @app.after_request
    def no_store_private_pages(response):
        """Keeps authenticated pages out of the browser cache.

        Logging out clears the session cookie, so the browser must not replay a
        cached dashboard when the user presses Back. Static assets stay cacheable,
        so only dynamic responses get these headers.
        """
        if not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

        return response

    return app
