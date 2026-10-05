from ..database import Database, DatabaseError, upsert_sql


class QuestionRepository:
    """All SQL touching the `assessment_questions` table."""

    def all(self):
        with Database.cursor() as cursor:
            cursor.execute("SELECT * FROM assessment_questions")
            return cursor.fetchall()

    def by_ids(self, ids):
        if not ids:
            return []
        placeholders = ",".join(["%s"] * len(ids))
        with Database.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM assessment_questions WHERE id IN ({placeholders})",
                tuple(ids),
            )
            return cursor.fetchall()

    def first(self, limit):
        with Database.cursor() as cursor:
            cursor.execute("SELECT * FROM assessment_questions LIMIT %s", (limit,))
            return cursor.fetchall()
