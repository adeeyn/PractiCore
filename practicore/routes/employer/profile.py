import os
import uuid

import mysql.connector
from flask import (
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask.views import MethodView

from . import employer_bp
from .context import current_employer, split_skills
from ...initials import initials_for
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

# Real uploads always live under this folder. Anything else in logo_path is not a
# file we wrote, so it is never deleted when a logo is replaced or removed.
LOGO_UPLOAD_PREFIX = "uploads/logos/"


class CompanyProfileView(MethodView):
    """Shows the employer's own company details and saves the edit form."""

    template = "employer/company_profile.html"

    def __init__(self):
        self.employers = EmployerRepository()

    def _company(self):
        employer = current_employer() or {}
        name = employer.get("company_name", "")
        return {
            "name": name,
            # Derived from the name rather than read back from the column, so a
            # company renamed outside this form still shows matching initials.
            "logo_text": initials_for(name),
            "logo_path": employer.get("logo_path") or "",
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
                 "contact_name", "contact_position", "website", "company_size")}
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

        # The logo initials are derived from the company name by the repository,
        # so renaming the company here updates them without a second field.
        skills = split_skills(form["required_skills"])

        try:
            self.employers.update_profile(
                employer_id=employer["id"],
                user_id=employer["user_id"],
                company_name=form["company_name"],
                company_email=form["email"],
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


class CompanyLogoView(MethodView):
    """Saves, replaces or removes the logged-in employer's company logo.

    Separate from the profile form so the picture appears as soon as it is
    picked, without the employer having to re-submit and re-save the whole form.
    """

    def __init__(self):
        self.employers = EmployerRepository()

    @staticmethod
    def file_extension(filename):
        return filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    @staticmethod
    def remove_file(logo_path):
        """Deletes a logo this upload replaces, if it is a real upload."""
        if not logo_path or not logo_path.startswith(LOGO_UPLOAD_PREFIX):
            return

        try:
            os.remove(os.path.join(current_app.config["STATIC_FOLDER"], logo_path))
        except OSError:
            pass  # Already gone; nothing to clean up

    def post(self):
        if "logo" not in request.files:
            return jsonify({"error": "No file submitted"}), 400

        file = request.files["logo"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        mime_types = current_app.config["LOGO_MIME_TYPES"]
        extension = self.file_extension(file.filename)
        if extension not in mime_types:
            return jsonify({"error": "Invalid file extension"}), 400

        data = file.read()
        max_bytes = current_app.config["LOGO_MAX_BYTES"]
        if len(data) > max_bytes:
            return jsonify({"error": f"File is too large (max {max_bytes // (1024 * 1024)} MB)"}), 400

        employer = current_employer()
        if not employer:
            return jsonify({"error": "Company profile not found"}), 404

        # The stored name is generated here, so no user-supplied name reaches the disk
        filename = f"{employer['id']}_{uuid.uuid4().hex[:8]}.{extension}"

        try:
            os.makedirs(current_app.config["LOGO_UPLOAD_DIR"], exist_ok=True)
            with open(os.path.join(current_app.config["LOGO_UPLOAD_DIR"], filename), "wb") as logo:
                logo.write(data)
        except OSError as e:
            return jsonify({"error": str(e)}), 500

        logo_path = LOGO_UPLOAD_PREFIX + filename
        try:
            self.employers.update_logo(employer["id"], logo_path)
        except mysql.connector.Error:
            # Migration 013 has not been applied, so the file is written but
            # unreachable. Drop it rather than leave an orphan behind.
            self.remove_file(logo_path)
            return jsonify({"error": "Logo storage is not set up yet."}), 500

        # Only cleared once the new path is safely stored, so a failure above
        # leaves the company with the logo it already had.
        self.remove_file(employer.get("logo_path"))

        return jsonify({
            "status": "success",
            "logo_path": logo_path,
            "logo_url": url_for("static", filename=logo_path),
        }), 200

    def delete(self):
        employer = current_employer()
        if not employer:
            return jsonify({"error": "Company profile not found"}), 404

        try:
            self.employers.update_logo(employer["id"], None)
        except mysql.connector.Error:
            return jsonify({"error": "Logo storage is not set up yet."}), 500

        self.remove_file(employer.get("logo_path"))

        # Handed back so the page falls back to the initials of the company name
        return jsonify({
            "status": "success",
            "logo_path": None,
            "logo_text": initials_for(employer.get("company_name")),
        }), 200


employer_bp.add_url_rule("/profile", view_func=CompanyProfileView.as_view("profile"))
employer_bp.add_url_rule("/profile/logo", view_func=CompanyLogoView.as_view("profile_logo"))
