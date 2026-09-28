from flask import render_template, session
from flask.views import MethodView

from . import student_bp
from ...repositories import ApplicationRepository, AssessmentRepository, StudentRepository
from ...services import AssessmentService, RecommendationService, SkillTaxonomy


class StudentDashboardView(MethodView):

    def __init__(self):
        self.students = StudentRepository()
        self.applications = ApplicationRepository()
        self.assessments = AssessmentRepository()
        self.recommender = RecommendationService()

    def get(self):
        student = self.students.get_dashboard_profile(session.get("username"))
        student_skills = SkillTaxonomy.parse_skill_string(student.get("skills") if student else "")

        assessment_percentage = AssessmentService.score_percentage(student)
        applications_count = self.applications.count_for_student(student["id"] if student else None)
        domain_scores = self.assessments.for_student(student["id"]) if student else {}

        recommendations, avg_resume_match = self.recommender.for_dashboard(
            student_skills, assessment_percentage, domain_scores=domain_scores
        )

        return render_template(
            "student/student_dashboard.html",
            username=student["name"] if student and student.get("name") else session.get("username"),
            assessment_score=assessment_percentage,
            competency_level=(student or {}).get("competency_level") if assessment_percentage else None,
            resume_match=avg_resume_match,
            applications_count=applications_count,
            recommendations=recommendations,
            active_page="dashboard",
        )


student_bp.add_url_rule("/dashboard", view_func=StudentDashboardView.as_view("dashboard"))
