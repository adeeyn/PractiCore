"""Assessment content oversight (CP2 p.80 step 5).

"Manage competency assessment questions and categories." This page reports what
exists: how many questions and parallel forms each competency has, and where the
bank is thin. It is deliberately READ-ONLY.

Editing items is not implemented yet. Two reasons: the published research bank
is an assessed instrument and editing it invalidates the validation, and the
question sets are seeded from code so a web edit would be overwritten by the
next seed. That needs a proper decision before it is exposed.
"""
from flask import render_template
from flask.views import MethodView

from . import admin_bp
from ...repositories import AdminRepository


class AssessmentOverviewView(MethodView):

    def get(self):
        rows = AdminRepository().question_bank_overview()
        total_questions = sum(r["question_count"] for r in rows)
        total_forms = sum(r["form_count"] for r in rows)
        full = [r for r in rows if r["form_count"] >= 3]
        thin = [r for r in rows if r["form_count"] < 3]
        return render_template(
            "admin/assessment.html",
            active_page="assessment",
            competencies=rows,
            total_questions=total_questions,
            total_forms=total_forms,
            full_coverage=len(full),
            thin_coverage=len(thin),
        )


admin_bp.add_url_rule("/assessment", view_func=AssessmentOverviewView.as_view("assessment"))