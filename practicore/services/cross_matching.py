"""Compares a student competency profile against what an internship requires.

The central rule, from the research design: a resume-listed skill is a CLAIM and
an assessment result is EVIDENCE. So the assessment decides the score and the
resume can only corroborate it. A student with no result in a required
competency cannot be rescued by listing the skill.
"""
import json

# How the two evidence types are combined. The assessment leads because it is the
# only measurable evidence; a claim is worth a third of the total at most.
ASSESSMENT_WEIGHT = 0.7
EVIDENCE_WEIGHT = 0.3

# A required competency the student has never been assessed on scores zero
# coverage, not "unknown", because the posting asked for it and no result exists.
UNASSESSED_COVERAGE = 0.0

# Evidence-strength ladder, used when turning a claim into a 0-100 contribution.
# "Claimed" is the corroboration value for a resume skill with no corroboration
# yet - it is deliberately worth far less than the weakest demonstrated result,
# and it is never used as the competency's status. Status comes from
# CompetencyRepository.assessment_state (Assessed / Assessment Required /
# Not assessed); a claim only ever reaches here as a minor corroboration term.
STRENGTH_VALUES = {
    "Strong": 100,
    "Moderate": 75,
    "Weak": 45,
    "Claimed": 25,   # claim only, never corroborated by an assessment
    "None": 0,
}


def score_posting(profile, requirements):
    """Compatibility of one profile against one posting's requirements.

    Returns a dict with the total plus the per-competency detail the UI shows, so
    a student can see exactly which requirement is holding the score down.
    """
    if not requirements:
        return {
            "total_score": 0, "assessment_score": 0, "evidence_score": 0,
            "competencies_met": 0, "competencies_total": 0, "detail": [],
        }

    detail = []
    weighted_total = 0.0
    weight_sum = 0.0
    met = 0

    for req in requirements:
        code = req["competency_code"]
        required = req.get("required_percent") or 60
        importance = req.get("importance") or "preferred"
        # An essential requirement counts double, so missing one hurts more.
        weight = 2.0 if importance == "essential" else 1.0

        entry = profile.get(code) or {}
        percent = entry.get("score_percent")
        strength = entry.get("evidence_strength") or "None"

        if percent is None:
            # Never assessed in a competency the posting needs: no coverage.
            coverage = UNASSESSED_COVERAGE
            status = "Not assessed"
        elif percent >= required:
            coverage = percent
            status = "Met"
            met += 1
        else:
            # Proportional shortfall rather than a flat penalty, so being just
            # under the bar is not scored the same as having no evidence.
            coverage = percent
            status = "Below requirement"

        evidence_value = STRENGTH_VALUES.get(strength, 0)
        weighted_total += coverage * weight
        weight_sum += weight

        detail.append({
            "code": code,
            "name": entry.get("name") or code,
            "importance": importance,
            "required_percent": required,
            "score_percent": percent,
            "coverage": round(coverage),
            "evidence_strength": strength,
            "evidence_skills": entry.get("evidence_skills") or [],
            "status": status,
        })

    assessment_score = round(weighted_total / weight_sum) if weight_sum else 0
    # Corroboration is averaged over the requirements so one strong claim on an
    # unrelated competency cannot lift the whole score.
    evidence_score = round(
        sum(STRENGTH_VALUES.get(d["evidence_strength"], 0) for d in detail) / len(detail)
    ) if detail else 0

    total = round(assessment_score * ASSESSMENT_WEIGHT + evidence_score * EVIDENCE_WEIGHT)

    return {
        "total_score": max(0, min(100, total)),
        "assessment_score": assessment_score,
        "evidence_score": evidence_score,
        "competencies_met": met,
        "competencies_total": len(requirements),
        "detail": detail,
        "detail_json": json.dumps(detail),
    }


def score_all(profile, requirements_by_posting):
    """Scores one profile against many postings -> {posting_id: result}."""
    return {
        posting_id: score_posting(profile, requirements)
        for posting_id, requirements in requirements_by_posting.items()
    }
