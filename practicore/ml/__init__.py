"""Ranking model support: shared feature building and the offline trainer.

Kept import-light on purpose: `features` must import on a machine that has no
scikit-learn, so the web app still boots with the fallback scorer.
"""
