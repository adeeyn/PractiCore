import mysql.connector

from ..database import Database


class AssessmentRepository:
    """All SQL touching the assessment_domain_scores and assessment_attempts tables.

    The per-domain breakdown used to live only in the Flask session, so it was
    lost on logout and no ranking model had per-domain features to score on.
    """

    @staticmethod
    def save_results(student_id, results, breakdown):
        """Stores one attempt plus its per-domain breakdown in a single transaction.

        `results` is the dict AssessmentService.grade() returns; `breakdown` is
        its "category_breakdown" section.
        """
        if not student_id:
            return False
        try:
            with Database.cursor(commit=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO assessment_attempts
                        (student_id, overall_percentage, total_correct,
                         total_questions, competency_level)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        student_id,
                        results.get("overall_percentage", 0),
                        results.get("total_correct", 0),
                        results.get("total_questions", 0),
                        results.get("competency_level"),
                    ),
                )
                for domain, stats in (breakdown or {}).items():
                    cursor.execute(
                        """
                        INSERT INTO assessment_domain_scores
                            (student_id, domain, correct, total, score_percent, track_code)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            correct = VALUES(correct),
                            total = VALUES(total),
                            score_percent = VALUES(score_percent),
                            track_code = VALUES(track_code)
                        """,
                        (
                            student_id,
                            domain,
                            stats.get("correct", 0),
                            stats.get("total", 0),
                            stats.get("score_percent", 0),
                            stats.get("track"),
                        ),
                    )
            return True
        except mysql.connector.Error:
            # Migration 006 not applied yet: the attempt is still readable
            # through students.assessment_score, so never break submission.
            return False

    @staticmethod
    def for_student(student_id):
        """{domain: score_percent} for the student's latest breakdown, or {}."""
        if not student_id:
            return {}
        try:
            with Database.cursor() as cursor:
                cursor.execute(
                    "SELECT domain, score_percent FROM assessment_domain_scores WHERE student_id = %s",
                    (student_id,),
                )
                return {row["domain"]: row["score_percent"] for row in cursor.fetchall()}
        except mysql.connector.Error:
            return {}

    @staticmethod
    def latest_percentage(student_id):
        """Most recent overall percentage from history, or None if unavailable."""
        if not student_id:
            return None
        try:
            with Database.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT overall_percentage FROM assessment_attempts
                    WHERE student_id = %s
                    ORDER BY taken_at DESC, id DESC LIMIT 1
                    """,
                    (student_id,),
                )
                row = cursor.fetchone()
                return row["overall_percentage"] if row else None
        except mysql.connector.Error:
            return None

    @staticmethod
    def count_for_student(student_id):
        """Completed attempts for the dashboard's Completed Assessments card."""
        if not student_id:
            return 0
        try:
            with Database.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS total FROM assessment_attempts WHERE student_id = %s",
                    (student_id,),
                )
                row = cursor.fetchone()
                return row["total"] if row else 0
        except DatabaseError:
            # Migration 006 not applied yet: the students row still carries the score.
            return 0

    @staticmethod
    def recent_for_student(student_id, limit=3):
        """Latest attempts as raw rows for the dashboard activity feed."""
        if not student_id:
            return []
        try:
            with Database.cursor() as cursor:
                cursor.execute("""
                    SELECT overall_percentage, competency_level, taken_at
                    FROM assessment_attempts
                    WHERE student_id = %s
                    ORDER BY taken_at DESC, id DESC
                    LIMIT %s
                """, (student_id, limit))
                return cursor.fetchall()
        except DatabaseError:
            return []
