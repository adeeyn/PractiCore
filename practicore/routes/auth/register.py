import mysql.connector
from flask import current_app, redirect, render_template, request, url_for
from flask.views import MethodView

from . import auth_bp
from ...repositories import StudentRepository, UserRepository
from ...services import AuthService


class StudentRegisterView(MethodView):
    """Self sign-up is for students only; employer accounts are created by an admin."""

    template = "auth/register.html"
    REQUIRED_FIELDS = ("name", "email", "username", "student_no", "course", "password", "confirm_password")

    def __init__(self):
        self.students = StudentRepository()
        self.users = UserRepository()

    def get(self):
        return render_template(self.template)

    @staticmethod
    def _read_form():
        form = request.form
        return {
            "name": form.get("name", "").strip(),
            "email": form.get("email", "").strip().lower(),
            "username": form.get("username", "").strip(),
            "student_no": form.get("studentNo", "").strip(),
            "phone": form.get("phone", "").strip(),
            "year_level": form.get("year_level", "4th Year").strip(),
            "course": form.get("course", "").strip(),
            "password": form.get("password", "").strip(),
            "confirm_password": form.get("confirmPassword", "").strip(),
        }

    def _error(self, message):
        return render_template(self.template, error=message)

    def post(self):
        data = self._read_form()

        if not all(data[field] for field in self.REQUIRED_FIELDS):
            return self._error("Please fill out all required fields.")
        if not AuthService.is_student_email(data["email"]):
            return self._error(f"Please use your school email (@{current_app.config['STUDENT_EMAIL_DOMAIN']}).")
        if data["password"] != data["confirm_password"]:
            return self._error("Passwords do not match.")

        try:
            if (self.users.exists(data["email"], data["username"])
                    or self.students.exists(data["student_no"], data["username"], data["email"])):
                return self._error("Student Number, Username, or Email already exists.")

            self.students.create(
                name=data["name"],
                email=data["email"],
                username=data["username"],
                student_no=data["student_no"],
                phone=data["phone"],
                year_level=data["year_level"],
                course=data["course"],
                password_hash=AuthService.hash_password(data["password"]),
            )
        except mysql.connector.Error as err:
            return self._error(f"Database error: {err}")

        return redirect(url_for("auth.login"))


auth_bp.add_url_rule("/register", view_func=StudentRegisterView.as_view("register"))
