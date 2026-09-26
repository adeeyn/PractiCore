from flask import render_template
from flask.views import MethodView

from . import student_bp


class ApplicationView(MethodView):

    def get(self):
        return render_template("student/application.html", active_page="application")


student_bp.add_url_rule("/application", view_func=ApplicationView.as_view("application"))
