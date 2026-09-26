from flask import Blueprint

from ...auth import role_guard

student_bp = Blueprint("student", __name__, url_prefix="/student")

# Every /student/* route requires a logged-in student
student_bp.before_request(role_guard("student"))

# Each module attaches its views to student_bp on import
from . import application, assessment, context, dashboard, profile, recommendation, resume  # noqa: E402,F401
