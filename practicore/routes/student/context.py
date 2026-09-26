from flask import g, session

from . import student_bp
from ...repositories import StudentRepository


def current_student():
    """The logged-in student's row, loaded once per request."""
    if "current_student" not in g:
        user_id = session.get("user_id")
        g.current_student = StudentRepository().find_by_user_id(user_id) if user_id else None
    return g.current_student


@student_bp.context_processor
def inject_current_student():
    # Available in every student template, e.g. {{ current_student.name }}
    return {"current_student": current_student()}
