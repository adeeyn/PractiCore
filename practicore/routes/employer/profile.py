import mysql.connector
from flask import redirect, render_template, request, session, url_for
from flask.views import MethodView

from . import employer_bp
from .context import current_employer, split_skills
from ...repositories import EmployerRepository
from ...services import AuthService

# Query-string codes for the profile redirects (same idiom as auth.login's ?failed=1)
PROFILE_MESSAGES = {
    "missing": "Company name, email and location are required.",
    "email": "Please enter a valid email address.",
    "taken": "That email address is already used by another account.",
    "failed": "We could not save your changes. Please try again.",
    "noaccount": "No company is linked to this login yet. Ask an admin to create one.",
}

COMPANY_SIZES = ["1-10", "11-50", "51-200", "201-500", "500+"]


class CompanyProfileView(MethodView):
    """Shows the employer's own company details and saves the edit form."""

    template = "employer/company_profile.html"

    def __init__(self):
        self.employers = EmployerRepository()

    def _company(self):
        employer = current_employer() or {}
        return {
            "name": employer.get("company_name", ""),
            "logo_text": employer.get("company_logo_text") or "?",
            "industry": employer.get("industry") or "",
            "email": session.get("email", ""),
            "location": employer.get("location", ""),
            "about": employer.get("about") or "",
            "required_skills": split_skills(employer.get("required_skills")),
            "contact_name": employer.get("contact_name") or "",
            "contact_position": employer.get("contact_position") or "",
            "website": employer.get("website") or "",
            "company_size": employer.get("company_size") or "",
            "is_hiring": bool(employer.get("is_hiring")),
        }

    def _render(self, message=None, message_type=None):
        return render_template(
            self.template,
            active_page="profile",
            company=self._company(),
            company_sizes=COMPANY_SIZES,
            message=message,
            message_type=message_type,
        )

    @staticmethod
    def valid_email(value):
        local, _, domain = value.partition("@")
        return bool(local and domain and "." in domain and " " not in value)

    def get(self):
        if request.args.get("saved") == "1":
            return self._render("Your company profile has been updated.", "success")

        error = PROFILE_MESSAGES.get(request.args.get("error"))
        return self._render(error, "error" if error else None)

    def post(self):
        form = {key: request.form.get(key, "").strip() for key in
                ("company_name", "email", "industry", "location", "about", "required_skills",
                 "contact_name", "contact_position", "website", "company_size", "logo_text")}
        form["email"] = form["email"].lower()

        if not (form["company_name"] and form["email"] and form["location"]):
            return redirect(url_for("employer.profile", error="missing"))
        if not self.valid_email(form["email"]):
            return redirect(url_for("employer.profile", error="email"))
        if AuthService.is_student_email(form["email"]):
            return redirect(url_for("employer.profile", error="email"))

        employer = current_employer()
        if not employer:
            return redirect(url_for("employer.profile", error="noaccount"))

        # Blank logo text falls back to the first letters of the company name
        logo_text = form["logo_text"] or "".join(w[0] for w in form["company_name"].split()[:2]).upper()
        skills = split_skills(form["required_skills"])

        try:
            self.employers.update_profile(
                employer_id=employer["id"],
                user_id=employer["user_id"],
                company_name=form["company_name"],
                company_email=form["email"],
                logo_text=logo_text[:10],
                industry=form["industry"],
                location=form["location"],
                about=form["about"],
                required_skills=", ".join(skills),
                contact_name=form["contact_name"],
                contact_position=form["contact_position"],
                website=form["website"],
                company_size=form["company_size"],
                is_hiring=1 if request.form.get("is_hiring") else 0,
            )
        except mysql.connector.IntegrityError:
            # users.email carries a UNIQUE index, so a clash locks the company out
            return redirect(url_for("employer.profile", error="taken"))
        except mysql.connector.Error:
            return redirect(url_for("employer.profile", error="failed"))

        # The login email changed with the profile, so keep the session truthful
        session["email"] = form["email"]
        return redirect(url_for("employer.profile", saved=1))


employer_bp.add_url_rule("/profile", view_func=CompanyProfileView.as_view("profile"))
