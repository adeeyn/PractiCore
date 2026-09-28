"""Loads the research-based question bank into `assessment_questions`.

Run it with:  flask --app app seed-questions

Replaces whatever is in the table with the 43 researcher-developed items from
the PractiCore question bank. It is safe to run more than once: rows are matched
on `question_code`, so a re-run refreshes the items in place rather than
duplicating them, and `--keep-existing` skips the delete entirely.

The previous generic bank is removed with `--replace` (the default), because a
leftover item from the old bank would be scored against the new domain model and
silently distort the competency profile.
"""


import mysql.connector

from .database import Database
from .services.research_bank import answer_key_distribution, balanced_rows, expected_track_counts

# Columns written by the seeder. `question_code` needs migration 008; the rest
# already exist, so a database that predates 008 still works minus the code and
# pathway columns, which is why the insert is built dynamically below.
CORE_COLUMNS = [
    "course_track", "category", "competency", "target_role", "pathway",
    "question_type", "difficulty", "standard_ref", "question_text",
    "option_a", "option_b", "option_c", "option_d", "correct_option",
]


def _table_columns(cursor):
    cursor.execute("SHOW COLUMNS FROM assessment_questions")
    return {row["Field"] for row in cursor.fetchall()}


def seed_questions(replace=True):
    """Inserts (or refreshes) the 43 research items. Returns a summary dict."""
    rows = list(balanced_rows())
    inserted, updated, removed = 0, 0, 0

    with Database.cursor(commit=True) as cursor:
        available = _table_columns(cursor)
        columns = [c for c in CORE_COLUMNS if c in available]
        has_code = "question_code" in available

        if replace:
            # Clear the old generic bank first, so it cannot be scored against
            # the new domain model.
            cursor.execute("DELETE FROM assessment_questions")
            removed = cursor.rowcount

        for row in rows:
            payload = {c: row[c] for c in columns}
            if has_code:
                payload["question_code"] = row["question_code"]
                # Upsert on the published code so a re-run refreshes in place.
                cursor.execute(
                    """
                    INSERT INTO assessment_questions
                        (question_code, %s)
                    VALUES (%%s, %s)
                    ON DUPLICATE KEY UPDATE
                        %s
                    """ % (
                        ", ".join(columns),
                        ", ".join(["%s"] * len(columns)),
                        ", ".join(f"{c} = VALUES({c})" for c in columns),
                    ),
                    (payload["question_code"],) + tuple(payload[c] for c in columns),
                )
            else:
                placeholders = ", ".join(["%s"] * len(columns))
                cursor.execute(
                    f"INSERT INTO assessment_questions ({', '.join(columns)}) "
                    f"VALUES ({placeholders})",
                    tuple(payload[c] for c in columns),
                )
            # rowcount is 1 for an insert, 2 for an update on a duplicate key.
            inserted += 1 if cursor.rowcount == 1 else 0
            updated += 1 if cursor.rowcount == 2 else 0

    return {
        "items": len(rows),
        "inserted": inserted,
        "updated": updated,
        "removed": removed,
        "per_track": expected_track_counts(),
        "answer_key": answer_key_distribution(rows),
    }
