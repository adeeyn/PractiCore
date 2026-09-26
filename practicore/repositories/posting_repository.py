from ..database import Database


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
                    e.company_logo_text,
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
