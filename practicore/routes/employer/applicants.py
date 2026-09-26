from flask import render_template, request
from flask.views import MethodView

from . import employer_bp, sample_data

APPLICATION_STATUSES = ["Pending", "In Review", "Shortlisted", "Scheduled", "Hired", "Rejected"]
ACTIONS = ["Shortlist", "Schedule Interview", "Hire", "Reject"]


class ApplicantsView(MethodView):
    def get(self):
        return render_template(
            "employer/applicants.html",
            active_page="applicants",
            posting_title=sample_data.POSITION + "s",
            total_applicants=sample_data.TOTAL_APPLICANTS,
            applicants=sample_data.APPLICANTS,
            statuses=APPLICATION_STATUSES,
        )


class ApplicantManagementView(MethodView):
    def get(self):
        applicants = sample_data.APPLICANTS
        selected_id = request.args.get("applicant", type=int)
        selected = next((a for a in applicants if a["id"] == selected_id), applicants[0] if applicants else None)

        return render_template(
            "employer/applicant_management.html",
            active_page="management",
            applicants=applicants,
            selected=selected,
            statuses=APPLICATION_STATUSES,
            actions=ACTIONS,
        )


employer_bp.add_url_rule("/applicants", view_func=ApplicantsView.as_view("applicants"))
employer_bp.add_url_rule("/applicants/manage", view_func=ApplicantManagementView.as_view("applicant_management"))
