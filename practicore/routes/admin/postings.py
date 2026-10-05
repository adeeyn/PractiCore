"""Internship Posting monitoring (CP2 1.3.4 / Figure 22).

The administrator reviews postings "to ensure that they follow the system's
guidelines" (CP2 p.75). That is a read-and-moderate job: the description,
skills, competency requirements and any compatibility or ranking data belong to
the employer and the matching engine, and are never modified here. The only
write is the posting's open/closed status.
"""
from flask import current_app, flash, redirect, render_template, request, url_for
from flask.views import MethodView

from . import admin_bp
from ...database import DatabaseError
from ...repositories import AdminRepository


class PostingListView(MethodView):

    def get(self):
        admin = AdminRepository(request.args.get("q", ""), request.args.get("status", ""))
        return render_template(
            "admin/postings.html",
            active_page="postings",
            postings=admin.all_postings(),
            search=admin.search,
            status=admin.status,
        )


class PostingDetailView(MethodView):

    def get(self, posting_id):
        posting = AdminRepository().find_posting(posting_id)
        if not posting:
            # A missing posting is a normal outcome, not an error: flash a
            # message and return the administrator to the list.
            flash("That internship posting could not be found.", "error")
            return redirect(url_for("admin.postings"))
        return render_template(
            "admin/posting_detail.html",
            active_page="postings",
            posting=posting,
        )


class PostingStatusView(MethodView):
    """Opens or closes a posting. Content is never touched."""

    def post(self, posting_id):
        status = request.form.get("status", "")
        try:
            changed = AdminRepository().set_posting_status(posting_id, status)
        except ValueError:
            flash("Unsupported posting status.", "error")
            return redirect(request.referrer or url_for("admin.postings"))
        except DatabaseError:
            current_app.logger.exception("posting status change failed")
            flash("The posting could not be updated. Please try again.", "error")
            return redirect(request.referrer or url_for("admin.postings"))

        if not changed:
            flash("That internship posting could not be found.", "error")
        else:
            flash("Internship posting %s." % ("reopened" if status == "active" else "closed"),
                  "success")
        return redirect(request.referrer or url_for("admin.postings"))


admin_bp.add_url_rule("/postings", view_func=PostingListView.as_view("postings"))
admin_bp.add_url_rule("/postings/<int:posting_id>", view_func=PostingDetailView.as_view("posting_detail"))
admin_bp.add_url_rule("/postings/<int:posting_id>/status",
                     view_func=PostingStatusView.as_view("posting_status"))