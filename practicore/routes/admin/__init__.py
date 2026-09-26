from flask import Blueprint

from ...auth import role_guard

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Every /admin/* route requires a logged-in admin
admin_bp.before_request(role_guard("admin"))

# Each module attaches its views to admin_bp on import
from . import dashboard, employers  # noqa: E402,F401
