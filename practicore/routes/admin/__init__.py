from flask import Blueprint

from ...auth import role_guard

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Every /admin/* route requires a logged-in admin
admin_bp.before_request(role_guard("admin"))

# Each module attaches its views to admin_bp on import.
#
# The seven destinations match the CP2 administrator scope:
#   Dashboard / Partner Companies / Internship Posting  -> Figures 20-22
#   Users / Assessment                                  -> p.80 steps 4 and 5
#   Reports                                             -> p.91
#   Settings                                            -> Figure 12
from . import (  # noqa: E402,F401
    assessment,
    dashboard,
    employers,
    postings,
    profile,
    reports,
    settings,
    users,
)
