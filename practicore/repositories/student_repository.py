from ..database import Database
from .user_repository import UserRepository


class StudentRepository:
    """All SQL touching the `students` table."""

    def find_by_username(self, username):
        with Database.cursor() as cursor:
            cursor.execute("SELECT * FROM students WHERE username = %s", (username,))
            return cursor.fetchone()

    def find_by_user_id(self, user_id):
        with Database.cursor() as cursor:
            cursor.execute("SELECT * FROM students WHERE user_id = %s", (user_id,))
            return cursor.fetchone()

    def exists(self, student_no, username, email):
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM students WHERE student_no = %s OR username = %s OR email = %s",
                (student_no, username, email),
            )
            return cursor.fetchone() is not None

    def create(self, name, email, username, student_no, phone, year_level, course, password_hash):
        """Creates the login account and the student profile in one transaction."""
        with Database.cursor(commit=True) as cursor:
            user_id = UserRepository.insert(cursor, email, username, password_hash, "student")
            cursor.execute("""
                INSERT INTO students (user_id, name, email, username, student_no, phone, year_level, course)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, name, email, username, student_no, phone, year_level, course))

    def get_dashboard_profile(self, username):
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, skills, assessment_score, total_questions
                FROM students
                WHERE username = %s
            """, (username,))
            return cursor.fetchone()

    def get_resume_details(self, username):
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT s.name, s.email, s.phone, s.skills, r.filename AS resume_filename
                FROM students s
                LEFT JOIN student_resumes r ON r.student_id = s.id
                WHERE s.username = %s
            """, (username,))
            return cursor.fetchone()

    def get_skills(self, username):
        with Database.cursor() as cursor:
            cursor.execute("SELECT skills FROM students WHERE username = %s", (username,))
            row = cursor.fetchone()
            return row.get("skills") if row else None

    def get_assessment_stats(self, username):
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT assessment_score, total_questions, competency_level FROM students WHERE username = %s",
                (username,),
            )
            return cursor.fetchone()

    def update_assessment(self, username, score, total_questions, competency_level):
        with Database.cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE students
                SET assessment_score = %s, total_questions = %s, competency_level = %s
                WHERE username = %s
            """, (score, total_questions, competency_level, username))
