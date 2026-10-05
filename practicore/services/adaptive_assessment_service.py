"""Builds and grades the adaptive, competency-based assessment.

This replaces the legacy per-job-domain builder in AssessmentService. The
difference that matters: questions are selected per COMPETENCY, where the
competency set is assembled from the core list, the student's resume, and the
target internship, and each competency draws from one randomly chosen parallel
form rather than from a flat domain bucket.

The legacy AssessmentService is deliberately left in place. Other pages still
read students.assessment_score for an overall summary, and deleting it would
break them for no gain.
"""
import random

from flask import current_app

from ..repositories import CompetencyRepository
from .assessment_selection import choose_forms, select_competencies
from .assessment_service import AssessmentService


class AdaptiveAssessmentService:
    """Assembles, serves and grades one adaptive attempt."""

    def __init__(self, repository=None):
        self.repo = repository or CompetencyRepository()

    # ---------- Building ----------

    def build(self, student_id, resume_skills=None, posting=None, rng=None):
        """Assembles the assessment for one student against one posting.

        `posting` is {'id':.., 'skills':[...], 'title':.., 'description':..} or
        None for a general assessment.

        Returns the questions, the chosen forms, the metadata explaining why
        each competency was included, and the shortfall report.
        """
        rng = rng or random
        posting = posting or {}
        posting_id = posting.get("id")

        selected = select_competencies(
            resume_skills=resume_skills or [],
            posting_skills=posting.get("skills") or [],
            posting_text="%s %s" % (posting.get("title") or "", posting.get("description") or ""),
            posting_id=posting_id,
        )

        sets_by_competency = self.repo.competencies_with_forms()
        exposure = self.repo.exposure_for_student(student_id)

        # Only competencies that actually have questions can be served.
        codes = [e["code"] for e in selected if sets_by_competency.get(e["code"])]
        forms, shortfall = choose_forms(codes, sets_by_competency, exposure, rng)

        # A competency selected but with no questions must still be visible in
        # the explanation, or the student silently loses an assessment section.
        for entry in selected:
            if entry["code"] not in forms:
                shortfall.setdefault(entry["code"], "no questions published yet")

        questions_by_set = self.repo.questions_for_sets(
            [f["id"] for f in forms.values()]
        )

        meta_by_code = {e["code"]: e for e in selected}
        per_competency, ordered = {}, []
        for code in codes:
            form = forms.get(code)
            if not form:
                continue
            questions = list(questions_by_set.get(form["id"]) or [])
            if not questions:
                shortfall[code] = "form has no questions"
                continue
            rng.shuffle(questions)   # item order within the form
            for q in questions:
                q["competency"] = code
                q["time_limit"] = AssessmentService.time_limit_for(q)
                ordered.append(q)
            per_competency[code] = {
                "name": meta_by_code[code]["name"],
                "is_core": meta_by_code[code]["is_core"],
                "sources": meta_by_code[code]["sources"],
                "triggered_by": meta_by_code[code]["triggered_by"],
                "set_id": form["id"],
                "set_code": form["set_code"],
                "question_ids": [q["id"] for q in questions],
            }

        rng.shuffle(ordered)   # do not present sections in pool order

        return {
            "questions": ordered,
            "per_competency": per_competency,
            "competency_map": {str(q["id"]): q["competency"] for q in ordered},
            "shortfall": shortfall,
            "selected": selected,
            "posting_id": posting_id,
        }

    # ---------- Grading ----------

    def grade(self, answers, competency_map, per_competency, questions_by_id):
        """Marks the submission; returns overall results and per-competency stats.

        A competency with no submitted items is omitted rather than scored 0:
        an unattempted section is not the same fact as a failed one.
        """
        bypass = current_app.config["ASSESSMENT_GRADING_BYPASS"]
        stats = {}
        total_correct = 0
        total_questions = 0
        # Per-item outcome, so the attempt can store which questions were served,
        # what was answered and whether it was right (attempt_questions).
        per_question = {}

        for q_id_str, code in (competency_map or {}).items():
            question = questions_by_id.get(int(q_id_str))
            if not question:
                continue
            meta = per_competency.get(code) or {}
            entry = stats.setdefault(code, {
                "correct": 0, "total": 0,
                "name": meta.get("name", code),
                "is_core": meta.get("is_core", False),
                "set_id": meta.get("set_id"),
            })
            entry["total"] += 1
            total_questions += 1
            correct = bool(bypass or self._is_correct(question, answers))
            per_question[int(q_id_str)] = {
                "correct": correct,
                "competency": code,
                "answered": bool(self._selected_answer(question, answers)),
            }
            if correct:
                entry["correct"] += 1
                total_correct += 1

        for entry in stats.values():
            entry["score_percent"] = (
                round((entry["correct"] / entry["total"]) * 100) if entry["total"] else 0
            )

        overall = round((total_correct / total_questions) * 100) if total_questions else 0
        return {
            "overall_percentage": overall,
            "total_correct": total_correct,
            "total_questions": total_questions,
            "competency_level": AssessmentService.competency_level_for(overall),
            "competency_breakdown": stats,
            "per_question": per_question,
            "answers": answers or {},
        }

    @staticmethod
    def _selected_answer(question, answers):
        """The student's raw submission for one question, or ""."""
        q_id = str(question["id"])
        return answers.get("q_%s" % q_id) or answers.get(q_id) or ""

    @staticmethod
    def _is_correct(question, answers):
        q_id = str(question["id"])
        selected = answers.get("q_%s" % q_id) or answers.get(q_id) or ""
        correct = (question.get("correct_option") or question.get("correct_answer")
                   or question.get("answer") or "")
        return bool(selected) and str(selected).strip().upper() == str(correct).strip().upper()

