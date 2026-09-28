from flask import current_app, render_template
from flask.views import MethodView

from . import employer_bp
from .context import current_employer
from ...repositories import ApplicationRepository


class CandidateRankingView(MethodView):
    """Applicants ordered by the match score the screening engine computed."""

    def __init__(self):
        self.applications = ApplicationRepository()

    def get(self):
        employer = current_employer() or {}

        # The scorer that produced the numbers is also what the page advertises,
        # so the footnote can never claim an algorithm that did not run.
        matcher = current_app.extensions.get("matching_service")
        ranking_note = matcher.status_line() if matcher else ""

        ranked = sorted(
            self.applications.for_employer(employer.get("id")),
            key=lambda a: a["match_score"],
            reverse=True,
        )
        return render_template(
            "employer/ranking.html",
            active_page="ranking",
            ranked_applicants=ranked,
            ranking_note=ranking_note,
            uses_model=bool(matcher and matcher.uses_model),
        )


employer_bp.add_url_rule("/ranking", view_func=CandidateRankingView.as_view("ranking"))
