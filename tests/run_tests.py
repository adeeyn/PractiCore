"""Runs the test suite without pytest installed.

    python tests/run_tests.py

pytest is the nicer way to run these (python -m pytest tests/ -q) but it is not
required: this file discovers the Test* classes in the test modules and runs
every test_* method, so the suite works on a bare Python install.
"""
import inspect
import sys
import traceback
from pathlib import Path

from flask import Flask

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _build_fixtures():
    """Instantiates the fixtures the tests use, without depending on pytest."""
    from tests.test_question_bank import FakeQuestionRepository
    from practicore.config import Config
    from practicore.services.assessment_service import AssessmentService

    # Loads the real application settings, so a test can never pass against a
    # config the app does not actually use (e.g. a missing match weight).
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config.update(
        # Fake bank: 20 questions per category, so the per-domain caps are hit.
        QUESTIONS_PER_DOMAIN=15,
        CORE_QUESTIONS_PER_DOMAIN=8,
        RESUME_QUESTIONS_PER_SKILL=2,
        MAX_QUESTIONS_PER_DOMAIN=15,
        ASSESSMENT_GRADING_BYPASS=False,
    )
    return {
        "app": lambda: app,
        "service": lambda: AssessmentService(questions=FakeQuestionRepository()),
    }


def main():
    import tests.test_admin as test_admin
    import tests.test_competency_selection as test_competency_selection
    import tests.test_derived_initials as test_derived_initials
    import tests.test_employer_logo as test_employer_logo
    import tests.test_employer_resume as test_employer_resume
    import tests.test_master_bank as test_master_bank
    import tests.test_matching as test_matching
    import tests.test_question_bank as test_question_bank
    import tests.test_research_bank as test_research_bank
    import tests.test_resume_parser as test_resume_parser
    import tests.test_resume_repository as test_resume_repository

    modules = [test_admin, test_competency_selection, test_derived_initials,
               test_employer_logo, test_employer_resume, test_matching,
               test_question_bank, test_master_bank, test_research_bank,
               test_resume_parser, test_resume_repository]
    fixtures = _build_fixtures()

    passed, failed = 0, []
    for module in modules:
        for class_name, klass in vars(module).items():
            if not (inspect.isclass(klass) and class_name.startswith("Test")):
                continue
            for method_name in dir(klass):
                if not method_name.startswith("test_"):
                    continue
                func = getattr(klass(), method_name)
                names = inspect.signature(func).parameters
                try:
                    with app_context(fixtures, names):
                        func(**{name: fixtures[name]() for name in names})
                    passed += 1
                    print(f"  PASS  {class_name}.{method_name}")
                except Exception:
                    failed.append(f"{class_name}.{method_name}")
                    print(f"  FAIL  {class_name}.{method_name}")
                    traceback.print_exc()

    print(f"\n{passed} passed, {len(failed)} failed")
    if failed:
        print("Failed: " + ", ".join(failed))
    return 1 if failed else 0


def app_context(fixtures, names):
    """A no-op context manager: Flask app context is entered per-test instead."""
    from contextlib import contextmanager

    @contextmanager
    def ctx():
        app = fixtures["app"]()
        with app.app_context():
            yield

    return ctx()


if __name__ == "__main__":
    sys.exit(main())
