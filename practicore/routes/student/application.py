from flask import current_app, redirect, render_template, request, url_for
from flask.views import MethodView

from . import student_bp
from .context import current_student
from ...repositories import ApplicationRepository, AssessmentRepository, PostingRepository
from ...services import AssessmentService, SkillTaxonomy

# Query-string codes for the application page redirects
APPLICATION_MESSAGES = {
    "missing": "Upload your resume and take the assessment before applying.",
    "notfound": "That internship is no longer available.",
    "duplicate": "You have already applied to this internship.",
    "failed": "We could not submit your application. Please try again.",
}


class ApplicationView(MethodView):
    """'My Applications': only the internships this student actually applied to."""

    template = "student/application.html"

    def __init__(self):
        self.applications = ApplicationRepository()

    def get(self):
        student = current_student()

        if request.args.get("applied") == "1":
            message, message_type = "Application submitted.", "success"
        elif request.args.get("withdrawn") == "1":
            message, message_type = "Application withdrawn.", "success"
        else:
            error = APPLICATION_MESSAGES.get(request.args.get("error"))
            message, message_type = error, ("error" if error else None)

        return render_template(
            self.template,
            active_page="application",
            applications=self.applications.for_student(student["id"]) if student else [],
            message=message,
            message_type=message_type,
        )


class ApplyView(MethodView):
    """Applies the logged-in student to one internship posting."""

    def __init__(self):
        self.applications = ApplicationRepository()
        self.assessments = AssessmentRepository()
        self.postings = PostingRepository()

    def post(self, posting_id):
        student = current_student()
        if not student:
            return redirect(url_for("student.application", error="missing"))

        posting = self.postings.find_with_skills(posting_id)
        if not posting:
            return redirect(url_for("student.application", error="notfound"))

        # The recommender needs resume skills and an assessment score to score the match
        student_skills = SkillTaxonomy.parse_skill_string(student.get("skills"))
        if not student_skills or not student.get("total_questions"):
            return redirect(url_for("student.application", error="missing"))

        # Same shared scorer the recommendation page and employer ranking use, so
        # the stored match_score is exactly the number everyone else saw. The two
        # component percentages travel with it, so the employer can be shown which
        # half of the evidence is actually carrying the match.
        matcher = current_app.extensions.get("matching_service")
        components = matcher.score_components(
            {
                "skills": student_skills,
                "domain_scores": self.assessments.for_student(student["id"]),
            },
            posting["skills"],
            assessment_percentage=AssessmentService.score_percentage(student),
        )

        if not self.applications.apply(
            student["id"], posting_id,
            components["match_score"],
            resume_match_score=components["resume_match_percent"],
            assessment_match_score=components["assessment_match_percent"],
        ):
            return redirect(url_for("student.application", error="duplicate"))

        return redirect(url_for("student.application", applied=1))


class WithdrawView(MethodView):
    """Removes one of the student's own applications."""

    def __init__(self):
        self.applications = ApplicationRepository()

    def post(self, application_id):
        student = current_student()
        if student and self.applications.withdraw(application_id, student["id"]):
            return redirect(url_for("student.application", withdrawn=1))
        return redirect(url_for("student.application"))


student_bp.add_url_rule("/application", view_func=ApplicationView.as_view("application"))
student_bp.add_url_rule(
    "/application/<int:posting_id>/apply", view_func=ApplyView.as_view("apply")
)
student_bp.add_url_rule(
    "/application/<int:application_id>/withdraw", view_func=WithdrawView.as_view("withdraw")
)
