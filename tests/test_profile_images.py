"""Tests for profile images shown across modules.

Two features meet here:

* A student's uploaded profile photo (students.avatar_path) must appear on the
  employer side - applicant lists, ranking, the detail panel and the dashboard
  - falling back to the initials circle when the student never uploaded one.
* The company's uploaded logo (employers.logo_path) must appear on the student
  side - recommendation cards and My Applications - falling back to the
  derived initials badge.

The normalisation rule both sides share is "only paths under uploads/ are real
uploads" (the same guard student/_avatar.html has always used); it lives in
ApplicationRepository._shape and RecommendationService._logo_image and is
tested here without a database.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from practicore.repositories.application_repository import ApplicationRepository

TEMPLATES = Path(__file__).resolve().parent.parent / "practicore" / "templates"


def _row(**extra):
    """A shaped row as the employer queries produce it."""
    row = {
        "id": 7, "student_id": 2, "posting_id": 1,
        "name": "Juan Dela Cruz", "email": "juan@example.com",
        "skills": "python", "assessment_score": 80,
        "position": "IT Intern", "status": "Pending",
        "match_score": 74, "resume_match_score": None,
        "assessment_match_score": None, "notes": "",
        "applied_on": None,
    }
    row.update(extra)
    return row


class TestShapeNormalisesUploadedImages:
    """_shape is what every employer/student application query passes through."""

    def test_an_uploaded_photo_survives(self):
        row = ApplicationRepository._shape(_row(avatar_path="uploads/avatars/2_ab.png"))
        assert row["avatar_path"] == "uploads/avatars/2_ab.png"

    def test_no_photo_falls_back_to_the_initials_badge(self):
        for value in (None, "", "default.png"):
            row = ApplicationRepository._shape(_row(avatar_path=value))
            assert row["avatar_path"] is None, value
        # A query that does not select the column at all (legacy callers)
        row = ApplicationRepository._shape(_row())
        assert row["avatar_path"] is None

    def test_an_uploaded_company_logo_survives(self):
        row = ApplicationRepository._shape(
            _row(company_name="Tech Solution Inc.",
                 company_logo_path="uploads/logos/3_cd.png"))
        assert row["company_logo_path"] == "uploads/logos/3_cd.png"

    def test_no_company_logo_falls_back_to_initials(self):
        for value in (None, "", "default.png"):
            row = ApplicationRepository._shape(
                _row(company_name="Tech Solution Inc.", company_logo_path=value))
            assert row["company_logo_path"] is None, value
        row = ApplicationRepository._shape(_row(company_name="Tech Solution Inc."))
        assert row["company_logo_path"] is None

    def test_the_initials_fields_are_still_derived(self):
        row = ApplicationRepository._shape(
            _row(company_name="Tech Solution Inc.",
                 avatar_path="uploads/avatars/2_ab.png"))
        assert row["initials"] == "JD"
        assert row["logo_text"] == "TS"


def _jinja_env():
    """A bare Jinja environment pointed at the real template folder, with just
    enough of Flask's globals for the macros to render."""
    import jinja2

    env = jinja2.Environment(loader=jinja2.FileSystemLoader(str(TEMPLATES)))
    env.globals["url_for"] = lambda endpoint, filename="": f"/static/{filename}"
    return env


class TestAvatarMacro:
    """The one avatar helper every employer applicant view renders through
    (applicant list, ranking, detail panel)."""

    @staticmethod
    def _render(applicant):
        template = _jinja_env().from_string(
            "{% import 'employer/_macros.html' as ui %}{{ ui.avatar(applicant, size) }}"
        )
        return template.render(applicant=applicant, size="")

    def test_a_student_with_a_photo_gets_the_photo(self):
        html = self._render(ApplicationRepository._shape(
            _row(avatar_path="uploads/avatars/2_ab.png")))
        assert '<img src="/static/uploads/avatars/2_ab.png"' in html
        assert 'alt="Juan Dela Cruz"' in html
        assert ">JD<" not in html, "the initials should be replaced by the photo"

    def test_a_student_without_a_photo_gets_the_initials(self):
        html = self._render(ApplicationRepository._shape(_row(avatar_path=None)))
        assert "<img" not in html
        assert ">JD<" in html


class TestTemplatesCompile:
    """Every template touched by the profile-image feature must parse."""

    def test_the_edited_templates_compile(self):
        env = _jinja_env()
        for name in ("employer/_macros.html", "employer/dashboard.html",
                     "employer/_header.html", "student/recommendation.html",
                     "student/application.html"):
            env.get_template(name)


class TestTemplatesWireTheImage:
    """Source-level guards, the same style test_derived_initials.py uses."""

    @staticmethod
    def _source(*parts):
        return TEMPLATES.joinpath(*parts).read_text(encoding="utf-8")

    def test_employer_applicant_views_read_avatar_path(self):
        for parts in (("employer", "_macros.html"), ("employer", "dashboard.html")):
            assert "applicant.avatar_path" in self._source(*parts), parts

    def test_student_cards_read_the_company_logo(self):
        assert "rec.logo_image" in self._source("student", "recommendation.html")
        assert "company_logo_path" in self._source("student", "application.html")

    def test_the_employer_header_reads_its_own_logo(self):
        assert "employer.logo_path" in self._source("employer", "_header.html")
