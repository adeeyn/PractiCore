from ..competency_scoring import strength_level_for
from ..database import Database, DatabaseError, upsert_sql


class CompetencyRepository:
    """All SQL touching the competency, question-form, attempt and profile tables.

    Deliberately free of any `services` import. The repositories package is
    loaded before services, and importing the taxonomy from here would pull in
    services/__init__ -> assessment_service -> repositories, a cycle. The
    taxonomy is passed in by competency_seed, which owns reading it.
    """

    # ---------- Taxonomy ----------

    def seed_taxonomy(self, competencies, skill_map):
        """Writes the competency list and the skill map. Idempotent."""
        with Database.cursor(commit=True) as cursor:
            for order, (code, (name, track, is_core, description)) in enumerate(competencies.items()):
                cursor.execute(
                    upsert_sql(
                        "competencies",
                        ["code", "name", "track", "is_core", "description", "sort_order"],
                        ["code"],
                        ["name", "track", "is_core", "description", "sort_order"],
                    ),
                    (code, name, track, 1 if is_core else 0, description, order),
                )

            for skill, mapping in skill_map.items():
                for code, strength in mapping.items():
                    cursor.execute(
                        upsert_sql(
                            "competency_skill_map",
                            ["skill_key", "competency_code", "strength"],
                            ["skill_key", "competency_code"],
                            ["strength"],
                        ),
                        (skill, code, strength),
                    )
        return len(competencies), len(skill_map)

    def all_competencies(self):
        with Database.cursor() as cursor:
            cursor.execute("SELECT * FROM competencies ORDER BY is_core DESC, sort_order, code")
            return cursor.fetchall()

    def competencies_with_forms(self):
        """{competency_code: [form rows]} for every competency that has questions.

        `question_count` is recomputed from actual membership so an empty or short
        form is reported honestly rather than echoing what the seeder intended.
        """
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT qs.id, qs.competency_code, qs.set_code, qs.label,
                       qs.question_count AS declared,
                       (SELECT COUNT(*) FROM question_set_members m
                         WHERE m.set_id = qs.id) AS actual
                FROM question_sets qs
                JOIN competencies c ON c.code = qs.competency_code
                ORDER BY qs.competency_code, qs.set_code
            """)
            grouped = {}
            for row in cursor.fetchall():
                grouped.setdefault(row["competency_code"], []).append(row)
            return grouped

    # ---------- Question selection ----------

    def questions_for_sets(self, set_ids):
        """{set_id: [question rows]} for the chosen parallel forms.

        Membership is read from question_set_members, not assessment_questions
        .set_id: one question can serve two competencies (Q22 measures both
        Networking and Troubleshooting), and a single set_id column cannot
        express that.
        """
        if not set_ids:
            return {}
        placeholders = ",".join(["%s"] * len(set_ids))
        with Database.cursor() as cursor:
            # Column list is explicit: SELECT q.* would also return the question's
            # own set_id (always NULL now that membership is authoritative), which
            # would then overwrite the membership set_id this method groups by.
            columns = ", ".join("q.%s" % c for c in (
                "id", "question_code", "course_track", "category", "competency",
                "question_type", "difficulty", "standard_ref", "pathway",
                "question_text", "option_a", "option_b", "option_c", "option_d",
                "correct_option", "target_role",
            ))
            cursor.execute(
                f"SELECT {columns}, m.set_id AS form_id "
                f"FROM assessment_questions q "
                f"JOIN question_set_members m ON m.question_id = q.id "
                f"WHERE m.set_id IN ({placeholders})",
                tuple(set_ids),
            )
            grouped = {}
            for row in cursor.fetchall():
                grouped.setdefault(row["form_id"], []).append(row)
            return grouped

    def questions_by_ids(self, question_ids):
        """{id: question row} for grading a submission.

        Grading re-reads the questions rather than trusting anything the browser
        sends back, so a tampered payload cannot change a key or a competency.
        """
        if not question_ids:
            return {}
        ids = list(question_ids)
        placeholders = ",".join(["%s"] * len(ids))
        with Database.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM assessment_questions WHERE id IN ({placeholders})",
                tuple(ids),
            )
            return {row["id"]: row for row in cursor.fetchall()}

    def record_exposure(self, student_id, picks, attempt_id=None):
        """Remembers which FORM a student was shown, so a retake rotates."""
        with Database.cursor(commit=True) as cursor:
            for code, form in picks.items():
                cursor.execute("""
                    INSERT INTO question_exposure_history
                        (student_id, competency_code, set_id, attempt_id)
                    VALUES (%s, %s, %s, %s)
                """, (student_id, code, form["id"], attempt_id))

    def exposure_for_student(self, student_id):
        """{competency_code: [history rows]} used to avoid repeating a form."""
        if not student_id:
            return {}
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT competency_code, set_id, attempt_id, exposed_at
                FROM question_exposure_history
                WHERE student_id = %s
                ORDER BY exposed_at ASC, id ASC
            """, (student_id,))
            grouped = {}
            for row in cursor.fetchall():
                grouped.setdefault(row["competency_code"], []).append(row)
            return grouped

    # ---------- Master bank pool ----------

    def question_pool_by_competency(self, codes=None):
        """{competency_code: [question rows]} from the active master bank.

        Reads by competency rather than by parallel form, so the 130-item bank can
        be drawn from even where only a partial form exists. Inactive items are
        excluded, so retiring a question stops it being served without deleting it.
        """
        clauses = ["is_active = 1"]
        params = []
        if codes:
            clauses.append("competency IN (%s)" % ",".join(["%s"] * len(codes)))
            params.extend(codes)

        with Database.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, question_code, competency, question_type, difficulty,
                       standard_ref, question_text, option_a, option_b, option_c,
                       option_d, correct_option, explanation, model_answer,
                       option_json, position, source_type
                FROM assessment_questions
                WHERE %s
                ORDER BY question_code
                """ % " AND ".join(clauses),
                tuple(params),
            )
            grouped = {}
            for row in cursor.fetchall():
                grouped.setdefault(row["competency"], []).append(row)
            return grouped

    def questions_seen_by_student(self, student_id):
        """{question_id: {'times_seen', 'last_seen_at'}} for the retake selector.

        Returns {} when there is no history, and never raises: a missing
        question_seen_history table must degrade to "nothing seen" rather than
        break the assessment page.
        """
        if not student_id:
            return {}
        try:
            with Database.cursor() as cursor:
                cursor.execute(
                    "SELECT question_id, times_seen, last_seen_at "
                    "FROM question_seen_history WHERE student_id = %s",
                    (student_id,),
                )
                return {row["question_id"]: row for row in cursor.fetchall()}
        except DatabaseError:
            return {}

    def record_seen_questions(self, student_id, attempt_id, entries):
        """Upserts the per-item exposure ledger. Never deletes past rows.

        `entries` is [{question_id, competency_code}]. times_seen accumulates and
        last_seen_at advances, so a retake can prefer unseen or long-unseen items
        without any history being lost.
        """
        if not student_id or not entries:
            return
        try:
            with Database.cursor(commit=True) as cursor:
                for entry in entries:
                    cursor.execute(
                        """
                        INSERT INTO question_seen_history
                            (student_id, question_id, competency_code, attempt_id, times_seen)
                        VALUES (%s, %s, %s, %s, 1)
                        ON CONFLICT (student_id, question_id) DO UPDATE SET
                            times_seen = question_seen_history.times_seen + 1,
                            last_seen_at = CURRENT_TIMESTAMP,
                            attempt_id = EXCLUDED.attempt_id
                        """,
                        (student_id, entry["question_id"], entry["competency_code"], attempt_id),
                    )
        except DatabaseError:
            # Exposure tracking must never cost a student their attempt.
            pass

    def save_attempt_questions(self, attempt_id, per_question, answers):
        """Stores the per-question record for one attempt: order, answer, correctness.

        `per_question` is {question_id: {'correct': bool, 'order': int}} and
        `answers` the raw submission keyed 'q_<id>'. A skipped item is written with
        selected_answer NULL and is_correct 0, keeping "unanswered" distinct from
        "answered wrongly" in the report.
        """
        if not attempt_id or not per_question:
            return 0
        ordered = sorted(per_question.items(), key=lambda kv: kv[1].get("order", 0))
        written = 0
        with Database.cursor(commit=True) as cursor:
            for order, (q_id, outcome) in enumerate(ordered, start=1):
                raw = answers.get("q_%s" % q_id) or answers.get(str(q_id))
                cursor.execute(
                    upsert_sql(
                        "attempt_questions",
                        ["attempt_id", "question_id", "display_order",
                         "selected_answer", "is_correct"],
                        ["attempt_id", "question_id"],
                        ["display_order", "selected_answer", "is_correct"],
                    ),
                    (attempt_id, q_id, order, raw or None,
                     1 if outcome.get("correct") else 0),
                )
                written += 1
        return written

    # ---------- Attempts ----------

    def next_attempt_no(self, student_id, posting_id=None):
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(MAX(attempt_no), 0) AS n FROM assessment_attempts
                WHERE student_id = %s AND posting_id IS NOT DISTINCT FROM %s
            """, (student_id, posting_id))
            return (cursor.fetchone() or {"n": 0})["n"] + 1

    def save_attempt(self, student_id, posting_id, attempt_no, results, per_competency):
        """Stores the attempt, its per-competency results and the profile.

        One transaction: a half-written attempt would leave the student with a
        score they cannot account for.
        """
        with Database.cursor(commit=True) as cursor:
            # Column names follow the table created in migration 006
            # (overall_percentage, not overall_percent).
            cursor.execute("""
                INSERT INTO assessment_attempts
                    (student_id, posting_id, attempt_no, total_questions, total_correct,
                     overall_percentage, competency_level, submitted_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (student_id, posting_id, attempt_no, results["total_questions"],
                  results["total_correct"], results["overall_percentage"],
                  results["competency_level"]))
            attempt_id = cursor.lastrowid

            for code, stats in per_competency.items():
                cursor.execute("""
                    INSERT INTO attempt_competencies
                        (attempt_id, competency_code, set_id, correct_count,
                         question_count, score_percent)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (attempt_id, code, stats.get("set_id"), stats["correct"],
                      stats["total"], stats["score_percent"]))

                # The profile keeps the LATEST score and the best ever seen, so a
                # bad retake does not erase demonstrated ability and a good
                # retake is not thrown away either.
                cursor.execute(
                    """
                    INSERT INTO student_competency_scores
                        (student_id, competency_code, score_percent, attempts_count,
                         best_percent, last_attempt_id)
                    VALUES (%s, %s, %s, 1, %s, %s)
                    ON CONFLICT (student_id, competency_code) DO UPDATE SET
                        score_percent = EXCLUDED.score_percent,
                        attempts_count = student_competency_scores.attempts_count + 1,
                        best_percent = GREATEST(student_competency_scores.best_percent, EXCLUDED.best_percent),
                        last_attempt_id = EXCLUDED.last_attempt_id
                    """,
                    (student_id, code, stats["score_percent"],
                     stats["score_percent"], attempt_id),
                )
            return attempt_id

    # ---------- Profile ----------

    # Statuses a competency can hold. "Claimed" is deliberately NOT one of them:
    # a claim is not a result. Before an assessment runs the honest label is
    # ASSESSMENT_REQUIRED (questions exist, the student has not sat them), and
    # only a competency with no published questions at all reads NOT_ASSESSED.
    STATUS_ASSESSED = "Assessed"
    STATUS_ASSESSMENT_REQUIRED = "Assessment Required"
    STATUS_NOT_ASSESSED = "Not assessed"

    def assessable_competencies(self):
        """{competency_code: active question count} for every published pool.

        This is what decides ASSESSMENT_REQUIRED vs NOT_ASSESSED. Without it the
        profile cannot tell "the student still has to sit this" from "there is
        nothing to sit", and would have to label both as a claim.
        """
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT competency, COUNT(*) AS n
                FROM assessment_questions
                WHERE is_active = 1 AND competency IS NOT NULL
                GROUP BY competency
            """)
            return {row["competency"]: int(row["n"]) for row in cursor.fetchall()}

    def student_profile(self, student_id, assessable=None):
        """The student competency profile: demonstrated scores + resume evidence.

        Each entry keeps four facts APART, because they are different claims:

            resume_evidence     what the resume says (a claim, never a score)
            assessment_required questions exist and the student has not sat them
            assessment_completed an attempt produced a demonstrated percentage
            score_percent       that percentage, or None when never assessed

        `assessable` is accepted so a caller that already holds the pool sizes
        does not pay for a second query; when omitted it is read once here.
        """
        if not student_id:
            return {}
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT s.competency_code, s.score_percent, s.best_percent,
                       s.attempts_count, c.name, c.track, c.is_core
                FROM student_competency_scores s
                JOIN competencies c ON c.code = s.competency_code
                WHERE s.student_id = %s
            """, (student_id,))
            scores = {row["competency_code"]: row for row in cursor.fetchall()}

            cursor.execute("""
                SELECT competency_code, evidence_skills, evidence_count,
                       has_project, has_experience
                FROM resume_competency_evidence
                WHERE student_id = %s
            """, (student_id,))
            evidence = {row["competency_code"]: row for row in cursor.fetchall()}

        if assessable is None:
            assessable = self.assessable_competencies()

        profile = {}
        for code in set(scores) | set(evidence):
            score_row = scores.get(code) or {}
            ev_row = evidence.get(code) or {}
            percent = score_row.get("score_percent")
            entry = {
                "code": code,
                "name": score_row.get("name") or code,
                "track": score_row.get("track"),
                "is_core": bool(score_row.get("is_core")),
                "score_percent": percent,
                "best_percent": score_row.get("best_percent") or percent or 0,
                "attempts_count": score_row.get("attempts_count", 0),
                "evidence_skills": [
                    s.strip() for s in (ev_row.get("evidence_skills") or "").split(",") if s.strip()
                ],
                "has_project": bool(ev_row.get("has_project")),
                "has_experience": bool(ev_row.get("has_experience")),
            }
            entry.update(self.assessment_state(entry, assessable))
            # Retained for cross-matching: the evidence ladder is a corroboration
            # input, not the competency's result, and must never be read as one.
            entry["evidence_strength"] = self.evidence_strength(entry)
            profile[code] = entry
        return profile

    @classmethod
    def assessment_state(cls, entry, assessable):
        """Status + strength band for one profile entry.

        The status reflects ACTUAL assessment state only:

          score present                 -> Assessed (percentage + band)
          no score, questions published -> Assessment Required
          no score, nothing published   -> Not assessed

        The band thresholds come from Config when Flask is running, so they are
        configurable rather than hard-coded in a template. Outside an app context
        the module defaults apply, which keeps this callable from tests.
        """
        percent = entry.get("score_percent")
        has_questions = int((assessable or {}).get(entry.get("code"), 0)) > 0

        if percent is not None:
            status = cls.STATUS_ASSESSED
        elif has_questions:
            status = cls.STATUS_ASSESSMENT_REQUIRED
        else:
            status = cls.STATUS_NOT_ASSESSED

        bands = None
        try:
            from flask import current_app

            if current_app:
                bands = current_app.config.get("COMPETENCY_STRENGTH_BANDS")
        except Exception:
            bands = None   # no app context: fall back to the module defaults

        return {
            "resume_claimed": bool(entry.get("evidence_skills")),
            "resume_evidence": list(entry.get("evidence_skills") or []),
            "assessment_required": status == cls.STATUS_ASSESSMENT_REQUIRED,
            "assessment_completed": status == cls.STATUS_ASSESSED,
            "available_questions": int((assessable or {}).get(entry.get("code"), 0)),
            "status": status,
            "strength_level": strength_level_for(percent, bands),
        }

    @staticmethod
    def evidence_strength(entry):
        """Corroboration ladder for the RESUME EVIDENCE half only.

        'Strong' / 'Moderate' / 'Weak' / 'Claimed' / 'None'. This is NOT the
        competency's result: it measures how well a resume claim is backed up,
        and cross-matching uses it only as the low-weighted corroboration term.

        A demonstrated score always outranks a claim. Resume evidence can lift a
        passing result, but can never create one: with no assessment the best
        possible label here is 'Claimed', which is why the UI renders
        `score_percent` / `status` and never this field as the result.
        """
        percent = entry.get("score_percent")
        skill_count = len(entry.get("evidence_skills") or [])
        corroborated = skill_count >= 2 or entry.get("has_project") or entry.get("has_experience")

        if percent is None:
            return "Claimed" if skill_count else "None"
        if percent >= 70:
            return "Strong" if corroborated else "Moderate"
        if percent >= 50:
            return "Moderate" if corroborated else "Weak"
        return "Weak" if corroborated else "None"

    def save_resume_evidence(self, student_id, evidence_map):
        """Stores what the resume claims, separately from any score."""
        with Database.cursor(commit=True) as cursor:
            for code, ev in evidence_map.items():
                cursor.execute(
                    upsert_sql(
                        "resume_competency_evidence",
                        ["student_id", "competency_code", "evidence_skills",
                         "evidence_count", "has_project", "has_experience"],
                        ["student_id", "competency_code"],
                        ["evidence_skills", "evidence_count",
                         "has_project", "has_experience"],
                    ),
                    (student_id, code, ", ".join(ev["skills"]), len(ev["skills"]),
                     1 if ev.get("has_project") else 0,
                     1 if ev.get("has_experience") else 0),
                )

    # ---------- Internship requirements ----------

    def requirements_for_posting(self, posting_id):
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT r.competency_code, r.importance, r.required_percent,
                       c.name, c.track
                FROM internship_competency_requirements r
                JOIN competencies c ON c.code = r.competency_code
                WHERE r.posting_id = %s
            """, (posting_id,))
            return cursor.fetchall()

    def save_posting_requirements(self, posting_id, mapping):
        with Database.cursor(commit=True) as cursor:
            for code, meta in mapping.items():
                cursor.execute(
                    upsert_sql(
                        "internship_competency_requirements",
                        ["posting_id", "competency_code", "importance", "required_percent"],
                        ["posting_id", "competency_code"],
                        ["importance", "required_percent"],
                    ),
                    (posting_id, code, meta.get("importance", "preferred"),
                     meta.get("required_percent", 60)),
                )

    def save_compatibility(self, student_id, posting_id, result):
        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                upsert_sql(
                    "compatibility_scores",
                    ["student_id", "posting_id", "assessment_score", "evidence_score",
                     "total_score", "competencies_met", "competencies_total", "detail"],
                    ["student_id", "posting_id"],
                    ["assessment_score", "evidence_score", "total_score",
                     "competencies_met", "competencies_total", "detail"],
                ),
                (student_id, posting_id, result["assessment_score"],
                 result["evidence_score"], result["total_score"],
                 result["competencies_met"], result["competencies_total"],
                 result.get("detail_json")),
            )
