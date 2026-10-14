"""Production WSGI entry point for PractiCore.

Used by gunicorn on the VPS::

    gunicorn --config gunicorn.conf.py wsgi:app

``app.py`` stays as the local-dev entry (``python app.py``); this module is
what the production server imports so dev-only behaviour in ``app.py``
(``debug=True``) never leaks into production.
"""

import os

# Load /var/www/practicore/.env (or ./env) when python-dotenv is installed.
# systemd also provides these via EnvironmentFile, so this is a no-op there —
# it mainly helps `gunicorn wsgi:app` runs without systemd.
try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(os.path.abspath(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

from practicore import create_app

app = create_app()
