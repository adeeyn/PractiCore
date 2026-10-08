"""View Resume tests for the employer Applications page.

The employer could review an applicant's status, skills and notes but had no
way to open the resume the student actually uploaded. These tests cover the
pieces behind the new "View Resume" button on /employer/applicants/manage:
the /employer/applicants/<id>/resume stream and the has_resume flag that
decides whether the button renders.

Everything database-facing is stubbed; what runs for real is the routing,
the role guard, the per-employer authorisation and the template output.
"""
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from practicore import create_app
from practicore.repositories import ResumeRepository

EMPLOYER = {
    "id": 3,
    "user_id": 3,
    "company_name": "InnovaTech Solutions Inc.",
}

# Shaped like ApplicationRepository._shape() output: every key the
# applicant_management template and the _macros.html helpers read.
APPLICANT = {
    "id": 42,
    "student_id": 7,
    "posting_id": 5,
    "name": "Juan Dela Cruz",
    "email": "juan@example.com",
    "skills": "Python, SQL",
    "assessment_score": 80,
    "position": "Web Developer Intern",
    "status": "Pending",
    "match_score": 75,
    "resume_match_score": 70,
    "assessment_match_score": 80,
    "notes": "",
    "applied_on": "Jan 01, 2026",
    "initials": "JD",
    "logo_text": "JD",
}

RESUME = {
    "filename": "juan_resume.pdf",
    "mime_type": "application/pdf",
    "file_data": b"%PDF-1.4 fake resume bytes",
}

RESUME_URL = "/employer/applicants/42/resume"


def _signed_in_client(role="employer"):
    """A test client whose session claims `role` (same shape as the app's)."""
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["loggedin"] = True
        sess["role"] = role
        sess["user_id"] = EMPLOYER["user_id"]
        sess["email"] = "hr@innovatech.test"
    return client


def _patches(**overrides):
    """Context managers for the applicants route module.

    Keys: employer (logged-in company), application (find_for_employer result),
    applicants (for_employer result), has_resume (has_file result).
    """
    from practicore.routes.employer import applicants as applicants_mod

    return [
        mock.patch.object(applicants_mod, "current_employer",
                          return_value=dict(overrides.get("employer") or EMPLOYER)),
        mock.patch.object(applicants_mod.ApplicationRepository, "find_for_employer",
                          return_value=overrides.get("application", dict(APPLICANT))),
        mock.patch.object(applicants_mod.ApplicationRepository, "for_employer",
                          return_value=[dict(APPLICANT)]),
        mock.patch.object(applicants_mod.ResumeRepository, "has_file",
                          return_value=overrides.get("has_resume", True)),
    ]


class TestResumeAuthorisation:
    """Only the employer that owns the application may open the resume."""

    def test_an_anonymous_request_is_sent_to_login(self):
        app = create_app()
        app.config["TESTING"] = True
        response = app.test_client().get(RESUME_URL)
        assert response.status_code in (301, 302)
        assert "/login" in response.headers["Location"]

    def test_a_student_cannot_open_the_resume(self):
        response = _signed_in_client("student").get(RESUME_URL)
        assert response.status_code in (301, 302)
        # Sent to their own dashboard, never served the file.
        assert not response.headers["Location"].endswith("/resume")

    def test_another_employers_application_is_not_served(self):
        client = _signed_in_client()
        employer_patch, find_patch, _, _ = _patches(application=None)
        with employer_patch, find_patch, \
                mock.patch.object(ResumeRepository, "get_file") as get_file:
            response = client.get(RESUME_URL)

        assert response.status_code == 404
        assert not get_file.called, "a foreign application must not reach the resume lookup"


class TestResumeStreaming:
    """The stored BLOB is served back with its original type and filename."""

    def test_the_stored_file_is_streamed_to_the_employer(self):
        client = _signed_in_client()
        employer_patch, find_patch, _, _ = _patches()
        with employer_patch, find_patch, \
                mock.patch.object(ResumeRepository, "get_file",
                                  return_value=dict(RESUME)) as get_file:
            response = client.get(RESUME_URL)

        assert response.status_code == 200
        assert response.data == RESUME["file_data"]
        assert response.headers["Content-Type"].startswith("application/pdf")
        assert RESUME["filename"] in str(response.headers)
        get_file.assert_called_once_with(APPLICANT["student_id"])

    def test_a_student_without_a_resume_gets_a_404(self):
        client = _signed_in_client()
        employer_patch, find_patch, _, _ = _patches()
        with employer_patch, find_patch, \
                mock.patch.object(ResumeRepository, "get_file", return_value=None):
            response = client.get(RESUME_URL)

        assert response.status_code == 404


class TestViewResumeButton:
    """The Applications page offers the button only when a resume exists."""

    def _page(self, has_resume):
        client = _signed_in_client()
        employer_patch, find_patch, list_patch, has_patch = _patches(
            has_resume=has_resume
        )
        with employer_patch, find_patch, list_patch, has_patch:
            return client.get("/employer/applicants/manage/42").get_data(as_text=True)

    def test_the_button_is_rendered_when_a_resume_exists(self):
        body = self._page(True)
        assert "View Resume" in body
        assert RESUME_URL in body
        assert 'target="_blank"' in body

    def test_no_button_when_the_student_never_uploaded_one(self):
        body = self._page(False)
        assert "View Resume" not in body
        assert "has not uploaded a resume" in body
