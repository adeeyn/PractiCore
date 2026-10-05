from ..database import Database, DatabaseError, upsert_sql


class ResumeRepository:
    """All SQL touching the `student_resumes` table (resume files stored as BLOBs)."""

    SECTION_COLUMNS = ("education", "certifications", "experience", "projects")

    def save(self, student_id, filename, mime_type, data, skills_str, sections=None):
        """Stores (or replaces) the resume, its extracted skills and its sections.

        One transaction, so a re-upload never leaves a half-updated profile. The
        career sections are optional: a caller that does not pass them simply
        leaves those columns empty.

        If migration 007 has not been applied yet, the resume and its skills are
        still saved and the sections are skipped. Failing the whole upload over a
        cosmetic column would be the wrong trade.
        """
        sections = sections or {}
        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                upsert_sql(
                    "student_resumes",
                    ["student_id", "filename", "mime_type", "file_size", "file_data"],
                    ["student_id"],
                    ["filename", "mime_type", "file_size", "file_data"],
                ),
                (student_id, filename, mime_type, len(data), data),
            )
            cursor.execute("UPDATE students SET skills = %s WHERE id = %s", (skills_str, student_id))

        # Written after the upsert so a re-upload also refreshes the sections.
        # Kept in its own transaction so a missing column cannot roll back the
        # resume itself.
        try:
            with Database.cursor(commit=True) as cursor:
                for column in self.SECTION_COLUMNS:
                    cursor.execute(
                        f"UPDATE student_resumes SET {column} = %s WHERE student_id = %s",
                        (self._as_text(sections.get(column)), student_id),
                    )
        except DatabaseError:
            # Migration 007 not applied: skills are saved, sections are not.
            pass

    @staticmethod
    def _as_text(items):
        """Accepts either a list of lines or an already-joined string."""
        if items is None:
            return None
        if isinstance(items, str):
            return items.strip() or None
        return "\n".join(str(i).strip() for i in items if str(i).strip()) or None

    def get_sections(self, student_id):
        """The stored career sections as {key: [lines]}; empty lists if none saved.

        Returns empty lists (never raises) when migration 007 has not been applied
        yet, so the resume page still loads on a database that predates it.
        """
        empty = {key: [] for key in self.SECTION_COLUMNS}
        if not student_id:
            return empty
        try:
            with Database.cursor() as cursor:
                cursor.execute(
                    f"SELECT {', '.join(self.SECTION_COLUMNS)} FROM student_resumes WHERE student_id = %s",
                    (student_id,),
                )
                row = cursor.fetchone() or {}
        except DatabaseError:
            # Migration 007 not applied yet.
            return empty
        return {
            key: [line for line in (row.get(key) or "").splitlines() if line.strip()]
            for key in self.SECTION_COLUMNS
        }

    def get_file(self, student_id):
        """Returns filename, mime_type and file_data, or None."""
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT filename, mime_type, file_data FROM student_resumes WHERE student_id = %s",
                (student_id,),
            )
            return cursor.fetchone()

    def has_file(self, student_id):
        """True when a resume is stored for this student (the BLOB is not read).

        Lets a page decide whether to offer a "View Resume" button without
        pulling a multi-megabyte file into memory first.
        """
        if not student_id:
            return False
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM student_resumes WHERE student_id = %s",
                (student_id,),
            )
            return cursor.fetchone() is not None
