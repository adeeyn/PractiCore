import json

from flask import current_app, jsonify, redirect, render_template, request, session, url_for
from flask.views import MethodView

from . import student_bp
from .context import current_student
from ...repositories import CompetencyRepository, PostingRepository, StudentRepository
from ...services import AssessmentService, SkillTaxonomy
from ...services.adaptive_assessment_service import AdaptiveAssessmentService
from ...services.competency_taxonomy import evidence_from_skills

# What the assessment page needs to remember between GET /start and POST /submit.
# The question text and answer keys are deliberately NOT stored: the client is
# never told the key, and grading re-reads the questions from the database.
SESSION_MAP = "active_competency_map"
SESSION_META = "active_competency_meta"
SESSION_POSTING = "active_assessment_posting_id"


def _resume_skills(student):
    """The skills the student's resume produced, as a list."""
    if not student:
        return []
    return sorted(SkillTaxonomy.parse_skill_string(student.get("skills") or ""))


def _posting_for(posting_id):
    if not posting_id:
        return None
    for posting in PostingRepository().all_with_skills():
        if int(posting["id"]) == int(posting_id):
            return posting
    return None


class AssessmentView(MethodView):
    """Assessment landing page: the student's competency profile so far."""

    def __init__(self):
        self.students = StudentRepository()
        self.competencies = CompetencyRepository()

    def get(self):
        student = self.students.get_assessment_stats(session.get("username"))
        # .get rather than ["id"]: a missing column should leave the profile
        # empty, never turn the whole assessment page into a 500.
        profile = self.competencies.student_profile((student or {}).get("id"))
        return render_template(
            "student/assessment.html",
            active_page="assessment",
            student=student,
            score_percentage=AssessmentService.score_percentage(student),
            profile=profile,
            shortfall=self.competencies.competencies_with_forms(),
        )



class StartAssessmentView(MethodView):
    """Assembles the adaptive assessment and serves it."""

    def __init__(self):
        self.service = AdaptiveAssessmentService()
        self.competencies = CompetencyRepository()
        self.postings = PostingRepository()

    def _build_assessment(self, student_id, skills, posting):
        """Builds the attempt, preferring the master bank.

        The master bank is what makes a 40-50 question attempt possible: the legacy
        parallel-form builder serves one form per competency, which caps the paper at
        2 x (competencies) = 17-36 items. The fallback is deliberate rather than
        defensive - a database that has not been seeded with the master bank must
        still produce a working assessment, exactly as it did before.
        """
        if current_app.config.get("MASTER_BANK_ENABLED"):
            from ...services.master_selection import build_master_assessment

            built = build_master_assessment(
                student_id,
                resume_skills=skills,
                posting=posting,
                repo=self.competencies,
                target=current_app.config.get("MASTER_TARGET_QUESTIONS"),
            )
            if built["questions"]:
                return built
            current_app.logger.info(
                "Master bank produced no questions; falling back to parallel forms."
            )
        return self.service.build(student_id, skills, posting)

    def get(self):
        student = current_student()
        student_id = student["id"] if student else None
        skills = _resume_skills(student)

        # An optional target posting makes the assessment adaptive: the same
        # student is asked different things for a web role than for IT support.
        posting_id = request.args.get("posting") or None
        posting = _posting_for(posting_id)

        built = self._build_assessment(student_id, skills, posting)

        # Record the resume's claims, separately from any score.
        if student_id and skills:
            self.competencies.save_resume_evidence(
                student_id, evidence_from_skills(skills)
            )

        if not built["questions"]:
            return render_template(
                "student/assessment_unavailable.html",
                active_page="assessment",
                shortfall=built["shortfall"],
            )

        session[SESSION_MAP] = built["competency_map"]
        session[SESSION_META] = {
            "per_competency": built["per_competency"],
            "shortfall": built["shortfall"],
        }
        session[SESSION_POSTING] = posting_id

        # Record which forms this student was shown, so a retake rotates.
        if student_id:
            self.competencies.record_exposure(
                student_id,
                {code: {"id": meta["set_id"]}
                 for code, meta in built["per_competency"].items()
                 if meta.get("set_id")},
            )
            # Per-ITEM exposure for the master bank. A retake prefers items this
            # student has not seen, so the ledger must be written at build time,
            # not at submit: a student who abandons an attempt has still seen it.
            if current_app.config.get("MASTER_BANK_ENABLED"):
                self.competencies.record_seen_questions(
                    student_id,
                    None,
                    [{"question_id": q["id"], "competency_code": q["competency"]}
                     for q in built["questions"]],
                )

        # Group the shuffled questions by competency for display, preserving the
        # core-first ordering the selection engine produced.
        order = [e["code"] for e in built["selected"]]
        grouped = {}
        for q in built["questions"]:
            grouped.setdefault(q["competency"], []).append(q)
        sections = [
            {
                "code": code,
                "name": built["per_competency"].get(code, {}).get("name", code),
                "is_core": built["per_competency"].get(code, {}).get("is_core", False),
                "questions": grouped.get(code, []),
            }
            for code in order if grouped.get(code)
        ]

        return render_template(
            "student/start_assessment.html",
            questions=built["questions"],
            sections=sections,
            per_competency=built["per_competency"],
            shortfall=built["shortfall"],
            target_posting=posting,
            total_questions=len(built["questions"]),
            time_limits=current_app.config["QUESTION_TIME_LIMITS"],
            total_seconds=sum(q["time_limit"] for q in built["questions"]),
        )



class SubmitAssessmentView(MethodView):

    def __init__(self):
        self.students = StudentRepository()
        self.competencies = CompetencyRepository()
        self.service = AdaptiveAssessmentService()

    def post(self):
        answers = request.get_json() or {}
        student = current_student()
        if not student:
            return jsonify({"status": "error", "message": "Not signed in"}), 401

        competency_map = session.get(SESSION_MAP) or {}
        meta = session.get(SESSION_META) or {}
        per_competency = meta.get("per_competency") or {}
        posting_id = session.get(SESSION_POSTING)

        if not competency_map:
            return jsonify({"status": "error", "message": "No assessment in progress"}), 400

        try:
            # Re-read the questions: the browser's copy of the key is not trusted.
            question_ids = [int(q) for q in competency_map]
            questions = self.competencies.questions_by_ids(question_ids)

            results = self.service.grade(
                answers, competency_map, per_competency, questions
            )

            # The legacy overall score still backs the dashboard summary.
            self.students.update_assessment(
                session.get("username"),
                results["total_correct"],
                results["total_questions"],
                results["competency_level"],
            )

            attempt_no = self.competencies.next_attempt_no(student["id"], posting_id)
            per_comp_for_db = {
                code: {
                    "correct": s["correct"],
                    "total": s["total"],
                    "score_percent": s["score_percent"],
                    "set_id": s.get("set_id"),
                }
                for code, s in results["competency_breakdown"].items()
            }
            attempt_id = self.competencies.save_attempt(
                student["id"], posting_id, attempt_no, results, per_comp_for_db
            )

            # Per-question ledger: which items were served, in what order, what was
            # answered and whether it was right. Without this the system cannot tell
            # an unanswered item from a wrong one, or reconstruct a past attempt.
            if attempt_id and results.get("per_question"):
                self.competencies.save_attempt_questions(
                    attempt_id, results["per_question"], results.get("answers") or {}
                )

            # Recompute the ranking inputs for this posting, if one was targeted.
            if posting_id:
                self._refresh_compatibility(student["id"], posting_id)

        except Exception as e:  # surface the failure instead of losing the attempt
            current_app.logger.exception("submit_assessment failed")
            return jsonify({"status": "error", "message": str(e)}), 500

        session.pop(SESSION_MAP, None)
        session.pop(SESSION_META, None)
        session.pop(SESSION_POSTING, None)
        session["latest_assessment_results"] = results
        return jsonify({
            "status": "success",
            "redirect_url": url_for("student.assessment_results"),
        })

    def _refresh_compatibility(self, student_id, posting_id):
        """Recompute and cache the match for the targeted posting."""
        from ...services.cross_matching import score_posting

        profile = self.competencies.student_profile(student_id)
        requirements = self.competencies.requirements_for_posting(posting_id)
        if not requirements:
            return
        self.competencies.save_compatibility(
            student_id, posting_id, score_posting(profile, requirements)
        )


class AssessmentResultsView(MethodView):

    def get(self):
        results = session.get("latest_assessment_results")
        student = current_student()

        # Survives a logout: the breakdown is re-read from the saved attempt
        # rather than depending on the session.
        breakdown = (results or {}).get("competency_breakdown") or {}
        if not breakdown and student:
            breakdown = self._latest_breakdown(student["id"])

        if not results and not breakdown:
            return redirect(url_for("student.start_assessment"))

        return render_template(
            "student/assessment_results.html",
            active_page="assessment",
            competency_level=(results or {}).get("competency_level"),
            overall_percentage=(results or {}).get("overall_percentage"),
            total_correct=(results or {}).get("total_correct"),
            total_questions=(results or {}).get("total_questions"),
            category_breakdown=breakdown,
        )

    def _latest_breakdown(self, student_id):
        from ...database import Database

        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT ac.competency_code, ac.score_percent, ac.correct_count,
                       ac.question_count, c.name
                FROM attempt_competencies ac
                JOIN assessment_attempts a ON a.id = ac.attempt_id
                JOIN competencies c ON c.code = ac.competency_code
                WHERE a.student_id = %s
                ORDER BY a.id DESC
            """, (student_id,))
            rows = cursor.fetchall()
        if not rows:
            return {}
        # The first block returned is the most recent attempt; later rows for the
        # same attempt must not overwrite it, so only unseen codes are kept.
        out = {}
        for row in rows:
            out.setdefault(row["competency_code"], {
                "name": row["name"],
                "score_percent": row["score_percent"],
                "correct": row["correct_count"],
                "total": row["question_count"],
            })
        return out



student_bp.add_url_rule("/assessment", view_func=AssessmentView.as_view("assessment"))
student_bp.add_url_rule("/assessment/start", view_func=StartAssessmentView.as_view("start_assessment"))
student_bp.add_url_rule("/assessment/submit", view_func=SubmitAssessmentView.as_view("submit_assessment"))
student_bp.add_url_rule("/assessment/results", view_func=AssessmentResultsView.as_view("assessment_results"))
