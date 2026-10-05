"""Company logo upload tests for the employer module.

The employer Company Profile page had a "Change Logo" button wired to a
`data-demo-action` toast saying the upload was not connected yet. These tests
cover the endpoint that replaced it: /employer/profile/logo (POST to save,
DELETE to remove).

EmployerRepository.update_logo is stubbed so no row and no file is really
written; the file-system side points at a temp directory. What runs for real is
the routing, the role guard, the extension/size validation, and the fact that a
rejected upload never reaches the repository.
"""
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from practicore import create_app

# A 1x1 PNG, so the bytes really are a valid image file
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08"
    b"\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00"
    b"\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)

# The initials are derived from the company name (migration 014), so the fixture
# carries a name rather than a hand-written "IN".
EMPLOYER = {
    "id": 3,
    "user_id": 3,
    "company_name": "InnovaTech Solutions Inc.",
    "company_logo_text": "IS",
    "logo_path": None,
}


def _signed_in_client(role="employer"):
    """A test client whose session claims `role`."""
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["loggedin"] = True
        sess["role"] = role
        sess["user_id"] = EMPLOYER["user_id"]
        sess["email"] = "hr@techsolution.com.ph"
    return client


def _client(tmp_dir=None):
    """An employer client whose logo uploads land in tmp_dir."""
    client = _signed_in_client("employer")
    client.application.config["LOGO_UPLOAD_DIR"] = tmp_dir or tempfile.mkdtemp()
    return client


def _upload(client, filename="logo.png", data=PNG_BYTES):
    return client.post(
        "/employer/profile/logo",
        data={"logo": (io.BytesIO(data), filename)},
        content_type="multipart/form-data",
    )


def _stubbed(row=None, **config):
    """Patches current_employer + update_logo so nothing real is written.

    Yields (context managers for the employer row and the repository mock).
    """
    from practicore.routes.employer import profile as profile_mod

    employer_patch = mock.patch.object(profile_mod, "current_employer",
                                      return_value=dict(row or EMPLOYER))
    repo_patch = mock.patch.object(profile_mod.EmployerRepository, "update_logo")
    return employer_patch, repo_patch


class TestLogoAuthorisation:
    """Only a logged-in employer may upload or remove a company logo."""

    def test_an_anonymous_upload_is_sent_to_login(self):
        app = create_app()
        app.config["TESTING"] = True
        response = app.test_client().post(
            "/employer/profile/logo",
            data={"logo": (io.BytesIO(PNG_BYTES), "logo.png")},
            content_type="multipart/form-data",
        )
        assert response.status_code in (301, 302)
        assert "/login" in response.headers["Location"]

    def test_a_student_cannot_upload_a_logo(self):
        response = _signed_in_client("student").post(
            "/employer/profile/logo",
            data={"logo": (io.BytesIO(PNG_BYTES), "logo.png")},
            content_type="multipart/form-data",
        )
        # Redirected to the student dashboard, so the logo endpoint is never reached
        assert response.status_code in (301, 302)
        assert "/employer" not in response.headers["Location"]


class TestLogoValidation:
    """A rejected upload must never reach the repository."""

    def test_a_png_is_accepted_and_the_path_is_returned(self):
        tmp = tempfile.mkdtemp()
        try:
            client = _client(tmp)
            employer_patch, repo_patch = _stubbed()
            with employer_patch, repo_patch as update:
                response = _upload(client)

            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "success"
            assert data["logo_path"].startswith("uploads/logos/")
            assert data["logo_path"].endswith(".png")
            assert data["logo_url"].endswith(data["logo_path"])
            assert os.listdir(tmp), "the file was never written to disk"
            update.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_the_uploaded_name_is_generated_not_taken_from_the_form(self):
        """A hostile filename must not reach the disk."""
        tmp = tempfile.mkdtemp()
        try:
            client = _client(tmp)
            employer_patch, repo_patch = _stubbed()
            with employer_patch, repo_patch:
                response = _upload(client, filename="../../../evil.png")

            assert response.status_code == 200
            written = os.listdir(tmp)
            assert len(written) == 1
            assert ".." not in written[0]
            assert written[0].startswith("3_"), written[0]
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_non_image_extension_is_rejected(self):
        client = _client()
        employer_patch, repo_patch = _stubbed()
        with employer_patch, repo_patch as update:
            response = _upload(client, filename="logo.svg", data=b"<svg></svg>")

        assert response.status_code == 400
        assert "extension" in response.get_json()["error"].lower()
        assert not update.called, "a rejected file must not reach the database"

    def test_an_oversized_logo_is_rejected(self):
        tmp = tempfile.mkdtemp()
        try:
            client = _client(tmp)
            client.application.config["LOGO_MAX_BYTES"] = 16  # below the test PNG
            employer_patch, repo_patch = _stubbed()
            with employer_patch, repo_patch as update:
                response = _upload(client)

            assert response.status_code == 400
            assert "too large" in response.get_json()["error"].lower()
            assert not update.called
            assert not os.listdir(tmp), "an oversized file must not be written"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_a_missing_file_is_rejected(self):
        client = _client()
        employer_patch, repo_patch = _stubbed()
        with employer_patch, repo_patch as update:
            response = client.post("/employer/profile/logo", data={},
                                   content_type="multipart/form-data")
        assert response.status_code == 400
        assert not update.called


class TestLogoRemoval:
    """DELETE clears the column so the templates fall back to the initials."""

    def test_removing_a_logo_clears_it_and_hands_back_the_initials(self):
        row = dict(EMPLOYER, logo_path="uploads/logos/3_deadbeef.png")
        client = _client()
        employer_patch, repo_patch = _stubbed(row)
        with employer_patch, repo_patch as update:
            response = client.delete("/employer/profile/logo")

        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert data["logo_path"] is None
        assert data["logo_text"] == "IS"
        update.assert_called_once_with(EMPLOYER["id"], None)

    def test_replacing_a_logo_deletes_the_file_it_supersedes(self):
        static_root = tempfile.mkdtemp()
        logo_dir = os.path.join(static_root, "uploads", "logos")
        os.makedirs(logo_dir)
        old = os.path.join(logo_dir, "3_deadbeef.png")
        with open(old, "wb") as handle:
            handle.write(PNG_BYTES)

        try:
            client = _client(logo_dir)
            client.application.config["STATIC_FOLDER"] = static_root
            row = dict(EMPLOYER, logo_path="uploads/logos/3_deadbeef.png")
            employer_patch, repo_patch = _stubbed(row)
            with employer_patch, repo_patch:
                response = _upload(client)

            assert response.status_code == 200
            assert not os.path.exists(old), "the replaced logo should be deleted"
            assert len(os.listdir(logo_dir)) == 1, "the new logo should be the only one left"
        finally:
            shutil.rmtree(static_root, ignore_errors=True)

    def test_a_foreign_path_is_never_deleted(self):
        """Only files under uploads/logos/ are ours to remove."""
        static_root = tempfile.mkdtemp()
        keep = os.path.join(static_root, "bundled-default.png")
        with open(keep, "wb") as handle:
            handle.write(PNG_BYTES)

        try:
            client = _client()
            client.application.config["STATIC_FOLDER"] = static_root
            row = dict(EMPLOYER, logo_path="bundled-default.png")
            employer_patch, repo_patch = _stubbed(row)
            with employer_patch, repo_patch:
                response = client.delete("/employer/profile/logo")

            assert response.status_code == 200
            assert os.path.exists(keep), "a path outside uploads/logos/ must not be deleted"
        finally:
            shutil.rmtree(static_root, ignore_errors=True)


class TestCompanyProfilePage:
    """The page renders the upload control and no longer shows the demo toast."""

    def _page(self, row=None):
        from practicore.routes.employer import profile as profile_mod

        client = _client()
        with mock.patch.object(profile_mod, "current_employer", return_value=dict(row or EMPLOYER)):
            return client.get("/employer/profile").get_data(as_text=True)

    def test_the_demo_toast_is_gone(self):
        body = self._page()
        assert "Logo upload is not connected yet" not in body
        assert "data-demo-action" not in body

    def test_the_file_input_and_endpoint_are_rendered(self):
        body = self._page()
        assert 'id="logo-input"' in body
        assert 'id="logo-pick"' in body
        assert "/employer/profile/logo" in body

    def test_initials_are_shown_when_there_is_no_logo(self):
        body = self._page()
        assert 'id="company-logo"' in body
        assert ">IS<" in body, "initials should be derived from the company name"
        assert 'id="logo-remove"' not in body, "there is nothing to remove without a logo"

    def test_the_manual_initials_field_is_gone(self):
        """There is nothing to type: the name is the only source."""
        body = self._page()
        assert 'name="logo_text"' not in body
        assert "Logo Text" not in body
        assert "maxlength=\"10\"" not in body

    def test_the_uploaded_image_and_remove_button_are_shown(self):
        body = self._page(dict(EMPLOYER, logo_path="uploads/logos/3_deadbeef.png"))
        assert "/static/uploads/logos/3_deadbeef.png" in body
        assert 'id="logo-remove"' in body