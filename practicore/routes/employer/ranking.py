from flask import render_template
from flask.views import MethodView

from . import employer_bp, sample_data


class CandidateRankingView(MethodView):
    def get(self):
        ranked = sorted(sample_data.APPLICANTS, key=lambda a: a["match_score"], reverse=True)
        return render_template(
            "employer/ranking.html",
            active_page="ranking",
            ranked_applicants=ranked,
            ranking_note="Ranking generated using Random Forest ranking algorithm",
        )


employer_bp.add_url_rule("/ranking", view_func=CandidateRankingView.as_view("ranking"))
