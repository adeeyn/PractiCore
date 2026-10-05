"""Loads the competency taxonomy, the parallel question forms and the posting
requirements into the database.

Run it with:  flask --app app seed-competencies

Safe to re-run: every write is an upsert keyed on a natural key (competency
code, competency+set code, question code), so re-seeding refreshes in place.
"""
from .database import Database, upsert_sql
from .repositories.competency_repository import CompetencyRepository
from .services.competency_taxonomy import (
    COMPETENCIES,
    SKILL_COMPETENCY_MAP,
    required_competencies,
)
from .services.question_forms import (
    EXTRA_COMPETENCY_ITEMS,
    ITEMS_PER_SET,
    PARALLEL_FORMS,
    assign_competency,
)
from .services.research_bank import as_rows

SET_CODES = ("A", "B", "C")


def _parallel_question_rows():
    """New items for the parallel forms, shaped for assessment_questions.

    Codes are derived from the competency and set so re-seeding updates the same
    row instead of accumulating duplicates.
    """
    for competency, forms in sorted(PARALLEL_FORMS.items()):
        for set_code, items in sorted(forms.items()):
            for index, (text, options, key, standard_ref) in enumerate(items, start=1):
                code = "PF-%s-%s%d" % (competency, set_code, index)
                yield {
                    "question_code": code,
                    "course_track": _track_for(competency),
                    "category": competency,
                    "competency": competency,
                    "target_role": "Parallel form %s" % set_code,
                    "question_type": "Objective",
                    "difficulty": "medium",
                    "standard_ref": standard_ref,
                    "pathway": "All",
                    "question_text": text,
                    "option_a": options[0],
                    "option_b": options[1],
                    "option_c": options[2],
                    "option_d": options[3],
                    "correct_option": key,
                    "set_code": set_code,
                }


def _assign_published_items():
    """Groups the published bank (set A) plus borrowed items by competency."""
    buckets = {}
    for item in as_rows():
        code = assign_competency(item)
        item = dict(item)
        item["set_code"] = "A"
        buckets.setdefault(code, []).append(item)

    # Competencies with no dedicated sub-domain borrow specific published items,
    # so every core competency can still be measured.
    #
    # Guarded against duplicates: an item already present for this competency from
    # the sub-domain mapping is not added twice. Q27 belongs to the Operating
    # Systems sub-domain AND is listed here, so without this guard it would occupy
    # both Form A slots and push the borrowed Q24 out.
    for competency, codes in EXTRA_COMPETENCY_ITEMS.items():
        already = {item["question_code"] for item in buckets.get(competency, [])}
        for code in codes:
            if code in already:
                continue
            for item in as_rows():
                if item["question_code"] == code:
                    copy = dict(item)
                    copy["competency"] = competency
                    copy["set_code"] = "A"
                    buckets.setdefault(competency, []).append(copy)
                    already.add(code)
    return buckets


def seed_competencies(seed_posting_requirements=True):
    """Writes the taxonomy, the forms, the parallel items and posting needs."""
    repo = CompetencyRepository()
    competency_count, skill_count = repo.seed_taxonomy(COMPETENCIES, SKILL_COMPETENCY_MAP)

    published = _assign_published_items()
    parallel = {}
    for item in _parallel_question_rows():
        parallel.setdefault(item["competency"], []).append(item)

    inserted = 0
    with Database.cursor(commit=True) as cursor:
        for competency in sorted(set(published) | set(parallel)):
            for set_code in SET_CODES:
                # Set A draws on the published bank (plus any borrowed items);
                # B and C draw on the parallel forms.
                if set_code == "A":
                    items = published.get(competency, [])[:ITEMS_PER_SET]
                else:
                    items = [i for i in parallel.get(competency, [])
                             if i["set_code"] == set_code][:ITEMS_PER_SET]
                if not items:
                    continue

                cursor.execute(
                    upsert_sql(
                        "question_sets",
                        ["competency_code", "set_code", "label", "question_count"],
                        ["competency_code", "set_code"],
                        ["label", "question_count"],
                    ),
                    (competency, set_code,
                     "Form %s for %s" % (set_code, competency), len(items)),
                )

                # Always look the id up. lastrowid is unreliable here: on an
                # ON DUPLICATE KEY UPDATE that took the UPDATE branch, it returns
                # a stale value from an earlier insert, which silently assigned one
                # form's questions to another form's set.
                cursor.execute(
                    "SELECT id FROM question_sets WHERE competency_code = %s AND set_code = %s",
                    (competency, set_code))
                set_id = cursor.fetchone()["id"]

                for item in items:
                    # Insert (or refresh) the question itself. A borrowed item
                    # (e.g. Q22 into the Troubleshooting form) already exists, so
                    # the upsert refreshes that row and returns its real id --
                    # which is what lets one question serve two forms.
                    cursor.execute(
                        upsert_sql(
                            "assessment_questions",
                            ["question_code", "course_track", "category", "competency", "set_id",
                             "target_role", "question_type", "difficulty", "standard_ref",
                             "question_text", "option_a", "option_b", "option_c", "option_d",
                             "correct_option"],
                            ["question_code"],
                            ["question_text", "option_a", "option_b", "option_c",
                             "option_d", "correct_option"],
                        ),
                        (item["question_code"], item["course_track"], item["category"],
                         item.get("competency") or competency, set_id, item["target_role"],
                         item["question_type"], item["difficulty"], item["standard_ref"],
                         item["question_text"], item["option_a"], item["option_b"],
                         item["option_c"], item["option_d"], item["correct_option"]),
                    )

                    cursor.execute(
                        "SELECT id FROM assessment_questions WHERE question_code = %s",
                        (item["question_code"],))
                    question_id = cursor.fetchone()["id"]

                    # Membership is the authoritative many-to-many link.
                    # Postgres: ON CONFLICT on the composite key, do nothing.
                    cursor.execute(
                        "INSERT INTO question_set_members (set_id, question_id) "
                        "VALUES (%s, %s) "
                        "ON CONFLICT (set_id, question_id) DO NOTHING",
                        (set_id, question_id),
                    )
                    inserted += 1

    forms = repo.competencies_with_forms()
    coverage = {
        code: sorted(f["set_code"] for f in by_code)
        for code, by_code in sorted(forms.items())
    }
    full = [c for c, s in coverage.items() if len(s) == 3]
    partial = {c: s for c, s in coverage.items() if len(s) < 3}

    postings = 0
    if seed_posting_requirements:
        postings = _seed_posting_requirements(repo)

    return {
        "competencies": competency_count,
        "skills_mapped": skill_count,
        "questions_written": inserted,
        "competencies_with_forms": len(forms),
        "full_three_set": full,
        "partial_forms": partial,
        "postings_updated": postings,
    }


def _seed_posting_requirements(repo):
    """Derives what each seeded posting asks for, from its skills and blurb."""
    from .repositories.posting_repository import PostingRepository

    count = 0
    for posting in PostingRepository().all_with_skills():
        mapping = required_competencies(
            posting.get("skills") or [],
            "%s %s" % (posting.get("title") or "", posting.get("description") or ""),
        )
        if not mapping:
            continue
        # A primary requirement outranks a passing mention.
        payload = {
            code: {
                "importance": "essential" if strength == "primary" else "preferred",
                "required_percent": 60 if strength == "primary" else 50,
            }
            for code, strength in mapping.items()
        }
        repo.save_posting_requirements(posting["id"], payload)
        count += 1
    return count


def _track_for(competency):
    from .services.competency_taxonomy import COMPETENCIES

    return COMPETENCIES.get(competency, ("", "Software & Application Development", 0, ""))[1]
