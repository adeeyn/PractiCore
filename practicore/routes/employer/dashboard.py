from flask import render_template
from flask.views import MethodView

from . import employer_bp, sample_data


class EmployerDashboardView(MethodView):
    def get(self):
        return render_template(
            "employer/dashboard.html",
            active_page="dashboard",
            stats=sample_data.STATS,
            recent_applicants=sample_data.APPLICANTS[:4],
        )


employer_bp.add_url_rule("/dashboard", view_func=EmployerDashboardView.as_view("dashboard"))
