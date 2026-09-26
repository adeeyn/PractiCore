from flask import redirect, render_template, request, session, url_for
from flask.views import MethodView, View

from . import auth_bp
from ...services import AuthService


class IndexView(View):
    """`/` sends logged-in users to their dashboard, everyone else to login."""

    def dispatch_request(self):
        role = session.get("role")
        if role in AuthService.DASHBOARDS:
            return redirect(url_for(AuthService.dashboard_endpoint(role)))
        return redirect(url_for("auth.login"))


class LoginView(MethodView):
    """One login page for students, employers and admins."""

    template = "auth/login.html"

    def __init__(self):
        self.auth = AuthService()

    def get(self):
        role = session.get("role")
        if role in AuthService.DASHBOARDS:
            return redirect(url_for(AuthService.dashboard_endpoint(role)))

        return render_template(
            self.template,
            failed=request.args.get("failed") == "1",
            username=request.args.get("username", ""),
        )

    def post(self):
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = self.auth.authenticate(identifier, password)
        if not user:
            # main.js reads ?failed=1 to show the error message
            return redirect(url_for("auth.login", failed=1, username=identifier))

        self.auth.login(user)
        return redirect(url_for(AuthService.dashboard_endpoint(user["role"])))


class LogoutView(View):
    def dispatch_request(self):
        AuthService.logout()
        return redirect(url_for("auth.login"))


auth_bp.add_url_rule("/", view_func=IndexView.as_view("index"))
auth_bp.add_url_rule("/login", view_func=LoginView.as_view("login"))
auth_bp.add_url_rule("/logout", view_func=LogoutView.as_view("logout"))
