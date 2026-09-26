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

    def create_with_account(self, email, password_hash, company_name, location, logo_text):
        """Creates the login account and a new company in one transaction."""
        with Database.cursor(commit=True) as cursor:
            user_id = UserRepository.insert(cursor, email, None, password_hash, "employer")
            cursor.execute(
                "INSERT INTO employers (user_id, company_name, company_logo_text, location) VALUES (%s, %s, %s, %s)",
                (user_id, company_name, logo_text, location),
            )

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
