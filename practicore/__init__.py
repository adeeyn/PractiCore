from datetime import date, datetime

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

    @app.template_filter("timeago")
    def timeago(value):
        """Relative stamps ("2 hours ago") for the Recent Activity feeds.

        Anything that is not a date/datetime falls back to an em dash, so a
        null timestamp can never break the feed.
        """
        if isinstance(value, datetime):
            stamp = value
        elif isinstance(value, date):
            stamp = datetime(value.year, value.month, value.day)
        else:
            return "—"

        now = datetime.now(stamp.tzinfo) if stamp.tzinfo else datetime.now()
        seconds = (now - stamp).total_seconds()
        if seconds < 0:
            return stamp.strftime("%b %d, %Y")
        if seconds < 60:
            return "just now"
        minutes = int(seconds // 60)
        if minutes < 60:
            return "%d minute%s ago" % (minutes, "" if minutes == 1 else "s")
        hours = minutes // 60
        if hours < 24:
            return "%d hour%s ago" % (hours, "" if hours == 1 else "s")
        days = hours // 24
        if days == 1:
            return "Yesterday"
        if days < 7:
            return "%d days ago" % days
        return stamp.strftime("%b %d, %Y")

    return app
