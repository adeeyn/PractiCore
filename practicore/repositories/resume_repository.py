from ..database import Database


class ResumeRepository:
    """All SQL touching the `student_resumes` table (resume files stored as BLOBs)."""

    def save(self, student_id, filename, mime_type, data, skills_str):
        """Stores (or replaces) the student's resume and their extracted skills in one transaction."""
        with Database.cursor(commit=True) as cursor:
            cursor.execute("""
                INSERT INTO student_resumes (student_id, filename, mime_type, file_size, file_data)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    filename = VALUES(filename),
                    mime_type = VALUES(mime_type),
                    file_size = VALUES(file_size),
                    file_data = VALUES(file_data)
            """, (student_id, filename, mime_type, len(data), data))
            cursor.execute("UPDATE students SET skills = %s WHERE id = %s", (skills_str, student_id))

    def get_file(self, student_id):
        """Returns filename, mime_type and file_data, or None."""
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT filename, mime_type, file_data FROM student_resumes WHERE student_id = %s",
                (student_id,),
            )
            return cursor.fetchone()
