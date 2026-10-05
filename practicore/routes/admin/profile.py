"""The administrator's own account view.

Read-only, and deliberately thin: CP2's Administrator duties are managing company
accounts and monitoring postings, not maintaining a personal profile. The row
shown is the logged-in administrator's own, resolved from the session id rather
than from any request parameter, so no other account can be read through this
page.
"""
from flask import render_template, session
from flask.views import MethodView

from . import admin_bp
from ...repositories import AdminRepository


class AdminProfileView(MethodView):

    def get(self):
        return render_template(
            "admin/profile.html",
            active_page="profile",
            account=AdminRepository().find_user(session.get("user_id")),
        )


admin_bp.add_url_rule("/profile", view_func=AdminProfileView.as_view("profile"))