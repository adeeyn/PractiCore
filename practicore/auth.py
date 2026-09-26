from flask import jsonify, redirect, request, session, url_for


def role_guard(role):
    """Builds a blueprint `before_request` hook that only lets `role` through.

    Anonymous users go to the login page (or get a 401 for JSON requests);
    users with a different role are sent to their own dashboard.
    """
    def guard():
        if "loggedin" not in session:
            if request.is_json:
                return jsonify({"status": "error", "message": "User not logged in"}), 401
            return redirect(url_for("auth.login"))

        if session.get("role") != role:
            from .services import AuthService
            return redirect(url_for(AuthService.dashboard_endpoint(session.get("role"))))

        return None

    return guard
