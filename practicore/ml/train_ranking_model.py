"""Offline trainer for the Random Forest ranking model.

Run from the project root (it needs a configured DB and app context):

    flask --app app retrain-ranking
    flask --app app retrain-ranking --allow-synthetic   # demo data only

Labels
------
By default this trains on REAL outcomes: an application counts as a positive
only if the employer moved the student to `Shortlisted`, `Scheduled` or
`Hired`. That is the only label source that means anything, because it is the
employer's own decision rather than our own scoring formula.

`--allow-synthetic` exists so a demo can be run before any real hiring outcome
exists, but it labels rows with the same weighted formula the fallback scorer
uses. A model trained that way can only learn to reproduce that formula, so it
is stamped `label_source: synthetic` in the metadata and the UI says so out
loud. Never present one as trained on real outcomes.

Outputs
-------
    practicore/models/ranking_rf.joblib   the estimator + feature schema
    practicore/models/ranking_rf.meta.json  provenance, metrics, importances
"""


import json
import os
from datetime import datetime

from flask import current_app

from ..repositories import ApplicationRepository, AssessmentRepository
from .features import (
    FEATURE_NAMES,
    FEATURE_SCHEMA_VERSION,
    build_features,
    feature_importance_report,
)

# The employer statuses that mean "this candidate was good enough".
POSITIVE_STATUSES = ("Shortlisted", "Scheduled", "Hired")
# Below this many labelled rows a forest would only be memorising the sample.
MIN_SAMPLES = 30


def _load_training_rows(allow_synthetic):
    """Builds (rows, labels, label_source, count) from the applications table.

    Rows go through the same `build_features` the live scorer uses, so the model
    can never be trained on a different vector than it is scored on.
    """
    applications = ApplicationRepository()
    assessments = AssessmentRepository()

    labelled = applications.for_training()
    if not labelled:
        raise RuntimeError(
            "No labelled applications found. PractiCore needs employer outcomes "
            "(Shortlisted/Scheduled/Hired vs the rest) before it can train."
        )

    # One domain-score lookup per student, not one per application.
    domain_cache = {}
    rows, labels, label_source = [], [], "real"

    for app in labelled:
        student_id = app["student_id"]
        if student_id not in domain_cache:
            domain_cache[student_id] = assessments.for_student(student_id)

        total_questions = app.get("total_questions") or 0
        overall = round((app["assessment_score"] / total_questions) * 100) if total_questions else 0

        student = {
            "skills": app.get("skills") or "",
            "assessment_overall": overall,
            "domain_scores": domain_cache[student_id],
        }
        rows.append(build_features(student, app["skills_required"]))

        if allow_synthetic:
            # Circular by construction: this only teaches the model our formula.
            from ..services.matching_service import MatchingService

            label_source = "synthetic"
            labels.append(
                1 if MatchingService.fallback_score(student, app["skills_required"]) >= 60 else 0
            )
        else:
            labels.append(1 if app["status"] in POSITIVE_STATUSES else 0)

    return rows, labels, label_source, len(labelled)



def train(allow_synthetic=False, model_path=None, n_estimators=200):
    """Trains the forest, writes the artifact, and returns its metadata.

    Refuses to write a model trained on too little data, because a forest fitted
    on a handful of rows scores confidently and is worse than the fallback.
    """
    try:
        import joblib
        import numpy as np
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import accuracy_score, roc_auc_score
        from sklearn.model_selection import train_test_split
    except ImportError as exc:
        raise RuntimeError(
            "Training needs scikit-learn, numpy and joblib. "
            f"Install them with: pip install scikit-learn numpy joblib ({exc})"
        )

    rows, labels, label_source, count = _load_training_rows(allow_synthetic)

    positives = sum(labels)
    if label_source == "real":
        print(f"Labelled applications: {count} ({positives} positive / {count - positives} negative)")
        if count < MIN_SAMPLES:
            raise RuntimeError(
                f"Only {count} labelled applications (need >= {MIN_SAMPLES}). A Random Forest "
                "trained on this little data would just memorise it. Keep using the weighted "
                "content-based scorer, or pass --allow-synthetic for a clearly-labelled demo model."
            )
        if positives == 0 or positives == count:
            raise RuntimeError(
                "Every application has the same label - there is nothing to learn from. "
                "Move some candidates to Shortlisted/Hired and some to Rejected first."
            )
    else:
        print("WARNING: training on SYNTHETIC labels derived from the weighted formula.")
        print("         This model can only reproduce that formula. Do not present it as")
        print("         trained on real employer outcomes.")

    X = np.array(rows, dtype=float)
    y = np.array(labels, dtype=int)

    # Stratify so a rare 'Hired' still lands in the test split.
    stratify = y if min(np.bincount(y)) >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=stratify
    )

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    accuracy = float(accuracy_score(y_test, predictions))
    try:
        auc = float(roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]))
    except ValueError:
        auc = None  # only one class present in the split

    importances = feature_importance_report(model)
    meta = {
        "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "label_source": label_source,
        "algorithm": "RandomForestClassifier",
        "n_estimators": n_estimators,
        "training_rows": count,
        "positives": positives,
        "accuracy": accuracy,
        "roc_auc": auc,
        "feature_names": list(FEATURE_NAMES),
        "feature_importances": {name: float(value) for name, value in importances},
    }

    model_path = model_path or current_app.config["RANKING_MODEL_PATH"]
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    joblib.dump(
        {
            "model": model,
            "feature_names": list(FEATURE_NAMES),
            "schema_version": FEATURE_SCHEMA_VERSION,
            "meta": meta,
        },
        model_path,
    )

    with open(os.path.splitext(model_path)[0] + ".meta.json", "w", encoding="utf-8") as handle:
        json.dump(meta, handle, indent=2)

    print(f"\nTrained on {count} rows ({label_source} labels)")
    print(f"Validation accuracy: {accuracy:.1%}" + (f" | ROC AUC: {auc:.3f}" if auc else ""))
    print("Top feature importances:")
    for name, value in importances[:6]:
        print(f"  {name:24s} {value:.3f}")
    print(f"\nSaved model to   {model_path}")
    print(f"Saved metadata to {os.path.splitext(model_path)[0]}.meta.json")
    return meta
