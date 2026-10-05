from flask import g, session

from . import employer_bp
from ...initials import initials_for
from ...repositories import EmployerRepository


def split_skills(value):
    """'Python, SQL , Python' -> ['Python', 'SQL'] (case kept, order kept, no dupes)."""
    seen, skills = set(), []
    for part in (value or "").split(","):
        clean = part.strip()
        if clean and clean.lower() not in seen:
            seen.add(clean.lower())
            skills.append(clean)
    return skills


def current_employer():
    """The logged-in employer's company row, loaded once per request."""
    if "current_employer" not in g:
        user_id = session.get("user_id")
        g.current_employer = EmployerRepository().find_by_user_id(user_id) if user_id else None
    return g.current_employer


@employer_bp.context_processor
def inject_current_employer():
    # Available in every employer template, e.g. {{ current_employer.company_name }}
    employer = current_employer() or {}

    # Handy derived values so templates do not repeat the same fallbacks
    employer.setdefault("required_skill_list", split_skills(employer.get("required_skills")))
    # The initials are derived from the company name, so the topbar chip and the
    # profile page always show the same two letters for the same company.
    employer.setdefault("logo_text", initials_for(employer.get("company_name")))
    employer.setdefault("display_name", employer.get("contact_name")
                        or employer.get("company_name") or "Employer")
    employer.setdefault("display_role", employer.get("contact_position") or "Hiring Manager")

    return {
        "current_employer": current_employer(),
        "employer": employer,
    }
