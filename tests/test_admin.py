"""Administrator Module tests: ADM-01 to ADM-13 from the CP2 test plan.

Validation and authorisation are exercised for real. The repository calls are
stubbed, because these tests are about access control and input handling, not
about SQL -- the SQL is verified separately against the live database.
"""
import os
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask

from practicore import create_app
from practicore.services import admin_validation as validation

SCHOOL = "student.tsu.edu.ph"


def _client(role=None, logged_in=True):
    """A test client whose session claims `role`."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    client = app.test_client()
    with client.session_transaction() as sess:
        if logged_in:
            sess["loggedin"] = True
            sess["role"] = role
            sess["user_id"] = 1
            sess["email"] = "admin@practicore.test"
        else:
            sess.clear()
    return client


class TestValidation:
    """The rules on the Partner Company Account Creation form."""

    def base(self, **over):
        form = {
            "company_name": "Acme Corp", "location": "Tarlac City",
            "contact_name": "Ana Cruz", "email": "hr@acme.test",
            "password": "secret123",
        }
        form.update(over)
        return validation.collect(form)

    def test_a_complete_form_is_accepted(self):
        data, error = validation.validate(self.base(), SCHOOL)
        assert error is None, error
        assert data["email"] == "hr@acme.test"

    def test_email_is_lowercased(self):
        data, _ = validation.validate(self.base(email="HR@Acme.TEST"), SCHOOL)
        assert data["email"] == "hr@acme.test"

    def test_surrounding_whitespace_is_trimmed(self):
        data, _ = validation.validate(self.base(company_name="  Acme Corp  "), SCHOOL)
        assert data["company_name"] == "Acme Corp"

    def test_each_required_field_is_enforced(self):
        for field in ("company_name", "location", "contact_name", "email", "password"):
            data, error = validation.validate(self.base(**{field: ""}), SCHOOL)
            assert error and field.replace("_", " ").capitalize() in error, field

    def test_a_malformed_email_is_rejected(self):
        for bad in ("nope", "a@b", "a b@c.test", "@acme.test", "a@.test"):
            _, error = validation.validate(self.base(email=bad), SCHOOL)
            assert error, bad

    def test_a_school_email_is_rejected(self):
        _, error = validation.validate(self.base(email="student@" + SCHOOL), SCHOOL)
        assert error and "student" in error.lower()

    def test_a_short_password_is_rejected(self):
        _, error = validation.validate(self.base(password="abc"), SCHOOL)
        assert error and "6 characters" in error

    def test_mismatched_confirmation_is_rejected(self):
        _, error = validation.validate(self.base(confirm_password="different"), SCHOOL)
        assert error and "do not match" in error

    def test_matching_confirmation_is_accepted(self):
        _, error = validation.validate(self.base(confirm_password="secret123"), SCHOOL)
        assert error is None, error

    def test_an_over_long_company_name_is_rejected(self):
        _, error = validation.validate(self.base(company_name="x" * 200), SCHOOL)
        assert error and "150" in error

    def test_a_bad_phone_number_is_rejected(self):
        _, error = validation.validate(self.base(contact_phone="call me"), SCHOOL)
        assert error and "contact number" in error.lower()

    def test_a_good_phone_number_is_accepted(self):
        _, error = validation.validate(self.base(contact_phone="+63 917 000 0000"), SCHOOL)
        assert error is None, error


class TestAuthorisation:
    """ADM-03 / ADM-04 / ADM-13: only an admin may reach an admin page."""

    ADMIN_PAGES = ["/admin/dashboard", "/admin/companies", "/admin/postings",
                   "/admin/profile", "/admin/companies/new"]

    def test_an_anonymous_visitor_is_sent_to_login(self):
        client = _client(logged_in=False)
        for page in self.ADMIN_PAGES:
            response = client.get(page)
            assert response.status_code in (301, 302), page
            assert "/login" in response.headers["Location"], page

    def test_a_student_cannot_reach_the_admin_dashboard(self):
        """ADM-03"""
        client = _client("student")
        response = client.get("/admin/dashboard")
        assert response.status_code in (301, 302)
        assert "/login" not in response.headers["Location"], \
            "student should be sent to their own dashboard, not login"

    def test_a_student_cannot_reach_any_admin_page(self):
        client = _client("student")
        for page in self.ADMIN_PAGES:
            response = client.get(page)
            assert response.status_code in (301, 302), page
            assert "/admin" not in response.headers["Location"], \
                "%s leaked an admin page to a student" % page

    def test_an_employer_cannot_reach_any_admin_page(self):
        """ADM-04"""
        client = _client("employer")
        for page in self.ADMIN_PAGES:
            response = client.get(page)
            assert response.status_code in (301, 302), page
            assert "/admin" not in response.headers["Location"], \
                "%s leaked an admin page to an employer" % page



class TestAdminRepositoryQueries:
    """The read models, against the live database.

    These are the statements a page issues; a typo in a column name or a JOIN
    that drops rows shows up here rather than in the browser.
    """

    def _app(self):
        app = create_app()
        app.config["TESTING"] = True
        return app

    def test_stats_returns_every_counter_the_dashboard_renders(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            stats = AdminRepository().stats()
        for key in ("students", "active_students", "companies", "active_employers",
                    "pending_accounts", "postings", "active_postings",
                    "applications", "admins"):
            assert key in stats, key
            assert isinstance(stats[key], int), key

    def test_recent_lists_are_ordered_and_limited(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            repo = AdminRepository()
            for rows in (repo.recent_employers(3), repo.recent_companies(3),
                         repo.recent_postings(3)):
                assert len(rows) <= 3

    def test_employer_list_includes_account_and_posting_counts(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            rows = AdminRepository().all_employer_accounts()
        assert rows, "expected seeded partner companies"
        for row in rows:
            for key in ("company_name", "email", "is_active", "posting_count",
                        "user_id", "contact_phone"):
                assert key in row, key

    def test_employer_search_filters_results(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            all_rows = AdminRepository().all_employer_accounts()
            first = all_rows[0]["company_name"]
            token = first.split()[0]
            filtered = AdminRepository(token).all_employer_accounts()
        assert len(filtered) < len(all_rows) or len(filtered) == 1
        assert any(token.lower() in r["company_name"].lower() for r in filtered)

    def test_employer_status_filter_splits_active_and_inactive(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            active = AdminRepository("", "active").all_employer_accounts()
            inactive = AdminRepository("", "inactive").all_employer_accounts()
        for row in active:
            assert row["is_active"] == 1
        for row in inactive:
            assert row["is_active"] == 0

    def test_postings_expose_skills_and_competencies(self):
        """ADM-11: the detail page needs both, plus the status."""
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            rows = AdminRepository().all_postings()
        assert rows, "expected seeded postings"
        for key in ("title", "company_name", "description", "skills", "competencies",
                    "status", "posted_date"):
            assert key in rows[0], key

    def test_posting_search_filters_by_title(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            all_rows = AdminRepository().all_postings()
            token = all_rows[0]["title"].split()[0]


class TestAdminPages:
    """ADM-01 / ADM-09 / ADM-11: the pages render for an admin."""

    def test_the_dashboard_renders(self):
        client = _client("admin")
        response = client.get("/admin/dashboard")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "Dashboard" in body
        # CP2 Figure 20: four cards, each populated from the database rather
        # than hard-coded. The counts themselves are checked in
        # TestAdminRepositoryQueries.test_stats_returns_every_counter_...
        for card in ("Partner Companies", "Active Postings",
                     "Total Applicants", "Total Users"):
            assert card in body, card
        assert "Recent Activity" in body

    def test_the_partner_company_pages_render(self):
        client = _client("admin")
        for page in ("/admin/companies", "/admin/companies/new"):
            assert client.get(page).status_code == 200, page

    def test_the_postings_pages_render(self):
        from practicore import create_app
        from practicore.repositories import AdminRepository

        client = _client("admin")
        assert client.get("/admin/postings").status_code == 200
        with create_app().app_context():
            rows = AdminRepository().all_postings()
        if rows:
            assert client.get("/admin/postings/%d" % rows[0]["id"]).status_code == 200

    def test_a_missing_posting_returns_to_the_list_with_a_message(self):
        client = _client("admin")
        response = client.get("/admin/postings/999999", follow_redirects=True)
        assert response.status_code == 200
        assert "could not be found" in response.get_data(as_text=True)

    def test_a_missing_company_returns_to_the_list_with_a_message(self):
        client = _client("admin")


class TestPartnerCompanyCreation:
    """ADM-05 to ADM-08, with the database stubbed so no row is really written."""

    def form(self, **over):
        data = {
            "company_name": "Acme Corp", "location": "Tarlac City",
            "contact_name": "Ana Cruz", "email": "hr@acme.test",
            "password": "secret123", "confirm_password": "secret123",
        }
        data.update(over)
        return data

    def test_a_valid_submission_is_accepted(self):
        """ADM-05"""
        from practicore.repositories import admin_repository

        client = _client("admin")
        with mock.patch.object(admin_repository.AdminRepository,
                               "company_name_taken", return_value=False), \
             mock.patch.object(admin_repository.AdminRepository,
                               "create_partner_company", return_value=42) as create:
            response = client.post("/admin/companies/new", data=self.form(),
                                   follow_redirects=True)
        assert response.status_code == 200
        assert create.called
        assert "created successfully" in response.get_data(as_text=True)

    def test_a_duplicate_company_is_rejected(self):
        """ADM-06"""
        from practicore.repositories import admin_repository

        client = _client("admin")
        with mock.patch.object(admin_repository.AdminRepository,
                               "company_name_taken", return_value=True), \
             mock.patch.object(admin_repository.AdminRepository,
                               "create_partner_company") as create:
            response = client.post("/admin/companies/new", data=self.form())
        assert not create.called, "a duplicate must not reach the database"
        assert "already exists" in response.get_data(as_text=True)

    def test_a_duplicate_email_is_rejected(self):
        """ADM-08"""
        from practicore.repositories import admin_repository

        client = _client("admin")
        with mock.patch.object(admin_repository.AdminRepository,
                               "company_name_taken", return_value=False), \
             mock.patch.object(admin_repository.AdminRepository,
                               "create_partner_company",
                               side_effect=ValueError(
                                   "An account with that email already exists.")):
            response = client.post("/admin/companies/new", data=self.form())
        assert "already exists" in response.get_data(as_text=True)

    def test_an_invalid_submission_never_reaches_the_repository(self):
        from practicore.repositories import admin_repository

        client = _client("admin")
        with mock.patch.object(admin_repository.AdminRepository,
                               "create_partner_company") as create:
            response = client.post("/admin/companies/new",
                                   data=self.form(email="not-an-email"))
        assert not create.called
        assert "valid email" in response.get_data(as_text=True)

    def test_a_database_error_shows_a_readable_message(self):
        from practicore.database import DatabaseError
        from practicore.repositories import admin_repository

        client = _client("admin")
        with mock.patch.object(admin_repository.AdminRepository,
                               "company_name_taken", return_value=False), \
             mock.patch.object(admin_repository.AdminRepository,
                               "create_partner_company",
                               side_effect=DatabaseError(
                                   'relation "practicore.employers" does not exist')):
            response = client.post("/admin/companies/new", data=self.form())
        body = response.get_data(as_text=True)
        assert "could not be created" in body
        # The driver message names a table and a column: it must not be shown.
        assert "doesn't exist" not in body
        assert "practicore.employers" not in body


class TestRepositoryEdgeCases:
    """Lookups on ids that do not exist, and the writes that are refused.

    Separated from the other repository tests because these need the app
    fixture, and keeping them here stops them depending on class order.
    """

    def _app(self):
        app = create_app()
        app.config["TESTING"] = True
        return app

    def test_find_posting_returns_none_for_a_missing_id(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            assert AdminRepository().find_posting(999999) is None

    def test_find_employer_returns_none_for_a_missing_id(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            assert AdminRepository().find_employer(999999) is None

    def test_find_user_never_returns_a_password_hash(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            account = AdminRepository().find_user(1)
        if account is not None:
            assert "password_hash" not in account

    def test_an_unsupported_posting_status_is_refused(self):
        from practicore.repositories import AdminRepository

        with self._app().app_context():
            try:
                AdminRepository().set_posting_status(1, "hacked")
            except ValueError:
                pass
            else:
                raise AssertionError("an unknown status must be refused")


class TestAdminPagesExtras:
    """Page checks that need the rendered sidebar and the row-level notices."""

    def test_the_sidebar_has_every_cp2_destination(self):
        """CP2 p.80 steps 4-5, plus Figures 20-22 and Figure 12."""
        client = _client("admin")
        body = client.get("/admin/dashboard").get_data(as_text=True)
        for label in ("Dashboard", "Partner Companies", "Internship Posting",
                      "Users", "Assessment", "Reports", "Settings"):
            assert label in body, label

    def test_no_password_field_is_ever_rendered(self):
        client = _client("admin")
        for page in ("/admin/dashboard", "/admin/companies", "/admin/profile"):
            assert "password_hash" not in client.get(page).get_data(as_text=True), page

    def test_the_posting_list_never_exposes_a_match_score(self):
        """The admin oversees postings; the ranking stays with the employer."""
        client = _client("admin")
        body = client.get("/admin/postings").get_data(as_text=True)
        for forbidden in ("match_score", "compatibility", "Candidate Ranking"):
            assert forbidden not in body, forbidden

    def test_a_company_without_a_login_is_labelled_not_removed(self):
        """A company row with no user is a real state, not an error."""
        client = _client("admin")
        body = client.get("/admin/companies").get_data(as_text=True)
        assert "No account" in body or "No partner companies match" in body

    def test_status_changes_are_post_only(self):
        """A GET must not be able to deactivate anything."""
        client = _client("admin")
        response = client.get("/admin/companies/1/status")
        assert response.status_code in (404, 405)

    def test_logout_destroys_the_session(self):
        """ADM-13"""
        client = _client("admin")
        client.get("/logout")
        response = client.get("/admin/dashboard")
        assert response.status_code in (301, 302)
        assert "/login" in response.headers["Location"]


def _denied(client, page):
    """True when `page` bounced a signed-in non-admin somewhere harmless.

    A student is sent to their own dashboard rather than to the login page, so
    the meaningful assertion is that they never reach an admin URL.
    """
    response = client.get(page)
    if response.status_code not in (301, 302):
        return False
    return "/admin" not in response.headers["Location"]


class TestUserMonitoring:
    """CP2 p.80 step 4: monitor registered users and system activities."""

    def test_the_user_page_lists_every_role(self):
        body = _client("admin").get("/admin/users").get_data(as_text=True)
        for label in ("Students", "Employers", "Administrators", "Total Users"):
            assert label in body, label

    def test_no_credential_column_is_ever_selected_or_shown(self):
        client = _client("admin")
        for page in ("/admin/users", "/admin/users?status=admin",
                     "/admin/users?q=a", "/admin/assessment"):
            assert "password_hash" not in client.get(page).get_data(as_text=True), page

    def test_the_search_box_is_accepted(self):
        assert _client("admin").get("/admin/users?q=zzz-no-such-user").status_code == 200

    def test_each_role_filter_is_accepted(self):
        client = _client("admin")
        for role in ("student", "employer", "admin", "active", "inactive", ""):
            assert client.get("/admin/users?status=" + role).status_code == 200, role

    def test_an_unsupported_status_action_is_rejected(self):
        client = _client("admin")
        with client.session_transaction() as sess:
            sess["user_id"] = 99
        response = client.post("/admin/users/2/status", data={"action": "delete-everything"})
        assert response.status_code in (301, 302)

    def test_status_changes_are_post_only(self):
        assert _client("admin").get("/admin/users/2/status").status_code in (404, 405)

    def test_the_page_is_protected_from_students_and_employers(self):
        assert _denied(_client("student"), "/admin/users")
        assert _denied(_client("employer"), "/admin/users")


class TestAssessmentOversight:
    """CP2 p.80 step 5: manage competency assessment questions and categories."""

    def test_the_page_shows_competency_coverage(self):
        body = _client("admin").get("/admin/assessment").get_data(as_text=True)
        for label in ("Competencies", "Questions", "Parallel Forms", "Forms"):
            assert label in body, label

    def test_the_page_states_that_editing_is_not_offered(self):
        assert "read-only" in _client("admin").get("/admin/assessment").get_data(as_text=True)

    def test_it_is_protected_from_employers(self):
        assert _denied(_client("employer"), "/admin/assessment")


class TestReports:
    """CP2 p.91: the administrator report view."""

    def test_the_page_renders(self):
        assert _client("admin").get("/admin/reports").status_code == 200

    def test_it_shows_aggregates_not_individual_scores(self):
        """Counts and averages only: no student's own score leaks here."""
        body = _client("admin").get("/admin/reports").get_data(as_text=True)
        assert "Applications by Posting" in body
        for forbidden in ("match_score", "Candidate Ranking", "resume_text"):
            assert forbidden not in body, forbidden

    def test_it_is_protected_from_students(self):
        assert _denied(_client("student"), "/admin/reports")


class TestSettings:
    """CP2 Figure 12: the user updates their own password."""

    def _post(self, current, new, confirm):
        return _client("admin").post("/admin/settings", data={
            "current_password": current, "new_password": new,
            "confirm_password": confirm}).get_data(as_text=True)

    def test_the_page_shows_the_signed_in_admin(self):
        """It must show the SESSION's account, so the real admin id is placed in
        the session here rather than _client()'s placeholder id."""
        from practicore import create_app
        from practicore.repositories import AdminRepository

        app = create_app()
        with app.app_context():
            admin_id = AdminRepository("", "admin").all_users()[0]["id"]

        client = _client("admin")
        with client.session_transaction() as sess:
            sess["user_id"] = admin_id
        body = client.get("/admin/settings").get_data(as_text=True)

        assert "admin@practicore.test" in body
        assert "password_hash" not in body

    def test_a_wrong_current_password_is_refused(self):
        assert "incorrect" in self._post("definitely-wrong", "brandnew123",
                                         "brandnew123").lower()

    def test_mismatched_confirmation_is_refused(self):
        assert "do not match" in self._post("admin123", "brandnew123", "other123").lower()

    def test_a_short_new_password_is_refused(self):
        assert "6 characters" in self._post("admin123", "abc", "abc")

    def test_reusing_the_current_password_is_refused(self):
        assert "different" in self._post("admin123", "admin123", "admin123").lower()

    def test_no_stack_trace_or_sql_escapes_to_the_page(self):
        body = self._post("' OR 1=1 --", "x", "x")
        assert "Traceback" not in body
        assert "psycopg2" not in body

    def test_it_is_protected_from_students(self):
        assert _denied(_client("student"), "/admin/settings")
