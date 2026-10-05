from .assessment_service import AssessmentService
from .auth_service import AuthService
from .matching_service import MatchingService
from .recommendation_service import RecommendationService
from .resume_parser import ResumeParser
from .skill_taxonomy import SkillTaxonomy

# NOTE: the competency modules (competency_taxonomy, assessment_selection,
# cross_matching) are deliberately NOT imported here. They are reached by their
# full module path, because they are imported BY the repositories layer and
# re-exporting them would create a cycle:
#   repositories -> services/__init__ -> matching_service -> repositories.

__all__ = [
    "AssessmentService",
    "AuthService",
    "MatchingService",
    "RecommendationService",
    "ResumeParser",
    "SkillTaxonomy",
]
