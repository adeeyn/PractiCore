"""Tests for the researcher master question bank and the adaptive selector.

Pure logic, so none of these need a database: the bank is a module of dicts and the
selector is driven directly. They are the guard rail for the two things that would
silently corrupt an assessment - a wrong answer key and a duplicated item.
"""
from collections import Counter

from practicore.services import master_question_bank as bank
from practicore.services.master_bank_document import ITEMS
from practicore.services.master_selection import (
    MAX_QUESTIONS,
    MIN_QUESTIONS,
    allocate_quota,
    competency_weight,
    pick_items,
)


class TestBankShape:
    def test_has_all_130_document_items(self):
        assert len(ITEMS) == 130

    def test_codes_are_unique(self):
        assert len({i["code"] for i in ITEMS}) == 130

    def test_every_item_has_four_options(self):
        for item in ITEMS:
            assert len(item["options"]) == 4, item["code"]

    def test_no_option_is_blank(self):
        for item in ITEMS:
            for option in item["options"]:
                assert option and str(option).strip(), item["code"]

    def test_published_key_is_a_valid_letter(self):
        for item in ITEMS:
            assert item["correct_option"] in "ABCD", item["code"]

    def test_question_text_is_meaningful(self):
        for item in ITEMS:
            assert item["question_text"] and len(item["question_text"]) > 15, item["code"]

    def test_ten_items_per_document_competency(self):
        counts = Counter(i["code"].split("-")[0] for i in ITEMS)
        assert len(counts) == 13, counts
        assert set(counts.values()) == {10}, counts

    def test_difficulty_uses_the_schema_enum(self):
        for item in ITEMS:
            assert item["difficulty"] in ("easy", "medium", "hard"), item["code"]


class TestProvenance:
    """Every item must be traceable, and none may claim a source it lacks."""

    def test_every_item_carries_a_framework_citation(self):
        for item in ITEMS:
            assert item["framework"] and item["framework"].strip(), item["code"]

    def test_every_item_carries_an_explanation(self):
        for item in ITEMS:
            assert item["explanation"] and item["explanation"].strip(), item["code"]

    def test_every_item_records_its_validation_state(self):
        for item in ITEMS:
            assert item["validation"] and item["validation"].strip(), item["code"]

    def test_source_type_is_always_researcher_developed(self):
        for row in bank.balanced_rows():
            assert row["source_type"] == "Researcher-Developed", row["question_code"]

    def test_nothing_claims_cp2_provenance(self):
        # The source document states CP2 was NOT available to its authors, so a CP2
        # label would be a fabricated citation.
        allowed = {"Researcher-Developed", "Framework-Derived",
                   "Research-Supported", "Validation-Approved"}
        for row in bank.balanced_rows():
            assert row["source_type"] in allowed, row["question_code"]
            assert "CP2" not in row["source_type"]


class TestAnswerKeyVerification:
    """The document's published keys contradict their own explanations; the bank
    must adjudicate each one rather than trusting it blindly."""

    def test_every_item_is_classified(self):
        assert len(bank.verify_keys()) == 130

    def test_statuses_partition_the_bank(self):
        summary = bank.key_status_summary()
        assert sum(summary.values()) == 130
        assert set(summary) == {"Verified", "Corrected", "Unresolved"}

    def test_a_corrected_key_never_equals_the_published_one(self):
        for record in bank.corrections():
            assert record["recorded_option"] != record["applied_option"], record

    def test_corrections_preserve_both_option_texts(self):
        for record in bank.corrections():
            assert record["recorded_option_text"], record
            assert record["applied_option_text"], record

    def test_unresolved_items_are_never_served(self):
        for row in bank.balanced_rows():
            if row["key_status"] == "Unresolved":
                assert row["is_active"] == 0, row["question_code"]

    def test_verified_items_stay_active(self):
        for row in bank.balanced_rows():
            if row["key_status"] == "Verified":
                assert row["is_active"] == 1, row["question_code"]

    def test_the_documented_prog001_conflict_is_detected(self):
        # Published "A" = "Store only one value" for the purpose of a loop, while
        # the explanation says "Repeat instructions".
        info = bank.verify_keys()["PROG-001"]
        assert info["recorded"] == "A"
        assert info["recorded_text"] == "Store only one value"
        assert info["applied"] == "B"
        assert info["applied_text"] == "Repeat instructions"
        assert info["status"] == "Corrected"


class TestBalancedRows:
    def test_yields_one_row_per_item(self):
        assert len(bank.balanced_rows()) == 130

    def test_balancing_is_deterministic(self):
        first = [(r["question_code"], r["correct_option"]) for r in bank.balanced_rows()]
        second = [(r["question_code"], r["correct_option"]) for r in bank.balanced_rows()]
        assert first == second

    def test_the_keyed_option_text_is_preserved(self):
        rows = {r["question_code"]: r for r in bank.balanced_rows()}
        row = rows["PROG-001"]
        assert row["option_%s" % row["correct_option"].lower()] == "Repeat instructions"

    def test_option_content_is_never_reordered_or_dropped(self):
        original = {i["code"]: i["options"] for i in ITEMS}
        for row in bank.balanced_rows():
            assert sorted([row["option_a"], row["option_b"],
                           row["option_c"], row["option_d"]]) == \
                   sorted(original[row["question_code"]])

    def test_answer_key_is_not_trivially_guessable(self):
        distribution = bank.answer_key_distribution()
        assert set(distribution) == {"A", "B", "C", "D"}
        assert max(distribution.values()) / 130 < 0.40, distribution

    def test_every_competency_exists_in_the_canonical_taxonomy(self):
        from practicore.services.competency_taxonomy import COMPETENCIES
        for row in bank.balanced_rows():
            assert row["competency"] in COMPETENCIES, row["question_code"]


class TestQuotaAllocation:
    def test_respects_the_requested_total(self):
        codes = ["PROG", "DB", "NET", "COMM", "SEC"]
        quota = allocate_quota(codes, {c: 1.0 for c in codes}, {c: 10 for c in codes}, 45)
        assert sum(quota.values()) == 45

    def test_no_competency_takes_more_than_its_share(self):
        quota = allocate_quota(["PROG", "DB"], {"PROG": 3.0, "DB": 1.0},
                               {"PROG": 40, "DB": 40}, 45)
        assert quota["PROG"] <= int(45 * 0.30)

    def test_posting_competencies_outrank_core_ones(self):
        weights = {"PROG": competency_weight({"sources": ["core"]}),
                   "SEC": competency_weight({"sources": ["core", "posting"]})}
        quota = allocate_quota(["PROG", "SEC"], weights, {"PROG": 10, "SEC": 10}, 40)
        assert quota["SEC"] >= quota["PROG"]

    def test_never_exceeds_the_bank(self):
        quota = allocate_quota(["PROG", "DB"], {"PROG": 1.0, "DB": 1.0},
                               {"PROG": 3, "DB": 2}, 45)
        assert sum(quota.values()) == 5

    def test_no_competency_is_starved_below_the_floor(self):
        quota = allocate_quota(["PROG", "DB", "NET"],
                               {"PROG": 9.0, "DB": 1.0, "NET": 1.0},
                               {c: 10 for c in ("PROG", "DB", "NET")}, 45)
        assert all(count >= 2 for count in quota.values()), quota

    def test_empty_input_is_handled(self):
        assert allocate_quota([], {}, {}, 45) == {}


class TestPickItems:
    @staticmethod
    def _pool(count, prefix="Q", difficulty="medium"):
        return [{"id": "%s%d" % (prefix, n), "difficulty": difficulty}
                for n in range(count)]

    def test_unseen_items_are_preferred(self):
        # `seen` is keyed by the same type the pool uses, exactly as the repository
        # returns it (int ids from MySQL).
        seen = {"Q0": {"times_seen": 5, "last_seen_at": "2026-01-01"},
                "Q1": {"times_seen": 5, "last_seen_at": "2026-02-01"}}
        picked = pick_items(self._pool(10), 4, seen, None)
        assert all(q["id"] not in ("Q0", "Q1") for q in picked)

    def test_least_recently_seen_comes_next(self):
        # Every item has been seen, so this exercises the recency ordering alone:
        # Q1 was seen longest ago, so it is the one that should come back first.
        pool = self._pool(3)
        seen = {"Q%d" % n: {"times_seen": 1, "last_seen_at": "2026-0%d-01" % (n + 1)}
                for n in range(3)}
        assert pick_items(pool, 1, seen, None)[0]["id"] == "Q0"

    def test_an_unseen_item_outranks_a_stale_one(self):
        # Recency is only a tie-break among seen items; never-seen always wins.
        pool = self._pool(3)
        seen = {"Q0": {"times_seen": 9, "last_seen_at": "2026-01-01"},
                "Q1": {"times_seen": 9, "last_seen_at": "2026-01-01"}}
        assert pick_items(pool, 1, seen, None)[0]["id"] == "Q2"

    def test_reuses_older_items_when_unseen_run_out(self):
        seen = {"Q%d" % n: {"times_seen": 1, "last_seen_at": "2026-0%d-01" % (n + 1)}
                for n in range(3)}
        picked = pick_items(self._pool(3), 3, seen, None)
        assert len(picked) == 3, "coverage must not shrink to avoid a repeat"

    def test_never_repeats_an_item_within_one_pick(self):
        assert len({q["id"] for q in pick_items(self._pool(8), 5, {}, None)}) == 5

    def test_returns_nothing_for_an_empty_pool(self):
        assert pick_items([], 5, {}, None) == []

    def test_spreads_across_difficulties_when_available(self):
        pool = (self._pool(4, "E", "easy") + self._pool(4, "M", "medium")
                + self._pool(4, "H", "hard"))
        assert len({q["difficulty"] for q in pick_items(pool, 6, {}, None)}) >= 2

    def test_respects_a_pool_smaller_than_the_quota(self):
        assert len(pick_items(self._pool(2), 5, {}, None)) == 2


class TestAssessmentSize:
    def test_target_is_inside_the_required_band(self):
        assert MIN_QUESTIONS <= 45 <= MAX_QUESTIONS
        assert (MIN_QUESTIONS, MAX_QUESTIONS) == (40, 50)
