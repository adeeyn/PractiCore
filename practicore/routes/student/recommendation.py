from flask import render_template, session
from flask.views import MethodView

from . import student_bp
from ...repositories import StudentRepository
from ...services import RecommendationService, SkillTaxonomy


class RecommendationView(MethodView):

    def __init__(self):
        self.students = StudentRepository()
        self.recommender = RecommendationService()

    def get(self):
        student_skills = SkillTaxonomy.parse_skill_string(self.students.get_skills(session.get("username")))
        category_breakdown = session.get("latest_assessment_results", {}).get("category_breakdown", {})

        recommendations = self.recommender.for_recommendation_page(student_skills, category_breakdown)
        return render_template("student/recommendation.html", active_page="recommendation", recommendations=recommendations)


student_bp.add_url_rule("/recommendation", view_func=RecommendationView.as_view("recommendation"))
