"""Question-selection tests: the core + resume-triggered bank.

Uses a fake question repository so no MySQL is needed, and a real Flask
app context because AssessmentService reads its settings from current_app.
"""
from flask import Flask

from practicore.services.assessment_service import AssessmentService
from practicore.services.recommendation_service import RecommendationService
from practicore.services.skill_taxonomy import SkillTaxonomy

# One synthetic question per (domain, index) so the bank is easy to reason about.
PER_DOMAIN_POOL = 20


class FakeQuestionRepository:
    def __init__(self):
        self.rows = []
        question_id = 1
        # course_track holds the SHORT TRACK CODE (DEV, NET, ...), which is what
        # the real assessment_questions rows are keyed on.
        for code in SkillTaxonomy.DOMAIN_TRACK_CODES.values():
            for _ in range(PER_DOMAIN_POOL):
                self.rows.append({
                    "id": question_id,
                    "course_track": code,
                    "difficulty": "medium",
                })
                question_id += 1

    def all(self):
        return [dict(row) for row in self.rows]


# `app` and `service` are supplied by tests/run_tests.py, or by pytest if the
# fixtures below are enabled. They are plain functions here so the suite runs
# on a bare Python install with no pytest available.


def app():
    application = Flask(__name__)
    application.config.update(
        QUESTIONS_PER_DOMAIN=15,
        CORE_QUESTIONS_PER_DOMAIN=8,
        RESUME_QUESTIONS_PER_SKILL=2,
        MAX_QUESTIONS_PER_DOMAIN=15,
        QUESTION_TIME_LIMITS={"easy": 30, "medium": 45, "hard": 60},
        ASSESSMENT_GRADING_BYPASS=False,
    )
    return application


def service():
    return AssessmentService(questions=FakeQuestionRepository())


def _count_per_domain(grouped):
    return {domain: len(items) for domain, items in grouped.items()}


class TestDomainMapping:
    """Regression cover for the substring-matching bug in map_to_domain."""

    def test_short_track_codes_map_correctly(self):
        for domain, code in SkillTaxonomy.DOMAIN_TRACK_CODES.items():
            assert SkillTaxonomy.map_to_domain(code) == domain

    def test_full_category_names_round_trip(self):
        # "Business Systems & Project Management" contains "NA" (Management),
        # which used to file it under Systems & Networks.
        for domain in SkillTaxonomy.DOMAIN_TRACK_CODES:
            assert SkillTaxonomy.map_to_domain(domain) == domain

    def test_category_names_are_case_insensitive(self):
        assert SkillTaxonomy.map_to_domain("business systems & project management") == (
            "Business Systems & Project Management"
        )

    def test_blank_input_falls_back_to_the_default(self):
        assert SkillTaxonomy.map_to_domain("") == SkillTaxonomy.DEFAULT_CATEGORY
        assert SkillTaxonomy.map_to_domain(None) == SkillTaxonomy.DEFAULT_CATEGORY

    def test_role_still_drives_mapping_when_there_is_no_track(self):
        assert SkillTaxonomy.map_to_domain("", "Network Administrator") == (
            "Systems, Infrastructure & Networks"
        )


class TestMatchScoreWeighting:
    """The assessment must outweigh the resume.

    A 50/50 average let a missing resume keyword erase a strong assessment
    result, which contradicts the research note that objective items are the
    primary evidence and self-reported skills are not proof of capability.
    """

    REQUIRED = ["JavaScript", "HTML", "CSS", "React", "Flask", "Python", "Git"]
    MINE = {"react", "git", "javascript", "sql", "linux"}  # 3 of 7

    def test_weights_sum_to_one(self):
        from practicore.config import Config

        total = Config.MATCH_ASSESSMENT_WEIGHT + Config.MATCH_RESUME_WEIGHT
        assert abs(total - 1.0) < 1e-9

    def test_assessment_carries_more_weight_than_resume(self):
        from practicore.config import Config

        assert Config.MATCH_ASSESSMENT_WEIGHT > Config.MATCH_RESUME_WEIGHT

    def test_a_strong_assessment_is_not_erased_by_missing_keywords(self):
        """The reported 68% case: 94% assessment, 3 of 7 skills on the resume."""
        from practicore.config import Config

        resume_pct = round(3 / 7 * 100)
        expected = round(94 * Config.MATCH_ASSESSMENT_WEIGHT + resume_pct * Config.MATCH_RESUME_WEIGHT)
        actual = RecommendationService.combined_match_score(self.REQUIRED, self.MINE, 94)
        assert actual == expected
        assert actual > 68, "a 94%% assessment should not score below the old 50/50 result"
        assert actual >= 75

    def test_perfect_everything_scores_100(self):
        from practicore.config import Config

        resume_pct = round(3 / 7 * 100)
        assert RecommendationService.combined_match_score(
            self.REQUIRED, self.MINE, 100
        ) == round(100 * Config.MATCH_ASSESSMENT_WEIGHT + resume_pct * Config.MATCH_RESUME_WEIGHT)

    def test_raising_the_assessment_always_raises_the_score(self):
        low = RecommendationService.combined_match_score(self.REQUIRED, self.MINE, 50)
        high = RecommendationService.combined_match_score(self.REQUIRED, self.MINE, 90)
        assert high > low

    def test_more_resume_overlap_always_raises_the_score(self):
        few = RecommendationService.combined_match_score(self.REQUIRED, {"git"}, 80)
        many = RecommendationService.combined_match_score(
            self.REQUIRED, {"git", "javascript", "html", "css", "react", "python"}, 80
        )
        assert many > few

    def test_score_is_always_bounded(self):
        for pct in (0, 50, 94, 100, 150, -10):
            score = RecommendationService.combined_match_score(self.REQUIRED, self.MINE, pct)
            assert 0 <= score <= 100


class TestDomainRelevantScoring:
    """A posting should be scored on the student's score in ITS category."""

    DOMAINS = {
        "Software & Application Development": 96,
        "Systems, Infrastructure & Networks": 40,
        "Data, AI & Analytics": 55,
    }

    def test_uses_the_domain_score_not_the_overall(self):
        relevant = RecommendationService.relevant_assessment_score(
            ["JavaScript", "HTML", "CSS", "React", "Flask", "Python", "Git"],
            self.DOMAINS,
            94,
        )
        assert relevant == 96

    def test_weak_domain_lowers_the_score_below_a_strong_overall(self):
        """A Networking-strong student must not out-score a DEV posting on average.

        Resume overlap is held equal so the only variable is which domain score
        the posting reads.
        """
        web = ["JavaScript", "HTML", "React", "Python"]
        network = ["TCP/IP", "Networking", "Cisco", "VLAN"]
        # 2 of 4 on both sides, so resume overlap is identical.
        mine = {"javascript", "react", "networking", "cisco"}

        # Overall (70) is inflated by a strong DEV score and a weak NET score; the
        # DEV posting is the one this student is actually strong for.
        overall = 70
        web_score = RecommendationService.combined_match_score(web, mine, overall, self.DOMAINS)
        network_score = RecommendationService.combined_match_score(
            network, mine, overall, self.DOMAINS
        )
        assert web_score > network_score
        # Using the flat 70 for both would have hidden the 96 vs 40 gap.
        assert web_score - network_score > 20

    def test_an_inflated_overall_cannot_rescue_a_weak_domain(self):
        """A 100% overall from other domains must not win a posting you scored 0% in."""
        domains = dict(self.DOMAINS)
        domains["Cybersecurity & Risk Management"] = 100  # a strong unrelated domain
        network = ["TCP/IP", "Networking", "Cisco", "VLAN"]
        score = RecommendationService.combined_match_score(
            network, {"networking"}, 100, domains
        )
        relevant = RecommendationService.relevant_assessment_score(network, domains, 100)
        assert relevant == self.DOMAINS["Systems, Infrastructure & Networks"]
        assert score < 100

    def test_falls_back_to_overall_without_domain_scores(self):
        assert RecommendationService.relevant_assessment_score(
            ["JavaScript", "HTML"], {}, 94
        ) == 94

    def test_falls_back_when_the_domain_is_absent(self):
        assert RecommendationService.relevant_assessment_score(
            ["JavaScript", "HTML"], {"Cybersecurity & Risk Management": 50}, 94
        ) == 94

    def test_handles_missing_posting_skills(self):
        assert RecommendationService.relevant_assessment_score([], self.DOMAINS, 94) == 94


class TestMatchBreakdown:
    REQUIRED = ["JavaScript", "HTML", "CSS", "React", "Flask", "Python", "Git"]
    MINE = {"react", "git", "javascript", "sql", "linux"}

    def test_reports_the_components_that_made_the_score(self):
        breakdown = RecommendationService.match_breakdown(self.REQUIRED, self.MINE, 94)
        for key in ("score", "matched_skills", "missing_skills", "resume_percent",
                    "assessment_overall", "assessment_relevant",
                    "assessment_weight", "resume_weight"):
            assert key in breakdown, key

    def test_matched_and_missing_partition_the_requirements(self):
        b = RecommendationService.match_breakdown(self.REQUIRED, self.MINE, 94)
        assert len(b["matched_skills"]) == b["matched_count"] == 3
        assert set(b["matched_skills"]) | set(b["missing_skills"]) == set(self.REQUIRED)
        assert not set(b["matched_skills"]) & set(b["missing_skills"])

    def test_breakdown_score_matches_the_scorer(self):
        b = RecommendationService.match_breakdown(self.REQUIRED, self.MINE, 94)
        assert b["score"] == RecommendationService.combined_match_score(self.REQUIRED, self.MINE, 94)

    def test_weights_are_reported_as_fractions(self):
        b = RecommendationService.match_breakdown(self.REQUIRED, self.MINE, 94)
        assert 0 <= b["assessment_weight"] <= 1
        assert 0 <= b["resume_weight"] <= 1


class TestCompetencyBands:
    """A score must never be labelled higher than it earned.

    The original code had two tiers, so a 10% score was reported as
    "Intermediate / Competent". The bands below must be monotonic.
    """

    def test_a_low_score_is_not_called_competent(self):
        assert "Competent" not in AssessmentService.competency_level_for(10)
        assert "Competent" not in AssessmentService.competency_level_for(25)

    def test_zero_is_the_weakest_band(self):
        assert AssessmentService.competency_level_for(0) == "Below Foundational"

    def test_high_scores_reach_the_top_band(self):
        assert AssessmentService.competency_level_for(100) == "Advanced / Job-Ready"
        assert AssessmentService.competency_level_for(85) == "Advanced / Job-Ready"

    def test_middle_scores_land_in_a_middle_band(self):
        assert AssessmentService.competency_level_for(75) == "Proficient"
        assert AssessmentService.competency_level_for(55) == "Developing"
        assert AssessmentService.competency_level_for(35) == "Foundational"

    def test_labels_get_stronger_as_the_score_rises(self):
        # COMPETENCY_BANDS is ordered strongest-first, so a rising score must
        # produce a strictly non-increasing band index.
        order = [AssessmentService.competency_level_for(p) for p in range(0, 101, 5)]
        rank = {label: i for i, (_t, label) in enumerate(AssessmentService.COMPETENCY_BANDS)}
        ranks = [rank[label] for label in order]
        assert ranks == sorted(ranks, reverse=True), (
            "band must not weaken as the score rises: %s" % list(zip(order, ranks))
        )

    def test_every_percentage_maps_to_exactly_one_band(self):
        for percent in range(0, 101):
            label = AssessmentService.competency_level_for(percent)
            assert label in {l for _t, l in AssessmentService.COMPETENCY_BANDS}


class TestCorePlusResumeTriggered:
    def test_every_domain_gets_core_questions_without_resume(self, app, service):
        with app.app_context():
            _, grouped, _ = service.build(student_skills=None)
        counts = _count_per_domain(grouped)
        for domain, count in counts.items():
            assert count == app.config["CORE_QUESTIONS_PER_DOMAIN"], (
                f"{domain} should get core questions even with no resume"
            )

    def test_resume_skills_add_questions_to_their_domain(self, app, service):
        with app.app_context():
            _, without_resume, _ = service.build(student_skills=None)
            _, with_resume, _ = service.build(student_skills={"Python", "React"})

        # Python/React both map to Software & Application Development.
        dev = "Software & Application Development"
        assert len(with_resume[dev]) > len(without_resume[dev])
        # An unrelated domain is unaffected.
        assert len(with_resume["Data, AI & Analytics"]) == len(
            without_resume["Data, AI & Analytics"]
        )

    def test_no_domain_exceeds_the_cap(self, app, service):
        with app.app_context():
            _, grouped, _ = service.build(student_skills={"Python", "React", "Django", "Flask"})
        for domain, count in _count_per_domain(grouped).items():
            assert count <= app.config["MAX_QUESTIONS_PER_DOMAIN"], f"{domain} exceeded the cap"

    def test_domain_map_covers_every_selected_question(self, app, service):
        with app.app_context():
            questions, _, domain_map = service.build(student_skills={"Python"})
        assert len(domain_map) == len(questions)

    def test_total_never_exceeds_cap_times_domains(self, app, service):
        with app.app_context():
            questions, _, _ = service.build(student_skills={"Python", "SQL", "Linux", "ITIL"})
        domains = len(SkillTaxonomy.categories())
        assert len(questions) <= app.config["MAX_QUESTIONS_PER_DOMAIN"] * domains

    def test_empty_resume_still_produces_an_assessment(self, app, service):
        with app.app_context():
            questions, grouped, domain_map = service.build(student_skills=set())
        assert questions
        assert grouped
        assert domain_map
