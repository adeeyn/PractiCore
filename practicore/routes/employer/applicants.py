import io

from flask import abort, redirect, render_template, request, send_file, url_for
from flask.views import MethodView

from . import employer_bp
from .context import current_employer
from ...repositories import ApplicationRepository, PostingRepository, ResumeRepository

# The screening pipeline, in the order a candidate moves through it
APPLICATION_STATUSES = ["Pending", "In Review", "Reviewed", "Shortlisted", "Scheduled", "Hired", "Rejected"]


class ApplicantsView(MethodView):
    """The employer's applicants, optionally narrowed to one posting."""

    def __init__(self):
        self.applications = ApplicationRepository()
        self.postings = PostingRepository()

    def get(self):
        employer = current_employer() or {}
        employer_id = employer.get("id")
        postings = self.postings.for_employer(employer_id)

        posting_id = request.args.get("posting", type=int)
        selected = next((p for p in postings if p["id"] == posting_id), None)
        applicants = self.applications.for_employer(
            employer_id, selected["id"] if selected else None
        )

        return render_template(
            "employer/applicants.html",
            active_page="applicants",
            postings=postings,
            selected_posting=selected,
            posting_title=selected["title"] if selected else "your internships",
            total_applicants=len(applicants),
            applicants=applicants,
            statuses=APPLICATION_STATUSES,
        )


class ApplicantManagementView(MethodView):
    """Reviews one applicant and saves the employer's status and notes."""

    def __init__(self):
        self.applications = ApplicationRepository()
        self.resumes = ResumeRepository()

    def get(self, application_id=None):
        employer = current_employer() or {}
        employer_id = employer.get("id")

        applicants = self.applications.for_employer(employer_id)
        selected = self.applications.find_for_employer(employer_id, application_id)
        if selected is None and applicants:
            selected = applicants[0]

        return render_template(
            "employer/applicant_management.html",
            active_page="management",
            applicants=applicants,
            selected=selected,
            statuses=APPLICATION_STATUSES,
            saved=request.args.get("saved") == "1",
            # Decides whether the "View Resume" button is offered; reads no BLOB.
            has_resume=bool(selected and self.resumes.has_file(selected.get("student_id"))),
        )

    def post(self, application_id):
        employer = current_employer() or {}
        employer_id = employer.get("id")

        # Only touch an application that belongs to this employer
        if not self.applications.find_for_employer(employer_id, application_id):
            return redirect(url_for("employer.applicant_management"))

        status = request.form.get("status", "Pending")
        if status not in APPLICATION_STATUSES:
            status = "Pending"

        self.applications.update_status_and_notes(
            application_id, status, request.form.get("notes", "").strip()
        )
        return redirect(url_for("employer.applicant_management", applicant=application_id, saved=1))


class ApplicantResumeView(MethodView):
    """Streams the applicant's stored resume to the employer that owns the application."""

    def __init__(self):
        self.applications = ApplicationRepository()
        self.resumes = ResumeRepository()

    def get(self, application_id):
        # find_for_employer only matches rows whose posting belongs to this
        # employer, so another company's application ends in a 404 here.
        employer = current_employer() or {}
        application = self.applications.find_for_employer(
            employer.get("id"), application_id
        )
        if application is None:
            abort(404)

        resume = self.resumes.get_file(application["student_id"])
        if not resume:
            abort(404)

        return send_file(
            io.BytesIO(resume["file_data"]),
            mimetype=resume["mime_type"],
            download_name=resume["filename"],
            as_attachment=False,  # PDFs open in the browser; DOCX downloads
            max_age=0,
        )


employer_bp.add_url_rule("/applicants", view_func=ApplicantsView.as_view("applicants"))
employer_bp.add_url_rule(
    "/applicants/manage", view_func=ApplicantManagementView.as_view("applicant_management")
)
employer_bp.add_url_rule(
    "/applicants/manage/<int:application_id>",
    view_func=ApplicantManagementView.as_view("applicant_management_detail"),
)
employer_bp.add_url_rule(
    "/applicants/<int:application_id>/resume",
    view_func=ApplicantResumeView.as_view("applicant_resume"),
)
