"""Chooses which competencies to assess, and which parallel form to use.

Three inputs, one output: the set of competency codes to be measured, each
carrying the sources that asked for it. The sources are kept because they are
what makes the selection explainable ("why is this student being asked about
Operating Systems?") and because a posting-driven competency is a different
kind of claim from a core one.

The resume is treated as a *trigger*, never as proof: a resume skill causes a
competency to be verified, it does not contribute a score.
"""
import random

from .competency_taxonomy import (
    COMPETENCIES,
    CORE_COMPETENCY_CODES,
    competencies_for_skills,
    required_competencies,
)

SOURCE_CORE = "core"
SOURCE_RESUME = "resume"
SOURCE_POSTING = "posting"


def select_competencies(resume_skills=None, posting_skills=None, posting_text="",
                        posting_id=None, core_codes=None, max_targeted=None):
    """Merge the three sources into one deduplicated competency list.

    Returns a list of dicts:
        code, name, track, is_core, sources (sorted list), triggered_by
        (the skills/requirements that raised it), strength

    `max_targeted` caps how many NON-core competencies are included, so a posting
    demanding eight skills does not turn into an eight-section assessment. The
    core is never capped.
    """
    core_codes = tuple(core_codes or CORE_COMPETENCY_CODES)
    selected = {}

    def add(code, source, reason, strength="primary"):
        if code not in COMPETENCIES:
            return  # a skill mapped to something we do not assess
        entry = selected.setdefault(code, {
            "code": code,
            "name": COMPETENCIES[code][0],
            "track": COMPETENCIES[code][1],
            "is_core": code in core_codes,
            "sources": set(),
            "triggered_by": set(),
            "strength": "supporting",
        })
        entry["sources"].add(source)
        if reason:
            entry["triggered_by"].add(reason)
        # Any primary trigger makes the competency primary overall.
        if strength == "primary":
            entry["strength"] = "primary"

    for code in core_codes:
        add(code, SOURCE_CORE, "core competency")

    for skill, strength in competencies_for_skills(resume_skills or {}).items():
        add(skill, SOURCE_RESUME, skill, strength)

    for code, strength in required_competencies(
        posting_skills or {}, posting_text
    ).items():
        add(code, SOURCE_POSTING, code, strength)

    results = list(selected.values())
    for entry in results:
        entry["sources"] = sorted(entry["sources"])
        entry["triggered_by"] = sorted(entry["triggered_by"])

    # Core first, then targeted ones in a stable order.
    results.sort(key=lambda e: (not e["is_core"], e["code"]))

    if max_targeted:
        core = [e for e in results if e["is_core"]]
        targeted = [e for e in results if not e["is_core"]]
        # Prefer competencies the posting actually asked for when trimming.
        targeted.sort(key=lambda e: (SOURCE_POSTING not in e["sources"], e["code"]))
        results = core + targeted[:max_targeted]
        results.sort(key=lambda e: (not e["is_core"], e["code"]))

    for entry in results:
        entry["posting_id"] = posting_id
    return results


def choose_forms(competency_codes, sets_by_competency, exposure=None, rng=None):
    """Pick one parallel form per competency, avoiding forms already seen.

    `sets_by_competency` is {code: [{'id':.., 'set_code': 'A'}, ...]}.
    `exposure` is {code: [{'set_id':.., 'exposed_at': ..}, ...]} from
    question_exposure_history.

    Order of preference: a form never seen, then the one seen longest ago, then
    random. When a competency has fewer than three forms (the bank is still being
    expanded) the best available is used, and the shortfall is reported in
    `shortfall` so it is visible rather than silently ignored.
    """
    rng = rng or random
    exposure = exposure or {}
    chosen, shortfall = {}, {}

    for code in competency_codes:
        available = sets_by_competency.get(code) or []
        if not available:
            shortfall[code] = "no questions yet"
            continue

        seen = exposure.get(code) or []
        seen_ids = {row["set_id"] for row in seen}
        last_seen = {row["set_id"]: row.get("exposed_at") for row in seen}

        unseen = [s for s in available if s["id"] not in seen_ids]
        if unseen:
            pick = rng.choice(unseen)
        else:
            # All forms have been shown: take the one shown longest ago, so a
            # retake still rotates rather than repeating the latest attempt.
            pick = min(available, key=lambda s: str(last_seen.get(s["id"], "")))

        chosen[code] = pick
        if len(available) < 3:
            shortfall[code] = "only %d of 3 forms available" % len(available)

    return chosen, shortfall
