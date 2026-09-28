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
