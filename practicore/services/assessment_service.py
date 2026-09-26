import random

from flask import current_app

from ..repositories import QuestionRepository
from .skill_taxonomy import SkillTaxonomy


class AssessmentService:
    """Builds randomized assessments and grades submissions per job domain."""

    FALLBACK_QUESTION_LIMIT = 90

    def __init__(self, questions=None):
        self.questions = questions or QuestionRepository()

    @staticmethod
    def score_percentage(student):
        """Overall % from a student row with assessment_score / total_questions."""
        if student and student.get("total_questions") and student["total_questions"] > 0:
            return round((student["assessment_score"] / student["total_questions"]) * 100)
        return 0

    @staticmethod
    def _question_domain(question):
        track = question.get("course_track") or question.get("track_code") or question.get("track") or ""
        role = question.get("target_role") or question.get("job_title") or ""
        return SkillTaxonomy.map_to_domain(track, role)

    @staticmethod
    def time_limit_for(question):
        """Seconds allowed for a question, based on its difficulty."""
        limits = current_app.config["QUESTION_TIME_LIMITS"]
        return limits.get(question.get("difficulty"), limits["medium"])

    def build(self):
        """Picks N random questions per domain, each tagged with its `time_limit`.

        Returns (shuffled_questions, grouped_questions, question_domain_map).
        """
        per_domain = current_app.config["QUESTIONS_PER_DOMAIN"]
        buckets = {domain: [] for domain in SkillTaxonomy.categories()}

        for question in self.questions.all():
            question["time_limit"] = self.time_limit_for(question)
            buckets[self._question_domain(question)].append(question)

        selected, grouped, domain_map = [], {}, {}
        for domain, question_list in buckets.items():
            random.shuffle(question_list)
            chosen = question_list[:per_domain]
            grouped[domain] = chosen
            for question in chosen:
                domain_map[str(question["id"])] = domain
                selected.append(question)

        random.shuffle(selected)
        return selected, grouped, domain_map

    def _load_submitted_questions(self, answers, active_map):
        # Parse submitted question IDs (handles "q_15" and "15" formats)
        submitted_ids = []
        for key in answers.keys():
            cleaned_id = str(key).replace("q_", "").strip()
            if cleaned_id.isdigit():
                submitted_ids.append(int(cleaned_id))

        if submitted_ids:
            return self.questions.by_ids(submitted_ids)
        if active_map:
            return self.questions.by_ids([int(k) for k in active_map if str(k).isdigit()])
        return self.questions.first(self.FALLBACK_QUESTION_LIMIT)

    @staticmethod
    def _is_correct(question, answers):
        q_id = str(question["id"])
        selected = answers.get(f"q_{q_id}") or answers.get(q_id) or ""
        correct = question.get("correct_option") or question.get("correct_answer") or question.get("answer") or ""
        return bool(selected) and str(selected).strip().upper() == str(correct).strip().upper()

    def grade(self, answers, active_map):
        """Grades the submission and returns the results dict stored in the session."""
        bypass = current_app.config["ASSESSMENT_GRADING_BYPASS"]
        breakdown = {
            domain: {"correct": 0, "total": 0, "track": code}
            for domain, code in SkillTaxonomy.DOMAIN_TRACK_CODES.items()
        }

        active_questions = self._load_submitted_questions(answers, active_map)
        total_correct = 0
        total_questions = len(active_questions)

        for question in active_questions:
            domain = active_map.get(str(question["id"])) or self._question_domain(question)
            if domain not in breakdown:
                continue

            breakdown[domain]["total"] += 1
            if bypass or self._is_correct(question, answers):
                breakdown[domain]["correct"] += 1
                total_correct += 1

        for stats in breakdown.values():
            stats["score_percent"] = round((stats["correct"] / stats["total"]) * 100) if stats["total"] > 0 else 0

        overall = round((total_correct / total_questions) * 100) if total_questions > 0 else 0
        competency_level = "Advanced / Job-Ready" if overall >= 85 else "Intermediate / Competent"

        return {
            "overall_percentage": overall,
            "total_correct": total_correct,
            "total_questions": total_questions,
            "competency_level": competency_level,
            "category_breakdown": breakdown,
        }
