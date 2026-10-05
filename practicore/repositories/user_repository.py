from ..database import Database, DatabaseError, upsert_sql


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
            "INSERT INTO users (email, username, password_hash, role) VALUES (%s, %s, %s, %s) RETURNING id",
            (email, username, password_hash, role),
        )
        return cursor.lastrowid

    @staticmethod
    def update_email(cursor, user_id, email):
        """Updates the login email with the caller's cursor so it shares the transaction."""
        cursor.execute("UPDATE users SET email = %s WHERE id = %s", (email, user_id))

    def create(self, email, username, password_hash, role):
        with Database.cursor(commit=True) as cursor:
            return self.insert(cursor, email, username, password_hash, role)

    def email_for(self, user_id):
        """The login email of one account, used when refreshing seeded employers."""
        with Database.cursor() as cursor:
            cursor.execute("SELECT email FROM users WHERE id = %s", (user_id,))
            row = cursor.fetchone()
            return row["email"] if row else None

    def set_password(self, user_id, password_hash):
        """Replaces an account's password (used by the seeder to make demos log in)."""
        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                "UPDATE users SET password_hash = %s, is_active = 1 WHERE id = %s",
                (password_hash, user_id),
            )
