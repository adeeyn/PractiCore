from flask import redirect, render_template, request, url_for
from flask.views import MethodView

from . import employer_bp
from .context import current_employer, split_skills
from ...database import DatabaseError
from ...repositories import PostingRepository
from ...services import SkillTaxonomy

POSTING_MESSAGES = {
    "missing": "Internship title and description are required.",
    "skills": "Add at least one required skill so students can be matched.",
    "duplicate": "You already have a posting with that title.",
    "failed": "We could not save the posting. Please try again.",
    "noaccount": "No company is linked to this login yet. Ask an admin to create one.",
}


class InternshipPostingView(MethodView):
    """Lists the employer's postings and creates new ones."""

    template = "employer/postings.html"

    def __init__(self):
        self.postings = PostingRepository()

    def _render(self, form=None, message=None, message_type=None):
        employer = current_employer() or {}
        required_skills = split_skills(employer.get("required_skills"))

        return render_template(
            self.template,
            active_page="postings",
            postings=self.postings.for_employer(employer.get("id")),
            # Pre-fill the tag box with the skills the company is already looking for
            suggested_skills=required_skills or SkillTaxonomy.all_skills()[:8],
            form=form or {},
            message=message,
            message_type=message_type,
        )

    def get(self):
        if request.args.get("created") == "1":
            return self._render(message="Internship posted.", message_type="success")

        # Missing title / no skills / not linked to a company all land here
        error = POSTING_MESSAGES.get(request.args.get("error"))
        return self._render(message=error, message_type="error" if error else None)

    def post(self):
        form = {key: request.form.get(key, "").strip() for key in
                ("title", "department", "location", "description", "required_skills", "positions_available")}
        form["title"] = form["title"][:150]
        form["positions_available"] = max(1, int(form["positions_available"] or 1)) \
            if form["positions_available"].isdigit() else 1

        if not (form["title"] and form["description"]):
            return redirect(url_for("employer.postings", error="missing"))

        skills = split_skills(form["required_skills"])
        if not skills:
            return redirect(url_for("employer.postings", error="skills"))

        employer = current_employer()
        if not employer:
            return redirect(url_for("employer.postings", error="noaccount"))

        if self.postings.find_by_employer_and_title(employer["id"], form["title"]):
            return redirect(url_for("employer.postings", error="duplicate"))

        try:
            self.postings.create_with_skills(
                employer_id=employer["id"],
                title=form["title"],
                department=form["department"] or None,
                description=form["description"],
                is_remote=1 if request.form.get("is_remote") else 0,
                positions_available=form["positions_available"],
                skills=skills,
            )
        except DatabaseError:
            return redirect(url_for("employer.postings", error="failed"))

        return redirect(url_for("employer.postings", created=1))


employer_bp.add_url_rule("/postings", view_func=InternshipPostingView.as_view("postings"))
