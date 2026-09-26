"""TEMPORARY placeholder data for the employer pages (taken from the UI mockups).

There is no applications table yet, so applicants, stats and rankings come from here.
When the backend is built, replace these with repository/service calls in the route
files; the templates will not need to change as long as the same keys are provided.
"""

POSITION = "IT Support Intern"

APPLICANTS = [
    {"id": 1, "name": "Juan Dela Cruz", "initials": "JD", "position": POSITION,
     "applied_on": "May 13, 2025", "match_score": 92, "status": "Shortlisted", "notes": ""},
    {"id": 2, "name": "Maria Santos", "initials": "MS", "position": POSITION,
     "applied_on": "May 14, 2025", "match_score": 90, "status": "In Review", "notes": ""},
    {"id": 3, "name": "Kevin Reyes", "initials": "KR", "position": POSITION,
     "applied_on": "May 15, 2025", "match_score": 87, "status": "In Review", "notes": ""},
    {"id": 4, "name": "Ashley Garcia", "initials": "AG", "position": POSITION,
     "applied_on": "May 13, 2025", "match_score": 82, "status": "Scheduled", "notes": ""},
    {"id": 5, "name": "Paul Lim", "initials": "PL", "position": POSITION,
     "applied_on": "May 16, 2025", "match_score": 79, "status": "In Review", "notes": ""},
]

TOTAL_APPLICANTS = 32

STATS = [
    {"icon": "users", "color": "purple", "value": "32", "label": "Total Applicants", "note": "+4 this week"},
    {"icon": "briefcase", "color": "blue", "value": "3", "label": "Active Postings", "note": "1 closing soon"},
    {"icon": "user-check", "color": "green", "value": "8", "label": "Shortlisted", "note": "+2 this week"},
    {"icon": "trending-up", "color": "amber", "value": "86%", "label": "Avg Match Score", "note": "Above average"},
]

SUGGESTED_SKILLS = ["Troubleshooting", "Networking", "Windows"]
