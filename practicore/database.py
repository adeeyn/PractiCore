from contextlib import contextmanager

import mysql.connector
from flask import current_app


class Database:
    """Opens MySQL connections and guarantees they are closed."""

    @staticmethod
    def connect():
        return mysql.connector.connect(**current_app.config["DB_CONFIG"])

    @classmethod
    @contextmanager
    def cursor(cls, dictionary=True, commit=False):
        """Usage: `with Database.cursor() as cursor: ...`"""
        conn = cls.connect()
        cursor = conn.cursor(dictionary=dictionary)
        try:
            yield cursor
            if commit:
                conn.commit()
        finally:
            cursor.close()
            conn.close()
