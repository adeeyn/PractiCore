"""Administrator reports (CP2 p.91).

"The Reports and Dashboard module presents processed information through
dedicated dashboards for ... administrators. This module enables users to
monitor assessment results, internship recommendations, applicant rankings."

This page reports counts and averages only. It deliberately exposes no
individual student's score and no candidate ranking: those belong to the
student and employer modules respectively.
"""
from flask import render_template
from flask.views import MethodView

from . import admin_bp
from ...repositories import AdminRepository


class ReportView(MethodView):

    def get(self):
        admin = AdminRepository()
        return render_template(
            "admin/reports.html",
            active_page="reports",
            summary=admin.report_summary(),
            top_postings=admin.applications_by_posting(8),
            activity=admin.recent_activity(12),
        )


admin_bp.add_url_rule("/reports", view_func=ReportView.as_view("reports"))