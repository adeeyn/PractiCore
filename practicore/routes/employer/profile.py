from flask import render_template, session
from flask.views import MethodView

from . import employer_bp
from .context import current_employer


class CompanyProfileView(MethodView):
    def get(self):
        employer = current_employer() or {}
        # industry and about have no database columns yet, so they start empty
        company = {
            "name": employer.get("company_name", ""),
            "logo_text": employer.get("company_logo_text") or "?",
            "industry": employer.get("industry") or "",
            "email": session.get("email", ""),
            "location": employer.get("location", ""),
            "about": employer.get("about") or "",
        }
        return render_template("employer/company_profile.html", active_page="profile", company=company)


employer_bp.add_url_rule("/profile", view_func=CompanyProfileView.as_view("profile"))
