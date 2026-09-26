from flask import Blueprint

from ...auth import role_guard

employer_bp = Blueprint("employer", __name__, url_prefix="/employer")

# Every /employer/* route requires a logged-in employer
employer_bp.before_request(role_guard("employer"))

# Each module attaches its views to employer_bp on import
from . import applicants, context, dashboard, postings, profile, ranking  # noqa: E402,F401
