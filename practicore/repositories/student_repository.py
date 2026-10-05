from ..database import Database, DatabaseError, upsert_sql
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

    def all_for_seeding(self):
        """Every student with the fields the seeder scores applications with."""
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT id, name, email, skills, assessment_score, total_questions
                FROM students
                ORDER BY id
            """)
            return cursor.fetchall()

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
                SELECT id, name, skills, assessment_score, total_questions, competency_level
                FROM students
                WHERE username = %s
            """, (username,))
            return cursor.fetchone()

    def get_resume_details(self, username):
        with Database.cursor() as cursor:
            # s.id is needed to read the parsed career sections back out of
            # student_resumes; without it the resume page cannot load.
            cursor.execute("""
                SELECT s.id, s.name, s.email, s.phone, s.skills,
                       r.filename AS resume_filename
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
        """The summary columns the dashboards and the assessment page read.

        `id` is selected because the assessment page needs it to load the
        student's competency profile. It used to be omitted, and a caller
        reaching for it got a KeyError that took the whole page down.
        """
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT id, assessment_score, total_questions, competency_level "
                "FROM students WHERE username = %s",
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

    def update_avatar(self, student_id, avatar_path):
        """Points the student at their new photo (path is relative to static/)."""
        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                "UPDATE students SET avatar_path = %s WHERE id = %s", (avatar_path, student_id)
            )

    def update_profile(self, student_id, user_id, name, email, phone, year_level, course):
        """Saves the profile fields and keeps the login account's email in step."""
        with Database.cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE students
                SET name = %s, email = %s, phone = %s, year_level = %s, course = %s
                WHERE id = %s
            """, (name, email, phone, year_level, course, student_id))

            # Users log in with their email, so a stale login email would lock them out
            if user_id:
                UserRepository.update_email(cursor, user_id, email)
