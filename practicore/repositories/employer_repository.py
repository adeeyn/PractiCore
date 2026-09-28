from ..database import Database
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

    def update_profile(self, employer_id, user_id, company_name, company_email, logo_text,
                       industry, location, about, required_skills, contact_name,
                       contact_position, website, company_size, is_hiring):
        """Saves the company profile and keeps the login account's email in step."""
        with Database.cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE employers
                SET company_name = %s, company_logo_text = %s, industry = %s, location = %s,
                    about = %s, required_skills = %s, contact_name = %s, contact_position = %s,
                    website = %s, company_size = %s, is_hiring = %s
                WHERE id = %s
            """, (company_name, logo_text, industry, location, about, required_skills,
                  contact_name, contact_position, website, company_size, is_hiring, employer_id))

            # Employers log in with their email, so a stale login email would lock them out
            if user_id:
                UserRepository.update_email(cursor, user_id, company_email)

    def create_with_account(self, email, password_hash, company_name, location, logo_text,
                            industry=None, about=None, required_skills=None, contact_name=None,
                            contact_position=None, website=None, company_size=None, is_hiring=1):
        """Creates the login account and a new company in one transaction."""
        with Database.cursor(commit=True) as cursor:
            user_id = UserRepository.insert(cursor, email, None, password_hash, "employer")
            cursor.execute("""
                INSERT INTO employers
                    (user_id, company_name, company_logo_text, industry, location, about,
                     required_skills, contact_name, contact_position, website, company_size, is_hiring)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, company_name, logo_text, industry, location, about, required_skills,
                  contact_name, contact_position, website, company_size, is_hiring))

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
