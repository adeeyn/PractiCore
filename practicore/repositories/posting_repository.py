from ..database import Database, DatabaseError, upsert_sql


class PostingRepository:
    """All SQL touching internship postings and their required skills."""

    def all_with_skills(self):
        """Returns every posting (newest first) with a `skills` list attached."""
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT
                    p.id,
                    p.title,
                    p.description,
                    p.is_remote,
                    p.posted_date,
                    e.company_name,
                    e.location
                FROM internship_postings p
                JOIN employers e ON p.employer_id = e.id
                ORDER BY p.posted_date DESC
            """)
            postings = cursor.fetchall()

            for posting in postings:
                cursor.execute(
                    "SELECT skill_name FROM posting_skills WHERE posting_id = %s",
                    (posting["id"],),
                )
                posting["skills"] = [row["skill_name"] for row in cursor.fetchall()]

            return postings

    # ---------- Employer-side queries ----------

    def for_employer(self, employer_id):
        """The employer's own postings (newest first) with a `skills` list attached."""
        if not employer_id:
            return []

        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT id, title, department, description, is_remote,
                       positions_available, posted_date
                FROM internship_postings
                WHERE employer_id = %s
                ORDER BY posted_date DESC, id DESC
            """, (employer_id,))
            postings = cursor.fetchall()

            for posting in postings:
                cursor.execute(
                    "SELECT skill_name FROM posting_skills WHERE posting_id = %s",
                    (posting["id"],),
                )
                posting["skills"] = [row["skill_name"] for row in cursor.fetchall()]

            return postings

    def find_by_employer_and_title(self, employer_id, title):
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM internship_postings WHERE employer_id = %s AND title = %s LIMIT 1",
                (employer_id, title),
            )
            return cursor.fetchone()

    def find_with_skills(self, posting_id):
        """One posting with a `skills` list, or None. Used to score an application."""
        if not posting_id:
            return None

        with Database.cursor() as cursor:
            cursor.execute("SELECT * FROM internship_postings WHERE id = %s", (posting_id,))
            posting = cursor.fetchone()
            if not posting:
                return None

            cursor.execute(
                "SELECT skill_name FROM posting_skills WHERE posting_id = %s", (posting_id,)
            )
            posting["skills"] = [row["skill_name"] for row in cursor.fetchall()]
            return posting

    def count_for_employer(self, employer_id):
        if not employer_id:
            return 0

        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM internship_postings WHERE employer_id = %s",
                (employer_id,),
            )
            row = cursor.fetchone()
            return row["total"] if row else 0

    def create_with_skills(self, employer_id, title, department, description,
                           is_remote, positions_available, skills):
        """Inserts the posting and its required skills in one transaction."""
        with Database.cursor(commit=True) as cursor:
            cursor.execute("""
                INSERT INTO internship_postings
                    (employer_id, title, department, description, is_remote, positions_available)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (employer_id, title, department, description, is_remote, positions_available))
            posting_id = cursor.lastrowid
            self._insert_skills(cursor, posting_id, skills)
            return posting_id

    def replace_skills(self, posting_id, skills):
        """Replaces a posting's required skills with the given list."""
        with Database.cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM posting_skills WHERE posting_id = %s", (posting_id,))
            self._insert_skills(cursor, posting_id, skills)

    def update_details(self, posting_id, department, description, is_remote, positions_available):
        with Database.cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE internship_postings
                SET department = %s, description = %s, is_remote = %s, positions_available = %s
                WHERE id = %s
            """, (department, description, is_remote, positions_available, posting_id))

    @staticmethod
    def _insert_skills(cursor, posting_id, skills):
        for skill in skills:
            cursor.execute(
                "INSERT INTO posting_skills (posting_id, skill_name) VALUES (%s, %s)",
                (posting_id, skill),
            )
