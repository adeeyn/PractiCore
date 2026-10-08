"""Partner Company Account Creation and Employer Account Management.

CP2 1.3.2 (Figure 21) and 1.3.3. The administrator creates the partner company
and its employer login together, then manages those accounts. No separate
"Partner Company" table is used: CP2's Partner Company IS the `employers` row,
joined to `users` for the login.
"""
import mysql.connector
from flask import current_app, flash, redirect, render_template, request, url_for
from flask.views import MethodView

from . import admin_bp
from ...repositories import AdminRepository
from ...services import AuthService
from ...services import admin_validation as validation


class PartnerCompanyListView(MethodView):
    """Employer Account Management (CP2 1.3.3): every partner company."""

    def get(self):
        admin = AdminRepository(request.args.get("q", ""), request.args.get("status", ""))
        return render_template(
            "admin/partner_companies.html",
            active_page="companies",
            companies=admin.all_employer_accounts(),
            search=admin.search,
            status=admin.status,
        )


class PartnerCompanyCreateView(MethodView):
    """Creates a partner company and its employer account (CP2 Figure 21)."""

    template = "admin/partner_company_form.html"

    def __init__(self):
        self.admin = AdminRepository()

    def _render(self, error=None, form=None):
        return render_template(
            self.template,
            active_page="companies",
            error=error,
            form=form or {},
        )

    def get(self):
        return self._render()

    def post(self):
        data = validation.collect(request.form)
        cleaned, error = validation.validate(
            data, current_app.config["STUDENT_EMAIL_DOMAIN"])

        if error:
            return self._render(error, data)

        # Checked here for an immediate message, and again inside the
        # transaction, because this check can be stale by the time it runs.
        if self.admin.company_name_taken(cleaned["company_name"]):
            return self._render("A company with that name already exists.", data)

        try:
            password_hash = AuthService.hash_password(cleaned["password"])
            self.admin.create_partner_company(cleaned, password_hash)
        except ValueError as err:
            return self._render(str(err), data)
        except mysql.connector.Error:
            # The driver message can name tables and columns, so it is logged
            # for the administrator and never shown on the page.
            current_app.logger.exception("partner company creation failed")
            return self._render(
                "The company could not be created. Please try again.", data)

        flash("Partner company account created successfully.", "success")
        return redirect(url_for("admin.companies"))


class PartnerCompanyDetailView(MethodView):
    def get(self, employer_id):
        company = self._admin().find_employer(employer_id)
        if not company:
            flash("That company could not be found.", "error")
            return redirect(url_for("admin.companies"))
        return render_template(
            "admin/partner_company_detail.html",
            active_page="companies",
            company=company,
        )

    def _admin(self):
        if not hasattr(self, "_repo"):
            self._repo = AdminRepository()
        return self._repo


class EmployerStatusView(MethodView):
    """Activate / deactivate an employer login (CP2 1.3.3).

    The account is never deleted, because its internship postings reference the
    company. Deactivating removes the employer's ability to log in while leaving
    the posting history intact.
    """

    def post(self, employer_id):
        action = request.form.get("action", "")
        want_active = action == "activate"
        if action not in ("activate", "deactivate"):
            flash("Unsupported account action.", "error")
            return redirect(request.referrer or url_for("admin.companies"))

        try:
            changed = AdminRepository().set_account_active(employer_id, want_active)
        except mysql.connector.Error:
            current_app.logger.exception("employer status change failed")
            flash("The account could not be updated. Please try again.", "error")
            return redirect(request.referrer or url_for("admin.companies"))

        if not changed:
            # Either the company is gone or it has no login attached yet.
            flash("That employer account could not be updated.", "error")
        else:
            flash("Employer account %s." % ("activated" if want_active else "deactivated"),
                  "success")
        return redirect(request.referrer or url_for("admin.companies"))


admin_bp.add_url_rule("/companies", view_func=PartnerCompanyListView.as_view("companies"))
admin_bp.add_url_rule("/companies/new", view_func=PartnerCompanyCreateView.as_view("create_company"))
admin_bp.add_url_rule("/companies/<int:employer_id>", view_func=PartnerCompanyDetailView.as_view("company_detail"))
admin_bp.add_url_rule("/companies/<int:employer_id>/status",
                     view_func=EmployerStatusView.as_view("employer_status"))
