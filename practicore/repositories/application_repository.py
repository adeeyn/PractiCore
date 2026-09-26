import mysql.connector

from ..database import Database


class ApplicationRepository:
    """All SQL touching the `applications` table."""

    def count_for_student(self, student_id):
        if not student_id:
            return 0
        try:
            with Database.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS total FROM applications WHERE student_id = %s",
                    (student_id,),
                )
                result = cursor.fetchone()
                return result["total"] if result else 0
        except mysql.connector.Error:
            # Fallback if applications table hasn't been created yet
            return 0
