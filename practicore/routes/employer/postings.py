from flask import render_template
from flask.views import MethodView

from . import employer_bp, sample_data


class InternshipPostingView(MethodView):
    def get(self):
        return render_template(
            "employer/postings.html",
            active_page="postings",
            suggested_skills=sample_data.SUGGESTED_SKILLS,
        )


employer_bp.add_url_rule("/postings", view_func=InternshipPostingView.as_view("postings"))
