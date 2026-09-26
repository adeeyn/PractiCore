import click

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
