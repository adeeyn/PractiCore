from flask import Blueprint

auth_bp = Blueprint("auth", __name__)

# Each module attaches its views to auth_bp on import
from . import login, register  # noqa: E402,F401
