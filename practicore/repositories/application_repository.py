from ..database import Database, DatabaseError, upsert_sql
from ..initials import initials_for

# Read model for the employer pages. The column aliases match the keys the
# employer templates and the _macros.html helpers expect.
APPLICANT_COLUMNS = """
    a.id               AS id,
    a.student_id       AS student_id,
    a.posting_id       AS posting_id,
    s.name             AS name,
    s.email            AS email,
    s.skills           AS skills,
    s.assessment_score AS assessment_score,
    p.title            AS position,
    a.status           AS status,
    a.match_score      AS match_score,
    a.resume_match_score     AS resume_match_score,
    a.assessment_match_score AS assessment_match_score,
    a.employer_notes   AS notes,
    a.applied_on       AS applied_on
"""


class ApplicationRepository:
    """All SQL touching the `applications` table."""

    # ---------- Student side ----------

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
        except DatabaseError:
            # Fallback if applications table hasn't been created yet
            return 0

    def count_for_student_since(self, student_id, since):
        """Applications filed at or after `since` (the dashboard's "N new this week")."""
        if not student_id:
            return 0
        try:
            with Database.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS total FROM applications "
                    "WHERE student_id = %s AND applied_on >= %s",
                    (student_id, since),
                )
                result = cursor.fetchone()
                return result["total"] if result else 0
        except DatabaseError:
            return 0

    def recent_for_student(self, student_id, limit=3):
        """Latest applications as raw rows for the dashboard activity feed.

        Unlike `for_student` this keeps `applied_on` as a datetime, because the
        dashboard renders relative labels ("2 days ago") from it.
        """
        if not student_id:
            return []
        try:
            with Database.cursor() as cursor:
                cursor.execute("""
                    SELECT p.title AS position, a.applied_on
                    FROM applications a
                    JOIN internship_postings p ON a.posting_id = p.id
                    WHERE a.student_id = %s
                    ORDER BY a.applied_on DESC
                    LIMIT %s
                """, (student_id, limit))
                return cursor.fetchall()
        except DatabaseError:
            return []

    def for_student(self, student_id):
        if not student_id:
            return []

        with Database.cursor() as cursor:
            # company_name is enough: the initials are derived from it, so the
            # stored company_logo_text column is not needed here.
            cursor.execute(f"""
                SELECT {APPLICANT_COLUMNS}, e.company_name
                FROM applications a
                JOIN students s ON a.student_id = s.id
                JOIN internship_postings p ON a.posting_id = p.id
                JOIN employers e ON p.employer_id = e.id
                WHERE a.student_id = %s
                ORDER BY a.applied_on DESC
            """, (student_id,))
            return [self._shape(row) for row in cursor.fetchall()]

    def applied_posting_ids(self, student_id):
        """The posting ids this student already applied to, for the Apply button state."""
        if not student_id:
            return set()

        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT posting_id FROM applications WHERE student_id = %s", (student_id,)
            )
            return {row["posting_id"] for row in cursor.fetchall()}

    def apply(self, student_id, posting_id, match_score,
              resume_match_score=None, assessment_match_score=None):
        """Records an application. Returns False when the student already applied.

        The two component percentages are stored beside the combined score so the
        employer pages can show a resume percentage and an assessment percentage
        instead of one opaque figure (migration 011).
        """
        if not student_id or not posting_id:
            return False

        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                "SELECT id FROM applications WHERE student_id = %s AND posting_id = %s",
                (student_id, posting_id),
            )
            if cursor.fetchone():
                return False

            cursor.execute("""
                INSERT INTO applications
                    (student_id, posting_id, status, match_score,
                     resume_match_score, assessment_match_score)
                VALUES (%s, %s, 'Pending', %s, %s, %s)
            """, (student_id, posting_id, match_score,
                  resume_match_score, assessment_match_score))
            return True

    def withdraw(self, application_id, student_id):
        """Removes one of the student's own applications. Returns True when deleted."""
        if not application_id or not student_id:
            return False

        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                "DELETE FROM applications WHERE id = %s AND student_id = %s",
                (application_id, student_id),
            )
            return cursor.rowcount > 0

    # ---------- Employer side ----------

    def for_employer(self, employer_id, posting_id=None):
        """Applicants for one of the employer's postings, or across all of them."""
        if not employer_id:
            return []

        query = f"""
            SELECT {APPLICANT_COLUMNS}
            FROM applications a
            JOIN students s ON a.student_id = s.id
            JOIN internship_postings p ON a.posting_id = p.id
            WHERE p.employer_id = %s
        """
        params = [employer_id]

        if posting_id:
            query += " AND p.id = %s"
            params.append(posting_id)

        query += " ORDER BY a.applied_on DESC, a.id DESC"

        with Database.cursor() as cursor:
            cursor.execute(query, tuple(params))
            return [self._shape(row) for row in cursor.fetchall()]

    def find_for_employer(self, employer_id, application_id):
        """One applicant, but only when it belongs to this employer."""
        if not employer_id or not application_id:
            return None

        with Database.cursor() as cursor:
            cursor.execute(f"""
                SELECT {APPLICANT_COLUMNS}
                FROM applications a
                JOIN students s ON a.student_id = s.id
                JOIN internship_postings p ON a.posting_id = p.id
                WHERE p.employer_id = %s AND a.id = %s
                LIMIT 1
            """, (employer_id, application_id))
            row = cursor.fetchone()
            return self._shape(row) if row else None

    def counts_for_employer(self, employer_id):
        """Dashboard totals: applicants, the per-status counts and the average score."""
        keys = ("total", "shortlisted", "hired", "pending", "avg_match")
        if not employer_id:
            return dict.fromkeys(keys, 0)

        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT
                    COUNT(*)                                              AS total,
                    COALESCE(SUM(CASE WHEN a.status = 'Shortlisted' THEN 1 ELSE 0 END), 0) AS shortlisted,
                    COALESCE(SUM(CASE WHEN a.status = 'Hired' THEN 1 ELSE 0 END), 0)      AS hired,
                    COALESCE(SUM(CASE WHEN a.status = 'Pending' THEN 1 ELSE 0 END), 0)     AS pending,
                    COALESCE(ROUND(AVG(a.match_score)), 0)     AS avg_match
                FROM applications a
                JOIN internship_postings p ON a.posting_id = p.id
                WHERE p.employer_id = %s
            """, (employer_id,))
            row = cursor.fetchone() or {}

        return {key: int(row.get(key) or 0) for key in keys}

    def update_status_and_notes(self, application_id, status, notes):
        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                "UPDATE applications SET status = %s, employer_notes = %s WHERE id = %s",
                (status, notes, application_id),
            )

    def create_if_missing(self, student_id, posting_id, status, match_score, notes=None,
                          resume_match_score=None, assessment_match_score=None):
        """Seeds an application without breaking the unique (student, posting) key.

        Re-running the seeder refreshes the score and its two components, so the
        demo data never keeps a split that disagrees with the combined number.
        """
        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                upsert_sql(
                    "applications",
                    ["student_id", "posting_id", "status", "match_score",
                     "employer_notes", "resume_match_score", "assessment_match_score"],
                    ["student_id", "posting_id"],
                    ["status", "match_score", "employer_notes",
                     "resume_match_score", "assessment_match_score"],
                ),
                (student_id, posting_id, status, match_score, notes,
                 resume_match_score, assessment_match_score),
            )

    def set_match_components(self, application_id, resume_match_score, assessment_match_score):
        """Backfills the two component percentages on one existing application.

        Used by `flask --app app backfill-match-components` for the rows written
        before migration 011 added the columns.
        """
        with Database.cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE applications
                   SET resume_match_score = %s, assessment_match_score = %s
                 WHERE id = %s
            """, (resume_match_score, assessment_match_score, application_id))

    def for_training(self):
        """Every application with the fields the ranking trainer needs.

        One row per application, carrying the student's resume skills, their
        assessment totals and the posting's required skills, so the trainer can
        rebuild exactly the feature vector the live scorer builds.
        """
        try:
            with Database.cursor() as cursor:
                cursor.execute("""
                    SELECT
                        a.id               AS id,
                        a.student_id       AS student_id,
                        a.posting_id       AS posting_id,
                        a.status           AS status,
                        a.match_score      AS match_score,
                        s.skills           AS skills,
                        s.assessment_score AS assessment_score,
                        s.total_questions  AS total_questions
                    FROM applications a
                    JOIN students s ON a.student_id = s.id
                """)
                applications = cursor.fetchall()

                # Required skills live in a second table, so this stays a plain
                # per-posting lookup instead of another join fan-out.
                for application in applications:
                    cursor.execute(
                        "SELECT skill_name FROM posting_skills WHERE posting_id = %s",
                        (application["posting_id"],),
                    )
                    application["skills_required"] = [
                        row["skill_name"] for row in cursor.fetchall()
                    ]

                return applications
        except DatabaseError:
            return []

    # ---------- Helpers ----------

    @staticmethod
    def _shape(row):
        """Adds the display fields the employer templates read."""
        row["initials"] = initials_for(row["name"])
        # The company badge on the student's My Applications card, derived the
        # same way as every other initials badge (migration 014).
        row["logo_text"] = initials_for(row.get("company_name"))
        applied_on = row.get("applied_on")
        row["applied_on"] = applied_on.strftime("%b %d, %Y") if applied_on else "-"

        # Normalise the two split percentages to int-or-None. A row written before
        # migration 011 has NULL here, and NULL must stay distinguishable from 0:
        # the templates hide the split when it is missing instead of implying the
        # applicant scored nothing.
        for key in ("resume_match_score", "assessment_match_score"):
            value = row.get(key)
            row[key] = int(value) if value is not None else None

        return row
