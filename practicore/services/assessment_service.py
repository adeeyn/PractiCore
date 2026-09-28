import random

from flask import current_app

from ..repositories import QuestionRepository
from .skill_taxonomy import SkillTaxonomy


class AssessmentService:
    """Builds randomized assessments and grades submissions per job domain."""

    FALLBACK_QUESTION_LIMIT = 90

    # Bands are (minimum percent, label). Ordered strongest first, so the first
    # match wins. The previous two-tier version labelled a 10% score
    # "Intermediate / Competent", which is not a defensible reading of a score.
    COMPETENCY_BANDS = (
        (85, "Advanced / Job-Ready"),
        (70, "Proficient"),
        (50, "Developing"),
        (30, "Foundational"),
        (0, "Below Foundational"),
    )

    @classmethod
    def competency_level_for(cls, overall_percent):
        """Maps an overall percentage onto a competency band."""
        for threshold, label in cls.COMPETENCY_BANDS:
            if overall_percent >= threshold:
                return label
        return cls.COMPETENCY_BANDS[-1][1]

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
        """Which of the 6 job categories an item is scored under.

        The research bank stores the track code in `course_track` (DEV, NET, ...)
        and the finer sub-domain in `category` ("Programming", "Networking", ...).
        The track code is authoritative; `category` is only a fallback for older
        rows that predate the research bank.
        """
        track = question.get("course_track") or question.get("track_code") or question.get("track") or ""
        role = question.get("target_role") or question.get("job_title") or ""
        if not track:
            track = question.get("category") or ""
        return SkillTaxonomy.map_to_domain(track, role)

    @staticmethod
    def time_limit_for(question):
        """Seconds allowed for a question, based on its difficulty."""
        limits = current_app.config["QUESTION_TIME_LIMITS"]
        return limits.get(question.get("difficulty"), limits["medium"])

    @staticmethod
    def _domains_for_skills(student_skills):
        """The job categories a student's resume skills map onto.

        Used to send extra (resume-triggered) questions to domains the student
        claims experience in, without abandoning the other domains.
        """
        domains = set()
        for skill in student_skills or set():
            domain = SkillTaxonomy.map_skills_to_category([skill])
            domains.add(domain)
        return domains

    def build(self, student_skills=None):
        """Picks core questions per domain, then adds resume-triggered questions.

        Every domain gets `CORE_QUESTIONS_PER_DOMAIN` questions so a student who
        never mentions Networking is still measured on it. Domains matching the
        student's resume skills then get up to `RESUME_QUESTIONS_PER_SKILL` extra
        questions per matched skill, capped by `MAX_QUESTIONS_PER_DOMAIN`.

        Returns (shuffled_questions, grouped_questions, question_domain_map).
        """
        per_domain = current_app.config["QUESTIONS_PER_DOMAIN"]
        core = current_app.config["CORE_QUESTIONS_PER_DOMAIN"]
        per_skill = current_app.config["RESUME_QUESTIONS_PER_SKILL"]
        cap = current_app.config["MAX_QUESTIONS_PER_DOMAIN"]
        # Honour the cap even if the legacy QUESTIONS_PER_DOMAIN is set higher.
        per_domain = min(per_domain, cap)
        # Core must never exceed what a single domain can supply.
        core = min(core, per_domain)

        buckets = {domain: [] for domain in SkillTaxonomy.categories()}
        for question in self.questions.all():
            question["time_limit"] = self.time_limit_for(question)
            buckets[self._question_domain(question)].append(question)

        # How many resume-triggered questions each domain earns, from the skills
        # the resume actually named.
        extra_allowance = {
            domain: 0 for domain in buckets
        }
        for domain in self._domains_for_skills(student_skills):
            extra_allowance[domain] += per_skill

        selected, grouped, domain_map = [], {}, {}
        for domain, question_list in buckets.items():
            random.shuffle(question_list)
            target = min(core + extra_allowance[domain], cap, len(question_list))
            chosen = question_list[:target]
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

        overall = round((total_correct / total_questions) * 100) if total_questions else 0
        competency_level = self.competency_level_for(overall)

        return {
            "overall_percentage": overall,
            "total_correct": total_correct,
            "total_questions": total_questions,
            "competency_level": competency_level,
            "category_breakdown": breakdown,
        }
