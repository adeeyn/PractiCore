from flask import render_template
from flask.views import MethodView

from . import student_bp


class StudentProfileView(MethodView):

    def get(self):
        return render_template("student/student_profile.html", active_page="profile")


student_bp.add_url_rule("/profile", view_func=StudentProfileView.as_view("profile"))
