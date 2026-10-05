import os

from ..ml.features import FEATURE_NAMES, FEATURE_SCHEMA_VERSION, build_features
from .recommendation_service import RecommendationService
from .skill_taxonomy import SkillTaxonomy

FALLBACK_ALGORITHM_LABEL = (
    "Weighted match scoring (assessment is the primary evidence; resume only "
    "corroborates it) - ML model not loaded"
)


class MatchingService:
    """Scores a student against one internship posting.

    This is the single scorer behind every match score in PractiCore: the student
    dashboard, the recommendation page, the Apply button and the employer's
    candidate ranking all call it, so a student always sees the same number the
    employer does.

    It prefers a trained Random Forest model and degrades to the weighted
    content-based scorer when the artifact is missing, the feature schema has
    drifted, or scikit-learn is not installed. `algorithm_label()` is what the
    employer UI prints, so the claim on screen always matches the code that ran.
    """

    def __init__(self, model=None, model_path=None, meta=None):
        self.model = model
        self.model_path = model_path
        self.meta = meta or {}
        self._load_error = None

    @classmethod
    def load(cls, model_path, enabled=True):
        """Loads the artifact, returning a ready service or a fallback one.

        Never raises: a missing or broken model is a configuration state, not a
        crash. The reason is kept in `_load_error` for the CLI and the UI.
        """
        service = cls(model_path=model_path)
        if not enabled:
            service._load_error = "ranking model disabled by RANKING_MODEL_ENABLED"
            return service

        try:
            import joblib  # imported lazily so the app boots without it
        except ImportError as exc:
            service._load_error = f"scikit-learn/joblib not installed ({exc})"
            return service

        if not model_path or not os.path.exists(model_path):
            service._load_error = f"model artifact not found at {model_path!r}"
            return service

        try:
            payload = joblib.load(model_path)
        except Exception as exc:  # corrupt/incompatible artifact
            service._load_error = f"could not load model artifact ({exc})"
            return service

        # A model trained against an older feature layout is worse than none.
        if isinstance(payload, dict):
            if list(payload.get("feature_names") or FEATURE_NAMES) != list(FEATURE_NAMES):
                service._load_error = "model was trained on a different feature schema"
                return service
            schema = payload.get("schema_version")
            if schema is not None and schema != FEATURE_SCHEMA_VERSION:
                service._load_error = "model feature schema version does not match the code"
                return service
            service.model = payload.get("model")
            service.meta = payload.get("meta", {})
        else:
            service.model = payload
            service.meta = {"schema_version": FEATURE_SCHEMA_VERSION}

        if service.model is None:
            service._load_error = "model artifact contained no estimator"
        return service

    # ---------- Scoring ----------

    def score(self, student, posting_skills, assessment_percentage=None):
        """Match score 0-100 for one student/posting pair.

        `student` is a mapping with `skills` and optionally `domain_scores`;
        `assessment_percentage` is passed separately because the call sites read
        it from students.assessment_score / total_questions.
        """
        student = self._normalize_student(student, assessment_percentage)

        if self.model is not None:
            try:
                row = build_features(student, posting_skills)
                probability = self.model.predict_proba([row])[0][1]
                return max(0, min(100, int(round(probability * 100))))
            except Exception as exc:
                # A scoring failure must never take down a page: fall through to
                # the heuristic and record why.
                self._load_error = f"model scoring failed, using fallback ({exc})"
                self.model = None

        return self.fallback_score(student, posting_skills)

    def score_components(self, student, posting_skills, assessment_percentage=None):
        """The combined match score plus the two separated percentages behind it.

        `match_score` is the single number PractiCore ranks, stores and sorts by,
        so ordering is unchanged by reporting the halves. The two components are
        returned alongside it because one percentage on its own says nothing about
        *why* an applicant scored what they did: 68% can mean a strong assessment
        against a thin resume, or the exact reverse, and those two applicants
        should not be presented identically.

        When a trained model is loaded the combined score comes from the model,
        but the components stay the deterministic, explainable inputs, so the UI
        can always show how the number was reached.
        """
        student = self._normalize_student(student, assessment_percentage)

        breakdown = RecommendationService.match_breakdown(
            posting_skills,
            student["skills"],
            student.get("assessment_overall", 0),
            domain_scores=student.get("domain_scores") or {},
        )

        return {
            "match_score": self.score(student, posting_skills),
            "resume_match_percent": breakdown["resume_match_percent"],
            "assessment_match_percent": breakdown["assessment_match_percent"],
            "assessment_overall": breakdown["assessment_overall"],
            "assessment_weight": breakdown["assessment_weight"],
            "resume_weight": breakdown["resume_weight"],
            "matched_count": breakdown["matched_count"],
            "required_count": breakdown["required_count"],
            "matched_skills": breakdown["matched_skills"],
            "missing_skills": breakdown["missing_skills"],
        }

    @staticmethod
    def _normalize_student(student, assessment_percentage=None):
        """Fills in the defaults the scorer relies on, without mutating the caller.

        `student["skills"]` reaches this from both directions: the routes pass an
        already-parsed set from SkillTaxonomy.parse_skill_string, while the
        seeder passes a raw comma-separated string. Both shapes are normalised
        here, once, so `score` and `score_components` can never disagree about
        what a student actually has.
        """
        student = dict(student or {})

        if assessment_percentage is not None:
            student["assessment_overall"] = assessment_percentage
        student.setdefault("assessment_overall", 0)
        student.setdefault("domain_scores", {})

        skills = student.get("skills")
        if isinstance(skills, str):
            student["skills"] = SkillTaxonomy.parse_skill_string(skills)
        else:
            student["skills"] = {str(s).strip().lower() for s in (skills or []) if str(s).strip()}

        return student

    @staticmethod
    def fallback_score(student, posting_skills):
        """The Phase 0 heuristic: 50% assessment + 50% resume skill overlap.

        `student["skills"]` reaches this from both directions: the routes pass an
        already-parsed set from SkillTaxonomy.parse_skill_string, while the
        seeder passes a raw comma-separated string. Normalise both, and only
        ever call .split() on something that is genuinely a string.
        """
        skills = student.get("skills")
        if isinstance(skills, str):
            skills = SkillTaxonomy.parse_skill_string(skills)
        else:
            skills = {str(s).strip().lower() for s in (skills or []) if str(s).strip()}

        return RecommendationService.combined_match_score(
            posting_skills,
            skills,
            student.get("assessment_overall", 0),
            domain_scores=student.get("domain_scores") or {},
        )

    # ---------- Transparency helpers ----------

    @property
    def uses_model(self):
        return self.model is not None

    def algorithm_label(self):
        """Human-readable name of the algorithm that produced the score."""
        if not self.uses_model:
            return FALLBACK_ALGORITHM_LABEL

        label = "Random Forest ranking model"
        if self.meta.get("label_source") == "synthetic":
            label += " (trained on SYNTHETIC heuristic labels - prototype only)"
        trained_at = self.meta.get("trained_at")
        if trained_at:
            label += f" - {trained_at}"
        return label

    def status_line(self):
        """One-liner for the CLI and the employer footer, including any reason."""
        if self.uses_model:
            accuracy = self.meta.get("accuracy")
            suffix = f" (validation accuracy {accuracy:.1%})" if isinstance(accuracy, float) else ""
            return self.algorithm_label() + suffix
        return FALLBACK_ALGORITHM_LABEL
