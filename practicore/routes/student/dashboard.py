from datetime import datetime, timedelta

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
        student_id = student["id"] if student else None
        applications_count = self.applications.count_for_student(student_id)
        applications_this_week = self.applications.count_for_student_since(
            student_id, datetime.now() - timedelta(days=7)
        )
        domain_scores = self.assessments.for_student(student_id) if student else {}

        completed_assessments = self.assessments.count_for_student(student_id)
        if not completed_assessments and student and student.get("total_questions"):
            # Rows graded before migration 006 have no attempt to count; the
            # score on the students row is that one completed assessment.
            completed_assessments = 1

        recommendations, avg_resume_match = self.recommender.for_dashboard(
            student_skills, assessment_percentage, domain_scores=domain_scores
        )

        # An empty profile has no evidence to recommend on, so the dashboard
        # says so instead of claiming the matches are "based on your skills".
        has_profile = bool(student_skills) or bool(assessment_percentage)

        return render_template(
            "student/student_dashboard.html",
            username=student["name"] if student and student.get("name") else session.get("username"),
            assessment_score=assessment_percentage,
            competency_level=(student or {}).get("competency_level") if assessment_percentage else None,
            resume_match=avg_resume_match,
            applications_count=applications_count,
            applications_this_week=applications_this_week,
            completed_assessments=completed_assessments,
            has_profile=has_profile,
            profile_completion=self._profile_completion(student),
            recent_activity=self._recent_activity(student_id),
            recommendations=recommendations,
            active_page="dashboard",
        )

    @staticmethod
    def _profile_completion(student):
        """Percent of the profile steps that actually have data (0 for a guest)."""
        if not student:
            return 0
        steps = (
            student.get("name"),
            student.get("email"),
            student.get("phone"),
            student.get("course"),
            student.get("skills"),
            student.get("has_resume"),
        )
        return round(100 * sum(1 for step in steps if step) / len(steps))

    @staticmethod
    def _time_ago(when):
        """Short relative label for an activity timestamp."""
        if not when:
            return ""
        days = (datetime.now() - when).days
        if days <= 0:
            return "Today"
        if days == 1:
            return "Yesterday"
        if days < 7:
            return f"{days} days ago"
        return when.strftime("%b %d, %Y")

    def _recent_activity(self, student_id):
        """The student's latest real actions, newest first (max 3)."""
        items = []
        for row in self.applications.recent_for_student(student_id, 3):
            items.append({
                "icon": "file-check-2",
                "css_class": "act-applied",
                "title": f"You applied to {row['position']}",
                "when": row.get("applied_on"),
            })
        for row in self.assessments.recent_for_student(student_id, 3):
            level = row.get("competency_level") or f"{row.get('overall_percentage', 0)}%"
            items.append({
                "icon": "award",
                "css_class": "act-assessment",
                "title": f"Your skill assessment is complete! {level}",
                "when": row.get("taken_at"),
            })
        items.sort(key=lambda item: item["when"] or datetime.min, reverse=True)
        for item in items:
            item["when_text"] = self._time_ago(item["when"])
        return items[:3]


student_bp.add_url_rule("/dashboard", view_func=StudentDashboardView.as_view("dashboard"))
