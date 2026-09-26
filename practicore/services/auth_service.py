from flask import current_app, session
from werkzeug.security import check_password_hash, generate_password_hash

from ..repositories import EmployerRepository, StudentRepository, UserRepository


class AuthService:
    """Shared login for every role: password checks, session setup, role routing."""

    STUDENT = "student"
    EMPLOYER = "employer"
    ADMIN = "admin"

    # Where each role lands after logging in
    DASHBOARDS = {
        STUDENT: "student.dashboard",
        EMPLOYER: "employer.dashboard",
        ADMIN: "admin.dashboard",
    }

    HASH_PREFIXES = ("pbkdf2:", "scrypt:")

    def __init__(self):
        self.users = UserRepository()

    # --- Passwords ---

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    @classmethod
    def verify_password(cls, stored_password, password):
        if not stored_password:
            return False
        if stored_password.startswith(cls.HASH_PREFIXES):
            return check_password_hash(stored_password, password)
        # Legacy plain-text passwords
        return stored_password == password

    # --- Email rules ---

    @staticmethod
    def is_student_email(email):
        domain = current_app.config["STUDENT_EMAIL_DOMAIN"]
        return email.lower().endswith("@" + domain)

    # --- Login / session ---

    def authenticate(self, identifier, password):
        """Returns the user row if the email/username and password match an active account."""
        user = self.users.find_by_login(identifier)
        if user and user["is_active"] and self.verify_password(user["password_hash"], password):
            return user
        return None

    def login(self, user):
        session.clear()
        session["loggedin"] = True
        session["user_id"] = user["id"]
        session["role"] = user["role"]
        session["email"] = user["email"]
        session["username"] = user["username"]

        if user["role"] == self.STUDENT:
            student = StudentRepository().find_by_user_id(user["id"])
            if student:
                session["username"] = student["username"]
                session["studentNo"] = student["student_no"]
        elif user["role"] == self.EMPLOYER:
            employer = EmployerRepository().find_by_user_id(user["id"])
            if employer:
                session["employer_id"] = employer["id"]

    @staticmethod
    def logout():
        session.clear()

    @classmethod
    def dashboard_endpoint(cls, role):
        return cls.DASHBOARDS.get(role, "auth.login")
