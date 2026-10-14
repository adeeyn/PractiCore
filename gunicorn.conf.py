"""Gunicorn production config for PractiCore on Hostinger VPS (Ubuntu).

Usage on the server (from the project dir, venv active):
    gunicorn --config gunicorn.conf.py wsgi:app
"""

import multiprocessing
import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
timeout = 120  # spaCy + pdf parsing can be slow on first hit
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
accesslog = os.environ.get("GUNICORN_ACCESSLOG", "-")
errorlog = os.environ.get("GUNICORN_ERRORLOG", "-")
loglevel = os.environ.get("GUNICORN_LOGLEVEL", "info")
preload_app = True
