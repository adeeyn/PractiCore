"""Administrator Settings (CP2 Figure 12).

CP2 describes the Settings Page as the place "users ... update their password,
account information, and other personal settings". This is the administrator's
own settings: it shows their account and lets them change their own password.

It is scoped to the signed-in administrator only. There is no route that reads
or writes another user's account from this page.
"""
import mysql.connector
from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask.views import MethodView

from . import admin_bp
from ...repositories import AdminRepository, UserRepository
from ...services import AuthService


class AdminSettingsView(MethodView):

    def get(self, error=None):
        return render_template(
            "admin/settings.html",
            active_page="settings",
            account=AdminRepository().find_user(session.get("user_id")),
            error=error,
        )

    def post(self):
        """Changes the administrator's own password."""
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        user = UserRepository().find_by_login(session.get("email"))
        if not user:
            flash("Your account could not be loaded. Please sign in again.", "error")
            return redirect(url_for("auth.login"))

        # The stored hash is checked before anything is written, so a wrong
        # current password can never overwrite a good one.
        if not AuthService.verify_password(user["password_hash"], current):
            return self._render("Your current password is incorrect.")

        if len(new) < 6:
            return self._render("New password must be at least 6 characters.")
        if new != confirm:
            return self._render("New passwords do not match.")
        if AuthService.verify_password(user["password_hash"], new):
            return self._render("The new password must be different from the current one.")

        try:
            UserRepository().set_password(user["id"], AuthService.hash_password(new))
        except mysql.connector.Error:
            current_app.logger.exception("admin password change failed")
            return self._render("The password could not be changed. Please try again.")

        flash("Password updated.", "success")
        return redirect(url_for("admin.settings"))

    def _render(self, error):
        return self.get(error=error)


admin_bp.add_url_rule("/settings", view_func=AdminSettingsView.as_view("settings"))