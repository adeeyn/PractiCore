from ..database import Database, DatabaseError, upsert_sql
from ..initials import initials_for
from .user_repository import UserRepository


class EmployerRepository:
    """All SQL touching the `employers` table."""

    def all_with_accounts(self):
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.company_name, e.company_logo_text, e.location, e.created_at,
                       u.email, u.is_active
                FROM employers e
                LEFT JOIN users u ON e.user_id = u.id
                ORDER BY e.company_name
            """)
            return cursor.fetchall()

    def without_account(self):
        with Database.cursor() as cursor:
            cursor.execute("SELECT id, company_name FROM employers WHERE user_id IS NULL ORDER BY company_name")
            return cursor.fetchall()

    def find_by_user_id(self, user_id):
        with Database.cursor() as cursor:
            cursor.execute("SELECT * FROM employers WHERE user_id = %s", (user_id,))
            return cursor.fetchone()

    def find_by_company_name(self, company_name):
        with Database.cursor() as cursor:
            cursor.execute("SELECT * FROM employers WHERE company_name = %s", (company_name,))
            return cursor.fetchone()

    def save_logo(self, employer_id, data, mime):
        """Stores the logo's bytes in employer_logos and flags logo_path.

        The flag becomes 'db' (templates use it to pick the media route); the
        bytes live in their own table so employers' SELECT * stays light.
        Passing data=None clears the logo, which sends the templates back to
        the company_logo_text initials.
        """
        with Database.cursor(commit=True) as cursor:
            if data is None:
                cursor.execute(
                    "DELETE FROM employer_logos WHERE employer_id = %s", (employer_id,))
            else:
                cursor.execute(
                    upsert_sql("employer_logos", ["employer_id", "mime", "data"],
                               ["employer_id"], ["mime", "data"]),
                    (employer_id, mime, data))
            cursor.execute(
                "UPDATE employers SET logo_path = %s WHERE id = %s",
                ("db" if data is not None else None, employer_id))

    def get_logo(self, employer_id):
        """The stored logo as {mime, data}, or None."""
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT mime, data FROM employer_logos WHERE employer_id = %s",
                (employer_id,))
            return cursor.fetchone()

    def update_profile(self, employer_id, user_id, company_name, company_email,
                       industry, location, about, required_skills, contact_name,
                       contact_position, website, company_size, is_hiring):
        """Saves the company profile and keeps the login account's email in step.

        The logo initials are derived from company_name here rather than accepted
        from the caller, so they can never disagree with the name they stand for
        and no caller has to remember to recompute them.
        """
        with Database.cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE employers
                SET company_name = %s, company_logo_text = %s, industry = %s, location = %s,
                    about = %s, required_skills = %s, contact_name = %s, contact_position = %s,
                    website = %s, company_size = %s, is_hiring = %s
                WHERE id = %s
            """, (company_name, initials_for(company_name), industry, location, about,
                  required_skills, contact_name, contact_position, website, company_size,
                  is_hiring, employer_id))

            # Employers log in with their email, so a stale login email would lock them out
            if user_id:
                UserRepository.update_email(cursor, user_id, company_email)

    def create_with_account(self, email, password_hash, company_name, location,
                            industry=None, about=None, required_skills=None, contact_name=None,
                            contact_position=None, website=None, company_size=None, is_hiring=1):
        """Creates the login account and a new company in one transaction.

        The logo initials come from company_name, like update_profile does.
        """
        with Database.cursor(commit=True) as cursor:
            user_id = UserRepository.insert(cursor, email, None, password_hash, "employer")
            cursor.execute("""
                INSERT INTO employers
                    (user_id, company_name, company_logo_text, industry, location, about,
                     required_skills, contact_name, contact_position, website, company_size, is_hiring)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, company_name, initials_for(company_name), industry, location, about,
                  required_skills, contact_name, contact_position, website, company_size,
                  is_hiring))

    def attach_to_user(self, employer_id, user_id):
        """Points an existing company at a login account that has no company yet."""
        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                "UPDATE employers SET user_id = %s WHERE id = %s AND user_id IS NULL",
                (user_id, employer_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("That company already has an account.")

    def attach_account(self, employer_id, email, password_hash):
        """Creates a login account for an existing company that has none yet."""
        with Database.cursor(commit=True) as cursor:
            user_id = UserRepository.insert(cursor, email, None, password_hash, "employer")
            cursor.execute(
                "UPDATE employers SET user_id = %s WHERE id = %s AND user_id IS NULL",
                (user_id, employer_id),
            )
            if cursor.rowcount == 0:
                raise ValueError("That company already has an account.")
