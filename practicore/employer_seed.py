"""Dummy partner-company accounts for the employer module.

Each entry becomes a real `users` + `employers` login (plus internship postings
and applications) so the employer pages read from the database instead of the
placeholder lists that used to live in routes/employer/sample_data.py.

The skills per company/posting are taken from SkillTaxonomy so postings still map
onto the six job categories the recommender expects.

Run it with:  flask --app app seed-employers
"""

from flask import current_app

from .repositories import (
    ApplicationRepository,
    AssessmentRepository,
    EmployerRepository,
    PostingRepository,
    StudentRepository,
    UserRepository,
)
from .services import AuthService, RecommendationService, SkillTaxonomy

DEFAULT_PASSWORD = "PractiCore123"

# The application pipeline statuses, in the order an employer moves a candidate through them.
STATUS_FLOW = ["Pending", "In Review", "Reviewed", "Shortlisted", "Scheduled", "Hired", "Rejected"]

DUMMY_EMPLOYERS = [
    {
        "company_name": "Tech Solution Inc.",
        "email": "hr@techsolution.com.ph",
        "location": "Cebu City, Philippines",
        "industry": "Information Technology",
        "company_size": "51-200",
        "website": "https://techsolution.com.ph",
        "is_hiring": True,
        "contact_name": "Natalie Cruz",
        "contact_position": "HR Manager",
        "about": (
            "Tech Solution Inc. is a Cebu-based IT services company that builds and "
            "supports software for retail and logistics clients. We run a year-round "
            "internship program and mentor each intern through a real support queue."
        ),
        "required_skills": ["Technical Support", "Networking", "Windows", "Troubleshooting", "Incident Management"],
        "postings": [
            {
                "title": "IT Support Intern",
                "department": "IT Operations",
                "description": "Assist in network troubleshooting, workstation configuration, hardware diagnostics, and maintaining internal IT infrastructure.",
                "is_remote": False,
                "positions_available": 3,
                "skills": ["Technical Support", "Networking", "Windows", "Troubleshooting", "Incident Management"],
            },
            {
                "title": "Service Desk Intern",
                "department": "IT Operations",
                "description": "Handle first-line user tickets, log incidents in the service desk tool, and follow up on open requests until closure.",
                "is_remote": True,
                "positions_available": 2,
                "skills": ["Service Desk", "Incident Management", "Technical Support", "Agile"],
            },
        ],
    },
    {
        "company_name": "DevPro Lab",
        "email": "careers@devprolab.ph",
        "location": "Remote, Philippines",
        "industry": "Software & Application Development",
        "company_size": "11-50",
        "website": "https://devprolab.ph",
        "is_hiring": True,
        "contact_name": "Marco Villanueva",
        "contact_position": "Talent Acquisition Lead",
        "about": (
            "DevPro Lab is a product studio that ships web platforms for startups. "
            "Our interns join real squads, review real pull requests, and own a feature "
            "from design to release."
        ),
        "required_skills": ["JavaScript", "HTML", "CSS", "React", "Flask", "Python", "Git"],
        "postings": [
            {
                "title": "Web Development Intern",
                "department": "Engineering",
                "description": "Collaborate with our front-end team to build responsive web portals, write clean modular CSS, and integrate REST APIs using Python/Flask.",
                "is_remote": True,
                "positions_available": 4,
                "skills": ["JavaScript", "HTML", "CSS", "React", "Flask", "Python", "Git"],
            },
            {
                "title": "Front-End Developer Intern",
                "department": "Engineering",
                "description": "Turn Figma designs into accessible React components, keep bundle size down, and document the component library as you go.",
                "is_remote": True,
                "positions_available": 2,
                "skills": ["React", "JavaScript", "HTML", "CSS", "UI/UX", "Git"],
            },
        ],
    },
    {
        "company_name": "InnovaTech Solutions Inc.",
        "email": "people@innovatech.com.ph",
        "location": "Makati City, Philippines",
        "industry": "Business Systems & Project Management",
        "company_size": "51-200",
        "website": "https://innovatech.com.ph",
        "is_hiring": True,
        "contact_name": "Grace Mendoza",
        "contact_position": "HR Business Partner",
        "about": (
            "InnovaTech Solutions Inc. delivers enterprise systems integration and "
            "process automation for BPO clients. Our interns help document workflows "
            "that thousands of agents depend on every day."
        ),
        "required_skills": ["Business Analysis", "Requirements Gathering", "BPMN", "SQL", "System Analysis", "Project Management"],
        "postings": [
            {
                "title": "Systems Analyst Intern",
                "department": "Business Solutions",
                "description": "Evaluate software requirements, prepare system workflow documentation, perform usability test cases, and model database architecture.",
                "is_remote": False,
                "positions_available": 2,
                "skills": ["Business Analysis", "Requirements Gathering", "BPMN", "SQL", "System Analysis"],
            },
            {
                "title": "Project Management Intern",
                "department": "Delivery Office",
                "description": "Support the delivery team with sprint backlogs, status reporting, and tracking of milestones across client projects.",
                "is_remote": False,
                "positions_available": 1,
                "skills": ["Project Management", "Agile", "Scrum", "Jira", "SDLC"],
            },
        ],
    },
    {
        "company_name": "Nexus Cyber Solutions",
        "email": "talent@nexuscyber.ph",
        "location": "Tarlac City, Philippines",
        "industry": "Cybersecurity & Risk Management",
        "company_size": "11-50",
        "website": "https://nexuscyber.ph",
        "is_hiring": True,
        "contact_name": "Rafael Ortiz",
        "contact_position": "IT Operations Manager",
        "about": (
            "Nexus Cyber Solutions operates a 24/7 security operations centre for "
            "regional businesses. Interns sit with the SOC team on real alert triage "
            "under the guidance of certified analysts."
        ),
        "required_skills": ["Cybersecurity", "Network Security", "Ethical Hacking", "OWASP", "NIST", "Linux"],
        "postings": [
            {
                "title": "Cybersecurity & SOC Trainee",
                "department": "Security Operations",
                "description": "Assist our SOC team in monitoring network alerts, auditing logs, and configuring firewall rules.",
                "is_remote": False,
                "positions_available": 2,
                "skills": ["Cybersecurity", "Network Security", "Linux", "TCP/IP"],
            },
            {
                "title": "Information Security Analyst Intern",
                "department": "Security Operations",
                "description": "Help evaluate vulnerability reports, conduct OWASP assessments, and implement security policies.",
                "is_remote": True,
                "positions_available": 2,
                "skills": ["Ethical Hacking", "OWASP", "NIST", "Risk Assessment", "Information Security", "Penetration Testing"],
            },
        ],
    },
    {
        "company_name": "DataPulse Analytics",
        "email": "careers@datapulse.ph",
        "location": "Clark, Pampanga, Philippines",
        "industry": "Data, AI & Analytics",
        "company_size": "51-200",
        "website": "https://datapulse.ph",
        "is_hiring": True,
        "contact_name": "Katrina Ramos",
        "contact_position": "People & Culture Officer",
        "about": (
            "DataPulse Analytics helps retail and logistics companies turn messy "
            "operational data into decisions. Interns contribute to production "
            "dashboards and NLP pipelines, not toy datasets."
        ),
        "required_skills": ["SQL", "Python", "Pandas", "Power BI", "Data Analysis", "Machine Learning"],
        "postings": [
            {
                "title": "Junior Data Analyst Intern",
                "department": "Analytics",
                "description": "Clean large datasets using Python and Pandas, run SQL queries, and build Power BI visualization dashboards.",
                "is_remote": True,
                "positions_available": 3,
                "skills": ["SQL", "Python", "Pandas", "Power BI", "Data Analysis"],
            },
            {
                "title": "AI & Machine Learning Developer Trainee",
                "department": "Data Science",
                "description": "Assist in training ML models, processing text data using NLP pipelines, and analyzing operational metrics.",
                "is_remote": False,
                "positions_available": 2,
                "skills": ["Machine Learning", "Python", "NLP", "Pandas", "Data Analysis"],
            },
        ],
    },
    {
        "company_name": "CloudScale Networks",
        "email": "interns@cloudscale.ph",
        "location": "Makati City, Philippines",
        "industry": "Systems, Infrastructure & Networks",
        "company_size": "201-500",
        "website": "https://cloudscale.ph",
        "is_hiring": True,
        "contact_name": "Dennis Ocampo",
        "contact_position": "Infrastructure Lead",
        "about": (
            "CloudScale Networks designs and operates campus and cloud networks for "
            "multi-site businesses. Our interns are trained on live equipment and "
            "certified towards CCNA."
        ),
        "required_skills": ["Networking", "Cisco", "TCP/IP", "VLAN", "Linux", "Cloud", "AWS"],
        "postings": [
            {
                "title": "Network & Systems Administrator Intern",
                "department": "Infrastructure",
                "description": "Manage local subnet routing, configure Cisco switches, VLANs, and maintain Linux server uptime.",
                "is_remote": False,
                "positions_available": 2,
                "skills": ["Networking", "Cisco", "TCP/IP", "VLAN", "Linux"],
            },
            {
                "title": "Cloud Operations Intern",
                "department": "Infrastructure",
                "description": "Help containerise internal services with Docker and keep staging environments reproducible on AWS.",
                "is_remote": True,
                "positions_available": 1,
                "skills": ["Cloud", "AWS", "Docker", "Linux", "Networking"],
            },
        ],
    },
    {
        "company_name": "AgileDev Studios",
        "email": "hello@agiledev.ph",
        "location": "Quezon City, Philippines",
        "industry": "Software & Application Development",
        "company_size": "11-50",
        "website": "https://agiledev.ph",
        "is_hiring": True,
        "contact_name": "Bea Fernandez",
        "contact_position": "Engineering Manager",
        "about": (
            "AgileDev Studios builds internal tools for cooperatives and small retail "
            "chains. We practise Scrum end to end, so interns join standups, demos, "
            "and retrospectives from their first week."
        ),
        "required_skills": ["Python", "Java", "JavaScript", "React", "Flask", "SQL", "Git", "Agile", "Scrum"],
        "postings": [
            {
                "title": "Full Stack Web Developer Intern",
                "department": "Engineering",
                "description": "Build dynamic web modules using JavaScript, React, Python Flask, and MySQL database backends.",
                "is_remote": True,
                "positions_available": 3,
                "skills": ["JavaScript", "React", "Python", "Flask", "SQL", "Git"],
            },
            {
                "title": "Java Developer Intern",
                "department": "Engineering",
                "description": "Maintain our Java services, write unit tests, and fix defects reported from client support tickets.",
                "is_remote": False,
                "positions_available": 1,
                "skills": ["Java", "SQL", "Git", "Agile"],
            },
        ],
    },
    {
        "company_name": "CoreIT Service Management",
        "email": "hrm@coreit.ph",
        "location": "Taguig City, Philippines",
        "industry": "IT Service Management & Operations",
        "company_size": "51-200",
        "website": "https://coreit.ph",
        "is_hiring": True,
        "contact_name": "Aaron Javier",
        "contact_position": "Workforce Development Lead",
        "about": (
            "CoreIT Service Management runs ITIL-aligned IT support desks for "
            "enterprise clients. Interns work inside a managed service team and are "
            "certified towards ITIL Foundation."
        ),
        "required_skills": ["ITIL", "Service Desk", "Incident Management", "Jira", "Technical Support", "Agile"],
        "postings": [
            {
                "title": "IT Service Desk & Technical Support Trainee",
                "department": "Service Delivery",
                "description": "Handle ITIL-aligned service management tickets, troubleshoot hardware/software, and support Jira workflows.",
                "is_remote": False,
                "positions_available": 5,
                "skills": ["ITIL", "Service Desk", "Incident Management", "Jira", "Technical Support"],
            },
        ],
    },
]


def _join_skills(skills):
    """Stores the skill list the same way students.skills is stored."""
    return ", ".join(skills)


def _components_for(student, posting_skills, matcher, assessments=None):
    """Scores through the shared MatchingService, exactly like the live pages.

    This used to re-implement the weighted formula by hand, which silently
    drifted away from the app the moment the real model was switched on.

    Returns the combined score together with the two separated percentages
    (resume overlap and the assessment score for this posting's category), so
    seeded applications carry the same split the live pages display.
    """
    total_questions = student["total_questions"] or 0
    assessment_pct = round((student["assessment_score"] / total_questions) * 100) if total_questions else 0
    domain_scores = assessments.for_student(student["id"]) if assessments else {}

    return matcher.score_components(
        {"skills": SkillTaxonomy.parse_skill_string(student["skills"]), "domain_scores": domain_scores},
        posting_skills,
        assessment_percentage=assessment_pct,
    )


def _status_for(index):
    """Spreads the seeded applicants across the pipeline, never landing on Rejected."""
    return STATUS_FLOW[min(index, len(STATUS_FLOW) - 2)]


def _upsert_company(employers, company, password_hash, is_hiring, reset_passwords=False):
    """Returns (employer_row, login_email) for one dummy company.

    A company that already has a login keeps its existing email, so re-running
    the seeder never orphans an account somebody is already using. Pass
    reset_passwords to also give that existing account the seeded password.
    """
    skills = _join_skills(company["required_skills"])
    employer = employers.find_by_company_name(company["company_name"])

    if employer and employer["user_id"]:
        login_email = UserRepository().email_for(employer["user_id"]) or company["email"]
        if reset_passwords:
            UserRepository().set_password(employer["user_id"], password_hash)
    elif employer:
        user_id = UserRepository().create(company["email"], None, password_hash, AuthService.EMPLOYER)
        employers.attach_to_user(employer["id"], user_id)
        login_email = company["email"]
    else:
        employers.create_with_account(
            company["email"], password_hash, company["company_name"], company["location"],
            company["industry"], company["about"], skills,
            company["contact_name"], company["contact_position"], company["website"],
            company["company_size"], is_hiring,
        )
        employer = employers.find_by_company_name(company["company_name"])
        login_email = company["email"]

    employers.update_profile(
        employer["id"], employer["user_id"], company["company_name"], login_email,
        company["industry"], company["location"], company["about"],
        skills, company["contact_name"], company["contact_position"], company["website"],
        company["company_size"], is_hiring,
    )
    return employer, login_email


def _upsert_posting(postings_repo, employer_id, posting):
    """Returns the posting id, creating or refreshing the posting as needed."""
    is_remote = 1 if posting["is_remote"] else 0
    existing = postings_repo.find_by_employer_and_title(employer_id, posting["title"])

    if existing:
        postings_repo.update_details(
            existing["id"], posting["department"], posting["description"],
            is_remote, posting["positions_available"],
        )
        postings_repo.replace_skills(existing["id"], posting["skills"])
        return existing["id"]

    return postings_repo.create_with_skills(
        employer_id, posting["title"], posting["department"], posting["description"],
        is_remote, posting["positions_available"], posting["skills"],
    )


def seed_employers(password=DEFAULT_PASSWORD, reset_passwords=False):
    """Creates (or refreshes) the dummy partner companies, postings and applications.

    Safe to run more than once: companies are matched by name, postings by title
    and applications by the unique (student, posting) key, so re-running updates
    in place instead of duplicating.

    reset_passwords also gives pre-existing employer logins the seeded password,
    which is what you want before a demo but not for a real account.

    Returns a list of (email, password) tuples for the logins that now work.
    """
    employers = EmployerRepository()
    postings_repo = PostingRepository()
    applications = ApplicationRepository()
    assessments = AssessmentRepository()
    students = StudentRepository().all_for_seeding()

    # Seeded applications must carry the same score the live pages would compute,
    # so the demo data and the running app never disagree.
    matcher = current_app.extensions.get("matching_service")
    if matcher is None:
        from .services import MatchingService

        matcher = MatchingService.load(current_app.config["RANKING_MODEL_PATH"])

    password_hash = AuthService.hash_password(password)
    accounts = []

    for company in DUMMY_EMPLOYERS:
        employer, login_email = _upsert_company(
            employers, company, password_hash, 1 if company["is_hiring"] else 0, reset_passwords
        )
        accounts.append((login_email, password))

        for posting in company["postings"]:
            posting_id = _upsert_posting(postings_repo, employer["id"], posting)

            for index, student in enumerate(students):
                components = _components_for(student, posting["skills"], matcher, assessments)
                match_score = components["match_score"]
                if match_score <= 0:
                    continue  # No skills and no assessment means nothing to screen on

                applications.create_if_missing(
                    student["id"], posting_id, _status_for(index), match_score,
                    f"Seeded demo application for {posting['title']}.",
                    resume_match_score=components["resume_match_percent"],
                    assessment_match_score=components["assessment_match_percent"],
                )

    return accounts

