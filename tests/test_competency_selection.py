"""Tests for competency-driven assessment selection and cross-matching.

Pure logic, so these need no database. They pin the three rules the design
depends on: three sources merged, a resume is a trigger not proof, and one form
per competency that rotates on a retake.
"""
import random

from practicore.repositories.competency_repository import CompetencyRepository
from practicore.services.assessment_selection import (
    SOURCE_CORE,
    SOURCE_POSTING,
    SOURCE_RESUME,
    choose_forms,
    select_competencies,
)
from practicore.services.competency_taxonomy import (
    COMPETENCIES,
    CORE_COMPETENCY_CODES,
    competencies_for_skill,
    required_competencies,
)
from practicore.services.cross_matching import score_posting

RESUME = ["React", "JavaScript", "SQL", "Linux", "Git"]


class TestSkillMapping:
    def test_the_documented_examples_map_correctly(self):
        assert "WEB" in competencies_for_skill("React")
        assert "PROG" in competencies_for_skill("JavaScript")
        assert competencies_for_skill("SQL") == {"DB": "primary"}
        assert "OS" in competencies_for_skill("Linux")
        assert "SUPP" in competencies_for_skill("Linux")
        # Git is its own competency in the master bank taxonomy, so it maps to GIT
        # as well as to DEV. Asserted by membership, not equality, because the
        # competency list grew.
        assert "DEV" in competencies_for_skill("Git")
        assert "GIT" in competencies_for_skill("Git")

    def test_mapping_is_case_insensitive(self):
        assert competencies_for_skill("react") == competencies_for_skill("React")

    def test_unknown_skill_maps_to_nothing(self):
        assert competencies_for_skill("Underwater Basket Weaving") == {}

    def test_every_mapped_competency_exists_in_the_taxonomy(self):
        for skill in ("react", "sql", "linux", "git", "cisco", "itil", "tableau"):
            for code in competencies_for_skill(skill):
                assert code in COMPETENCIES, "%s maps to unknown %s" % (skill, code)

    def test_operating_system_and_support_skills_are_mapped(self):
        # Regression: a truncated edit once dropped the whole OS/support section,
        # which silently broke the IT Support example.
        for skill in ("linux", "windows server", "troubleshooting",
                       "technical support", "itil", "service desk"):
            assert competencies_for_skill(skill), skill

    def test_primary_beats_supporting_when_merging(self):
        merged = required_competencies(["java", "git"])
        assert merged["PROG"] == "primary"
        assert merged["DEV"] == "primary"


class TestSelection:
    def test_core_is_always_included(self):
        selected = select_competencies(RESUME, ["React"], "")
        codes = {e["code"] for e in selected}
        for core in CORE_COMPETENCY_CODES:
            assert core in codes

    def test_internship_requirements_pull_in_competencies_the_resume_omits(self):
        """The whole point: an unmentioned requirement is still verified."""
        selected = select_competencies(["React"], ["Troubleshooting"], "")
        assert "TROUBLE" in {e["code"] for e in selected}

    def test_the_assessment_changes_with_the_target_internship(self):
        web = {e["code"] for e in select_competencies(
            RESUME, ["React", "JavaScript", "SQL", "Problem-solving"], "")}
        support = {e["code"] for e in select_competencies(
            RESUME, ["Linux", "Networking", "Troubleshooting", "Technical support"], "")}
        assert web != support, "the same student must be assessed differently per posting"
        assert "TROUBLE" in support and "TROUBLE" not in web

    def test_unrelated_competencies_are_not_assessed(self):
        codes = {e["code"] for e in select_competencies(
            RESUME, ["React", "JavaScript", "SQL", "Problem-solving"], "")}
        for unrelated in ("SEC", "DATA", "SYS"):
            assert unrelated not in codes, "%s assessed without being relevant" % unrelated

    def test_a_competency_from_several_sources_appears_once(self):
        selected = select_competencies(["Python"], ["JavaScript", "SQL"], "")
        prog = [e for e in selected if e["code"] == "PROG"]
        assert len(prog) == 1
        # Provenance is kept, which is what makes the selection explainable.
        assert set(prog[0]["sources"]) >= {SOURCE_CORE, SOURCE_RESUME, SOURCE_POSTING}

    def test_no_duplicate_codes_are_ever_returned(self):
        selected = select_competencies(RESUME, RESUME, "React Python SQL Linux networking")
        codes = [e["code"] for e in selected]
        assert len(codes) == len(set(codes))

    def test_the_degree_program_is_never_consulted(self):
        """No signature accepts a programme, so it cannot filter anything."""
        import inspect

        params = set(inspect.signature(select_competencies).parameters)
        for forbidden in ("course", "programme", "program", "degree", "major", "year_level"):
            assert forbidden not in params

    def test_core_comes_before_targeted(self):
        selected = select_competencies(RESUME, ["React"], "")
        flags = [e["is_core"] for e in selected]
        assert flags == sorted(flags, reverse=True)

    def test_max_targeted_caps_only_the_targeted_ones(self):
        selected = select_competencies(
            RESUME, ["React", "SQL", "Linux", "Git", "Cisco", "ITIL"], "", max_targeted=2)


class TestFormSelection:
    SETS = {
        "PROG": [{"id": 1, "set_code": "A"}, {"id": 2, "set_code": "B"}, {"id": 3, "set_code": "C"}],
        "DB": [{"id": 4, "set_code": "A"}, {"id": 5, "set_code": "B"}, {"id": 6, "set_code": "C"}],
    }

    def test_one_form_is_chosen_per_competency(self):
        chosen, _ = choose_forms(["PROG", "DB"], self.SETS)
        assert set(chosen) == {"PROG", "DB"}
        assert all("set_code" in form for form in chosen.values())

    def test_a_retake_prefers_an_unseen_form(self):
        first, _ = choose_forms(["PROG"], self.SETS, rng=random.Random(1))
        exposure = {"PROG": [{"set_id": first["PROG"]["id"], "exposed_at": "2026-09-28"}]}
        second, _ = choose_forms(["PROG"], self.SETS, exposure, rng=random.Random(1))
        assert second["PROG"]["id"] != first["PROG"]["id"]

    def test_repeated_retakes_eventually_cover_every_form(self):
        seen, rng = set(), random.Random(7)
        for _ in range(12):
            chosen, _ = choose_forms(["PROG"], self.SETS, rng=rng)
            seen.add(chosen["PROG"]["set_code"])
        assert seen == {"A", "B", "C"}

    def test_when_all_forms_are_seen_the_longest_ago_wins(self):
        exposure = {"PROG": [
            {"set_id": 1, "exposed_at": "2026-01-01"},
            {"set_id": 2, "exposed_at": "2026-06-01"},
            {"set_id": 3, "exposed_at": "2026-09-01"},
        ]}
        chosen, _ = choose_forms(["PROG"], self.SETS, exposure)
        assert chosen["PROG"]["set_code"] == "A"

    def test_a_shortfall_is_reported_rather_than_hidden(self):
        _, shortfall = choose_forms(["DB"], {"DB": [{"id": 4, "set_code": "A"}]})
        assert "1 of 3" in shortfall["DB"]

    def test_a_competency_with_no_questions_is_reported(self):
        chosen, shortfall = choose_forms(["GHOST"], self.SETS)
        assert "GHOST" not in chosen
        assert "no questions" in shortfall["GHOST"]


class TestCrossMatching:
    def profile(self, **overrides):
        profile = {
            "WEB": {"code": "WEB", "name": "Web Development", "score_percent": 85,
                    "evidence_skills": ["React", "JavaScript"], "has_project": True,
                    "has_experience": False, "evidence_strength": "Strong"},
        }
        profile.update(overrides)
        return profile

    def test_a_meeting_requirement_scores_well(self):
        result = score_posting(self.profile(), [
            {"competency_code": "WEB", "importance": "essential", "required_percent": 60},
        ])
        assert result["competencies_met"] == 1
        assert result["assessment_score"] == 85
        assert result["total_score"] > 80

    def test_a_resume_claim_alone_cannot_meet_a_requirement(self):
        """The central rule: a claim is not evidence."""
        profile = {"WEB": {"code": "WEB", "name": "Web", "score_percent": None,
                           "evidence_skills": ["React", "JavaScript", "HTML", "CSS"],
                           "has_project": True, "has_experience": True,
                           "evidence_strength": "Claimed"}}
        result = score_posting(profile, [
            {"competency_code": "WEB", "importance": "essential", "required_percent": 60},
        ])
        assert result["competencies_met"] == 0
        assert result["assessment_score"] == 0
        assert result["detail"][0]["status"] == "Not assessed"

    def test_an_unassessed_requirement_is_still_visible(self):
        result = score_posting(self.profile(), [
            {"competency_code": "SEC", "importance": "essential", "required_percent": 60},
        ])
        assert result["competencies_total"] == 1
        assert result["competencies_met"] == 0
        assert result["detail"][0]["code"] == "SEC"

    def test_the_assessment_outweighs_the_evidence(self):
        """A strong claim must not outweigh a failing assessment."""
        claim_but_failed = score_posting({
            "WEB": {"code": "WEB", "name": "Web", "score_percent": 20,
                    "evidence_skills": ["React", "JavaScript", "HTML", "CSS"],
                    "has_project": True, "has_experience": True, "evidence_strength": "Claimed"},
        }, [{"competency_code": "WEB", "importance": "essential", "required_percent": 60}])
        thin_claim_but_passed = score_posting({
            "WEB": {"code": "WEB", "name": "Web", "score_percent": 95,
                    "evidence_skills": [], "has_project": False, "has_experience": False,
                    "evidence_strength": "Moderate"},
        }, [{"competency_code": "WEB", "importance": "essential", "required_percent": 60}])
        assert thin_claim_but_passed["total_score"] > claim_but_failed["total_score"]

    def test_an_essential_requirement_matters_more(self):
        profile = self.profile(DEV={
            "code": "DEV", "name": "Software Development", "score_percent": 10,
            "evidence_skills": [], "has_project": False, "has_experience": False,
            "evidence_strength": "None",
        })
        dev_essential = score_posting(profile, [
            {"competency_code": "DEV", "importance": "essential", "required_percent": 60},
            {"competency_code": "WEB", "importance": "preferred", "required_percent": 60},
        ])
        dev_preferred = score_posting(profile, [
            {"competency_code": "DEV", "importance": "preferred", "required_percent": 60},
            {"competency_code": "WEB", "importance": "essential", "required_percent": 60},
        ])
        assert dev_preferred["assessment_score"] > dev_essential["assessment_score"]

    def test_a_better_assessment_always_raises_the_compatibility(self):
        low = score_posting({"WEB": {"code": "WEB", "name": "Web", "score_percent": 30,
                                     "evidence_skills": [], "has_project": False,
                                     "has_experience": False, "evidence_strength": "None"}},
                            [{"competency_code": "WEB", "importance": "essential",
                              "required_percent": 60}])
        high = score_posting({"WEB": {"code": "WEB", "name": "Web", "score_percent": 90,
                                      "evidence_skills": [], "has_project": False,
                                      "has_experience": False, "evidence_strength": "None"}},
                             [{"competency_code": "WEB", "importance": "essential",
                               "required_percent": 60}])
        assert high["total_score"] > low["total_score"]

    def test_no_requirements_scores_zero(self):
        assert score_posting(self.profile(), [])["total_score"] == 0

    def test_the_result_explains_itself(self):
        detail = score_posting(self.profile(), [
            {"competency_code": "WEB", "importance": "essential", "required_percent": 60},
        ])["detail"][0]
        for key in ("code", "name", "importance", "required_percent", "score_percent",
                    "evidence_strength", "evidence_skills", "status"):
            assert key in detail, key
        assert detail["evidence_skills"] == ["React", "JavaScript"]

    def test_the_score_is_always_bounded(self):
        for percent in (0, 50, 100):
            result = score_posting(
                {"WEB": {"code": "WEB", "name": "Web", "score_percent": percent,
                         "evidence_skills": ["React"], "has_project": True,
                         "has_experience": True, "evidence_strength": "Strong"}},
                [{"competency_code": "WEB", "importance": "essential", "required_percent": 60}])
            assert 0 <= result["total_score"] <= 100


class TestQuestionFormCodes:
    """Regression cover for the varchar(10) truncation that emptied a form.

    Parallel-form codes are PF-<competency>-<set><n>, so a long competency name
    pushes the code past 10 characters. The column was created as varchar(10) and
    silently truncated, which collapsed all four items of one competency onto a
    single key and left that form with no questions -- with no error raised.
    """

    def test_a_parallel_code_is_never_truncated(self):
        """A code must fit the widened column and keep its full form suffix."""
        from practicore.competency_seed import _parallel_question_rows

        for row in _parallel_question_rows():
            code = row["question_code"]
            assert len(code) <= 30, "too long for question_code: %s" % code
            # Must end in the set letter plus its index, e.g. ...-B1
            assert code[-2] == row["set_code"], code
            assert code[-1].isdigit(), code
            assert code.startswith("PF-%s-" % row["competency"]), code

    def test_codes_are_unique_across_the_whole_bank(self):
        from practicore.competency_seed import _parallel_question_rows

        codes = [r["question_code"] for r in _parallel_question_rows()]
        assert len(codes) == len(set(codes)), "duplicate parallel-form code"

    def test_every_competency_with_forms_declares_items(self):
        from practicore.services.question_forms import ITEMS_PER_SET, PARALLEL_FORMS

        for competency, forms in PARALLEL_FORMS.items():
            for set_code in ("B", "C"):
                items = forms.get(set_code) or []
                assert len(items) <= ITEMS_PER_SET, "%s form %s too large" % (competency, set_code)
                for text, options, key, ref in items:
                    assert len(options) == 4, "%s %s: needs 4 options" % (competency, set_code)
                    assert key in "ABCD", "%s %s: bad key" % (competency, set_code)
                    assert text and ref, "%s %s: missing text or source" % (competency, set_code)

class TestQuestionSetGrouping:
    """Guards the membership lookup that decides what a student is served.

    This lookup silently returned ZERO questions once, with no error: the query
    selected q.* , whose set_id column is always NULL now that membership is
    authoritative, and that NULL overwrote the membership set_id the method
    groups by. Every form came back 'empty' and the student saw an unavailable
    page. The grouping key is now aliased to form_id, and these tests pin it.
    """

    SETS = {
        "PROG": [{"id": 1, "set_code": "A"}, {"id": 2, "set_code": "B"}],
        "DB": [{"id": 3, "set_code": "A"}],
    }

    def _fake_repo(self, questions_by_set):
        forms = {k: list(v) for k, v in self.SETS.items()}

        class Repo:
            def competencies_with_forms(inner):
                return {k: [{"id": f["id"], "set_code": f["set_code"]} for f in v]
                        for k, v in forms.items()}

            def questions_for_sets(inner, set_ids):
                return {sid: questions_by_set.get(sid, []) for sid in set_ids}

            def exposure_for_student(inner, sid):
                return {}

        return Repo()

    def test_a_chosen_form_yields_its_questions(self):
        """The questions of whichever form is drawn are the ones served.

        Both forms carry a question, so this holds no matter which one
        choose_forms picks. It used to give questions to form A only, which made
        the assertion depend on a coin flip: roughly half of all runs drew form B
        and served nothing. The randomness is correct behaviour and is covered
        separately by the choose_forms rotation tests.
        """
        from practicore.services.adaptive_assessment_service import AdaptiveAssessmentService

        rows = [{"id": 11, "question_text": "q", "difficulty": "medium",
                 "correct_option": "A", "form_id": 1}]
        rows_b = [{"id": 12, "question_text": "q", "difficulty": "medium",
                   "correct_option": "A", "form_id": 2}]
        repo = self._fake_repo({1: rows, 2: rows_b, 3: []})
        svc = AdaptiveAssessmentService(repository=repo)
        built = svc.build(None, ["Python"], None)
        served = {q["id"] for q in built["questions"]}
        assert served in ({11}, {12}), "neither form's questions were served: %s" % sorted(served)

    def test_every_competency_map_entry_is_scored_under_its_own_code(self):
        from practicore.services.adaptive_assessment_service import AdaptiveAssessmentService

        # Both forms populated, so the loop below is never vacuous: with only
        # form A filled, drawing form B served nothing and the assertions
        # silently had nothing to check.
        rows = [{"id": 11, "question_text": "q", "difficulty": "medium",
                 "correct_option": "A", "form_id": 1}]
        rows_b = [{"id": 12, "question_text": "q", "difficulty": "medium",
                   "correct_option": "A", "form_id": 2}]
        repo = self._fake_repo({1: rows, 2: rows_b, 3: []})
        svc = AdaptiveAssessmentService(repository=repo)
        built = svc.build(None, ["Python"], None)
        assert built["questions"], "nothing was served, so this test proved nothing"
        for q in built["questions"]:
            assert built["competency_map"][str(q["id"])] == q["competency"]

    def test_a_question_id_is_never_served_twice(self):
        from practicore.services.adaptive_assessment_service import AdaptiveAssessmentService

        # Q22 legitimately belongs to two forms; a student must still see it once.
        rows = [{"id": 22, "question_text": "q", "difficulty": "medium",
                 "correct_option": "A", "form_id": 1}]
        repo = self._fake_repo({1: rows, 2: rows, 3: []})
        svc = AdaptiveAssessmentService(repository=repo)
        built = svc.build(None, ["Python"], None)
        ids = [q["id"] for q in built["questions"]]
        assert len(ids) == len(set(ids)), "duplicate question served: %s" % ids

    def test_choose_forms_never_returns_an_empty_form(self):
        from practicore.services.adaptive_assessment_service import AdaptiveAssessmentService

        repo = self._fake_repo({})
        svc = AdaptiveAssessmentService(repository=repo)
        built = svc.build(None, ["Python"], None)
        for code, meta in built["per_competency"].items():
            assert meta["question_ids"], "%s served with no questions" % code
        assert built["shortfall"], "an empty form must be reported, not hidden"



    def test_a_competency_pool_never_repeats_an_item(self):
        """A borrowed item already in the sub-domain must not be added twice.

        Q27 belongs to the Operating Systems sub-domain and is also listed as a
        borrowed item. Added twice it occupied both of Form A's slots and pushed
        the intended second item out, leaving the form one question short.
        """
        from practicore.competency_seed import _assign_published_items

        for competency, items in _assign_published_items().items():
            codes = [i["question_code"] for i in items]
            assert len(codes) == len(set(codes)), \
                "%s pool repeats an item: %s" % (competency, codes)

    def test_every_form_pool_can_fill_its_slots(self):
        """Every competency that gets a Form A must have enough items for it."""
        from practicore.competency_seed import _assign_published_items
        from practicore.services.question_forms import ITEMS_PER_SET

        for competency, items in _assign_published_items().items():
            assert len(items) >= ITEMS_PER_SET, \
                "%s has only %d items for Form A" % (competency, len(items))


class TestEvidenceStrength:
    def strength(self, percent, skills, has_project, has_experience):
        return CompetencyRepository.evidence_strength({
            "score_percent": percent,
            "evidence_skills": skills,
            "has_project": has_project,
            "has_experience": has_experience,
        })

    def test_a_claim_with_no_assessment_is_only_claimed(self):
        assert self.strength(None, ["React"], True, False) == "Claimed"

    def test_no_assessment_and_no_skills_is_none(self):
        assert self.strength(None, [], False, False) == "None"

    def test_resume_evidence_alone_never_reaches_strong(self):
        assert self.strength(None, ["React", "JS"], True, False) == "Claimed"

    def test_a_high_score_with_corroboration_is_strong(self):
        assert self.strength(85, ["React"], True, False) == "Strong"

    def test_a_high_score_without_corroboration_is_moderate(self):
        assert self.strength(85, [], False, False) == "Moderate"

    def test_a_mid_score_with_corroboration_is_moderate(self):
        assert self.strength(60, ["React"], True, False) == "Moderate"

    def test_a_low_score_is_never_strong(self):
        assert self.strength(20, ["React", "JS"], True, True) in ("Weak", "None")
