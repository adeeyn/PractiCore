"""Feature-vector and question-bank tests (no DB, spaCy or sklearn needed)."""

from practicore.ml.features import DOMAIN_FEATURES, FEATURE_NAMES, build_features
from practicore.services.matching_service import MatchingService
from practicore.services.skill_taxonomy import SkillTaxonomy


class TestFeatureVector:
    def test_row_matches_feature_names(self):
        row = build_features({"skills": "Python, SQL"}, ["Python", "Java"])
        assert len(row) == len(FEATURE_NAMES)

    def test_every_feature_is_a_plain_float(self):
        row = build_features(
            {"skills": "Python", "assessment_overall": 70}, ["Python"]
        )
        assert all(isinstance(value, float) for value in row)

    def test_full_skill_overlap_is_one(self):
        row = build_features({"skills": "Python, SQL"}, ["Python", "SQL"])
        assert row[FEATURE_NAMES.index("resume_overlap_ratio")] == 1.0
        assert row[FEATURE_NAMES.index("missing_skill_count")] == 0.0

    def test_no_skill_overlap_is_zero(self):
        row = build_features({"skills": "HTML"}, ["Python", "SQL"])
        assert row[FEATURE_NAMES.index("resume_overlap_ratio")] == 0.0
        assert row[FEATURE_NAMES.index("has_resume")] == 1.0
        assert row[FEATURE_NAMES.index("missing_skill_count")] == 2.0

    def test_empty_posting_skills_does_not_divide_by_zero(self):
        row = build_features({"skills": "Python"}, [])
        assert row[FEATURE_NAMES.index("resume_overlap_ratio")] == 0.0
        assert row[FEATURE_NAMES.index("posting_skill_count")] == 0.0

    def test_has_resume_and_has_assessment_flags(self):
        row = build_features({"skills": "", "assessment_overall": 0}, ["Python"])
        assert row[FEATURE_NAMES.index("has_resume")] == 0.0
        assert row[FEATURE_NAMES.index("has_assessment")] == 0.0

    def test_assessment_percentage_is_clamped(self):
        row = build_features({"skills": "Python", "assessment_overall": 500}, ["Python"])
        assert row[FEATURE_NAMES.index("assessment_overall_pct")] == 100.0

    def test_domain_columns_follow_the_taxonomy_order(self):
        scores = {domain: 50 + index for index, domain in enumerate(SkillTaxonomy.DOMAIN_TRACK_CODES)}
        row = build_features({"skills": "Python", "domain_scores": scores}, ["Python"])
        first = FEATURE_NAMES.index(DOMAIN_FEATURES[0])
        expected = [float(scores[domain]) for domain in SkillTaxonomy.DOMAIN_TRACK_CODES]
        assert row[first:first + len(expected)] == expected

    def test_skills_accept_a_list_or_a_string(self):
        from_list = build_features({"skills": ["Python", "SQL"]}, ["Python"])
        from_string = build_features({"skills": "python, sql"}, ["Python"])
        assert from_list == from_string


class TestSkillInputShapes:
    """Regression cover: a set has no .split(), so it must never be parsed as a string.

    The route views pass an already-parsed set while the seeder passes a raw
    comma-separated string, and both reach the same scorer.
    """

    def test_fallback_accepts_a_parsed_set(self):
        matcher = MatchingService()
        score = matcher.score({"skills": {"Python"}}, ["Python", "SQL"], assessment_percentage=100)
        # 50% resume overlap (1 of 2) at 30% weight, 100% assessment at 70%.
        assert score == 100 - round(0.5 * 30)

    def test_fallback_accepts_a_comma_string(self):
        matcher = MatchingService()
        from_set = matcher.score({"skills": {"Python"}}, ["Python", "SQL"], assessment_percentage=100)
        from_str = matcher.score({"skills": "Python"}, ["Python", "SQL"], assessment_percentage=100)
        assert from_set == from_str

    def test_fallback_accepts_a_list(self):
        matcher = MatchingService()
        score = matcher.score({"skills": ["Python"]}, ["Python", "SQL"], assessment_percentage=100)
        assert score == 100 - round(0.5 * 30)

    def test_fallback_accepts_none(self):
        matcher = MatchingService()
        assert matcher.score({"skills": None}, ["Python"], assessment_percentage=0) == 0

    def test_parse_skill_string_handles_a_set(self):
        assert SkillTaxonomy.parse_skill_string({"Python", "SQL"}) == {"python", "sql"}

    def test_parse_skill_string_handles_a_list(self):
        assert SkillTaxonomy.parse_skill_string(["Python", "SQL"]) == {"python", "sql"}

    def test_parse_skill_string_handles_none(self):
        assert SkillTaxonomy.parse_skill_string(None) == set()

    def test_parse_skill_string_still_splits_strings(self):
        assert SkillTaxonomy.parse_skill_string("Python, SQL") == {"python", "sql"}

    def test_build_features_accepts_both_shapes(self):
        from_set = build_features({"skills": {"Python"}}, ["Python"])
        from_str = build_features({"skills": "Python"}, ["Python"])
        assert from_set == from_str


class TestMatchingFallback:
    def test_falls_back_when_no_model_loaded(self):
        matcher = MatchingService()
        assert matcher.uses_model is False
        # 50% resume overlap (1 of 2 skills) at 30% weight, 100% assessment at 70%.
        score = matcher.score(
            {"skills": "Python"}, ["Python", "SQL"], assessment_percentage=100
        )
        assert score == 100 - round(0.5 * 30)

    def test_full_skill_match_reaches_100(self):
        matcher = MatchingService()
        score = matcher.score(
            {"skills": "Python, SQL"}, ["Python"], assessment_percentage=100
        )
        assert score == 100

    def test_label_is_honest_when_fallback(self):
        matcher = MatchingService()
        assert "Random Forest" not in matcher.status_line()
        assert "not loaded" in matcher.status_line()

    def test_load_missing_file_is_not_fatal(self):
        matcher = MatchingService.load("definitely/not/here.joblib")
        assert matcher.uses_model is False
        assert matcher._load_error

    def test_load_disabled_is_not_fatal(self):
        matcher = MatchingService.load("anything.joblib", enabled=False)
        assert matcher.uses_model is False

    def test_score_is_always_in_range(self):
        matcher = MatchingService()
        for skills, posting, pct in [("", [], 0), ("Python", ["Python"], 100), ("HTML", ["SQL"], 0)]:
            score = matcher.score({"skills": skills}, posting, assessment_percentage=pct)
            assert 0 <= score <= 100
