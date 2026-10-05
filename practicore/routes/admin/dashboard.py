from flask import render_template
from flask.views import MethodView

from . import admin_bp
from ...repositories import AdminRepository


class AdminDashboardView(MethodView):
    """CP2 section 1.3.1 / Figure 20.

    Reached by logging in with admin credentials on the SHARED login page --
    CP2 p.73 states this "eliminat[es] the need for a separate administrator
    login page", so there is deliberately no /admin/login route.

    Every figure is a live COUNT from the database. Nothing here is hard-coded.
    """

    def __init__(self):
        self.admin = AdminRepository()

    def get(self):
        admin = self.admin
        stats = admin.stats()
        return render_template(
            "admin/dashboard.html",
            active_page="dashboard",
            stats=stats,
            # The four cards in the CP2 Figure 20 layout.
            total_companies=stats["companies"],
            new_companies=admin.count_new_partner_companies(30),
            active_postings=stats["active_postings"],
            closed_postings=stats["postings"] - stats["active_postings"],
            total_applications=stats["applications"],
            total_users=admin.users_by_role()["total"],
            # One merged, time-ordered feed rather than three separate tables.
            activity=admin.recent_activity(8),
        )


admin_bp.add_url_rule("/dashboard", view_func=AdminDashboardView.as_view("dashboard"))
