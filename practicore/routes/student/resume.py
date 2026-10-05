import io

from flask import abort, current_app, jsonify, render_template, request, send_file, session
from flask.views import MethodView
from werkzeug.utils import secure_filename

from . import student_bp
from .context import current_student
from ...database import DatabaseError
from ...repositories import ResumeRepository, StudentRepository


class UploadResumeView(MethodView):
    def __init__(self):
        self.students = StudentRepository()
        self.resumes = ResumeRepository()
        self.parser = current_app.extensions["resume_parser"]

    @staticmethod
    def file_extension(filename):
        return filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    def get(self):
        # Fetch saved student resume details from Database
        student = self.students.get_resume_details(session.get("username"))

        saved_skills = []
        if student and student.get("skills"):
            saved_skills = [s.strip() for s in student["skills"].split(",") if s.strip()]

        # Career sections parsed out of the stored resume (migration 007).
        # student_id can be missing if the profile lookup failed, and get_sections
        # returns empty lists when there is no uploaded resume yet.
        student_id = student.get("id") if student else None
        sections = self.resumes.get_sections(student_id) if student_id else {}

        return render_template(
            "student/upload_resume.html",
            active_page="resume",
            student=student,
            skills=saved_skills,
            resume_sections=sections,
        )

    def post(self):
        if "resume" not in request.files:
            return jsonify({"error": "No file submitted"}), 400

        file = request.files["resume"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        mime_types = current_app.config["RESUME_MIME_TYPES"]
        extension = self.file_extension(file.filename)
        if extension not in mime_types:
            return jsonify({"error": "Invalid file extension"}), 400

        data = file.read()
        max_bytes = current_app.config["RESUME_MAX_BYTES"]
        if len(data) > max_bytes:
            return jsonify({"error": f"File is too large (max {max_bytes // (1024 * 1024)} MB)"}), 400

        student = current_student()
        if not student:
            return jsonify({"error": "Student profile not found"}), 404

        filename = secure_filename(file.filename)
        try:
            parsed_data = self.parser.parse(io.BytesIO(data), filename)
            self.resumes.save(
                student["id"],
                filename,
                mime_types[extension],
                data,
                ", ".join(parsed_data["skills"]),
                sections={key: parsed_data.get(key) for key in ResumeRepository.SECTION_COLUMNS},
            )
        except DatabaseError as e:
            # Postgres rejects an oversized bytea write outright; the 5 MB
            # app-level cap above normally stops this first.
            if getattr(e, "pgcode", "") in ("53400", "54000", "22001"):
                return jsonify({"error": "File is too large for the database."}), 500
            return jsonify({"error": str(e)}), 500
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        return jsonify({
            "status": "success",
            "filename": filename,
            "parsed_data": parsed_data,
        }), 200


class ResumeFileView(MethodView):
    """Streams the logged-in student's stored resume back to the browser."""

    def get(self):
        student = current_student()
        resume = ResumeRepository().get_file(student["id"]) if student else None
        if not resume:
            abort(404)

        return send_file(
            io.BytesIO(resume["file_data"]),
            mimetype=resume["mime_type"],
            download_name=resume["filename"],
            as_attachment=False,  # PDFs open in the browser; DOCX downloads
            max_age=0,
        )


student_bp.add_url_rule("/resume", view_func=UploadResumeView.as_view("resume"))
student_bp.add_url_rule("/resume/file", view_func=ResumeFileView.as_view("resume_file"))
