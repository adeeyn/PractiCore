"""The competency taxonomy PractiCore assesses, and the skill mapping onto it.

This layer replaced "pick questions by job category". Everything else keys off a
competency code, because a competency is the one thing all three evidence
sources can be expressed in:

    core competency        -> PROG, PROB, DB, NET, COMM
    resume skill           -> React, SQL, Linux ...
    internship requirement -> the same vocabulary, from the employer

Keeping the resume and the posting on ONE map is deliberate: it means an
internship can require a competency the student never mentioned, and that is
then verified rather than assumed either way.

Track codes are PractiCore's six job categories, carried for reporting only.
Nothing filters on a student's degree or programme.
"""

# code -> (name, track, is_core, description)
COMPETENCIES = {
    "PROG": (
        "Programming Fundamentals", "Software & Application Development", True,
        "Core programming constructs, debugging, testing and change control.",
    ),
    "PROB": (
        "Problem Solving", "Software & Application Development", True,
        "Breaking an unfamiliar problem into steps and verifying a solution.",
    ),
    "DB": (
        "Database Fundamentals", "Data, AI & Analytics", True,
        "Relational design, keys, backup and access control.",
    ),
    "NET": (
        "Networking Fundamentals", "Systems, Infrastructure & Networks", True,
        "Devices, addressing, name resolution and basic network security.",
    ),
    "COMM": (
        "Communication & Teamwork", "Business Systems & Project Management", True,
        "Clarifying requirements, confirming understanding, working with others.",
    ),
    "WEB": (
        "Web Development", "Software & Application Development", False,
        "HTML/CSS/JavaScript, client-server flow and input validation.",
    ),
    "OS": (
        "Operating Systems", "Systems, Infrastructure & Networks", False,
        "Managing hardware and resources, processes, files and permissions.",
    ),
    "TROUBLE": (
        "Troubleshooting", "IT Service Management & Operations", False,
        "Systematic fault isolation: identify, theorise, test, verify.",
    ),
    "SUPP": (
        "Technical Support", "IT Service Management & Operations", False,
        "User-facing support, customer care and service documentation.",
    ),
    "SEC": (
        "Cybersecurity", "Cybersecurity & Risk Management", False,
        "Access control, credential handling, phishing and incident response.",
    ),
    "DATA": (
        "Data & Analytics", "Data, AI & Analytics", False,
        "Data quality, preparation, visualisation and honest interpretation.",
    ),
    "SYS": (
        "Systems Analysis", "Business Systems & Project Management", False,
        "Requirements, stakeholders and use-case documentation.",
    ),
    "DEV": (
        "Software Development", "Software & Application Development", False,
        "Version control, integration and secure development practice.",
    ),
    "EVID": (
        "Evidence & Professional Practice", "Business Systems & Project Management", False,
        "Distinguishing a claim from demonstrated evidence; working autonomously.",
    ),
    # --- added for the 130-item master bank ---
    # The bank specifies four constructs the taxonomy above could only express as a
    # passing note (Git was just a DEV skill, cloud was merely "supporting"). They
    # are added as real competencies so each has its own questions and its own
    # score, rather than being folded into a neighbouring bucket.
    "OOP": (
        "Object-Oriented Programming", "Software & Application Development", False,
        "Classes, encapsulation, inheritance, polymorphism and interface design.",
    ),
    "DSA": (
        "Data Structures & Algorithms", "Software & Application Development", False,
        "Choosing a structure for a workload; time and space complexity; recursion.",
    ),
    "GIT": (
        "Version Control / Git", "Software & Application Development", False,
        "Commits, branching, merging, conflict resolution and collaboration workflow.",
    ),
    "CLOUD": (
        "Cloud & DevOps Fundamentals", "Systems, Infrastructure & Networks", False,
        "Virtualisation, containers, CI/CD, deployment environments and IaC basics.",
    ),
}

# The small always-assessed core. Deliberately five: every IT student is measured
# on these regardless of what they apply for.
CORE_COMPETENCY_CODES = tuple(
    code for code, (_n, _t, is_core, _d) in COMPETENCIES.items() if is_core
)

# skill (lower case) -> {competency: strength}
#
# One skill can evidence more than one competency. JavaScript genuinely is both
# web work and programming, so it is recorded twice rather than forced into one
# bucket.
SKILL_COMPETENCY_MAP = {
    # --- programming / web ---
    "react": {"WEB": "primary", "DEV": "supporting"},
    "javascript": {"WEB": "primary", "PROG": "primary"},
    "html": {"WEB": "primary"},
    "css": {"WEB": "primary"},
    "node.js": {"WEB": "primary", "PROG": "supporting"},
    "flask": {"WEB": "primary", "PROG": "supporting"},
    "django": {"WEB": "primary", "PROG": "supporting"},
    "php": {"WEB": "primary", "PROG": "supporting"},
    "ui/ux": {"WEB": "supporting"},
    "rest api": {"WEB": "supporting", "DEV": "supporting"},
    "responsive design": {"WEB": "supporting"},
    # --- programming / software ---
    "python": {"PROG": "primary"},
    "java": {"PROG": "primary"},
    "c++": {"PROG": "primary"},
    "vb.net": {"PROG": "primary"},
    "git": {"DEV": "primary", "GIT": "primary"},
    "version control": {"DEV": "primary", "GIT": "primary"},
    "debugging": {"PROG": "supporting"},
    "unit testing": {"PROG": "supporting", "DEV": "supporting"},
    "testing": {"PROG": "supporting", "DEV": "supporting"},
    "agile": {"DEV": "supporting", "COMM": "supporting"},
    "scrum": {"DEV": "supporting", "COMM": "supporting"},
    "jira": {"DEV": "supporting", "COMM": "supporting"},
    "problem-solving": {"PROB": "primary"},
    "problem solving": {"PROB": "primary"},
    "algorithm": {"PROB": "primary", "PROG": "supporting"},
    "data structures": {"PROB": "primary", "PROG": "supporting"},
    # --- database / data ---
    "sql": {"DB": "primary"},
    "mysql": {"DB": "primary"},
    "postgresql": {"DB": "primary"},
    "mongodb": {"DB": "primary"},
    "database": {"DB": "primary"},
    "data analysis": {"DATA": "primary"},
    "machine learning": {"DATA": "primary"},
    "pandas": {"DATA": "primary"},
    "power bi": {"DATA": "primary"},
    "tableau": {"DATA": "primary"},
    "nlp": {"DATA": "primary", "PROG": "supporting"},
    # --- networking ---
    "networking": {"NET": "primary"},
    "tcp/ip": {"NET": "primary"},
    "cisco": {"NET": "primary"},
    "vlan": {"NET": "primary"},
    "dns": {"NET": "primary"},
    "dhcp": {"NET": "primary"},
    "firewall": {"NET": "primary", "SEC": "supporting"},
    # --- os / support ---
    "linux": {"OS": "primary", "SUPP": "supporting"},
    "windows server": {"OS": "primary", "SUPP": "supporting"},
    "windows": {"OS": "primary", "SUPP": "supporting"},
    "unix": {"OS": "primary"},
    "troubleshooting": {"TROUBLE": "primary"},
    "technical support": {"SUPP": "primary"},
    "itil": {"SUPP": "primary"},
    "service desk": {"SUPP": "primary"},
    "incident management": {"SUPP": "primary", "TROUBLE": "supporting"},
    "help desk": {"SUPP": "primary"},
    "hardware": {"OS": "supporting", "SUPP": "supporting"},
    # --- security ---
    "cybersecurity": {"SEC": "primary"},
    "network security": {"SEC": "primary", "NET": "supporting"},
    "ethical hacking": {"SEC": "primary"},
    "nist": {"SEC": "primary"},
    "owasp": {"SEC": "primary", "DEV": "supporting"},
    "penetration testing": {"SEC": "primary"},
    "risk assessment": {"SEC": "primary", "SYS": "supporting"},
    "information security": {"SEC": "primary"},
    # --- systems / business ---
    "business analysis": {"SYS": "primary"},
    "requirements gathering": {"SYS": "primary", "COMM": "supporting"},
    "bpmn": {"SYS": "primary"},
    "project management": {"SYS": "primary", "COMM": "supporting"},
    "sdlc": {"SYS": "primary", "DEV": "supporting"},
    "system analysis": {"SYS": "primary"},
    # --- cloud / professional ---
    "cloud": {"OS": "supporting", "DEV": "supporting", "CLOUD": "primary"},
    "aws": {"OS": "supporting", "DEV": "supporting", "CLOUD": "primary"},
    "docker": {"OS": "supporting", "DEV": "supporting", "CLOUD": "primary"},
    # --- object-oriented programming ---
    "oop": {"OOP": "primary"},
    "object-oriented programming": {"OOP": "primary"},
    "solid principles": {"OOP": "primary"},
    "design patterns": {"OOP": "primary", "DEV": "supporting"},
    # --- data structures & algorithms ---
    "algorithms": {"DSA": "primary", "PROG": "supporting"},
    "algorithm analysis": {"DSA": "primary"},
    "big-o": {"DSA": "primary"},
    "recursion": {"DSA": "primary", "PROG": "supporting"},
    "linked list": {"DSA": "primary"},
    "binary tree": {"DSA": "primary"},
    # --- version control / git ---
    "github": {"GIT": "primary"},
    "gitlab": {"GIT": "primary"},
    "branching": {"GIT": "primary"},
    "merge conflict": {"GIT": "primary"},
    "git workflow": {"GIT": "primary"},
    # --- cloud & devops ---
    "devops": {"CLOUD": "primary"},
    "kubernetes": {"CLOUD": "primary", "OS": "supporting"},
    "ci/cd": {"CLOUD": "primary", "DEV": "supporting"},
    "continuous integration": {"CLOUD": "primary", "DEV": "supporting"},
    "infrastructure as code": {"CLOUD": "primary"},
    "terraform": {"CLOUD": "primary"},
    "virtualization": {"CLOUD": "primary", "OS": "supporting"},
    "nginx": {"CLOUD": "supporting", "WEB": "supporting"},
    "communication": {"COMM": "primary"},
    "collaboration": {"COMM": "primary"},
    "teamwork": {"COMM": "primary"},
    # Role words that appear in posting text rather than a skills list.
    "full-stack developer": {"WEB": "primary", "PROG": "primary"},
    "web developer": {"WEB": "primary", "PROG": "primary"},
    "front-end": {"WEB": "primary"},
    "frontend": {"WEB": "primary"},
    "back-end": {"PROG": "primary", "WEB": "supporting"},
    "backend": {"PROG": "primary", "WEB": "supporting"},
    "network administrator": {"NET": "primary", "OS": "primary"},
    "system administrator": {"OS": "primary", "SUPP": "supporting"},
    "systems administrator": {"OS": "primary", "SUPP": "supporting"},
    "it support": {"SUPP": "primary", "TROUBLE": "primary"},
    "helpdesk": {"SUPP": "primary", "TROUBLE": "primary"},
    "data analyst": {"DATA": "primary", "DB": "supporting"},
    "database administrator": {"DB": "primary", "OS": "supporting"},
    "business analyst": {"SYS": "primary", "COMM": "supporting"},
    "qa engineer": {"DEV": "primary", "PROG": "supporting"},
}


def competencies_for_skill(skill):
    """{competency: strength} for one skill name; {} when it maps to nothing."""
    return SKILL_COMPETENCY_MAP.get(str(skill or "").strip().lower(), {})


def competencies_for_skills(skills):
    """{competency: 'primary'|'supporting'} merged over many skills.

    A competency stays 'primary' if ANY skill maps to it primarily, so one
    strong match is not diluted by several weak ones.
    """
    merged = {}
    for skill in skills or []:
        for code, strength in competencies_for_skill(skill).items():
            if merged.get(code) != "primary":
                merged[code] = strength
    return merged


def _phrases(text):
    """Lower-cased single tokens and two-word phrases, for phrase lookup."""
    import re

    words = re.findall(r"[a-z0-9+./-]+", str(text or "").lower())
    return set(words) | {" ".join(words[i:i + 2]) for i in range(len(words) - 1)}


def evidence_from_skills(skills, has_project=False, has_experience=False):
    """Resume claims grouped by competency, ready for storage.

    Produces {competency_code: {'skills': [...], 'has_project': bool,
    'has_experience': bool}}. Written to resume_competency_evidence, which is a
    different table from the score table on purpose: a claim must never be
    storable in the same place as a demonstrated result.
    """
    grouped = {}
    for skill in skills or []:
        for code in competencies_for_skill(skill):
            entry = grouped.setdefault(code, {
                "skills": [], "has_project": has_project,
                "has_experience": has_experience,
            })
            entry["skills"].append(skill)
    return grouped


def required_competencies(posting_skills, extra_text=""):
    """Competencies an internship asks for, from its skills plus its description.

    The description is searched too, because postings often state the need in
    prose ("troubleshoot and communicate with users") without listing it as a
    skills row.
    """
    merged = competencies_for_skills(posting_skills)
    for code, strength in competencies_for_skills(_phrases(extra_text)).items():
        merged.setdefault(code, strength)
    return merged
