"""Loads the competency-coverage bank into `assessment_questions`.

Run it with:  flask --app app seed-coverage-bank

WHY A SEPARATE SEEDER
---------------------
master_bank_seed owns the 130 researcher-document items. This module owns the 60
items in services/competency_coverage_bank.py, which fill the six competencies
the document does not cover (DATA, SYS, GIT, OOP, DSA, CLOUD). Keeping them
separate means the master bank's provenance, key-correction audit and validation
claims stay exactly as they were, and the two sets can be re-seeded independently.

IDEMPOTENT, SAME AS THE MASTER SEEDER
-------------------------------------
Every row carries a stable `question_code` (MB2-<COMP>-<nn>), which
`assessment_questions` holds under a UNIQUE index (migration 008), so the write
is INSERT ... ON DUPLICATE KEY UPDATE. Re-running refreshes the same 60 rows,
creates nothing new, and contains no DELETE. The MB2- prefix cannot collide with
the document's MB- codes or with the published Q*/PF-* rows, so no existing
question is ever overwritten.

Nothing here inserts a competency. The six codes already exist in the taxonomy
(seeded by competency_seed), so this module never forks the framework.
"""

from .database import Database, upsert_sql
from .services.competency_coverage_bank import (
    COVERED_COMPETENCIES,
    SOURCE_TYPE,
    VALIDATION,
    answer_key_distribution,
    as_rows,
    counts_per_competency,
    verify_keys,
)

# Columns this seeder writes. `source_type`, `explanation`, `key_status` and
# `is_active` need migration 012; they are detected at runtime so a database
# without 012 still loads the older columns instead of failing outright.
CORE_COLUMNS = (
    "course_track", "category", "competency", "doc_competency", "target_role",
    "question_type", "difficulty", "standard_ref", "question_text",
    "option_a", "option_b", "option_c", "option_d", "correct_option",
    "explanation", "is_active", "source_type", "key_status",
)


def _table_columns(cursor):
    # Postgres: introspect via the information schema (no SHOW COLUMNS).
    cursor.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'assessment_questions'"
    )
    return {row["column_name"] for row in cursor.fetchall()}


def _existing_counts(cursor):
    """Active items already stored per competency, for the before/after report."""
    cursor.execute("""
        SELECT competency, SUM(is_active) AS active_items
        FROM assessment_questions
        WHERE competency IN (%s)
        GROUP BY competency
    """ % ",".join(["%s"] * len(COVERED_COMPETENCIES)), COVERED_COMPETENCIES)
    return {row["competency"]: int(row["active_items"] or 0) for row in cursor.fetchall()}


def seed_coverage_bank():
    """Inserts or refreshes the 60 coverage items. Returns a summary dict."""
    rows = as_rows()
    inserted = updated = skipped = 0

    with Database.cursor(commit=True) as cursor:
        available = _table_columns(cursor)
        columns = [c for c in CORE_COLUMNS if c in available]
        if "question_code" not in available:
            raise RuntimeError(
                "assessment_questions.question_code is missing - apply migration 008 "
                "before seeding the coverage bank."
            )
        before = _existing_counts(cursor)

        sql = upsert_sql(
            "assessment_questions",
            ["question_code"] + list(columns),
            ["question_code"],
            list(columns),
        )

        cursor.execute("SELECT question_code FROM assessment_questions")
        counts = {
            row["question_code"]
            for row in cursor.fetchall()
            if row["question_code"]
        }
        for row in rows:
            cursor.execute(sql, (row["question_code"],) + tuple(row[c] for c in columns))
            # Postgres reports rowcount 1 for both insert and update, so the
            # before-run counts decide: a row already at its final code is an update.
            if row["question_code"] in counts:
                updated += 1
            else:
                inserted += 1
                counts.add(row["question_code"])

        after = _existing_counts(cursor)

    verification = verify_keys()
    return {
        "items": len(rows),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "competencies": COVERED_COMPETENCIES,
        "per_competency": counts_per_competency(),
        "active_per_competency": counts_per_competency(active_only=True),
        "unresolved": sorted(c for c, v in verification.items()
                              if v["status"] != "Verified"),
        "before": before,
        "after": after,
        "source_type": SOURCE_TYPE,
        "validation": VALIDATION,
        "answer_key": answer_key_distribution(),
    }