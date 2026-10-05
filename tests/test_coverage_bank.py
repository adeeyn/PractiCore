"""Tests for the competency-coverage bank and the assessment-status logic.

These pin the fix for "Claimed": a resume skill must reach questions and a real
score, and "Claimed" must never be the terminal result of a competency.

Pure logic, so none of these need a database.
"""
from collections import Counter

from practicore.competency_scoring import STRENGTH_BANDS, strength_level_for
from practicore.repositories.competency_repository import CompetencyRepository
from practicore.services import competency_coverage_bank as bank
from practicore.services.competency_taxonomy import COMPETENCIES, competencies_for_skill
from practicore.services.master_selection import allocate_quota

RESUME = ["pandas", "power bi", "git", "python", "java", "sql"]

# Competencies the 130-item researcher bank already covers.
BANKED = {"PROG", "WEB", "DB", "NET", "COMM", "OS", "TROUBLE", "SUPP",
          "SEC", "PROB", "DEV", "EVID"}


class TestCoverageBankShape:
    def test_every_covered_competency_exists_in_the_taxonomy(self):
        """No second Git competency is invented: these codes already exist."""
        for code in bank.COVERED_COMPETENCIES:
            assert code in COMPETENCIES, "%s is not in the taxonomy" % code

    def test_ten_items_per_covered_competency(self):
        """Ten matches the master bank, and is what makes a retake meaningful."""
        counts = bank.counts_per_competency()
        assert set(counts) == set(bank.COVERED_COMPETENCIES), counts
        assert set(counts.values()) == {10}, counts

    def test_codes_are_unique_and_namespaced(self):
        codes = [row["question_code"] for row in bank.as_rows()]
        assert len(codes) == len(set(codes))
        # MB2- cannot collide with the document's MB-* or the published Q*/PF-*.
        assert all(c.startswith("MB2-") for c in codes)

    def test_every_item_has_four_non_blank_options(self):
        for row in bank.as_rows():
            options = [row["option_a"], row["option_b"], row["option_c"], row["option_d"]]
            assert len(options) == 4
            for option in options:
                assert option and str(option).strip(), row["question_code"]

    def test_the_keyed_option_is_always_present_in_the_row(self):
        """Rotation moves options, so the key must be re-derived, never assumed."""
        for row in bank.as_rows():
            assert row["correct_option"] in "ABCD", row["question_code"]
            keyed = {"A": "option_a", "B": "option_b",
                     "C": "option_c", "D": "option_d"}[row["correct_option"]]
            assert row[keyed], row["question_code"]

    def test_every_item_is_verified_and_therefore_servable(self):
        unresolved = [c for c, v in bank.verify_keys().items()
                      if v["status"] != "Verified"]
        assert unresolved == [], unresolved

    def test_rotation_is_deterministic(self):
        """Re-seeding must rewrite the same rows, not reshuffle them."""
        assert bank.as_rows() == bank.as_rows()

    def test_the_answer_key_is_spread_across_letters(self):
        keys = bank.answer_key_distribution()
        assert min(keys.values()) > 0, keys
        assert max(keys.values()) - min(keys.values()) <= 10, keys

    def test_provenance_never_claims_the_research_document(self):
        for row in bank.as_rows():
            assert row["source_type"] == bank.SOURCE_TYPE
            assert "Researcher" not in str(row["source_type"])

    def test_every_item_carries_a_framework_citation(self):
        for row in bank.as_rows():
            assert row["standard_ref"] and row["standard_ref"].strip()

    def test_difficulty_uses_the_schema_enum(self):
        for row in bank.as_rows():
            assert row["difficulty"] in ("easy", "medium", "hard")

    def test_rotation_preserves_the_set_of_options(self):
        for row, item in zip(bank.as_rows(), bank.ITEMS):
            options = {row["option_a"], row["option_b"],
                       row["option_c"], row["option_d"]}
            assert options == set(item[6]), row["question_code"]
class TestResumeTriggersReachQuestions:
    """The reported bug: the skill was detected, but nothing could measure it."""

    def test_every_competency_a_resume_skill_maps_to_has_questions(self):
        """A trigger with an empty pool is what produced 'Claimed'."""
        populated = BANKED | set(bank.COVERED_COMPETENCIES)
        for skill in RESUME:
            for code in competencies_for_skill(skill):
                assert code in populated, "%s maps to %s, which has no bank" % (
                    skill, code)

    def test_the_reported_skills_now_have_pools(self):
        for skill, code in (("pandas", "DATA"), ("power bi", "DATA"), ("git", "GIT")):
            assert code in competencies_for_skill(skill)
            assert bank.counts_per_competency().get(code, 0) >= 10

    def test_ten_items_support_the_retake_rotation(self):
        """With 2-13 items drawn per competency, ten leaves unseen spares."""
        quota = allocate_quota(list(bank.COVERED_COMPETENCIES),
                               {c: 1.0 for c in bank.COVERED_COMPETENCIES},
                               {c: 10 for c in bank.COVERED_COMPETENCIES}, 45)
        for code, count in quota.items():
            assert count <= 10, "%s quota %d exceeds its pool" % (code, count)


class TestStrengthBands:
    def test_the_documented_thresholds(self):
        assert strength_level_for(0) == "Weak"
        assert strength_level_for(59) == "Weak"
        assert strength_level_for(60) == "Moderate"
        assert strength_level_for(79) == "Moderate"
        assert strength_level_for(80) == "Strong"
        assert strength_level_for(100) == "Strong"

    def test_no_score_is_never_a_band(self):
        """"Not measured" must not render as a measured result."""
        assert strength_level_for(None) is None

    def test_bands_are_configurable(self):
        bands = ((95, "Excellent"), (50, "Pass"), (0, "Not yet"))
        assert strength_level_for(96, bands) == "Excellent"
        assert strength_level_for(60, bands) == "Pass"
        assert strength_level_for(10, bands) == "Not yet"

    def test_default_table_matches_config(self):
        assert STRENGTH_BANDS == ((80, "Strong"), (60, "Moderate"), (0, "Weak"))


class TestAssessmentStatus:
    """'Claimed' must never be the RESULT of a competency."""

    def state(self, percent, available):
        entry = {"code": "DATA", "score_percent": percent}
        return CompetencyRepository.assessment_state(
            entry, {"DATA": available} if available else {})

    def test_a_measured_competency_is_assessed_with_a_band(self):
        state = self.state(67, 10)
        assert state["status"] == CompetencyRepository.STATUS_ASSESSED
        assert state["assessment_completed"] is True
        assert state["strength_level"] == "Moderate"

    def test_a_claim_with_questions_is_assessment_required_not_claimed(self):
        """THE regression test: this was 'Claimed' with 'not assessed'."""
        state = self.state(None, 10)
        assert state["status"] == CompetencyRepository.STATUS_ASSESSMENT_REQUIRED
        assert state["status"] != "Claimed"
        assert state["assessment_required"] is True
        assert state["strength_level"] is None

    def test_no_questions_at_all_is_not_assessed(self):
        state = self.state(None, 0)
        assert state["status"] == CompetencyRepository.STATUS_NOT_ASSESSED
        assert state["assessment_required"] is False

    def test_claim_is_recorded_separately_from_the_score(self):
        entry = {"code": "DATA", "score_percent": 67,
                 "evidence_skills": ["pandas", "power bi"]}
        state = CompetencyRepository.assessment_state(entry, {"DATA": 10})
        assert state["resume_claimed"] is True
        assert state["resume_evidence"] == ["pandas", "power bi"]
        # The claim is present AND the score is a demonstration: two facts.
        assert state["assessment_completed"] is True

    def test_no_status_is_ever_claimed(self):
        for percent in (None, 0, 50, 100):
            for available in (0, 10):
                assert self.state(percent, available)["status"] != "Claimed"

    def test_available_questions_is_reported_for_the_ui(self):
        assert self.state(None, 10)["available_questions"] == 10
        assert self.state(None, 0)["available_questions"] == 0


class TestEvidenceStrengthIsNotTheResult:
    """evidence_strength stays as corroboration, and keeps its existing ladder."""

    def test_a_claim_alone_is_still_claimed_as_CORROBORATION(self):
        entry = {"score_percent": None, "evidence_skills": ["pandas"],
                 "has_project": False, "has_experience": False}
        assert CompetencyRepository.evidence_strength(entry) == "Claimed"

    def test_but_a_measured_claim_needs_corroboration_to_reach_strong(self):
        base = {"score_percent": 85, "has_project": False, "has_experience": False}
        assert CompetencyRepository.evidence_strength(
            dict(base, evidence_skills=["pandas"])) == "Moderate"
        assert CompetencyRepository.evidence_strength(
            dict(base, evidence_skills=["pandas"], has_project=True)) == "Strong"


class TestScenarioItems:
    """Applied and workplace constructs are scenario-based, not opinion polls."""

    def test_question_types_include_scenario_items(self):
        types = Counter(row["question_type"] for row in bank.as_rows())
        assert types["Scenario-Based Multiple Choice"] >= 20, types

    def test_no_item_asks_the_student_to_rate_themselves(self):
        """'Are you a good communicator?' measures nothing about skill."""
        banned = ("are you a good", "how would you rate yourself",
                  "rate your own", "describe yourself as", "are you better at")
        for row in bank.as_rows():
            text = row["question_text"].lower()
            for phrase in banned:
                assert phrase not in text, row["question_code"]

    def test_applied_constructs_ask_what_to_do_not_what_is_true(self):
        """Soft and applied items should be phrased as a situation to resolve."""
        for row in bank.as_rows():
            assert row["question_text"].endswith("?"), row["question_code"]
            assert not row["question_text"].lower().startswith(
                ("are you", "do you", "would you like", "can you ")), (
                row["question_code"])