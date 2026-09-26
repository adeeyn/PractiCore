from flask import render_template
from flask.views import MethodView

from . import admin_bp
from ...repositories import EmployerRepository


class AdminDashboardView(MethodView):
    def __init__(self):
        self.employers = EmployerRepository()

    def get(self):
        return render_template(
            "admin/dashboard.html",
            active_page="dashboard",
            employers=self.employers.all_with_accounts(),
        )


admin_bp.add_url_rule("/dashboard", view_func=AdminDashboardView.as_view("dashboard"))
