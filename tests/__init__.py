"""Logic tests for the matching pipeline. Run with: python -m pytest tests/ -q

Deliberately dependency-light: everything here runs without MySQL, spaCy or
scikit-learn, because the point is to test OUR logic (feature layout, question
selection, fallback behaviour) rather than the libraries.
"""
