import os

from flask import current_app, jsonify, redirect, render_template, request, session, url_for
from flask.views import MethodView

from . import student_bp
from .context import current_student
from ...database import DatabaseError
from ...repositories import StudentRepository

# Query-string codes for the profile redirects (same idiom as auth.login's ?failed=1)
PROFILE_MESSAGES = {
    "missing": "Full name, email and course are required.",
    "email": "Please enter a valid email address.",
    "taken": "That email address is already used by another account.",
    "failed": "We could not save your changes. Please try again.",
}


class StudentProfileView(MethodView):
    """Shows the student's own details and saves the edit form."""

    template = "student/student_profile.html"

    def __init__(self):
        self.students = StudentRepository()

    def _render(self, message=None, message_type=None):
        return render_template(
            self.template,
            active_page="profile",
            message=message,
            message_type=message_type,
        )

    @staticmethod
    def valid_email(value):
        local, _, domain = value.partition("@")
        return bool(local and domain and "." in domain and " " not in value)

    def get(self):
        if request.args.get("saved") == "1":
            return self._render("Your profile has been updated.", "success")

        error = PROFILE_MESSAGES.get(request.args.get("error"))
        return self._render(error, "error" if error else None)

    def post(self):
        form = {key: request.form.get(key, "").strip() for key in
                ("fullname", "email", "phone", "year", "course")}
        form["email"] = form["email"].lower()

        if not (form["fullname"] and form["email"] and form["course"]):
            return redirect(url_for("student.profile", error="missing"))
        if not self.valid_email(form["email"]):
            return redirect(url_for("student.profile", error="email"))

        student = current_student()
        if not student:
            return redirect(url_for("student.profile", error="failed"))

        try:
            self.students.update_profile(
                student_id=student["id"],
                user_id=student["user_id"],
                name=form["fullname"],
                email=form["email"],
                phone=form["phone"],
                year_level=form["year"],
                course=form["course"],
            )
        except DatabaseError as err:
            # students.email and users.email both carry a UNIQUE index, so a
            # clash (Postgres 23505) means "taken"; anything else is "failed".
            if getattr(err, "pgcode", "") == "23505":
                return redirect(url_for("student.profile", error="taken"))
            return redirect(url_for("student.profile", error="failed"))

        # The login email changed with the profile, so keep the session truthful
        session["email"] = form["email"]
        return redirect(url_for("student.profile", saved=1))


class StudentAvatarView(MethodView):
    """Saves or replaces the logged-in student's profile photo."""

    def __init__(self):
        self.students = StudentRepository()

    @staticmethod
    def file_extension(filename):
        return filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    @staticmethod
    def remove_previous(avatar_path):
        """Deletes the photo this upload replaces, if it was a real upload."""
        if not avatar_path or not avatar_path.startswith("uploads/avatars/"):
            return

        try:
            os.remove(os.path.join(current_app.config["STATIC_FOLDER"], avatar_path))
        except OSError:
            pass  # Already gone; nothing to clean up

    def post(self):
        if "avatar" not in request.files:
            return jsonify({"error": "No file submitted"}), 400

        file = request.files["avatar"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        mime_types = current_app.config["AVATAR_MIME_TYPES"]
        extension = self.file_extension(file.filename)
        if extension not in mime_types:
            return jsonify({"error": "Invalid file extension"}), 400

        data = file.read()
        max_bytes = current_app.config["AVATAR_MAX_BYTES"]
        if len(data) > max_bytes:
            return jsonify({"error": f"File is too large (max {max_bytes // (1024 * 1024)} MB)"}), 400

        student = current_student()
        if not student:
            return jsonify({"error": "Student profile not found"}), 404

        # The bytes go to the database: the upload filesystem is read-only on
        # Vercel, and student_photos keeps them out of the students SELECT *.
        self.students.save_avatar(student["id"], data, mime_types[extension])
        # Clean up a photo from the old file-based storage, if there is one.
        self.remove_previous(student.get("avatar_path"))

        return jsonify({
            "status": "success",
            "avatar_path": "db",
            "avatar_url": url_for("media.avatar", student_id=student["id"]),
        }), 200


student_bp.add_url_rule("/profile", view_func=StudentProfileView.as_view("profile"))
student_bp.add_url_rule("/profile/avatar", view_func=StudentAvatarView.as_view("profile_avatar"))
