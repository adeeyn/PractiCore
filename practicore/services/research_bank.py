"""The 43 researcher-developed competency items from the PractiCore question bank.

Generated from the source document by regenerating this module; edit the .docx
and re-run the generator rather than hand-editing the list below.

SFIA 9, CompTIA A+, CompTIA Network+, Google IT Support and Cisco Skills for All
are used as competency *references* only. These are PractiCore's own items, not
copied certification questions.

Each tuple is:
    (code, domain, pathway, source, competency, question, (A,B,C,D), key)

`domain` is the research document's sub-domain. `DOMAIN_TRACK` below maps each
sub-domain onto one of PractiCore's 6 job categories, so the taxonomy and the
Random Forest feature columns stay stable.

Answer-key balancing
--------------------
The published instrument keys 37 of its 43 items as "A", so a student could
score ~86% by always choosing the first option. `balanced_rows()` re-orders each
item's options deterministically (seeded by its own question code) so the correct
answer is spread across A-D. This changes only the *position* of the options,
never their wording, so item content and difficulty are untouched. Callers
should use `balanced_rows()`; `as_rows()` keeps the original published order.
"""

import random

# The research document groups items into 11 sub-domains. PractiCore scores them
# under its 6 job categories so the competency profile stays comparable.
DOMAIN_TRACK = {
    "Programming": "DEV",
    "Web Development": "DEV",
    "Database": "DEV",
    "Systems Analysis": "SYS",
    "Networking": "NET",
    "Technical Support": "TSM",
    "Operating Systems": "TSM",
    "Cybersecurity": "SEC",
    "Data & Analytics": "DATA",
    "Workplace Competencies": "SYS",
    "Resume Verification": "SYS",}

# The document's "Pathway" column is guidance, NOT a hard filter: a student's
# demonstrated competency decides their matches, not their degree program.
PATHWAY_ROLES = {
    "Programming": "Software Developer",
    "Web Development": "Web Developer",
    "Database": "Database Developer",
    "Systems Analysis": "Systems Analyst",
    "Networking": "Network Support",
    "Technical Support": "IT Support",
    "Operating Systems": "Systems Administrator",
    "Cybersecurity": "Cybersecurity Analyst",
    "Data & Analytics": "Data Analyst",
    "Workplace Competencies": "Team Member",
    "Resume Verification": "Team Member",}

# Objective items only. The bank is scored with (correct / answered) * 100, and
# self-rating is never accepted as proof of capability.
QUESTIONS = [
    ("Q01", "Programming", "WMA / BSCS", "SFIA PROG; Cisco Python", "Programming",
     "Which construct repeats a task for each item in a list?",
     ("Loop", "Comment", "Import only", "Variable only"), "A"),
    ("Q02", "Programming", "WMA / BSCS", "SFIA PROG", "Debugging",
     "A program runs but gives the wrong result. What should you do first?",
     ("Delete it", "Reproduce the problem and inspect the relevant logic/data", "Reinstall the OS", "Rename variables"), "B"),
    ("Q03", "Programming", "WMA / BSCS", "SFIA PROG", "Testing",
     "Which best demonstrates software verification?",
     ("Test normal and edge-case inputs", "Change colors", "Print source code", "Rename project"), "A"),
    ("Q04", "Programming", "WMA / BSCS", "SFIA PROG", "Security",
     "Which is appropriate for a login system?",
     ("Plain-text passwords", "Secure password hashing and access controls", "Passwords in URLs", "Shared admin account"), "B"),
    ("Q05", "Programming", "WMA / BSCS", "SFIA PROG", "Change control",
     "A new requirement appears during development. What should the team do?",
     ("Change production immediately", "Assess, update requirements/plan, implement and test", "Ignore it", "Delete previous work"), "B"),
    ("Q06", "Web Development", "WMA / BSCS", "SFIA PROG", "Web fundamentals",
     "Which technology structures web-page content?",
     ("HTML", "SQL", "DNS", "DHCP"), "A"),
    ("Q07", "Web Development", "WMA / BSCS", "SFIA PROG", "Web development",
     "Which combination is suitable for a basic responsive interface?",
     ("HTML + CSS + JavaScript", "SQL + DNS + DHCP", "SMTP + FTP", "BIOS + RAM"), "A"),
    ("Q08", "Web Development", "WMA / BSCS", "SFIA PROG", "Integration",
     "A web app needs database records. What normally connects the browser to the database?",
     ("Application/server-side logic", "Monitor driver", "Keyboard firmware", "Wi-Fi antenna"), "A"),
    ("Q09", "Web Development", "WMA / BSCS", "SFIA PROG; TEST", "Validation",
     "A registration form accepts invalid email addresses. What should be added?",
     ("Input validation", "New monitor", "Disable database", "Remove form"), "A"),
    ("Q10", "Database", "BSIS / WMA / BSCS", "SFIA DBDS", "Database design",
     "A student can submit many applications. What design is preferable?",
     ("Store all applications in one field", "Use related tables with keys", "Duplicate student records", "Store applications as images"), "B"),
    ("Q11", "Database", "BSIS / WMA / BSCS", "SFIA DBDS", "Data modelling",
     "What is the main purpose of a primary key?",
     ("Uniquely identify a record", "Encrypt the database", "Increase CPU speed", "Replace foreign keys"), "A"),
    ("Q12", "Database", "BSIS / WMA / BSCS", "SFIA DBAD", "Database administration",
     "Why are database backups important?",
     ("Support recovery after data loss/failure", "Increase typing speed", "Remove need for security", "Prevent every bug"), "A"),
    ("Q13", "Database", "BSIS / WMA / BSCS", "SFIA DBAD", "Database security",
     "Which practice protects database access?",
     ("Appropriate permissions/access controls", "Everyone gets admin rights", "Publish password", "Disable authentication"), "A"),
    ("Q14", "Systems Analysis", "BSIS / All", "SFIA REQM", "Requirements",
     "Before developing a new feature, what should an analyst do?",
     ("Identify and clarify requirements", "Code immediately", "Delete records", "Choose colors only"), "A"),
    ("Q15", "Systems Analysis", "BSIS / All", "SFIA REQM", "Requirements",
     "An employer says, “I need better applicants.” What should the analyst do first?",
     ("Translate it into specific measurable requirements", "Reject the request", "Add random filters", "Ignore it"), "A"),
    ("Q16", "Systems Analysis", "BSIS / All", "SFIA REQM", "Stakeholders",
     "Two stakeholders have conflicting requirements. What is best?",
     ("Choose secretly", "Clarify, document alternatives and obtain agreement", "Ignore both", "Implement both blindly"), "B"),
    ("Q17", "Systems Analysis", "BSIS / All", "SFIA REQM", "Documentation",
     "Which artifact describes how a user interacts with a system function?",
     ("Use case", "RAM", "MAC address", "Power supply"), "A"),
    ("Q18", "Networking", "TSM / NA / BSIT / BSCS", "CompTIA Network+; Cisco", "Networking concepts",
     "Which device forwards traffic between different IP networks?",
     ("Router", "Keyboard", "Monitor", "Printer"), "A"),
    ("Q19", "Networking", "TSM / NA", "CompTIA Network+; Cisco", "IP addressing",
     "What is an IP address primarily used for?",
     ("Identify a host/interface for network communication", "Store passwords", "Increase CPU speed", "Replace a browser"), "A"),
    ("Q20", "Networking", "TSM / NA", "CompTIA Network+; Cisco", "DNS",
     "Which service maps domain names to IP addresses?",
     ("DNS", "DHCP", "SMTP", "FTP"), "A"),
    ("Q21", "Networking", "TSM / NA", "CompTIA Network+; Cisco", "DHCP",
     "A computer has no valid IP on a network using automatic addressing. What should be checked?",
     ("DHCP", "SMTP", "HTTP", "FTP"), "A"),
    ("Q22", "Networking", "TSM / NA", "CompTIA Network+", "Troubleshooting",
     "What is the best general troubleshooting approach?",
     ("Make random changes", "Identify, form a theory, test, verify", "Replace everything", "Ignore symptoms"), "B"),
    ("Q23", "Networking", "TSM / NA", "CompTIA Network+; Cisco", "Security",
     "Which strengthens basic network security?",
     ("Access controls and secure configurations", "Shared admin credentials", "Disable authentication", "Publish passwords"), "A"),
    ("Q24", "Networking", "TSM / NA", "CompTIA Network+", "Monitoring",
     "Why is network monitoring useful?",
     ("Identify performance, availability or security issues", "Eliminate all attacks", "Replace configuration", "Prevent every outage"), "A"),
    ("Q25", "Technical Support", "TSM / NA / All", "Google IT Support; CompTIA A+", "Troubleshooting",
     "A user reports an application stopped working. What is the best first response?",
     ("Gather symptoms/details", "Delete the OS", "Replace motherboard", "Ignore user"), "A"),
    ("Q26", "Technical Support", "TSM / NA / All", "Google IT Support; CompTIA A+", "Customer support",
     "A nontechnical user does not understand instructions. What should support do?",
     ("Explain clearly in user-friendly language", "Add jargon", "End conversation", "Blame user"), "A"),
    ("Q27", "Operating Systems", "TSM / NA", "Google IT Support; CompTIA A+", "OS fundamentals",
     "What is a major purpose of an operating system?",
     ("Manage hardware/resources and provide services to applications", "Replace CPU", "Act only as a web page", "Store passwords in plain text"), "A"),
    ("Q28", "Technical Support", "TSM / NA", "Google IT Support; CompTIA A+", "Documentation",
     "Why document a resolved support issue?",
     ("Create a record for future troubleshooting/service continuity", "Make PC faster", "Replace communication", "Prevent every future issue"), "A"),
    ("Q29", "Cybersecurity", "NA / BSCS / All", "SFIA SCTY; Cisco; CompTIA", "Access control",
     "Which is an example of access control?",
     ("Restrict resources according to permissions", "Increase resolution", "Compress video", "Format USB"), "A"),
    ("Q30", "Cybersecurity", "NA / BSCS / All", "SFIA SCTY; Cisco", "Credential security",
     "Which protects account credentials?",
     ("Secure password storage and access controls", "Share passwords", "Put passwords in public code", "Reuse admin password everywhere"), "A"),
    ("Q31", "Cybersecurity", "NA / BSCS / All", "SFIA SCTY; Cisco", "Phishing awareness",
     "A suspicious message asks for credentials through a link. What is safest?",
     ("Verify through a trusted channel and avoid the link", "Submit credentials", "Forward password", "Disable security"), "A"),
    ("Q32", "Cybersecurity", "NA / BSCS", "SFIA SCTY; Cisco", "Incident response",
     "You notice suspicious activity on a school system. What should you do?",
     ("Follow incident-reporting procedure and preserve evidence", "Delete logs", "Post details publicly", "Change every setting"), "A"),
    ("Q33", "Cybersecurity", "NA / BSCS", "SFIA SCTY", "Least privilege",
     "Which principle limits access to what is needed for assigned tasks?",
     ("Least privilege", "Open access", "Anonymous administration", "Unlimited permissions"), "A"),
    ("Q34", "Data & Analytics", "BSIS / BSCS", "SFIA DAAN; Cisco Data Science", "Data preparation",
     "Why review missing or invalid data before analysis?",
     ("It can affect reliability", "It always improves accuracy", "It removes validation", "It guarantees prediction"), "A"),
    ("Q35", "Data & Analytics", "BSIS / BSCS", "SFIA DAAN", "Visualization",
     "What is the main purpose of data visualization?",
     ("Communicate patterns/trends clearly", "Encrypt data", "Replace collection", "Guarantee causation"), "A"),
    ("Q36", "Data & Analytics", "BSIS / BSCS", "SFIA DAAN", "Interpretation",
     "A graph shows correlation. What should an analyst avoid claiming without evidence?",
     ("That one variable caused the other", "That a relationship exists in the data", "That more investigation is possible", "That context matters"), "A"),
    ("Q37", "Data & Analytics", "BSIS / BSCS", "SFIA DAAN; Cisco", "Data quality",
     "Why validate data before generating recommendations?",
     ("Poor data can produce misleading results", "It guarantees desired results", "It removes need for analysis", "It eliminates all bias"), "A"),
    ("Q38", "Workplace Competencies", "All", "SFIA Communication/Collaboration", "Communication",
     "A team member does not understand a requirement. What should they do?",
     ("Ask for clarification and confirm the expected outcome", "Guess silently", "Ignore task", "Blame another member"), "A"),
    ("Q39", "Workplace Competencies", "All", "SFIA Collaboration", "Collaboration",
     "Two members work on related system components. What supports collaboration?",
     ("Coordinate interfaces and share progress", "Hide changes", "Modify others' work secretly", "Avoid documentation"), "A"),
    ("Q40", "Workplace Competencies", "All", "SFIA Autonomy", "Autonomy",
     "An internship task is unfamiliar and instructions are incomplete. What is appropriate?",
     ("Review guidance, try reasonable steps and ask when needed", "Make risky changes", "Refuse all tasks", "Hide the issue"), "A"),
    ("Q41", "Workplace Competencies", "All", "SFIA Knowledge/Skill/Competency", "Evidence",
     "Which gives stronger evidence of technical capability than simply listing a skill?",
     ("Successfully completing a relevant task/project", "Listing the skill", "Selecting it in a checklist", "Saying “expert”"), "A"),
    ("Q42", "Resume Verification", "All", "SFIA Knowledge/Skill/Competency; PractiCore", "Evidence verification",
     "A resume lists JavaScript. What gives stronger evidence of the skill?",
     ("Correctly completing a JavaScript task", "Repeating the word", "Selecting it only", "Listing a job title"), "A"),
    ("Q43", "Resume Verification", "All", "SFIA Knowledge/Skill/Competency; PractiCore", "Evidence conflict",
     "A resume lists networking, but assessment performance is weak. What should PractiCore do?",
     ("Store both evidence sources instead of assuming the resume proves high competency", "Ignore assessment", "Label advanced automatically", "Delete resume"), "A"),
]


def as_rows():
    """Yields one dict per item, shaped for the assessment_questions table.

    Kept in code rather than a hand-written SQL dump so the bank stays reviewable
    in version control and can be reloaded with `flask --app app seed-questions`.
    """
    for code, domain, pathway, source, competency, text, options, key in QUESTIONS:
        yield {
            "question_code": code,
            "course_track": DOMAIN_TRACK[domain],
            "category": domain,
            "target_role": PATHWAY_ROLES[domain],
            "question_type": "Objective",
            "difficulty": "medium",
            "standard_ref": source,
            "pathway": pathway,
            "competency": competency,
            "question_text": text,
            "option_a": options[0],
            "option_b": options[1],
            "option_c": options[2],
            "option_d": options[3],
            "correct_option": key,
        }


# How evenly the correct answer should be spread across the four letters.
# 43 items cannot divide perfectly by 4, so this is the best achievable spread.
TARGET_KEY_SPREAD = (11, 11, 11, 10)


def _key_targets():
    """Assigns a target letter to each item, respecting TARGET_KEY_SPREAD.

    Items keep their published order, and the least-used letter is handed out
    next, so the result is deterministic and as flat as 43 items allow.
    """
    letters = "ABCD"
    targets = []
    used = [0, 0, 0, 0]
    for _code, _d, _p, _s, _c, _t, _o, _k in QUESTIONS:
        # Pick whichever letter still has the most headroom, breaking ties in
        # A-B-C-D order so the outcome never depends on dict or set ordering.
        index = min(range(4), key=lambda i: (used[i], i))
        used[index] += 1
        targets.append(letters[index])
    return targets


def balanced_rows():
    """Yields the same rows as `as_rows()` with the options re-ordered.

    Only the *position* of the options changes: the four option strings are
    permuted and `correct_option` is updated to match, so the item still tests
    exactly the same competency at the same difficulty. The permutation is
    seeded from the item's own code, so re-seeding the bank is stable and a
    student cannot learn the answer key from item order either.
    """
    targets = _key_targets()
    for row, target in zip(as_rows(), targets):
        current = row["correct_option"]
        if current == target:
            yield row
            continue

        options = [row["option_a"], row["option_b"], row["option_c"], row["option_d"]]
        # Position the correct answer where we want it, then shuffle only the
        # three distractors, so the answer always lands on the target letter.
        distractors = [o for i, o in enumerate(options) if i != "ABCD".index(current)]
        rng = random.Random(f"{row['question_code']}:{current}->{target}")
        rng.shuffle(distractors)

        shuffled = distractors[: "ABCD".index(target)]
        shuffled.append(options["ABCD".index(current)])
        shuffled.extend(distractors["ABCD".index(target):])

        row = dict(row)
        row["option_a"], row["option_b"], row["option_c"], row["option_d"] = shuffled
        row["correct_option"] = target
        yield row


def answer_key_distribution(rows=None):
    """{letter: count} for the given rows (defaults to the balanced bank)."""
    from collections import Counter

    return dict(Counter(row["correct_option"] for row in (rows or balanced_rows())))


def expected_track_counts():
    """{track code: number of items}, used by the seeder and the tests."""
    counts = {}
    for _code, domain, *_rest in QUESTIONS:
        track = DOMAIN_TRACK[domain]
        counts[track] = counts.get(track, 0) + 1
    return counts
