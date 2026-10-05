"""All SQL the Administrator Module needs: counts, monitoring lists, and the
partner-company creation transaction.

Read-only for everything the employer owns. The administrator observes
postings, competencies and scores; this module never writes to the matching,
assessment or ranking data.
"""
from ..database import Database, DatabaseError, upsert_sql
from ..initials import initials_for
from .user_repository import UserRepository

# Re-exported so callers can catch it without importing psycopg2 directly.


class AdminRepository:
    """Read models for the admin pages, plus partner-company creation.

    Search and filter state lives on the instance rather than being passed to
    every call, so each list method builds its own WHERE clause from the same
    two values. All values are bound with %s.
    """

    def __init__(self, search="", status=""):
        self.search = (search or "").strip()
        self.status = (status or "").strip()

    # ---------- Dashboard ----------

    def stats(self):
        """Counters for the dashboard. One round trip, one row per source.

        Active means `is_active` for accounts and `status='active'` for postings,
        which is the same distinction the lists below use.
        """
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT
                  (SELECT COUNT(*) FROM students)                          AS students,
                  (SELECT COUNT(*) FROM students s
                     JOIN users u ON u.id = s.user_id
                    WHERE u.is_active = 1)                                 AS active_students,
                  (SELECT COUNT(*) FROM employers)                        AS companies,
                  (SELECT COUNT(*) FROM employers e
                     JOIN users u ON u.id = e.user_id
                    WHERE u.is_active = 1)                                 AS active_employers,
                  (SELECT COUNT(*) FROM employers WHERE user_id IS NULL)   AS pending_accounts,
                  (SELECT COUNT(*) FROM internship_postings)              AS postings,
                  (SELECT COUNT(*) FROM internship_postings
                    WHERE status = 'active')                              AS active_postings,
                  (SELECT COUNT(*) FROM applications)                    AS applications,
                  (SELECT COUNT(*) FROM users WHERE role = 'admin')       AS admins
            """)
            return cursor.fetchone()

    def recent_employers(self, limit=5):
        """Newest partner companies, with the login status of each account."""
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.company_name, e.company_logo_text, e.location,
                       e.contact_name, e.contact_phone, e.created_at,
                       u.email, u.is_active, u.created_at AS registered_at
                FROM employers e
                LEFT JOIN users u ON u.id = e.user_id
                ORDER BY COALESCE(u.created_at, e.created_at) DESC, e.id DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()

    def recent_companies(self, limit=5):
        """Partner companies by registration date, newest first."""
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT e.id, e.company_name, e.company_logo_text, e.location,
                       e.contact_name, e.created_at,
                       u.is_active, u.email,
                       (SELECT COUNT(*) FROM internship_postings p
                         WHERE p.employer_id = e.id) AS posting_count
                FROM employers e
                LEFT JOIN users u ON u.id = e.user_id
                ORDER BY e.created_at DESC, e.id DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()

    def recent_postings(self, limit=5):
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.title, p.department, p.status, p.posted_date,
                       p.positions_available,
                       e.company_name, e.company_logo_text
                FROM internship_postings p
                JOIN employers e ON e.id = p.employer_id
                ORDER BY p.posted_date DESC, p.id DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()

# ---------- Registered user monitoring (CP2 p.80 step 4) ----------

    def all_users(self):
        """Every account, with its role and display name.

        The display name comes from `students.name` for student accounts and from
        the company contact for employer accounts, because `users` has no name
        column of its own. password_hash is never selected.
        """
        sql = """
            SELECT u.id, u.email, u.username, u.role, u.is_active, u.created_at,
                   COALESCE(s.name, e.contact_name, e.company_name) AS display_name,
                   s.student_no, e.company_name
            FROM users u
            LEFT JOIN students s ON s.user_id = u.id
            LEFT JOIN employers e ON e.user_id = u.id
            WHERE 1 = 1
        """
        params = []
        if self.search:
            sql += (" AND (u.email LIKE %s OR u.username LIKE %s "
                    "OR s.name LIKE %s OR e.company_name LIKE %s)")
            like = "%" + self.search + "%"
            params += [like] * 4
        if self.status in ("active", "inactive"):
            sql += " AND u.is_active = %s"
            params.append(1 if self.status == "active" else 0)
        if self.status in ("student", "employer", "admin"):
            sql += " AND u.role = %s"
            params.append(self.status)
        sql += " ORDER BY u.created_at DESC, u.id DESC"
        return self._run(sql, params)

    def users_by_role(self):
        with Database.cursor() as cursor:
            cursor.execute("SELECT role, COUNT(*) AS n FROM users GROUP BY role")
            counts = {r["role"]: r["n"] for r in cursor.fetchall()}
        return {
            "students": counts.get("student", 0),
            "employers": counts.get("employer", 0),
            "admins": counts.get("admin", 0),
            "total": sum(counts.values()),
        }

    def set_user_active(self, user_id, is_active):
        """Activates or deactivates any account.

        Guarded against self-deactivation: an administrator who switches their own
        account off locks themselves out with no other admin to restore it.
        """
        from flask import session

        me = session.get("user_id")
        if me is not None and int(user_id) == int(me):
            return False
        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                "UPDATE users SET is_active = %s WHERE id = %s", (1 if is_active else 0, user_id))
            return cursor.rowcount > 0

    # ---------- Assessment content and reports (CP2 p.80 step 5, p.91) ----------

    def question_bank_overview(self):
        """Per-competency counts of questions and parallel forms.

        Read-only. The administrator sees what exists and how well covered each
        competency is.
        """
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT c.code, c.name, c.is_core,
                       COUNT(DISTINCT m.question_id) AS question_count,
                       COUNT(DISTINCT qs.id) AS form_count
                FROM competencies c
                LEFT JOIN question_sets qs ON qs.competency_code = c.code
                LEFT JOIN question_set_members m ON m.set_id = qs.id
                GROUP BY c.code, c.name, c.is_core
                ORDER BY c.is_core DESC, c.name
            """)
            return cursor.fetchall()

    def report_summary(self):
        """Aggregate figures for the administrator report page.

        Every number is a COUNT or an AVG over existing tables. Nothing from the
        matching pipeline is exposed beyond a count.
        """
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT
                  (SELECT COUNT(*) FROM students)                   AS students,
                  (SELECT COUNT(*) FROM employers)                 AS companies,
                  (SELECT COUNT(*) FROM internship_postings)        AS postings,
                  (SELECT COUNT(*) FROM internship_postings
                    WHERE status = 'active')                      AS active_postings,
                  (SELECT COUNT(*) FROM applications)              AS applications,
                  (SELECT COUNT(*) FROM users WHERE role='employer') AS employers,
                  (SELECT COUNT(*) FROM assessment_questions)      AS questions,
                  (SELECT COUNT(*) FROM competencies)              AS competencies,
                  (SELECT COUNT(*) FROM assessment_attempts)       AS attempts,
                  (SELECT COUNT(*) FROM students
                    WHERE total_questions > 0)                     AS students_assessed,
                  (SELECT ROUND(AVG(assessment_score / total_questions * 100))
                     FROM students WHERE total_questions > 0)      AS mean_assessment
            """)
            return cursor.fetchone()

    def applications_by_posting(self, limit=8):
        """How many applications each posting has drawn, highest first."""
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT p.id, p.title, e.company_name, p.status,
                       COUNT(a.id) AS application_count
                FROM internship_postings p
                JOIN employers e ON e.id = p.employer_id
                LEFT JOIN applications a ON a.posting_id = p.id
                GROUP BY p.id, p.title, e.company_name, p.status
                ORDER BY application_count DESC, p.posted_date DESC
                LIMIT %s
            """, (limit,))
            return cursor.fetchall()

    def recent_activity(self, limit=8):
        """A merged, time-ordered feed of the events an admin cares about.

        Built in Python from two ordered queries rather than one UNION, so each
        source keeps its own readable SQL.
        """
        entries = []
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT u.role, u.created_at, u.email,
                       COALESCE(s.name, e.contact_name, e.company_name) AS who
                FROM users u
                LEFT JOIN students s ON s.user_id = u.id
                LEFT JOIN employers e ON e.user_id = u.id
                ORDER BY u.created_at DESC, u.id DESC
                LIMIT 5
            """)
            for row in cursor.fetchall():
                label = {"student": "New student registered",
                         "employer": "New partner company registered",
                         "admin": "New administrator registered"}.get(
                             row["role"], "New user registered")
                entries.append((row["created_at"], label, row["who"] or row["email"], "user"))

            cursor.execute("""
                SELECT p.title, p.status, p.posted_date, e.company_name,
                       (SELECT COUNT(*) FROM applications a
                         WHERE a.posting_id = p.id) AS n
                FROM internship_postings p
                JOIN employers e ON e.id = p.employer_id
                ORDER BY p.posted_date DESC, p.id DESC
                LIMIT 5
            """)
            for row in cursor.fetchall():
                if row["status"] == "closed":
                    label = "%s posting closed" % row["title"]
                else:
                    label = "%s posting created" % row["title"]
                    if row["n"]:
                        label += " received %d applicant%s" % (
                            row["n"], "" if row["n"] == 1 else "s")
                entries.append((row["posted_date"], label, row["company_name"], "posting"))

        entries.sort(key=lambda e: str(e[0]), reverse=True)
        return entries[:limit]

    def count_new_partner_companies(self, days=30):
        """Companies added in the last N days, for the dashboard trend line."""
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS n FROM employers "
                "WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)", (days,))
            return (cursor.fetchone() or {}).get("n", 0)

    # ---------- Administrator own account ----------

    def find_user(self, user_id):
        """One account by id, for the administrator profile page.

        The password_hash column is deliberately NOT selected: no admin screen
        has any reason to hold a credential in memory.
        """
        if not user_id:
            return None
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT id, email, username, role, is_active, created_at
                FROM users WHERE id = %s
            """, (user_id,))
            return cursor.fetchone()

    # ---------- Employer account management (CP2 1.3.2) ----------

    def all_employer_accounts(self):
        """Every partner company with its login and posting count.

        Parameterised end to end: the search term and the status filter are
        bound with %s, never string-formatted into the SQL.
        """
        sql = """
            SELECT e.id, e.company_name, e.company_logo_text, e.industry, e.location,
                   e.contact_name, e.contact_position, e.contact_phone, e.created_at,
                   u.id AS user_id, u.email, u.is_active, u.created_at AS registered_at,
                   (SELECT COUNT(*) FROM internship_postings p
                     WHERE p.employer_id = e.id) AS posting_count
            FROM employers e
            LEFT JOIN users u ON u.id = e.user_id
            WHERE 1 = 1
        """
        params = []
        if self.search:
            sql += (" AND (e.company_name LIKE %s OR u.email LIKE %s "
                    "OR e.contact_name LIKE %s OR e.location LIKE %s)")
            like = "%" + self.search + "%"
            params += [like] * 4
        if self.status in ("active", "inactive"):
            sql += " AND u.is_active = %s"
            params.append(1 if self.status == "active" else 0)
        # Pending = company exists but no login has been attached yet.
        if self.status == "pending":
            sql += " AND u.id IS NULL"
        sql += " ORDER BY e.company_name"
        return self._run(sql, params)

    def find_employer(self, employer_id):
        with Database.cursor() as cursor:
            cursor.execute("""
                SELECT e.*, u.email, u.is_active, u.created_at AS registered_at
                FROM employers e
                LEFT JOIN users u ON u.id = e.user_id
                WHERE e.id = %s
            """, (employer_id,))
            return cursor.fetchone()

    def set_account_active(self, employer_id, is_active):
        """Activates or deactivates an employer login.

        The account is never deleted: an internship posting has to keep its
        employer, so deactivation hides the login while preserving the record.
        Returns True when a row changed.
        """
        with Database.cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE users u
                JOIN employers e ON e.user_id = u.id
                SET u.is_active = %s
                WHERE e.id = %s
            """, (1 if is_active else 0, employer_id))
            return cursor.rowcount > 0

    def _run(self, sql, params):
        with Database.cursor() as cursor:
            cursor.execute(sql, tuple(params))
            return cursor.fetchall()

    # ---------- Internship posting monitoring (CP2 1.3.4) ----------

    def all_postings(self):
        """Every posting with its company, skills and required competencies.

        Competency requirements are aggregated in SQL rather than per posting,
        so the table does not issue N+1 queries while rendering.
        """
        sql = """
            SELECT p.id, p.title, p.department, p.description, p.status,
                   p.is_remote, p.positions_available, p.posted_date,
                   e.id AS employer_id, e.company_name, e.company_logo_text,
                   e.location,
                   (SELECT string_agg(s.skill_name, ', ' ORDER BY s.skill_name)
                      FROM posting_skills s WHERE s.posting_id = p.id) AS skills,
                   (SELECT string_agg(r.competency_code || ' (' || r.importance || ')',
                                      ', ' ORDER BY r.importance, r.competency_code)
                      FROM internship_competency_requirements r
                     WHERE r.posting_id = p.id) AS competencies,
                   (SELECT COUNT(*) FROM applications a
                     WHERE a.posting_id = p.id) AS application_count
            FROM internship_postings p
            JOIN employers e ON e.id = p.employer_id
            WHERE 1 = 1
        """
        params = []
        if self.search:
            sql += (" AND (p.title LIKE %s OR p.description LIKE %s "
                    "OR e.company_name LIKE %s OR p.department LIKE %s)")
            like = "%" + self.search + "%"
            params += [like] * 4
        if self.status in ("active", "closed"):
            sql += " AND p.status = %s"
            params.append(self.status)
        sql += " ORDER BY p.posted_date DESC, p.id DESC"
        return self._run(sql, params)

    def find_posting(self, posting_id):
        rows = self.all_postings()
        for row in rows:
            if int(row["id"]) == int(posting_id):
                return row
        return None

    def set_posting_status(self, posting_id, status):
        """Opens or closes a posting. The employer still owns its content.

        Only `status` is written. The description, skills and competency
        requirements belong to the employer and are never modified here, which
        is what keeps the administrator out of the matching pipeline.
        """
        if status not in ("active", "closed"):
            raise ValueError("Unsupported posting status.")
        with Database.cursor(commit=True) as cursor:
            cursor.execute(
                "UPDATE internship_postings SET status = %s WHERE id = %s",
                (status, posting_id),
            )
            return cursor.rowcount > 0

    # ---------- Partner company account creation (CP2 1.3.2) ----------

    def company_name_taken(self, company_name):
        """Duplicate check.

        The default MySQL collation is already case-insensitive, so the lookup
        catches "Acme Corp" against an existing "acme corp" with no extra
        LOWER() in the query.
        """
        with Database.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM employers WHERE company_name = %s", (company_name,))
            return cursor.fetchone() is not None

    def create_partner_company(self, data, password_hash):
        """Creates the company and its employer login in ONE transaction.

        A company row with no login would be a company nobody can log into, so
        both are written together or neither is.
        """
        with Database.cursor(commit=True) as cursor:
            # Re-check inside the transaction: the page check can be stale by the
            # time this runs, and a duplicate would otherwise raise a raw
            # IntegrityError out of the DB layer.
            cursor.execute(
                "SELECT id FROM users WHERE email = %s", (data["email"],))
            if cursor.fetchone():
                raise ValueError("An account with that email already exists.")

            cursor.execute(
                "SELECT id FROM employers WHERE company_name = %s",
                (data["company_name"],))
            if cursor.fetchone():
                raise ValueError("A company with that name already exists.")

            user_id = UserRepository.insert(
                cursor, data["email"], None, password_hash, "employer")

            # The initials are derived, never typed: the admin form has no field
            # for them, so they always match the company name beside them.
            logo = initials_for(data["company_name"])

            cursor.execute("""
                INSERT INTO employers
                    (user_id, company_name, company_logo_text, industry, location, about,
                     required_skills, contact_name, contact_position, contact_phone,
                     website, company_size, is_hiring)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_id, data["company_name"], logo, data.get("industry"),
                  data["location"], data.get("about"), data.get("required_skills"),
                  data.get("contact_name"), data.get("contact_position"),
                  data.get("contact_phone"), data.get("website"),
                  data.get("company_size"), 1 if data.get("is_hiring") else 0))
            return cursor.lastrowid
