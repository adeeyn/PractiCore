import click
from flask import current_app

from .employer_seed import DEFAULT_PASSWORD, seed_employers
from .repositories import UserRepository
from .services import AuthService


def register_commands(app):
    @app.cli.command("create-admin")
    @click.option("--email", prompt=True, help="Admin login email.")
    @click.option("--username", prompt=True, default="admin", show_default=True, help="Admin login username.")
    @click.password_option(help="Admin password.")
    def create_admin(email, username, password):
        """Create an admin account (run: flask --app app create-admin)."""
        users = UserRepository()
        email = email.strip().lower()
        username = username.strip() or None

        if users.exists(email, username):
            raise click.ClickException("An account with that email or username already exists.")

        users.create(email, username, AuthService.hash_password(password), AuthService.ADMIN)
        click.echo(f"Admin account created for {email}.")

    @app.cli.command("seed-employers")
    @click.option("--password", default=DEFAULT_PASSWORD, show_default=True,
                  help="Password given to every seeded employer account.")
    @click.option("--reset-passwords", is_flag=True,
                  help="Also apply the password to employer logins that already existed.")
    def seed_employers_command(password, reset_passwords):
        """Create dummy partner-company accounts (run: flask --app app seed-employers).

        Gives each company a login, a full company profile (including the skills
        it is looking for), internship postings and demo applications. Safe to
        run more than once; existing rows are refreshed, not duplicated.
        """
        accounts = seed_employers(password, reset_passwords)

        click.echo(f"Seeded {len(accounts)} employer account(s).\n")
        for email, account_password in accounts:
            click.echo(f"  {email}  /  {account_password}")
        click.echo("\nLog in at /login with any of the emails above.")

    @app.cli.command("seed-questions")
    @click.option("--keep-existing", is_flag=True,
                  help="Add the research bank without deleting the current questions.")
    def seed_questions_command(keep_existing):
        """Load the 43 research-based competency questions (flask --app app seed-questions).

        Replaces the current question bank with the researcher-developed items
        from the PractiCore question bank, mapped onto PractiCore's six job
        categories. Safe to re-run: rows are matched on their published code.
        """
        from .question_seed import seed_questions

        summary = seed_questions(replace=not keep_existing)

        click.echo(f"Loaded {summary['items']} research-based question(s).")
        if summary["removed"]:
            click.echo(f"Removed {summary['removed']} question(s) from the previous bank.")
        click.echo(f"  new rows: {summary['inserted']}   refreshed: {summary['updated']}")
        click.echo("Items per job category:")
        for track, count in sorted(summary["per_track"].items()):
            click.echo(f"  {track:<6} {count}")
        # Shown because the published bank is 37/43 keyed 'A'; the seeded bank
        # re-orders options so a student cannot score by always picking A.
        click.echo(f"Answer key: {summary['answer_key']}")

    @app.cli.command("seed-competencies")
    def seed_competencies_command():
        """Load the competency taxonomy and parallel question forms.

        Builds the competency list, the skill mapping, three parallel forms
        (A/B/C) per competency, and the requirements each seeded posting implies.
        Run: flask --app app seed-competencies
        """
        from .competency_seed import seed_competencies

        summary = seed_competencies()

        click.echo(f"Competencies: {summary['competencies']}  "
                   f"skills mapped: {summary['skills_mapped']}  "
                   f"questions written: {summary['questions_written']}")
        click.echo(f"Posting requirements derived for: {summary['postings_updated']} posting(s)")
        click.echo(f"\nCompetencies with all three forms ({len(summary['full_three_set'])}): "
                   f"{', '.join(summary['full_three_set']) or 'none'}")
        if summary["partial_forms"]:
            click.echo("\nCompetencies with fewer than three forms yet:")
            for code, forms in summary["partial_forms"].items():
                click.echo(f"  {code}: has {','.join(forms)} - needs more parallel items")
        click.echo("\nRun 'flask --app app competency-status' for the coverage report.")

    @app.cli.command("seed-master-bank")
    def seed_master_bank_command():
        """Load the 130-item competency master bank.

        Run: flask --app app seed-master-bank

        Adds the researcher-developed master bank (10 items x 13 competencies) to
        the existing 79 published questions. It is purely additive: rows are matched
        on their MB-* question_code, so re-running refreshes them in place instead
        of duplicating, and the 43-item research bank plus the parallel forms are
        left exactly as they are.
        """
        from .master_bank_seed import seed_master_bank

        summary = seed_master_bank()

        click.echo(f"Master bank: {summary['items']} item(s) from the researcher document.")
        click.echo(f"  inserted: {summary['inserted']}   refreshed: {summary['updated']}"
                   f"   unchanged: {summary['skipped']}")

        status = summary["key_status"]
        click.echo("\nAnswer-key verification (published key vs the item's own explanation):")
        click.echo(f"  verified   {status['Verified']}")
        click.echo(f"  corrected  {status['Corrected']}   (recorded in question_key_corrections)")
        click.echo(f"  unresolved {status['Unresolved']}   (stored inactive, NOT served)")
        if status["Corrected"]:
            click.echo("  NOTE: run 'flask --app app key-corrections' to review every "
                       "correction before release.")
        if status["Unresolved"]:
            click.echo("  NOTE: unresolved items need researcher adjudication. Review with "
                       "'flask --app app key-corrections --unresolved'.")

        click.echo("\nItems per competency (active / total):")
        for code, count in sorted(summary["per_competency"].items()):
            click.echo(f"  {code:<8} {summary['active_per_competency'].get(code, 0):>3} / {count}")

        click.echo("\nPer question type:")
        for name, count in sorted(summary["per_type"].items()):
            click.echo(f"  {name:<32} {count}")
        click.echo("\nPer difficulty:")
        for level, count in sorted(summary["per_difficulty"].items()):
            click.echo(f"  {level:<8} {count}")
        click.echo(f"\nAnswer key: {summary['answer_key']}")
        top = max(summary["answer_key"].items(), key=lambda kv: kv[1])
        click.echo(f"Most frequent key: {top[0]} ({top[1]}/{summary['items']}).")
        click.echo("\nRun 'flask --app app master-bank-status' for live coverage.")

    @app.cli.command("seed-coverage-bank")
    def seed_coverage_bank_command():
        """Load the 60-item bank for competencies the master bank omits.

        Run: flask --app app seed-coverage-bank

        The 130-item researcher bank covers ten canonical competencies. Six more
        exist in the taxonomy - DATA, SYS, GIT, OOP, DSA, CLOUD - and had no
        questions at all, so a resume naming pandas or git could select the
        competency but never measure it. This adds 10 items each.

        Purely additive: rows are matched on their MB2-* question_code, so
        re-running refreshes them in place, and no existing question is touched.
        No new competency is created.
        """
        from .coverage_bank_seed import seed_coverage_bank

        summary = seed_coverage_bank()

        click.echo(f"Coverage bank: {summary['items']} item(s) across "
                   f"{len(summary['competencies'])} competenc"
                   f"{'y' if len(summary['competencies']) == 1 else 'ies'}.")
        click.echo(f"  inserted: {summary['inserted']}   refreshed: {summary['updated']}"
                   f"   unchanged: {summary['skipped']}")

        click.echo("\nActive items per competency (before -> after seeding):")
        for code in summary["competencies"]:
            click.echo(f"  {code:<8} {summary['before'].get(code, 0):>3} -> "
                       f"{summary['active_per_competency'].get(code, 0):>3}")

        if summary["unresolved"]:
            click.echo("\nWARNING - these items are stored INACTIVE and never served "
                       "because their key could not be verified:")
            for code in summary["unresolved"]:
                click.echo(f"  {code}")
        click.echo(f"\nProvenance: {summary['source_type']} - {summary['validation']}")
        click.echo(f"Answer key: {summary['answer_key']}")
        click.echo("\nRun 'flask --app app master-bank-status' for full live coverage.")

    @app.cli.command("key-corrections")
    @click.option("--unresolved", is_flag=True,
                  help="List the items whose key could not be adjudicated instead.")
    def key_corrections_command(unresolved):
        """Show the answer-key audit trail (read-only)."""
        from .services.master_question_bank import corrections, verify_keys
        from .services.competency_taxonomy import COMPETENCIES

        if unresolved:
            rows = [(c, i) for c, i in verify_keys().items() if i["status"] == "Unresolved"]
            click.echo(f"{len(rows)} item(s) awaiting researcher adjudication "
                       f"(stored inactive, never served):\n")
        else:
            records = corrections()
            click.echo(f"{len(records)} corrected answer key(s).\n")
            rows = [(r["question_code"], {
                "status": "Corrected",
                "recorded": r["recorded_option"],
                "applied": r["applied_option"],
                "recorded_text": r["recorded_option_text"],
                "applied_text": r["applied_option_text"],
            }) for r in records]

        for code, info in sorted(rows):
            click.echo(f"{code}")
            click.echo(f"   published: {info['recorded']}  {info['recorded_text']!r}")
            click.echo(f"   applied:   {info['applied']}  {info['applied_text']!r}")
        click.echo("\nFull detail: SELECT * FROM question_key_corrections;")
        click.echo(f"Competencies: {len(COMPETENCIES)} defined in the taxonomy.")

    @app.cli.command("master-bank-status")
    def master_bank_status_command():
        """Report the master bank as it currently sits in the database."""
        from flask import current_app as _app

        from .repositories import CompetencyRepository

        repo = CompetencyRepository()
        with _app.app_context():
            pool = repo.question_pool_by_competency()
            total = sum(len(rows) for rows in pool.values())

        click.echo(f"{total} active question(s) in the master pool, "
                   f"across {len(pool)} competenc(ies).\n")
        click.echo(f"{'code':<10} {'items':<7} difficulty spread")
        for code in sorted(pool):
            rows = pool[code]
            spread = {}
            for row in rows:
                spread[row.get("difficulty")] = spread.get(row.get("difficulty"), 0) + 1
            detail = ", ".join(f"{k}:{v}" for k, v in sorted(spread.items()))
            click.echo(f"{code:<10} {len(rows):<7} {detail}")

    @app.cli.command("competency-status")
    def competency_status_command():
        """Report competency, form and set coverage."""
        from flask import current_app as _app
        from .repositories import CompetencyRepository

        repo = CompetencyRepository()
        with _app.app_context():
            competencies = repo.all_competencies()
            forms = repo.competencies_with_forms()

        click.echo(f"{len(competencies)} competencies defined\n")
        click.echo(f"{'code':<6} {'core':<5} {'forms':<8} name")
        for row in competencies:
            codes = ",".join(f["set_code"] for f in forms.get(row["code"], []))
            click.echo(f"{row['code']:<6} {'yes' if row['is_core'] else '':<5} "
                       f"{codes or '-':<8} {row['name']}")
        full = sum(1 for v in forms.values() if len(v) == 3)
        click.echo(f"\n{len(forms)} of {len(competencies)} competencies have questions; "
                   f"{full} have all three forms.")

    @app.cli.command("backfill-match-components")
    def backfill_match_components_command():
        """Split the stored match score into its resume and assessment halves.

        (run: flask --app app backfill-match-components)

        Fills applications.resume_match_score / assessment_match_score for the
        rows written before migration 011 added those columns. Recomputes through
        the same shared scorer the live pages use, so the stored halves always
        agree with the combined match_score beside them. Safe to re-run.
        """
        from flask import current_app as _app

        from .repositories import ApplicationRepository, AssessmentRepository
        from .services import AssessmentService, MatchingService

        with _app.app_context():
            applications = ApplicationRepository()
            assessments = AssessmentRepository()
            matcher = _app.extensions.get("matching_service") or MatchingService.load(
                _app.config["RANKING_MODEL_PATH"], enabled=_app.config["RANKING_MODEL_ENABLED"]
            )

            updated = skipped = 0
            for application in applications.for_training():
                total_questions = application.get("total_questions") or 0
                if not total_questions:
                    # Never assessed: there is no assessment percentage to store.
                    skipped += 1
                    continue

                components = matcher.score_components(
                    {
                        "skills": application.get("skills"),
                        "domain_scores": assessments.for_student(application["student_id"]),
                    },
                    application.get("skills_required") or [],
                    assessment_percentage=AssessmentService.score_percentage({
                        "assessment_score": application.get("assessment_score"),
                        "total_questions": total_questions,
                    }),
                )
                applications.set_match_components(
                    application["id"],
                    components["resume_match_percent"],
                    components["assessment_match_percent"],
                )
                updated += 1

        click.echo(f"Backfilled the match split on {updated} application(s); "
                   f"skipped {skipped} with no assessment taken.")

    @app.cli.command("retrain-ranking")
    @click.option("--allow-synthetic", is_flag=True,
                  help="Label rows with the weighted formula instead of real employer outcomes.")
    def retrain_ranking(allow_synthetic):
        """Train the Random Forest ranking model (run: flask --app app retrain-ranking).

        Trains on real employer outcomes by default: an application is a positive
        when the employer marked it Shortlisted, Scheduled or Hired. If there is
        not enough history yet the command refuses to write a model and PractiCore
        keeps using the weighted content-based scorer.
        """
        from .ml.train_ranking_model import train

        try:
            train(allow_synthetic=allow_synthetic)
        except RuntimeError as exc:
            raise click.ClickException(str(exc)) from exc

        # The running app caches the model at startup, so tell them to restart.
        click.echo("\nRestart the app (or re-run `flask run`) to pick up the new model.")

    @app.cli.command("ranking-status")
    def ranking_status():
        """Report which ranking algorithm is active right now."""
        from .services import MatchingService

        matcher = current_app.extensions.get("matching_service")
        if matcher is None:
            matcher = MatchingService.load(current_app.config["RANKING_MODEL_PATH"])

        click.echo(matcher.status_line())
        if matcher.uses_model and matcher.meta.get("trained_at"):
            click.echo(f"  trained at: {matcher.meta['trained_at']}")
            click.echo(f"  label source: {matcher.meta.get('label_source', 'unknown')}")
        elif not matcher.uses_model:
            click.echo(f"  reason: {matcher._load_error or 'unknown'}")
