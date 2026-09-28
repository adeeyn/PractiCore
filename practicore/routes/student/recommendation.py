from flask import render_template, session
from flask.views import MethodView

from . import student_bp
from .context import current_student
from ...repositories import ApplicationRepository, AssessmentRepository, StudentRepository
from ...services import AssessmentService, RecommendationService, SkillTaxonomy


class RecommendationView(MethodView):
    def __init__(self):
        self.students = StudentRepository()
        self.applications = ApplicationRepository()
        self.assessments = AssessmentRepository()
        self.recommender = RecommendationService()

    def get(self):
        student = current_student()
        student_skills = SkillTaxonomy.parse_skill_string(self.students.get_skills(session.get("username")))

        # Read the score from the students table, not the session: a session-only
        # breakdown is lost on logout and used to fall back to a flat 50%.
        assessment_percentage = AssessmentService.score_percentage(student)
        domain_scores = self.assessments.for_student(student["id"]) if student else {}

        recommendations = self.recommender.for_recommendation_page(
            student_skills, assessment_percentage, domain_scores=domain_scores
        )
        return render_template(
            "student/recommendation.html",
            active_page="recommendation",
            recommendations=recommendations,
            assessment_percentage=assessment_percentage,
            # Drives the Apply button: which cards already read "Applied"
            applied_posting_ids=self.applications.applied_posting_ids(student["id"]) if student else set(),
        )


student_bp.add_url_rule("/recommendation", view_func=RecommendationView.as_view("recommendation"))
