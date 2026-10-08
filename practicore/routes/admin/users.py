"""Registered User monitoring (CP2 p.80 step 4).

"Monitor registered users and system activities." Every role is listed in one
table so the administrator can see the whole population at once, with search and
filtering. No credential is ever selected or displayed.
"""
import mysql.connector
from flask import current_app, flash, redirect, render_template, request, url_for
from flask.views import MethodView

from . import admin_bp
from ...repositories import AdminRepository


class UserListView(MethodView):

    def get(self):
        admin = AdminRepository(request.args.get("q", ""), request.args.get("status", ""))
        return render_template(
            "admin/users.html",
            active_page="users",
            users=admin.all_users(),
            counts=admin.users_by_role(),
            search=admin.search,
            status=admin.status,
        )


class UserStatusView(MethodView):
    """Activate / deactivate an account.

    Only student and employer accounts can be toggled. The repository refuses to
    deactivate the signed-in administrator, who would otherwise lock themselves
    out with no other admin able to restore the account.
    """

    def post(self, user_id):
        action = request.form.get("action", "")
        want_active = action == "activate"
        if action not in ("activate", "deactivate"):
            flash("Unsupported account action.", "error")
            return redirect(request.referrer or url_for("admin.users"))

        try:
            changed = AdminRepository().set_user_active(user_id, want_active)
        except mysql.connector.Error:
            current_app.logger.exception("user status change failed")
            flash("The account could not be updated. Please try again.", "error")
            return redirect(request.referrer or url_for("admin.users"))

        if not changed:
            flash("That account could not be updated. You cannot change your own status.",
                  "error")
        else:
            flash("Account %s." % ("activated" if want_active else "deactivated"), "success")
        return redirect(request.referrer or url_for("admin.users"))


admin_bp.add_url_rule("/users", view_func=UserListView.as_view("users"))
admin_bp.add_url_rule("/users/<int:user_id>/status",
                     view_func=UserStatusView.as_view("user_status"))