"""Streams stored images (student photo, company logo) from the database.

The upload filesystem is read-only on Vercel, so avatars and logos live in
`student_photos` / `employer_logos` instead of static/uploads/. This blueprint
deliberately has no role guard:

  * /media/logo/<id>  - company branding, public by design.
  * /media/avatar/<id> - only the owning student may see their photo, so the
    route compares the row's user_id with the session instead.

`avatar_path` / `logo_path` remain the "has image" flag ('db'); the bytes are
fetched here so page renders never carry image payloads.
"""
import io

from flask import abort, Blueprint, send_file, session

from ..repositories import EmployerRepository, StudentRepository

media_bp = Blueprint("media", __name__, url_prefix="/media")


@media_bp.route("/avatar/<int:student_id>")
def avatar(student_id):
    user_id = session.get("user_id")
    if not user_id:
        abort(404)

    student = StudentRepository().find_by_id(student_id)
    if not student or student.get("user_id") != user_id:
        abort(404)

    photo = StudentRepository().get_photo(student_id)
    if not photo:
        abort(404)
    return _stream(photo)


@media_bp.route("/logo/<int:employer_id>")
def logo(employer_id):
    stored = EmployerRepository().get_logo(employer_id)
    if not stored:
        abort(404)
    return _stream(stored)


def _stream(stored):
    return send_file(
        io.BytesIO(stored["data"]),
        mimetype=stored["mime"],
        download_name="image",
        max_age=0,  # re-upload replaces bytes at the same URL: never serve stale
    )
