"""Tests for derived logo initials (migration 014).

The logo initials used to be typed into two forms and capped at 10 characters,
with the "first two words" rule copy-pasted into four places that had already
drifted apart. They are now derived from the company name by
practicore/initials.py, so these tests pin the rule itself and the places that
consume it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from practicore.initials import initials_for


class TestInitialsRule:
    """The one rule every initials badge in the app now shares."""

    def test_the_first_two_words_give_the_initials(self):
        assert initials_for("Tech Solution Inc.") == "TS"
        assert initials_for("Nexus Cyber Solutions") == "NC"
        assert initials_for("Juan Dela Cruz") == "JD"

    def test_a_longer_name_is_not_truncated_mid_word(self):
        """"InnovaTech Solutions Inc." must not become "IN" just because the
        seeder used to hard-code that; it is the first two WORDS that count."""
        assert initials_for("InnovaTech Solutions Inc.") == "IS"
        assert initials_for("CoreIT Service Management") == "CS"

    def test_a_single_word_name_gives_one_letter(self):
        assert initials_for("Globex") == "G"

    def test_the_result_is_always_upper_case(self):
        assert initials_for("tech solution inc.") == "TS"
        assert initials_for("devpro lab") == "DL"

    def test_extra_whitespace_does_not_add_empty_letters(self):
        assert initials_for("  Tech   Solution  Inc. ") == "TS"

    def test_blank_input_still_renders_a_badge(self):
        """An empty badge is invisible; a placeholder is not."""
        for blank in (None, "", "   "):
            assert initials_for(blank) == "?"

    def test_the_fallback_can_be_overridden(self):
        """The recommendation cards use 'IT' rather than a bare '?'."""
        assert initials_for("", fallback="IT") == "IT"

    def test_the_word_count_is_configurable(self):
        assert initials_for("Alpha Beta Gamma", words=3) == "ABG"


class TestNoManualInitialsLeft:
    """The field is gone from both forms and from validation."""

    def _source(self, *parts):
        return Path(__file__).resolve().parent.parent.joinpath(*parts).read_text(encoding="utf-8")

    def test_the_employer_profile_form_has_no_initials_input(self):
        template = self._source("practicore", "templates", "employer", "company_profile.html")
        assert 'name="logo_text"' not in template

    def test_the_admin_company_form_has_no_initials_input(self):
        template = self._source("practicore", "templates", "admin", "partner_company_form.html")
        assert 'name="logo_text"' not in template

    def test_admin_validation_does_not_collect_or_limit_initials(self):
        from practicore.services import admin_validation as validation

        assert "logo_text" not in validation.TEXT_FIELDS
        assert "logo_text" not in validation.MAX_LENGTHS

    def test_nothing_still_truncates_the_initials_to_ten_characters(self):
        """The old [:10] cap is gone, so a name cannot be cut mid-way."""
        route = self._source("practicore", "routes", "employer", "profile.py")
        assert "logo_text[:10]" not in route

    def test_the_repositories_derive_rather_than_accept_initials(self):
        """Both write paths take company_name only, so callers cannot disagree."""
        repo = self._source("practicore", "repositories", "employer_repository.py")
        assert "initials_for(company_name)" in repo

        # The parameter is gone from the signatures. Matched with a preceding
        # word boundary so the SQL column list (company_logo_text) does not
        # count as the removed parameter.
        import re

        for method in ("def update_profile", "def create_with_account"):
            body = repo.split(method)[1].split("\n    def ")[0]
            signature = body.split("):")[0]
            assert not re.search(r"(?<![\w])logo_text(?![\w])", signature), method