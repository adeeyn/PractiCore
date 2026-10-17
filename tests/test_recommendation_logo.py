"""Tests for the company badge on the recommendation card.

Regression: /student/recommendation raised KeyError: 'company_logo_text'.
That column was dropped by migration 014; the card derives its initials from
company_name instead, and additionally renders employers.logo_path (the
uploaded logo) when the posting row carries a real uploads/ path.

The badge rule itself is pure logic and is tested without Flask. The two
page-level tests do build real cards, so they push their own application
context: match_breakdown reads MATCH_ASSESSMENT_WEIGHT from current_app.config,
and this repo has no conftest.py providing an `app` fixture.
"""
from contextlib import contextmanager

from practicore.initials import initials_for
from practicore.services.recommendation_service import RecommendationService


@contextmanager
def app_context():
    """A minimal Flask app carrying only the match weights the scorer reads."""
    from flask import Flask

    from practicore.config import Config

    app = Flask(__name__)
    app.config.from_object(Config)
    with app.app_context():
        yield


def _posting(company_name, **extra):
    """A row shaped exactly like PostingRepository.all_with_skills() produces.

    Deliberately does NOT include company_logo_text: that absence is the bug.
    """
    row = {
        "id": 1, "title": "Developer Intern", "description": "d",
        "is_remote": 0, "posted_date": None,
        "company_name": company_name, "location": "Quezon City",
        "skills": ["java", "sql"],
    }
    row.update(extra)
    return row


class TestLogoFor:
    def test_it_does_not_index_a_column_the_row_does_not_carry(self):
        """THE regression test: this used to be posting['company_logo_text']."""
        posting = _posting("DevPro Lab")
        assert "company_logo_text" not in posting
        assert RecommendationService._logo_for(posting) == "DL"

    def test_a_missing_company_name_is_a_fallback_not_an_exception(self):
        assert RecommendationService._logo_for({}) == "IT"
        assert RecommendationService._logo_for({"company_name": ""}) == "IT"
        assert RecommendationService._logo_for({"company_name": None}) == "IT"

    def test_it_agrees_with_the_shared_initials_rule(self):
        for name in ("Tech Solution Inc.", "InnovaTech Solutions Inc.",
                     "Nexus Cyber Solutions", "DataPulse Analytics",
                     "AgileDev Studios", "CloudScale Networks",
                     "CoreIT Service Management"):
            assert RecommendationService._logo_for(
                _posting(name)) == initials_for(name), name

    def test_a_renamed_company_shows_initials_matching_its_new_name(self):
        """Deriving beats the stored column, which would still be stale."""
        assert RecommendationService._logo_for(_posting("Globex")) == "G"

    def test_it_survives_extra_keys(self):
        posting = _posting("Tech Solution Inc.", logo_path="uploads/logos/a.png")
        assert RecommendationService._logo_for(posting) == "TS"


class TestLogoImage:
    """The uploaded logo half of the badge: image when there is one, else None
    so the card falls back to the initials from _logo_for."""

    def test_an_uploaded_logo_is_returned_verbatim(self):
        path = "uploads/logos/3_ab12cd34.png"
        assert RecommendationService._logo_image({"logo_path": path}) == path

    def test_no_logo_means_the_card_falls_back_to_initials(self):
        for row in ({}, {"logo_path": None}, {"logo_path": ""}):
            assert RecommendationService._logo_image(row) is None

    def test_a_legacy_sentinel_is_not_rendered_as_a_path(self):
        """Only paths under uploads/ are real uploads (the _avatar.html rule)."""
        assert RecommendationService._logo_image({"logo_path": "default.png"}) is None

    def test_rows_without_the_column_still_work(self):
        """A query that does not select logo_path must not raise KeyError."""
        posting = _posting("DevPro Lab")
        assert "logo_path" not in posting
        assert RecommendationService._logo_image(posting) is None


class TestRecommendationPageBadge:
    """The card row must carry a renderable logo for every recommendation."""

    class _Repo:
        """Stands in for PostingRepository. Must be truthy, because the service
        does `postings or PostingRepository()` - an empty list is falsy and would
        silently fall through to a real database connection."""

        def __init__(self, rows):
            self._rows = rows

        def all_with_skills(self):
            return [dict(r) for r in self._rows]

    def _recs(self, postings, skills=("java", "sql")):
        """The page keeps a posting only when match_required_skills finds at
        least one of its skills on the resume (the RESUME FILTER). It matches
        against the taxonomy's lower-cased vocabulary, so the fixture uses
        lower-case skills on both sides."""
        with app_context():
            return RecommendationService(postings=self._Repo(postings)).for_recommendation_page(
                list(skills), 70, domain_scores={}
            )

    def test_every_recommendation_row_carries_a_logo(self):
        rows = [_posting("DevPro Lab"), _posting("AgileDev Studios")]
        recs = self._recs(rows)
        assert recs, "no cards built, so this test proved nothing"
        for rec in recs:
            assert isinstance(rec["logo"], str) and rec["logo"], rec["company"]

    def test_every_recommendation_row_carries_logo_image(self):
        """logo_image drives the <img> branch; it is a real upload path or None."""
        rows = [_posting("DevPro Lab", logo_path="uploads/logos/dl.png"),
                _posting("AgileDev Studios")]
        recs = self._recs(rows)
        assert recs, "no cards built, so this test proved nothing"
        by_company = {r["company"]: r for r in recs}
        assert by_company["DevPro Lab"]["logo_image"] == "uploads/logos/dl.png"
        assert by_company["AgileDev Studios"]["logo_image"] is None

    def test_two_companies_never_share_a_badge(self):
        recs = self._recs([_posting("DevPro Lab"), _posting("AgileDev Studios")])
        assert len(recs) >= 2, "expected a card per company"
        assert {r["logo"] for r in recs} == {"DL", "AS"}

    def test_a_company_with_a_blank_name_still_renders(self):
        recs = self._recs([_posting("")])
        assert recs, "no cards built, so this test proved nothing"
        assert recs[0]["logo"] == "IT"