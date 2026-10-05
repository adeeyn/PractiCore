"""Loads the 130-item master competency bank into `assessment_questions`.

Run it with:  flask --app app seed-master-bank

IDEMPOTENT BY DESIGN. Every row carries a stable `question_code` (MB-<COMP>-<nn>),
which `assessment_questions` already holds under a UNIQUE index (migration 008), so
the write is an INSERT ... ON DUPLICATE KEY UPDATE. Running this twice refreshes the
same 130 rows and creates nothing new -- there is no DELETE anywhere in this module.

Existing rows are never touched. The 79 published items (43 research + 36
parallel-form) have different code families (`Q01..Q43`, `PF-*`), so they do not
collide with `MB-*` and keep the ids that attempt_competencies, question_set_members
and question_exposure_history already reference.

The bank is ADDITIVE to the taxonomy rather than a replacement: `seed_competencies`
still owns the competencies and parallel forms, and this module only writes questions.
"""

from .database import Database
from .services.master_question_bank import (
    answer_key_distribution,
    balanced_rows,
    corrections,
    counts_per_competency,
    counts_per_difficulty,
    counts_per_type,
    key_status_summary,
)

# Columns written by this seeder. `source_type`, `explanation`, `key_status`,
# `doc_competency`, `is_active` and `question_key_corrections` require migration 012;
# they are detected at runtime so a database without 012 still loads the older columns
# rather than failing outright.
CORE_COLUMNS = (
    "course_track", "category", "competency", "doc_competency", "target_role",
    "pathway", "question_type", "difficulty", "standard_ref", "question_text",
    "option_a", "option_b", "option_c", "option_d", "correct_option",
    "explanation", "is_active", "source_type", "key_status",
)

# course_track is the SHORT track code the rest of the system keys on
# (SkillTaxonomy.DOMAIN_TRACK_CODES), not the long category name.
TRACK_BY_COMPETENCY = {
    "PROG": "DEV", "WEB": "DEV", "DB": "DATA", "SUPP": "TSM", "NET": "NET",
    "OS": "TSM", "SEC": "SEC", "EVID": "BSP", "COMM": "BSP", "PROB": "DEV",
}


def _table_columns(cursor):
    cursor.execute("SHOW COLUMNS FROM assessment_questions")
    return {row["Field"] for row in cursor.fetchall()}


def _to_row(item):
    """Maps one bank item onto assessment_questions columns."""
    competency = item["competency"]
    return {
        "question_code": item["question_code"],
        "course_track": TRACK_BY_COMPETENCY.get(competency, "DEV"),
        # category is the document's own competency label, so the sub-domain the item
        # was written against stays visible even where PractiCore maps it elsewhere.
        "category": item.get("doc_competency") or competency,
        "competency": competency,
        "doc_competency": item.get("doc_competency"),
        "target_role": item.get("target_role"),
        "pathway": item.get("pathway"),
        "question_type": item["question_type"],
        "difficulty": item["difficulty"],
        "standard_ref": item.get("standard_ref"),
        "question_text": item["question_text"],
        "option_a": item.get("option_a", ""),
        "option_b": item.get("option_b", ""),
        "option_c": item.get("option_c", ""),
        "option_d": item.get("option_d", ""),
        "correct_option": item["correct_option"],
        "explanation": item.get("explanation"),
        "is_active": item.get("is_active", 1),
        "source_type": item.get("source_type"),
        "key_status": item.get("key_status"),
    }


def _write_corrections(cursor, rows):
    """Records every corrected key so the change is auditable and reversible.

    The published letter is preserved in `recorded_option` before the applied key is
    relied on, so a reviewer can always see what the document said and what the bank
    now grades against.
    """
    written = 0
    for record in corrections():
        cursor.execute(
            """
            INSERT INTO question_key_corrections
                (question_code, recorded_option, applied_option, recorded_option_text,
                 applied_option_text, explanation, rule)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                recorded_option = VALUES(recorded_option),
                applied_option = VALUES(applied_option),
                recorded_option_text = VALUES(recorded_option_text),
                applied_option_text = VALUES(applied_option_text),
                explanation = VALUES(explanation),
                rule = VALUES(rule),
                corrected_at = CURRENT_TIMESTAMP
            """,
            (record["question_code"], record["recorded_option"], record["applied_option"],
             record["recorded_option_text"], record["applied_option_text"],
             record["explanation"], record["rule"]),
        )
        written += 1
    return written


def seed_master_bank():
    """Inserts or refreshes the 130 document items. Returns a summary dict.

    Idempotent: rows are matched on `question_code` (UNIQUE since migration 008), so
    re-running refreshes in place. Existing published rows (Q*, PF-*) are untouched.
    """
    rows = [_to_row(item) for item in balanced_rows()]
    inserted, updated, skipped, corrected = 0, 0, 0, 0

    with Database.cursor(commit=True) as cursor:
        available = _table_columns(cursor)
        columns = [c for c in CORE_COLUMNS if c in available]
        if "question_code" not in available:
            raise RuntimeError(
                "assessment_questions.question_code is missing - apply migration 008 "
                "before seeding the master bank."
            )

        assignments = ", ".join("%s = VALUES(%s)" % (c, c) for c in columns)
        sql = (
            "INSERT INTO assessment_questions (question_code, %s) VALUES (%%s, %s) "
            "ON DUPLICATE KEY UPDATE %s"
            % (", ".join(columns), ", ".join(["%s"] * len(columns)), assignments)
        )

        for row in rows:
            cursor.execute(sql, (row["question_code"],) + tuple(row[c] for c in columns))
            # MySQL reports 1 for an insert, 2 for an updated duplicate key.
            if cursor.rowcount == 1:
                inserted += 1
            elif cursor.rowcount == 2:
                updated += 1
            else:
                skipped += 1

        corrected = _write_corrections(cursor, rows)

    return {
        "items": len(rows),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
        "corrected": corrected,
        "key_status": key_status_summary(),
        "per_competency": counts_per_competency(),
        "active_per_competency": counts_per_competency(active_only=True),
        "per_type": counts_per_type(),
        "per_difficulty": counts_per_difficulty(),
        "answer_key": answer_key_distribution(rows),
    }
