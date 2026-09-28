class SkillTaxonomy:
    """The 6 core job categories and the helpers that map skills/tracks onto them."""

    DEFAULT_CATEGORY = "Software & Application Development"

    # Mapped Skills Taxonomy aligned with the 6 Core Job Categories
    SKILL_CATEGORY_MAP = {
        "Software & Application Development": [
            "Python", "Java", "C++", "VB.NET", "JavaScript", "HTML", "CSS",
            "React", "Node.js", "Flask", "Django", "UI/UX", "Git"
        ],
        "Systems, Infrastructure & Networks": [
            "Networking", "Cisco", "TCP/IP", "VLAN", "Linux", "Windows Server",
            "Cloud", "AWS", "Docker", "Cybersecurity"
        ],
        "IT Service Management & Operations": [
            "ITIL", "Service Desk", "Incident Management", "Agile", "Scrum",
            "Jira", "Technical Support"
        ],
        "Data, AI & Analytics": [
            "SQL", "PostgreSQL", "MongoDB", "Machine Learning", "Data Analysis",
            "NLP", "Pandas", "Power BI", "Tableau"
        ],
        "Cybersecurity & Risk Management": [
            "Network Security", "Ethical Hacking", "NIST", "OWASP", "Penetration Testing",
            "Risk Assessment", "Information Security"
        ],
        "Business Systems & Project Management": [
            "Business Analysis", "Requirements Gathering", "BPMN", "Project Management",
            "SDLC", "System Analysis"
        ]
    }

    # Short track code used for each category in assessment results
    DOMAIN_TRACK_CODES = {
        "Software & Application Development": "DEV",
        "Systems, Infrastructure & Networks": "NET",
        "IT Service Management & Operations": "TSM",
        "Data, AI & Analytics": "DATA",
        "Cybersecurity & Risk Management": "SEC",
        "Business Systems & Project Management": "SYS",
    }

    @classmethod
    def categories(cls):
        return list(cls.SKILL_CATEGORY_MAP.keys())

    @classmethod
    def all_skills(cls):
        return list({skill for skills in cls.SKILL_CATEGORY_MAP.values() for skill in skills})

    @classmethod
    def categorize(cls, found_skills):
        """Groups extracted skills into their respective categories."""
        categorized = {}
        for skill in found_skills:
            for category, skills_list in cls.SKILL_CATEGORY_MAP.items():
                if any(s.lower() == skill.lower() for s in skills_list):
                    categorized.setdefault(category, [])
                    if skill not in categorized[category]:
                        categorized[category].append(skill)
        return categorized

    @classmethod
    def map_skills_to_category(cls, required_skills):
        """Maps a list of required posting skills to 1 of the 6 core job taxonomy categories."""
        category_scores = {cat: 0 for cat in cls.SKILL_CATEGORY_MAP}

        for skill in required_skills:
            skill_clean = skill.strip().lower()
            for category, taxonomy_skills in cls.SKILL_CATEGORY_MAP.items():
                for tax_skill in taxonomy_skills:
                    tax_clean = tax_skill.lower()
                    if tax_clean in skill_clean or skill_clean in tax_clean:
                        category_scores[category] += 1

        best_category = max(category_scores, key=category_scores.get)
        if category_scores[best_category] == 0:
            best_category = cls.DEFAULT_CATEGORY
        return best_category

    @classmethod
    def map_to_domain(cls, track_code, target_role=""):
        """Maps a question's track code or target role to 1 of the 6 core job categories.

        Exact matches are resolved first, on purpose. The substring fallback below
        is convenient but ambiguous: "Business Systems & Project Management"
        contains "NA" (in "Management") and would otherwise be filed under
        Systems & Networks. Any question whose course_track already holds one of
        the six category names must round-trip to itself, or the per-domain
        competency breakdown silently reports the wrong domain.
        """
        track = str(track_code or "").strip().upper()
        role = str(target_role or "").strip().lower()

        if not track and not role:
            return cls.DEFAULT_CATEGORY

        # 1. An exact category name (the 6 canonical strings).
        for domain in cls.SKILL_CATEGORY_MAP:
            if track == domain.upper():
                return domain

        # 2. An exact short track code (DEV, NET, TSM, DATA, SEC, SYS).
        for domain, code in cls.DOMAIN_TRACK_CODES.items():
            if track == code.upper():
                return domain

        # 3. Fall back to substring matching on the track, then the role.
        if "SEC" in track or "CYBER" in track or any(k in role for k in ["security", "cyber", "risk", "soc", "penetration"]):
            return "Cybersecurity & Risk Management"
        if "DATA" in track or "AI" in track or "ANALYTICS" in track or any(k in role for k in ["data", "analytics", "ai", "machine learning"]):
            return "Data, AI & Analytics"
        if "TSM" in track or "ITSM" in track or any(k in role for k in ["service", "support", "helpdesk", "itsm", "operations"]):
            return "IT Service Management & Operations"
        if "NET" in track or "NA" in track or "INFRA" in track or any(k in role for k in ["network", "sysadmin", "infrastructure", "cisco"]):
            return "Systems, Infrastructure & Networks"
        if "SYS" in track or "BIZ" in track or "PM" in track or any(k in role for k in ["project", "business analyst", "scrum", "erp"]):
            return "Business Systems & Project Management"
        if "DEV" in track or "WMA" in track or "APP" in track or any(k in role for k in ["developer", "software", "web", "frontend", "backend", "fullstack"]):
            return "Software & Application Development"
        return cls.DEFAULT_CATEGORY

    @staticmethod
    def parse_skill_string(skills_str):
        """'Python, SQL' -> {'python', 'sql'}

        Callers sometimes hand over an already-parsed set/list (the route views
        do), so anything that is not a string is normalised item by item rather
        than being sent through .split(), which a set does not have.
        """
        if not isinstance(skills_str, str):
            return {
                str(s).strip().lower() for s in (skills_str or []) if str(s).strip()
            }
        return {s.strip().lower() for s in skills_str.split(",") if s.strip()}

    @staticmethod
    def match_required_skills(required_skills, student_skills):
        """Returns the required skills the student has (loose substring match)."""
        matched = []
        for req_skill in required_skills:
            req_lower = req_skill.strip().lower()
            if any(req_lower in user_skill or user_skill in req_lower for user_skill in student_skills):
                matched.append(req_skill)
        return matched
