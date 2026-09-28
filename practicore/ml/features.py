"""The one place that turns (student, posting) into numbers for the model.

Training and inference must never disagree about the vector layout, so both the
offline trainer and the live scorer build rows through `build_features` and both
read `FEATURE_NAMES`.

Deliberately free of scikit-learn imports so the web app runs without them.
"""

from ..services.skill_taxonomy import SkillTaxonomy

# The six job categories, in a fixed order. The per-domain assessment columns
# follow this order, so appending a category here is a model-breaking change:
# existing artifacts will be rejected by the loader and the app falls back.
DOMAIN_FEATURES = [f"pct_{code.lower()}" for code in SkillTaxonomy.DOMAIN_TRACK_CODES.values()]

FEATURE_NAMES = [
    "resume_overlap_ratio",      # share of the posting's skills the resume proves
    "assessment_overall_pct",    # measured competency, 0-100
    "has_resume",                # 1 when any skill was extracted
    "has_assessment",            # 1 when the student has taken the assessment
    "posting_skill_count",       # how demanding the posting is
    "matched_skill_count",
    "missing_skill_count",
] + DOMAIN_FEATURES

# The model is only allowed to score a pair whose domain columns are in this
# order; stored in the artifact and compared on load.
FEATURE_SCHEMA_VERSION = 1


def _student_skill_set(student):
    """Accepts either a raw comma string or an already-parsed set of skills."""
    skills = student.get("skills")
    if isinstance(skills, str):
        return SkillTaxonomy.parse_skill_string(skills)
    return {str(s).strip().lower() for s in (skills or []) if str(s).strip()}


def build_features(student, posting_skills):
    """Returns the feature row for one student/posting pair, in FEATURE_NAMES order.

    `student` is a mapping that may carry:
        skills            comma-separated string or iterable of skill names
        assessment_overall  overall competency percentage (0-100)
        domain_scores     {domain name: score_percent} from the last assessment

    Every value is a plain float, so the result feeds a NumPy array directly.
    """
    skills = _student_skill_set(student)
    required = [s for s in (posting_skills or []) if str(s).strip()]

    matched = SkillTaxonomy.match_required_skills(required, skills) if required else []
    matched_count = len(matched)
    posting_count = len(required)

    overlap_ratio = (matched_count / posting_count) if posting_count else 0.0

    overall = student.get("assessment_overall")
    overall = float(overall) if overall is not None else 0.0
    overall = max(0.0, min(100.0, overall))

    domain_scores = student.get("domain_scores") or {}
    domain_pcts = []
    for domain in SkillTaxonomy.DOMAIN_TRACK_CODES:
        value = domain_scores.get(domain)
        value = float(value) if value is not None else 0.0
        domain_pcts.append(max(0.0, min(100.0, value)))

    row = [
        overlap_ratio,
        overall,
        1.0 if skills else 0.0,
        1.0 if overall > 0 else 0.0,
        float(posting_count),
        float(matched_count),
        float(posting_count - matched_count),
    ] + domain_pcts

    # Cheap guard against a future refactor silently changing the vector length,
    # which sklearn would otherwise reject with an opaque error at predict time.
    assert len(row) == len(FEATURE_NAMES), "feature row does not match FEATURE_NAMES"
    return row


def feature_importance_report(model):
    """Pairs each feature with the model's importance, biggest first."""
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return []
    pairs = zip(FEATURE_NAMES, importances)
    return sorted(pairs, key=lambda pair: pair[1], reverse=True)
