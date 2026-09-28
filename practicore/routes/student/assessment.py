from flask import current_app, jsonify, redirect, render_template, request, session, url_for
from flask.views import MethodView

from . import student_bp
from .context import current_student
from ...repositories import AssessmentRepository, StudentRepository
from ...services import AssessmentService, SkillTaxonomy


class AssessmentView(MethodView):
    """Assessment landing page with the student's current score."""

    def __init__(self):
        self.students = StudentRepository()

    def get(self):
        student = self.students.get_assessment_stats(session.get("username"))
        return render_template(
            "student/assessment.html",
            active_page="assessment",
            student=student,
            score_percentage=AssessmentService.score_percentage(student),
        )


class StartAssessmentView(MethodView):

    def __init__(self):
        self.service = AssessmentService()

    def get(self):
        # Resume skills drive the resume-triggered portion of the question bank.
        student = current_student()
        student_skills = SkillTaxonomy.parse_skill_string(student.get("skills") if student else "")

        questions, grouped_questions, domain_map = self.service.build(student_skills)

        # Store question -> domain mapping in session for submission evaluation
        session["active_assessment_map"] = domain_map

        return render_template(
            "student/start_assessment.html",
            questions=questions,
            grouped_questions=grouped_questions,
            total_questions=len(questions),
            time_limits=current_app.config["QUESTION_TIME_LIMITS"],
            total_seconds=sum(q["time_limit"] for q in questions),
        )


class SubmitAssessmentView(MethodView):

    def __init__(self):
        self.students = StudentRepository()
        self.assessments = AssessmentRepository()
        self.service = AssessmentService()

    def post(self):
        answers = request.get_json() or {}
        student = current_student()
        try:
            results = self.service.grade(answers, session.get("active_assessment_map", {}))
            self.students.update_assessment(
                session.get("username"),
                results["total_correct"],
                results["total_questions"],
                results["competency_level"],
            )
            # Persist the per-domain breakdown so the ranker has real features
            # and the results page survives a logout (migration 006).
            if student:
                self.assessments.save_results(
                    student["id"], results, results.get("category_breakdown", {})
                )
        except Exception as e:
            print(f"Error in submit_assessment: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

        session["latest_assessment_results"] = results
        return jsonify({
            "status": "success",
            "redirect_url": url_for("student.assessment_results"),
        })


class AssessmentResultsView(MethodView):

    def get(self):
        results = session.get("latest_assessment_results")
        if not results:
            return redirect(url_for("student.start_assessment"))

        return render_template(
            "student/assessment_results.html",
            active_page="assessment",
            competency_level=results["competency_level"],
            overall_percentage=results["overall_percentage"],
            total_correct=results["total_correct"],
            total_questions=results["total_questions"],
            category_breakdown=results["category_breakdown"],
        )


student_bp.add_url_rule("/assessment", view_func=AssessmentView.as_view("assessment"))
student_bp.add_url_rule("/assessment/start", view_func=StartAssessmentView.as_view("start_assessment"))
student_bp.add_url_rule("/assessment/submit", view_func=SubmitAssessmentView.as_view("submit_assessment"))
student_bp.add_url_rule("/assessment/results", view_func=AssessmentResultsView.as_view("assessment_results"))
