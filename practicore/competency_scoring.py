"""Strength bands for a demonstrated competency score.

Kept OUT of practicore/services and practicore/repositories on purpose:

  * services/__init__ imports assessment_service, which imports repositories, so a
    repositories -> services import would close a cycle. That is exactly why
    competency_repository.py carries the comment "free of any `services` import".
  * Config must be able to read the same defaults, and importing a repository from
    config would pull mysql.connector into every process that reads settings.

This module therefore has no PractiCore imports at all. Both the repository (to
label a score) and Config (to publish the thresholds) read it from here, so the
band table exists once.

Existing project thresholds are preserved, not replaced:
  * AssessmentService.COMPETENCY_BANDS is the OVERALL band ladder shown on the
    results header ("Advanced / Job-Ready" etc.). Unchanged.
  * CompetencyRepository.evidence_strength's 70 / 50 cut-offs are the RESUME
    EVIDENCE corroboration ladder, where a score is only lifted when a project or
    experience entry backs it up. Unchanged, and still used by cross-matching.
  * The table below is the PER-COMPETENCY strength LEVEL. No such table existed
    before, so it is introduced here, in Config, rather than hard-coded in the
    template or in a template conditional.
"""

# (minimum percent, label), strongest first, so the first match wins.
# 0-59 Weak / 60-79 Moderate / 80-100 Strong.
STRENGTH_BANDS = (
    (80, "Strong"),
    (60, "Moderate"),
    (0, "Weak"),
)

# Shown when there is no demonstrated score at all. Kept distinct from every band
# above so "not measured" can never be mistaken for "measured and poor".
NO_SCORE_LABEL = None


def strength_level_for(percent, bands=None):
    """The strength band for a demonstrated score, or None when there is no score.

    `percent` of None means the competency was never assessed, which is NOT the
    same fact as scoring 0. Returning None keeps that distinction intact so the
    caller can render "Assessment Required" / "Not assessed" instead of a band.
    """
    if percent is None:
        return NO_SCORE_LABEL
    try:
        value = int(percent)
    except (TypeError, ValueError):
        return NO_SCORE_LABEL
    for threshold, label in (bands or STRENGTH_BANDS):
        if value >= threshold:
            return label
    return (bands or STRENGTH_BANDS)[-1][1]