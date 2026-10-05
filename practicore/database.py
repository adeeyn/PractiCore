"""Supabase Postgres connection + small MySQL->Postgres shims.

Supabase is Postgres. The two MySQL-isms used across PractiCore are:

  1. `cursor.lastrowid` after INSERT  -> Postgres uses `RETURNING id`.
     `Database.cursor` backfills `.lastrowid` from RETURNING when the
     statement asked for it, so migrated code keeps working.
  2. `ON DUPLICATE KEY UPDATE ... VALUES(col)` -> Postgres
     `ON CONFLICT (...) DO UPDATE SET col = EXCLUDED.col`.
     Use `upsert_sql(...)` below to build it.

`DatabaseError` is re-exported here so repositories can
`except DatabaseError:` without importing psycopg2 directly.
"""
from contextlib import contextmanager
import os
import re

from flask import current_app

try:
    import psycopg2
    import psycopg2.extras

    DatabaseError = psycopg2.Error
except ImportError:  # pragma: no cover - local test env without driver
    psycopg2 = None

    class DatabaseError(Exception):
        pass


def _connect_kwargs():
    """Connection args from env (Supabase) with local fallback.

    Priority:
      1. DATABASE_URL / SUPABASE_DB_URL (pooled Supabase URL - best for Vercel)
      2. Discrete DB_HOST/DB_USER/DB_PASSWORD/DB_NAME/DB_PORT vars
      3. Legacy Flask DB_CONFIG (local config, kept for tests)
    """
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if url:
        return {"_use_url": True, "url": url}

    cfg = {}
    try:
        cfg = dict(current_app.config.get("DB_CONFIG", {}) or {})
    except RuntimeError:
        cfg = {}
    return {
        "_use_url": False,
        "host": os.environ.get("DB_HOST", cfg.get("host", "127.0.0.1")),
        "user": os.environ.get("DB_USER", cfg.get("user", "postgres")),
        "password": os.environ.get("DB_PASSWORD", cfg.get("password", "")),
        "dbname": os.environ.get("DB_NAME", cfg.get("database", cfg.get("dbname", "postgres"))),
        "port": int(os.environ.get("DB_PORT", cfg.get("port", 5432))),
        "sslmode": os.environ.get("DB_SSLMODE", "require"),
    }


class Database:
    """Opens Supabase Postgres connections and guarantees they close.

    Same `with Database.cursor(commit=True) as cursor:` API as before.
    `%s` placeholders still work, rows are dicts.
    """

    @staticmethod
    def connect():
        if psycopg2 is None:
            raise RuntimeError("psycopg2 is not installed. Run: pip install psycopg2-binary")
        kwargs = _connect_kwargs()
        if kwargs.pop("_use_url"):
            return psycopg2.connect(kwargs["url"], sslmode="require")
        return psycopg2.connect(**kwargs)

    @classmethod
    @contextmanager
    def cursor(cls, dictionary=True, commit=False):
        """Usage: `with Database.cursor() as cursor: ...`"""
        conn = cls.connect()
        try:
            cursor_factory = psycopg2.extras.RealDictCursor if dictionary else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            # Compat: backfill .lastrowid from RETURNING when present.
            _orig_execute = cursor.execute

            def execute(sql, params=None):
                result = _orig_execute(sql, params) if params is not None else _orig_execute(sql)
                try:
                    wants_id = isinstance(sql, str) and re.search(
                        r"RETURNING\s+id\b", sql, re.IGNORECASE
                    )
                    if wants_id:
                        row = cursor.fetchone()
                        cursor.lastrowid = row["id"] if isinstance(row, dict) else row[0]
                    elif not hasattr(cursor, "lastrowid"):
                        cursor.lastrowid = None
                except Exception:
                    pass
                return result

            cursor.execute = execute
            if not hasattr(cursor, "lastrowid"):
                cursor.lastrowid = None
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                try:
                    cursor.close()
                except Exception:
                    pass
        finally:
            try:
                conn.close()
            except Exception:
                pass


def upsert_sql(table, columns, conflict, update_columns=None):
    """Builds `INSERT ... ON CONFLICT DO UPDATE` for Postgres.

    Example:
        sql = upsert_sql("applications",
                         ["student_id", "posting_id", "status"],
                         ["student_id", "posting_id"],
                         ["status"])
        # INSERT INTO applications (student_id, posting_id, status)
        # VALUES (%s, %s, %s)
        # ON CONFLICT (student_id, posting_id) DO UPDATE SET status = EXCLUDED.status
    """
    cols = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
    if not conflict:
        return sql
    update_columns = update_columns or [c for c in columns if c not in conflict]
    if not update_columns:
        return sql + f" ON CONFLICT ({', '.join(conflict)}) DO NOTHING"
    assignments = ", ".join(f"{c} = EXCLUDED.{c}" for c in update_columns)
    return sql + f" ON CONFLICT ({', '.join(conflict)}) DO UPDATE SET {assignments}"



