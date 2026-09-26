import mysql.connector
from flask import redirect, render_template, request, url_for
from flask.views import MethodView

from . import admin_bp
from ...repositories import EmployerRepository, UserRepository
from ...services import AuthService


class CreateEmployerAccountView(MethodView):
    """Admins create employer logins, either for a new company or an existing one."""

    template = "admin/create_employer.html"

    def __init__(self):
        self.employers = EmployerRepository()
        self.users = UserRepository()

    def _render(self, error=None, form=None):
        return render_template(
            self.template,
            active_page="employers",
            companies_without_account=self.employers.without_account(),
            error=error,
            form=form or {},
        )

    def get(self):
        return self._render()

    def post(self):
        form = {key: request.form.get(key, "").strip() for key in
                ("employer_id", "company_name", "location", "logo_text", "email", "password")}
        form["email"] = form["email"].lower()

        if not form["email"] or not form["password"]:
            return self._render("Email and password are required.", form)
        if AuthService.is_student_email(form["email"]):
            return self._render("Student school emails cannot be used for employer accounts.", form)
        if not form["employer_id"] and not (form["company_name"] and form["location"]):
            return self._render("Pick an existing company or enter a company name and location.", form)

        try:
            if self.users.exists(form["email"]):
                return self._render("An account with that email already exists.", form)

            password_hash = AuthService.hash_password(form["password"])
            if form["employer_id"]:
                self.employers.attach_account(int(form["employer_id"]), form["email"], password_hash)
            else:
                logo = form["logo_text"] or "".join(w[0] for w in form["company_name"].split()[:2]).upper()
                self.employers.create_with_account(
                    form["email"], password_hash, form["company_name"], form["location"], logo
                )
        except (ValueError, mysql.connector.Error) as err:
            return self._render(str(err), form)

        return redirect(url_for("admin.dashboard"))


admin_bp.add_url_rule("/employers/new", view_func=CreateEmployerAccountView.as_view("create_employer"))
