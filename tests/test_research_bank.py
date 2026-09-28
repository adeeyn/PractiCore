"""Tests for the 43-item research-based question bank.

These run against the real bank module, so a transcription slip in the .docx
-> module step is caught here rather than in front of a panel.
"""
from collections import Counter

from practicore.services.research_bank import (
    DOMAIN_TRACK,
    PATHWAY_ROLES,
    QUESTIONS,
    answer_key_distribution,
    as_rows,
    balanced_rows,
    expected_track_counts,
)
from practicore.services.skill_taxonomy import SkillTaxonomy


class TestBankShape:
    def test_has_all_43_items(self):
        assert len(QUESTIONS) == 43

    def test_codes_are_unique(self):
        codes = [q[0] for q in QUESTIONS]
        assert len(set(codes)) == 43

    def test_codes_run_from_q01_to_q43(self):
        assert sorted(q[0] for q in QUESTIONS) == ["Q%02d" % i for i in range(1, 44)]

    def test_every_item_has_four_options(self):
        for code, _d, _p, _s, _c, _t, options, _k in QUESTIONS:
            assert len(options) == 4, code

    def test_no_option_is_blank(self):
        for code, _d, _p, _s, _c, _t, options, _k in QUESTIONS:
            for option in options:
                assert option and str(option).strip(), code

    def test_answer_key_is_always_valid(self):
        for code, _d, _p, _s, _c, _t, _o, key in QUESTIONS:
            assert key in ("A", "B", "C", "D"), code

    def test_question_text_is_meaningful(self):
        for code, _d, _p, _s, _c, text, _o, _k in QUESTIONS:
            assert text and len(text) > 15, code

    def test_every_domain_is_mapped_to_a_track(self):
        for _code, domain, *_rest in QUESTIONS:
            assert domain in DOMAIN_TRACK, domain

    def test_every_track_is_a_real_job_category(self):
        for track in DOMAIN_TRACK.values():
            assert track in set(SkillTaxonomy.DOMAIN_TRACK_CODES.values()), track

    def test_all_six_categories_are_covered(self):
        # Every job category must have at least one item, otherwise a student
        # can never be assessed in it.
        assert set(expected_track_counts()) == set(SkillTaxonomy.DOMAIN_TRACK_CODES.values())

    def test_every_domain_has_a_role(self):
        for _code, domain, *_rest in QUESTIONS:
            assert domain in PATHWAY_ROLES, domain


class TestBankIsUsable:
    def test_as_rows_yields_one_dict_per_item(self):
        assert len(list(as_rows())) == 43

    def test_rows_carry_the_standard_reference(self):
        # The bank claims SFIA/CompTIA/Google/Cisco provenance, so every item
        # must name the framework it was written against.
        for row in as_rows():
            assert row["standard_ref"] and row["standard_ref"].strip(), row["question_code"]

    def test_rows_carry_the_competency(self):
        for row in as_rows():
            assert row["competency"] and row["competency"].strip(), row["question_code"]

    def test_track_code_is_stored_so_the_taxonomy_can_read_it(self):
        for row in as_rows():
            assert row["course_track"] in set(SkillTaxonomy.DOMAIN_TRACK_CODES.values())

    def test_track_code_maps_back_to_the_right_job_category(self):
        for row in as_rows():
            assert SkillTaxonomy.map_to_domain(row["course_track"])

    def test_items_are_objective_type(self):
        # Self-rating is never accepted as proof, so nothing may be typed as a
        # subjective item.
        for row in as_rows():
            assert row["question_type"] == "Objective"

    def test_track_counts_sum_to_the_bank_size(self):
        assert sum(expected_track_counts().values()) == 43


class TestAnswerKeyBalance:
    """The published bank keys 37/43 as 'A'; balanced_rows() must fix that.

    A near-single-letter key means a student can score highly without knowing
    anything, which is exactly the weakness the research note warns about. The
    published order is preserved in `as_rows()` for traceability; the seeded
    bank uses `balanced_rows()`.
    """

    def test_published_bank_is_known_to_be_skewed(self):
        from collections import Counter

        published = Counter(row["correct_option"] for row in as_rows())
        # Documented, not asserted as acceptable: this is the defect we fix.
        assert published["A"] > 30

    def test_balanced_bank_is_not_trivially_guessable(self):
        distribution = answer_key_distribution()
        top_letter, top_count = max(distribution.items(), key=lambda kv: kv[1])
        assert top_count / 43 < 0.40, (
            "answer key is still skewed toward %r (%d/43) - a student can score by "
            "always picking that letter." % (top_letter, top_count)
        )

    def test_balanced_bank_spreads_across_all_letters(self):
        distribution = answer_key_distribution()
        assert set(distribution) == {"A", "B", "C", "D"}

    def test_balancing_preserves_item_content(self):
        original = {r["question_code"]: r for r in as_rows()}
        for row in balanced_rows():
            source = original[row["question_code"]]
            assert row["question_text"] == source["question_text"]
            # Same four option strings, just in a different order.
            assert sorted([row["option_a"], row["option_b"], row["option_c"], row["option_d"]]) == \
                sorted([source["option_a"], source["option_b"], source["option_c"], source["option_d"]])

    def test_balancing_preserves_the_correct_answer_text(self):
        original = {r["question_code"]: r for r in as_rows()}
        for row in balanced_rows():
            source = original[row["question_code"]]
            answer = source["option_%s" % source["correct_option"].lower()]
            assert row["option_%s" % row["correct_option"].lower()] == answer, row["question_code"]

    def test_balancing_is_deterministic(self):
        first = [(r["question_code"], r["correct_option"], r["option_a"]) for r in balanced_rows()]
        second = [(r["question_code"], r["correct_option"], r["option_a"]) for r in balanced_rows()]
        assert first == second

    def test_balanced_rows_has_the_same_item_count(self):
        assert len(list(balanced_rows())) == 43
