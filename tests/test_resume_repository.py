"""ResumeRepository.get_sections tests, including the migration-007-not-applied case.

Fakes Database.cursor so no MySQL is needed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from practicore.repositories import resume_repository as rr_mod
from practicore.repositories.resume_repository import ResumeRepository


class FakeCursor:
    def __init__(self, row=None, error=None, calls=None):
        self._row = row
        self._error = error
        self._calls = calls if calls is not None else []
        self.closed = False

    def execute(self, query, params=None):
        self._calls.append(query)
        if self._error and "student_resumes" in query and "SELECT education" in query:
            raise self._error
        if self._error and "SET education" in query:
            raise self._error
        return self

    def fetchone(self):
        return self._row

    def close(self):
        self.closed = True


def _install(monkey_row=None, monkey_error=None, calls=None):
    """Points Database.cursor at a fake that returns monkey_row or raises."""
    import contextlib

    @contextlib.contextmanager
    def fake_cursor(dictionary=True, commit=False):
        yield FakeCursor(row=monkey_row, error=monkey_error, calls=calls)

    original = rr_mod.Database.cursor
    rr_mod.Database.cursor = staticmethod(fake_cursor)
    return original


def _restore(original):
    rr_mod.Database.cursor = original


class TestGetSections:
    def test_returns_empty_lists_without_a_student_id(self):
        original = _install()
        try:
            result = ResumeRepository().get_sections(None)
        finally:
            _restore(original)
        assert result == {key: [] for key in ResumeRepository.SECTION_COLUMNS}

    def test_splits_stored_text_into_lines(self):
        row = {
            "education": "BSIT\nTSU 2024",
            "certifications": None,
            "experience": "Intern at ABC",
            "projects": "",
        }
        original = _install(monkey_row=row)
        try:
            result = ResumeRepository().get_sections(7)
        finally:
            _restore(original)
        assert result["education"] == ["BSIT", "TSU 2024"]
        assert result["certifications"] == []
        assert result["experience"] == ["Intern at ABC"]
        assert result["projects"] == []

    def test_missing_columns_do_not_raise(self):
        """Migration 007 not applied: the SELECT raises, and we return empties."""
        import mysql.connector

        # A real driver error, not a bare Exception: get_sections catches
        # mysql.connector.Error specifically.
        original = _install(
            monkey_error=mysql.connector.Error(msg="Unknown column 'education' in 'field list'")
        )
        try:
            result = ResumeRepository().get_sections(7)
        finally:
            _restore(original)
        assert result == {key: [] for key in ResumeRepository.SECTION_COLUMNS}

    def test_always_returns_all_four_keys(self):
        original = _install(monkey_row={})
        try:
            result = ResumeRepository().get_sections(1)
        finally:
            _restore(original)
        for key in ("education", "certifications", "experience", "projects"):
            assert key in result


class TestResumePageIdHandling:
    """Regression cover for KeyError: 'id' on /student/resume.

    UploadResumeView.get() reads the student's id to load the parsed career
    sections. get_resume_details() did not SELECT s.id, so the page raised
    KeyError for every logged-in student.
    """

    def test_get_resume_details_selects_the_id_column(self):
        """The query must include s.id, or the route cannot find the student."""
        import re
        from pathlib import Path

        source = Path(rr_mod.__file__).with_name("student_repository.py").read_text(encoding="utf-8")
        # Pull out just the get_resume_details body.
        body = source.split("def get_resume_details", 1)[1].split("def ", 1)[0]
        assert re.search(r"SELECT\s+s\.id\b", body), "get_resume_details must SELECT s.id"

    def test_missing_id_degrades_to_empty_sections(self):
        """A row without an id must not raise; the page just shows no sections."""
        original = _install()
        try:
            row_without_id = {"name": "Juan", "skills": "Python"}  # no "id" key
            result = ResumeRepository().get_sections(row_without_id.get("id"))
        finally:
            _restore(original)
        assert result == {key: [] for key in ResumeRepository.SECTION_COLUMNS}


class TestAsText:
    def test_list_is_joined_with_newlines(self):
        assert ResumeRepository._as_text(["a", "b"]) == "a\nb"

    def test_none_becomes_none(self):
        assert ResumeRepository._as_text(None) is None

    def test_empty_list_becomes_none(self):
        assert ResumeRepository._as_text([]) is None

    def test_blank_string_becomes_none(self):
        assert ResumeRepository._as_text("   ") is None

    def test_string_passes_through(self):
        assert ResumeRepository._as_text("a\nb") == "a\nb"


class TestAsTextViaClass:
    def test_still_callable_on_the_class(self):
        assert ResumeRepository._as_text(["x"]) == "x"
