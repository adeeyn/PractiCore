from ..repositories import PostingRepository
from .skill_taxonomy import SkillTaxonomy


class RecommendationService:
    """Scores internship postings against a student's resume skills and assessment results."""

    def __init__(self, postings=None):
        self.postings = postings or PostingRepository()

    @staticmethod
    def _logo_for(posting):
        # Extract initials for logo fallback (e.g., Tech Solution Inc -> TS)
        logo = posting["company_logo_text"]
        if not logo and posting["company_name"]:
            logo = "".join(word[0] for word in posting["company_name"].split()[:2]).upper()
        return logo or "IT"

    def for_dashboard(self, student_skills, category_breakdown, assessment_percentage, limit=3):
        """Top postings for the dashboard preview.

        Returns (recommendations, average_resume_match_percent).
        """
        recommendations = []
        resume_match_scores = []

        for posting in self.postings.all_with_skills():
            posting_skills = posting["skills"]
            matched = SkillTaxonomy.match_required_skills(posting_skills, student_skills)
            resume_match_pct = round((len(matched) / len(posting_skills)) * 100) if posting_skills else 0

            category = SkillTaxonomy.map_skills_to_category(posting_skills)
            assessment_match_pct = category_breakdown.get(category, {}).get("score_percent", assessment_percentage)

            # Combined Match Score (50% Assessment + 50% Resume Match)
            if resume_match_pct > 0:
                combined_match = round((assessment_match_pct + resume_match_pct) / 2)
            else:
                combined_match = assessment_match_pct

            resume_match_scores.append(resume_match_pct)
            recommendations.append({
                "id": posting["id"],
                "title": posting["title"],
                "company": posting["company_name"],
                "location": posting["location"],
                "logo": self._logo_for(posting),
                "is_remote": posting["is_remote"],
                "match_score": combined_match if combined_match > 0 else 75,
                "match_color_class": "green" if combined_match >= 85 else "amber",
            })

        if resume_match_scores:
            avg_resume_match = round(sum(resume_match_scores) / len(resume_match_scores))
        else:
            avg_resume_match = 85 if student_skills else 0

        recommendations.sort(key=lambda r: r["match_score"], reverse=True)
        return recommendations[:limit], avg_resume_match

    def for_recommendation_page(self, student_skills, category_breakdown):
        """Postings that match at least one resume skill, ranked by domain assessment score."""
        recommendations = []

        for posting in self.postings.all_with_skills():
            posting_skills = posting["skills"]
            matched = SkillTaxonomy.match_required_skills(posting_skills, student_skills)

            # RESUME FILTER: Only display companies that match at least 1 resume skill
            if not matched:
                continue

            category = SkillTaxonomy.map_skills_to_category(posting_skills)
            match_score = category_breakdown.get(category, {}).get("score_percent", 50)

            if match_score >= 80:
                badge_class = "high"
            elif match_score >= 60:
                badge_class = "medium"
            else:
                badge_class = "top"

            recommendations.append({
                "id": posting["id"],
                "title": posting["title"],
                "company": posting["company_name"],
                "location": posting["location"],
                "logo": posting["company_logo_text"],
                "description": posting["description"],
                "is_remote": posting["is_remote"],
                "skills": posting_skills,
                "matched_resume_skills": matched,
                "match_score": match_score,
                "match_badge_class": badge_class,
                "recommended_category": category,
                "posted": posting["posted_date"].strftime("%b %d, %Y") if posting["posted_date"] else "Recently",
            })

        recommendations.sort(key=lambda r: r["match_score"], reverse=True)
        return recommendations
