from datetime import datetime

from flask import render_template
from flask.views import MethodView

from . import employer_bp
from .context import current_employer
from ...repositories import ApplicationRepository, PostingRepository


def _greeting():
    """'Good morning' style line, matching the hour the employer opened the page."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


class EmployerDashboardView(MethodView):
    def __init__(self):
        self.applications = ApplicationRepository()
        self.postings = PostingRepository()

    def get(self):
        employer = current_employer() or {}
        employer_id = employer.get("id")
        counts = self.applications.counts_for_employer(employer_id)

        recent_applicants = self.applications.for_employer(employer_id)[:4]
        active_postings = self.postings.count_for_employer(employer_id)

        return render_template(
            "employer/dashboard.html",
            active_page="dashboard",
            greeting=_greeting(),
            contact_name=employer.get("contact_name") or employer.get("company_logo_text") or "there",
            stats=[
                {"icon": "users", "label": "Total Applicants", "value": counts["total"],
                 "note": f"{counts['pending']} awaiting review"},
                {"icon": "briefcase", "label": "Active Internships", "value": active_postings,
                 "note": "Currently open"},
                {"icon": "user-check", "label": "Shortlisted", "value": counts["shortlisted"],
                 "note": f"{counts['hired']} hired so far"},
                {"icon": "trending-up", "label": "Avg Match Score", "value": f"{counts['avg_match']}%",
                 "note": "Across all postings"},
            ],
            recent_applicants=recent_applicants,
            has_applicants=bool(recent_applicants),
            pending_count=counts["pending"],
            active_postings=active_postings,
        )


employer_bp.add_url_rule("/dashboard", view_func=EmployerDashboardView.as_view("dashboard"))
