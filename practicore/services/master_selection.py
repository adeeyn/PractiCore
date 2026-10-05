"""
Adaptive question selection for the 130-item master bank.

    build_master_assessment(student_id, resume_skills, posting, repo, rng, target)

Why this is separate from choose_forms()
-----------------------------------------
choose_forms() serves ONE form per competency, which caps an attempt at
2 x (competencies) = 17-36 questions. The master bank holds 10 items per
competency, so the 40-50 target is only reachable by drawing several items per
competency from the pool rather than one fixed form.

The algorithm (hybrid: weighted quota per competency, capped, coverage-weighted)
--------------------------------------------------------------------------
1. Cross-match. select_competencies() has already merged core + resume + posting
   and recorded WHY each competency was chosen. That list is the pool, not the
   whole bank, so a networking student is not asked about cybersecurity for no
   reason.
2. Weight. A competency asked for by the POSTING or the RESUME outranks a core
   competency, because it is the one the student is actually being screened on.
   Core still gets a floor so nobody escapes the baseline.
3. Quota. The target is split across the selected competencies by weight, with a
   per-competency cap so one area cannot swallow the attempt.
4. Staleness. Within a competency, never-seen items come first, then the least
   recently seen, then the fewest times seen. When the unseen pool is exhausted
   the selector falls back to older items rather than shortening the attempt:
   coverage is never traded away to avoid a repeat.
5. Difficulty. Easy/medium/hard are spread proportionally inside each competency,
   so a competency is not scored on one difficulty band alone.

The total is clamped to [MIN_QUESTIONS, MAX_QUESTIONS] and, when the bank cannot
supply the target, the shortfall is reported rather than hidden.
"""
import random

from .assessment_service import AssessmentService
from .assessment_selection import select_competencies

# Requested assessment size. The lower bound matters: dropping below it would
# make a competency-level percentage rest on one or two items.
MIN_QUESTIONS = 40
TARGET_QUESTIONS = 45
MAX_QUESTIONS = 50

# No single competency may take more than this share of the attempt, so a posting
# naming eight skills cannot turn into an eight-section paper.
MAX_SHARE_PER_COMPETENCY = 0.30

# Relative difficulty mix inside a competency. Weights rather than fixed counts,
# so a small competency pool (say 4 items) still spreads instead of picking only
# its easy items.
DIFFICULTY_WEIGHTS = (("easy", 0.25), ("medium", 0.50), ("hard", 0.25))

# Weight by why a competency was selected: the posting is what the employer

# No competency is assessed on fewer than this many items when the bank allows it.
# Below two, a competency score is effectively a coin toss.
MIN_PER_COMPETENCY = 2


def allocate_quota(codes, weights, available, target):
    """Splits `target` questions across `codes` by weight, clamped to availability.

    Largest-remainder apportionment followed by a top-up pass, then a fairness pass
    so no competency sits below MIN_PER_COMPETENCY while another still has spare.
    No competency can exceed MAX_SHARE_PER_COMPETENCY of the target. Returns
    {code: count}.
    """
    if not codes:
        return {}

    cap = max(MIN_PER_COMPETENCY, int(target * MAX_SHARE_PER_COMPETENCY))
    quota = {code: 0 for code in codes}

    total_weight = sum(weights.get(code, 1.0) for code in codes) or 1.0
    exact = {code: target * weights.get(code, 1.0) / total_weight for code in codes}

    for code in codes:
        quota[code] = min(int(exact[code]), cap, available.get(code, 0))

    # Top-up by largest fractional remainder, so the target is reached whenever the
    # bank can supply it.
    shortfall = target - sum(quota.values())
    while shortfall > 0:
        progressed = False
        for code in sorted(codes, key=lambda c: (-(exact[c] - int(exact[c])), c)):
            if shortfall <= 0:
                break
            ceiling = min(cap, available.get(code, 0))
            if quota[code] < ceiling:
                quota[code] += 1
                shortfall -= 1
                progressed = True
        if not progressed:
            break   # the bank cannot supply more; the shortfall is reported upstream

    # Fairness pass: lift a starved competency from one that is above the floor.
    for code in sorted(codes):
        while quota[code] < MIN_PER_COMPETENCY:
            donors = [c for c in codes
                      if c != code and quota[c] > MIN_PER_COMPETENCY]
            if not donors:
                break
            donor = max(donors, key=lambda c: (quota[c], c))
            quota[donor] -= 1
            quota[code] += 1
    return quota


def _staleness_rank(question, seen):
    """Sort key preferring never-seen, then least recently seen, then least seen.

    `seen` is {question_id: row}. A missing row sorts as never-seen, so a student
    with no history is treated as having seen nothing.
    """
    row = seen.get(question["id"])
    if not row:
        return (0, "", 0)
    return (1, str(row.get("last_seen_at") or ""), int(row.get("times_seen") or 0))


# actually asked for, so it outranks the always-on core.
WEIGHT_BY_SOURCE = {"posting": 3.0, "resume": 2.0, "core": 1.0}



def pick_items(pool, quota, seen, rng):
    """Chooses `quota` items from one competency's pool, favouring unseen ones.

    The difficulty mix is honoured first, taking the stalest available item in each
    band, then any remainder is filled from what is left, still stalest-first. So a
    competency is only filled from a single difficulty when that is all the bank has.
    """
    if quota <= 0 or not pool:
        return []

    ordered_by_staleness = sorted(pool, key=lambda q: _staleness_rank(q, seen))
    by_difficulty = {}
    for question in ordered_by_staleness:
        by_difficulty.setdefault(question.get("difficulty") or "medium", []).append(question)

    chosen, taken = [], set()
    for name, share in DIFFICULTY_WEIGHTS:
        want = max(1, round(quota * share))
        picked = 0
        for question in by_difficulty.get(name) or []:
            if picked >= want:
                break
            if question["id"] in taken:
                continue
            chosen.append(question)
            taken.add(question["id"])
            picked += 1

    # Remainder: anything the difficulty bands did not supply, stalest-first.
    if len(chosen) < quota:
        for question in ordered_by_staleness:
            if len(chosen) >= quota:
                break
            if question["id"] in taken:
                continue
            chosen.append(question)
            taken.add(question["id"])

    return chosen[:quota]


def build_master_assessment(student_id, resume_skills=None, posting=None,
                            repo=None, rng=None, target=None):
    """Assembles one adaptive attempt from the master bank.

    Returns the same shape AdaptiveAssessmentService.build() returns, so the
    existing route and template keep working unchanged.
    """
    from ..repositories import CompetencyRepository

    rng = rng or random
    repo = repo or CompetencyRepository()
    posting = posting or {}
    posting_id = posting.get("id")
    target = max(MIN_QUESTIONS, min(MAX_QUESTIONS, int(target or TARGET_QUESTIONS)))

    selected = select_competencies(
        resume_skills=resume_skills or [],
        posting_skills=posting.get("skills") or [],
        posting_text="%s %s" % (posting.get("title") or "", posting.get("description") or ""),
        posting_id=posting_id,
    )
    meta_by_code = {e["code"]: e for e in selected}

    pool = repo.question_pool_by_competency(list(meta_by_code))
    # Only a competency the cross-match actually selected may be assessed, and only
    # if the bank holds an active item for it. Intersecting with meta_by_code matters:
    # the repository can return codes for items the selection never asked about (the
    # published bank carries its own competency labels), and assessing those would
    # silently widen the paper beyond the student's resume and target posting.
    available = {
        code: len(rows)
        for code, rows in pool.items()
        if rows and code in meta_by_code
    }
    weights = {code: competency_weight(meta_by_code[code]) for code in available}

    quota = allocate_quota(sorted(available), weights, available, target)
    seen = repo.questions_seen_by_student(student_id)

    per_competency, ordered, shortfall = {}, [], {}
    for code in sorted(quota):
        want = quota[code]
        if want <= 0:
            continue
        items = pick_items(pool[code], want, seen, rng)
        if not items:
            shortfall[code] = "no active questions published"
            continue
        if len(items) < want:
            shortfall[code] = "only %d of %d requested items available" % (len(items), want)

        rng.shuffle(items)
        for question in items:
            question["competency"] = code
            question["time_limit"] = AssessmentService.time_limit_for(question)
        ordered.extend(items)
        per_competency[code] = {
            "name": meta_by_code[code]["name"],
            "is_core": meta_by_code[code]["is_core"],
            "sources": meta_by_code[code]["sources"],
            "triggered_by": meta_by_code[code]["triggered_by"],
            "set_id": None,
            "set_code": "MASTER",
            "question_ids": [q["id"] for q in items],
        }

    # A competency chosen by the cross-match but absent from the bank must still be
    # visible, or the student silently loses a section they can see is missing.
    for code in meta_by_code:
        if code not in per_competency:
            shortfall.setdefault(code, "no questions published yet")

    rng.shuffle(ordered)

    return {
        "questions": ordered,
        "per_competency": per_competency,
        "competency_map": {str(q["id"]): q["competency"] for q in ordered},
        "shortfall": shortfall,
        "selected": selected,
        "posting_id": posting_id,
        "target": target,
    }


def competency_weight(entry):
    """Selection weight for one competency, from the sources that raised it."""
    sources = set(entry.get("sources") or ())
    for source in ("posting", "resume", "core"):
        if source in sources:
            return WEIGHT_BY_SOURCE[source]
    return WEIGHT_BY_SOURCE["core"]
