from flask import g, session

from . import employer_bp
from ...repositories import EmployerRepository


def current_employer():
    """The logged-in employer's company row, loaded once per request."""
    if "current_employer" not in g:
        user_id = session.get("user_id")
        g.current_employer = EmployerRepository().find_by_user_id(user_id) if user_id else None
    return g.current_employer


@employer_bp.context_processor
def inject_current_employer():
    # Available in every employer template, e.g. {{ current_employer.company_name }}
    return {"current_employer": current_employer()}
