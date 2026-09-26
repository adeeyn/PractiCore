from ..database import Database


class UserRepository:
    """All SQL touching the `users` table (login accounts for every role)."""

    def find_by_login(self, identifier):
        """Looks a user up by email or username."""
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE email = %s OR username = %s LIMIT 1",
                (identifier, identifier),
            )
            return cursor.fetchone()

    def exists(self, email, username=None):
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE email = %s OR (username IS NOT NULL AND username = %s)",
                (email, username),
            )
            return cursor.fetchone() is not None

    @staticmethod
    def insert(cursor, email, username, password_hash, role):
        """Inserts using the caller's cursor so it can share a transaction. Returns the new id."""
        cursor.execute(
            "INSERT INTO users (email, username, password_hash, role) VALUES (%s, %s, %s, %s)",
            (email, username, password_hash, role),
        )
        return cursor.lastrowid

    def create(self, email, username, password_hash, role):
        with Database.cursor(commit=True) as cursor:
            return self.insert(cursor, email, username, password_hash, role)
