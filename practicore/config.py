import os

from .competency_scoring import STRENGTH_BANDS

PACKAGE_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.abspath(os.path.join(PACKAGE_DIR, os.pardir))


class Config:
    """Central application settings."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "nyek")

    # Only emails on this domain can self-register as students
    STUDENT_EMAIL_DOMAIN = "student.tsu.edu.ph"

    # templates/ and static/ are split per module: student/, employer/, admin/
    TEMPLATE_FOLDER = os.path.join(PACKAGE_DIR, "templates")
    STATIC_FOLDER = os.path.join(PACKAGE_DIR, "static")

    # Resume uploads (stored in the student_resumes table)
    # en_core_web_sm is small/fast; en_core_web_md adds real word vectors, which
    # lets SkillTaxonomy fall back to true semantic similarity, at the cost of a
    # large download and slower startup.
    SPACY_MODEL = os.environ.get("SPACY_MODEL", "en_core_web_sm")
    RESUME_MIME_TYPES = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    RESUME_MAX_BYTES = 5 * 1024 * 1024  # 5 MB; MySQL max_allowed_packet must be larger
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # hard limit for any request

    # Avatar uploads (written to static/uploads/avatars and served by Flask)
    AVATAR_MIME_TYPES = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    AVATAR_MAX_BYTES = 2 * 1024 * 1024  # 2 MB
    AVATAR_UPLOAD_DIR = os.path.join(STATIC_FOLDER, "uploads", "avatars")

    # Company logo uploads (written to static/uploads/logos and served by Flask).
    # Same image formats as the avatar above; kept as its own settings because a
    # logo is drawn much larger, so the byte budget is higher.
    LOGO_MIME_TYPES = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    LOGO_MAX_BYTES = 3 * 1024 * 1024  # 3 MB
    LOGO_UPLOAD_DIR = os.path.join(STATIC_FOLDER, "uploads", "logos")

    # MySQL Configuration
    DB_CONFIG = {
        "host": "127.0.0.1",
        "user": "root",
        "password": "",
        "database": "practicore",
    }

    # Assessment settings
    # Tuned for the 43-item research bank (6 job categories, DEV/DATA/SEC/TSM
    # have the most items, SYS/NET the fewest). build() clamps each domain to
    # what the bank actually holds, so these are upper bounds, not quotas.
    QUESTIONS_PER_DOMAIN = 8
    CORE_QUESTIONS_PER_DOMAIN = 5
    RESUME_QUESTIONS_PER_SKILL = 2
    MAX_QUESTIONS_PER_DOMAIN = 8

    # --- Master bank assessment (130 items, see services/master_selection.py) ---
    # The parallel-form builder can only ever serve 2 x (competencies) = 17-36
    # questions. The master bank holds 10 items per competency, which is what makes
    # a 40-50 question attempt possible.
    #
    # MASTER_BANK_ENABLED selects the master pool. It falls back to the legacy
    # parallel-form builder automatically when the master pool is empty, so a
    # database that has not been seeded with `flask --app app seed-master-bank`
    # keeps working exactly as before rather than serving an empty assessment.
    MASTER_BANK_ENABLED = True
    # Requested size. Clamped to MASTER_MIN..MASTER_MAX by the selection service.
    MASTER_TARGET_QUESTIONS = 45
    MASTER_MIN_QUESTIONS = 40
    MASTER_MAX_QUESTIONS = 50

    # --- Competency strength bands ---
    # The per-competency strength LEVEL shown next to a demonstrated score:
    # 0-59 Weak, 60-79 Moderate, 80-100 Strong. Ordered strongest first, so the
    # first match wins, and read through competency_scoring.strength_level_for
    # rather than repeated as literals in templates.
    #
    # Distinct from AssessmentService.COMPETENCY_BANDS above, which is the
    # OVERALL ladder for the results header, and from
    # CompetencyRepository.evidence_strength's 70/50 cut-offs, which grade how
    # well a RESUME CLAIM is corroborated. Those two are unchanged.
    #
    # A competency with no score gets NO band at all (strength_level_for returns
    # None), because "not measured" must never be rendered as a measured result.
    COMPETENCY_STRENGTH_BANDS = STRENGTH_BANDS

    # Seconds allowed per question, by assessment_questions.difficulty
    QUESTION_TIME_LIMITS = {"easy": 30, "medium": 45, "hard": 60}
    # TESTING BYPASS: marks every answer correct. Must stay False outside local
    # testing, otherwise every competency score is meaningless (100% for all).
    ASSESSMENT_GRADING_BYPASS = False

    # --- Match score weighting ---
    # The objective assessment is the primary evidence of capability, so it
    # carries most of the match score and the resume only corroborates it. A
    # 50/50 average let a missing resume keyword erase a strong assessment
    # result, which contradicts the research note that self-reported skills are
    # not proof. Weights must sum to 1.0.
    MATCH_ASSESSMENT_WEIGHT = 0.7
    MATCH_RESUME_WEIGHT = 0.3

    # --- Ranking model (Random Forest) ---
    # When the artifact is missing or scikit-learn is not installed, PractiCore
    # falls back to the weighted content-based scorer and says so in the UI.
    RANKING_MODEL_ENABLED = True
    RANKING_MODEL_PATH = os.path.join(PACKAGE_DIR, "models", "ranking_rf.joblib")
