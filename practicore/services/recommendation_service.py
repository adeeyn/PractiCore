from flask import current_app

from ..initials import initials_for
from ..repositories import PostingRepository
from .skill_taxonomy import SkillTaxonomy


class RecommendationService:
    """Scores internship postings against a student's resume skills and assessment results.

    Scoring itself is delegated to MatchingService so that recommendations, the
    Apply button, seeded applications and the employer ranking all agree on one
    number. This class only does the listing, filtering and presentation.
    """

    def __init__(self, postings=None):
        self.postings = postings or PostingRepository()

    @staticmethod
    def _matcher():
        """The app-wide scorer, or an unmodelled one when there is no app context.

        Imported here rather than at module scope because MatchingService falls
        back to `combined_match_score` below, which would be a circular import.
        """
        from flask import current_app

        from .matching_service import MatchingService

        matcher = current_app.extensions.get("matching_service") if current_app else None
        return matcher or MatchingService()

    @staticmethod
    def _logo_for(posting):
        """The company badge on a recommendation card.

        Derived from the name so a card can never show initials that disagree
        with the company it belongs to. 'IT' is the last resort for a posting
        whose company name is somehow blank.

        This is derived rather than read from employers.company_logo_text on
        purpose. The posting query joins employers only for company_name and
        location, so that column is not in the row at all - indexing it raised
        KeyError: 'company_logo_text' and took the whole page down. Deriving it
        also keeps the badge correct for a company renamed outside the profile
        form, which is the same reason application_repository and
        employer/context.py derive instead of storing.
        """
        return initials_for(posting.get("company_name"), fallback="IT")

    @staticmethod
    def relevant_assessment_score(posting_skills, domain_scores, overall_percentage):
        """The assessment score that actually speaks to this posting.

        The research note says objective items are the primary evidence, so the
        score for the job category this posting belongs to is far more
        informative than the student's flat overall average. A candidate strong
        in Networking but weak in Web Development should not be handed a web
        posting on the strength of a 94% average.

        Falls back to the overall percentage when the domain is unknown or the
        student has no per-domain breakdown (migration 006 not applied yet).
        """
        if not posting_skills or not domain_scores:
            return overall_percentage

        category = SkillTaxonomy.map_skills_to_category(posting_skills)
        for domain, percent in domain_scores.items():
            if domain == category and percent is not None:
                return percent
        return overall_percentage

    @staticmethod
    def match_breakdown(posting_skills, student_skills, assessment_percentage, domain_scores=None):
        """Every input to the match score, so the UI can show how it was reached.

        Returns a dict rather than a bare number because a single "68%" tells a
        student nothing about why. The weights here are the documented ones.
        """
        matched = SkillTaxonomy.match_required_skills(posting_skills, student_skills)
        resume_pct = round((len(matched) / len(posting_skills)) * 100) if posting_skills else 0

        overall = min(assessment_percentage or 0, 100)
        relevant = RecommendationService.relevant_assessment_score(
            posting_skills, domain_scores or {}, overall
        )
        relevant = min(relevant, 100)

        assessment_weight = current_app.config["MATCH_ASSESSMENT_WEIGHT"]
        resume_weight = current_app.config["MATCH_RESUME_WEIGHT"]

        score = round(relevant * assessment_weight + resume_pct * resume_weight)

        return {
            "score": score,
            "matched_skills": matched,
            "missing_skills": [s for s in posting_skills if s not in matched],
            "required_count": len(posting_skills),
            "matched_count": len(matched),
            "resume_percent": resume_pct,
            "assessment_overall": overall,
            "assessment_relevant": relevant,
            "assessment_weight": assessment_weight,
            "resume_weight": resume_weight,
            # The two halves, reported on their own. They are the exact operands
            # of `score` above, so:
            #   score == round(assessment_match_percent * assessment_weight
            #                 + resume_match_percent * resume_weight)
            # Pages show both percentages beside the combined number, because one
            # figure on its own cannot say whether an applicant is strong, thinly
            # evidenced, or the reverse. `resume_percent` / `assessment_relevant`
            # stay as the older aliases so nothing existing breaks.
            "resume_match_percent": resume_pct,
            "assessment_match_percent": relevant,
        }

    @staticmethod
    def combined_match_score(posting_skills, student_skills, assessment_percentage, domain_scores=None):
        """The score employers rank applicants on.

        Weighted, not averaged: the objective assessment carries most of the
        score and the resume only corroborates it, per the research note that
        self-reported skills are not proof of capability. `domain_scores` lets a
        posting be scored against the student's score in its own job category.
        """
        return RecommendationService.match_breakdown(
            posting_skills, student_skills, assessment_percentage, domain_scores
        )["score"]

    def for_dashboard(self, student_skills, assessment_percentage, limit=3, domain_scores=None):
        """Top postings for the dashboard preview.

        Returns (recommendations, average_resume_match_percent).
        """
        matcher = self._matcher()
        student_profile = {"skills": student_skills, "domain_scores": domain_scores or {}}
        recommendations = []
        resume_match_scores = []

        for posting in self.postings.all_with_skills():
            posting_skills = posting["skills"]

            # Same shared scorer the employer ranks applicants on, asked for the
            # combined number and the two separated percentages in one pass.
            components = matcher.score_components(
                student_profile, posting_skills, assessment_percentage=assessment_percentage
            )
            match_score = components["match_score"]

            resume_match_scores.append(components["resume_match_percent"])
            recommendations.append({
                "id": posting["id"],
                "title": posting["title"],
                "company": posting["company_name"],
                "location": posting["location"],
                "logo": self._logo_for(posting),
                "is_remote": posting["is_remote"],
                "match_score": match_score,
                "match_color_class": "green" if match_score >= 85 else "amber",
                # Shown beside the combined badge so the student can see which
                # half of the evidence is producing it.
                "resume_match_percent": components["resume_match_percent"],
                "assessment_match_percent": components["assessment_match_percent"],
            })

        if resume_match_scores:
            avg_resume_match = round(sum(resume_match_scores) / len(resume_match_scores))
        else:
            # No postings to compare against: report 0 rather than inventing 85.
            avg_resume_match = 0

        recommendations.sort(key=lambda r: r["match_score"], reverse=True)
        return recommendations[:limit], avg_resume_match

    def for_recommendation_page(self, student_skills, assessment_percentage, domain_scores=None):
        """Postings that match at least one resume skill, ranked by match score.

        Uses the same shared scorer as the employer applicant page, so a student
        sees the exact number their application will carry.
        """
        matcher = self._matcher()
        student_profile = {"skills": student_skills, "domain_scores": domain_scores or {}}
        recommendations = []

        for posting in self.postings.all_with_skills():
            posting_skills = posting["skills"]
            matched = SkillTaxonomy.match_required_skills(posting_skills, student_skills)

            # RESUME FILTER: Only display companies that match at least 1 resume skill
            if not matched:
                continue

            category = SkillTaxonomy.map_skills_to_category(posting_skills)
            # The score itself comes from the shared scorer, so a trained Random
            # Forest still drives it. Without a model this is the weighted
            # fallback, and the two agree because fallback_score uses the same
            # weights as match_breakdown.
            match_score = matcher.score(
                student_profile, posting_skills, assessment_percentage=assessment_percentage
            )
            breakdown = RecommendationService.match_breakdown(
                posting_skills, student_skills, assessment_percentage, domain_scores
            )

            if match_score >= 80:
                badge_class = "high"
            elif match_score >= 60:
                badge_class = "medium"
            else:
                badge_class = "low"

            recommendations.append({
                "id": posting["id"],
                "title": posting["title"],
                "company": posting["company_name"],
                "location": posting["location"],
                "logo": self._logo_for(posting),
                "description": posting["description"],
                "is_remote": posting["is_remote"],
                "skills": posting_skills,
                "matched_resume_skills": matched,
                "match_score": match_score,
                "match_badge_class": badge_class,
                "recommended_category": category,
                # Shown on the card so the student can see how the number was
                # reached instead of taking it on faith.
                "match_breakdown": breakdown,
                "posted": posting["posted_date"].strftime("%b %d, %Y") if posting["posted_date"] else "Recently",
            })

        recommendations.sort(key=lambda r: r["match_score"], reverse=True)
        return recommendations
