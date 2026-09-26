import os

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
    RESUME_MIME_TYPES = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    RESUME_MAX_BYTES = 5 * 1024 * 1024  # 5 MB; MySQL max_allowed_packet must be larger
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # hard limit for any request

    # MySQL Configuration
    DB_CONFIG = {
        "host": "127.0.0.1",
        "user": "root",
        "password": "",
        "database": "practicore",
    }

    # Assessment settings
    QUESTIONS_PER_DOMAIN = 15
    # Seconds allowed per question, by assessment_questions.difficulty
    QUESTION_TIME_LIMITS = {"easy": 30, "medium": 45, "hard": 60}
    # TESTING BYPASS: marks every answer correct. Set to False when going live.
    ASSESSMENT_GRADING_BYPASS = True
