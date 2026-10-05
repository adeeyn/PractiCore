"""Builds the parallel question forms from the published research bank.

Design decision: the validated 43-item research bank becomes SET A. Sets B and C
are parallel forms written against the same competency and difficulty, so a
retake measures the same thing without repeating the same items.

A competency only gets a form once it has enough items, and every set for a
competency is kept the same size. Where only one form exists the shortfall is
reported by the selection service rather than hidden.
"""
from .competency_taxonomy import COMPETENCIES

# Which competency each published sub-domain belongs to. The research bank's 11
# sub-domains collapse onto the competency taxonomy, so a score is reported per
# competency rather than per sub-domain.
CATEGORY_TO_COMPETENCY = {
    "Programming": "PROG",
    "Web Development": "WEB",
    "Database": "DB",
    "Systems Analysis": "SYS",
    "Networking": "NET",
    "Technical Support": "SUPP",
    "Operating Systems": "OS",
    "Cybersecurity": "SEC",
    "Data & Analytics": "DATA",
    # "Workplace Competencies" and "Resume Verification" are about professional
    # practice and evidence, not about a technical competency, so they map to the
    # dedicated EVID competency rather than being spread across the others.
    "Workplace Competencies": "EVID",
    "Resume Verification": "EVID",
}

# Items per form. Three forms of two items is enough to measure a competency
# without turning the assessment into an exam marathon.
ITEMS_PER_SET = 2

# Competencies that also measure problem solving / debugging, because the
# published bank has no dedicated items for them. Kept explicit rather than
# inferred, so the set sizes stay predictable.
#
# Q22 is a published Networking item on systematic fault isolation, so it
# legitimately measures Troubleshooting as well as Networking.
EXTRA_COMPETENCY_ITEMS = {
    "PROB": ["Q02", "Q22"],   # debugging approach; systematic troubleshooting
    "DEV": ["Q05", "Q09"],     # change control; input validation as testing
    "COMM": ["Q15", "Q16"],    # requirement clarification; stakeholder conflict
    "TROUBLE": ["Q22", "Q28"],  # fault isolation; the support escalation path
    # The published bank has only one Operating Systems item (Q27, on the
    # boot/startup sequence), which would leave Form A a single question and make
    # the form's score all-or-nothing. Q24 is a permissions item that is
    # legitimately an OS competency as well as a networking one.
    "OS": ["Q27", "Q24"],
}


def assign_competency(item):
    """The competency code for one published bank item."""
    return CATEGORY_TO_COMPETENCY.get(item.get("category") or "", "PROG")


# Parallel forms B and C, written against the same competency and the same
# difficulty as the published set A. Wording and scenario differ; the construct
# being measured does not. `standard_ref` keeps the framework provenance the
# validation procedure requires.
#
# format: competency -> set_code -> [(question, (A,B,C,D), key, standard_ref)]
PARALLEL_FORMS = {
    "TROUBLE": {
        "A": [],
        "B": [
            ("A user reports their machine is slow. Several fixes are possible. What should a technician do first?",
             ("Reproduce the problem and gather facts about when it started",
              "Reinstall the operating system", "Replace the hard drive",
              "Increase the screen timeout"), "A", "SFIA TSIS; Incident mgmt"),
            ("Two fixes appear to work, but the fault returns. What does that most likely indicate?",
             ("The cause was never identified, only the symptom was removed",
              "The user is describing it incorrectly", "The hardware is faulty",
              "The machine needs more memory"), "A", "SFIA TSIS"),
        ],
        "C": [
            ("A service fails only for users on one floor. What should be tested first?",
             ("What is different about that floor's network path",
              "Whether the monitor is switched on", "Whether the user has a keyboard",
              "Whether the room is booked"), "A", "SFIA TSIS"),
            ("A fix works for one user and not another with the same setup. What is the reasonable next step?",
             ("Compare the two configurations to find the difference",
              "Tell the second user to copy the first user's password",
              "Replace both machines", "Close the ticket as user error"), "A", "SFIA TSIS"),
        ],
    },
    "PROG": {
        "B": [
            ("A function returns the wrong total only when the list is empty. What is the most useful first step?",
             ("Check the empty-list case explicitly", "Rewrite the whole module",
              "Add print statements everywhere", "Change the variable names"), "A", "SFIA PROG"),
            ("A program compiles but produces incorrect output. Which activity best narrows the cause?",
             ("Isolate the failing part and test it with known inputs",
              "Install a different compiler", "Delete the project and restart",
              "Add more user interface"), "A", "SFIA PROG"),
        ],
        "C": [
            ("Before shipping a change to a shared function, which practice reduces the most risk?",
             ("Run the existing tests and add a case for the new behaviour",
              "Deploy first and fix afterwards", "Only test on the developer's machine",
              "Skip testing when the change is small"), "A", "SFIA PROG; TEST"),
            ("A loop runs one time too many. This suggests which class of defect?",
             ("An off-by-one boundary condition", "A missing import",
              "An incorrect file permission", "A wrong network address"), "A", "SFIA PROG"),
        ],
    },
    "PROB": {
        "A": [],
        "B": [
            ("A ticket describes a vague request with no error message. What should you do first?",
             ("Ask for a reproduction case and the expected result",
              "Guess the cause and patch it", "Escalate immediately",
              "Close the ticket as unclear"), "A", "SFIA REQM; Communication"),
            ("You have two possible fixes for a fault and cannot test either tonight. What is reasonable?",
             ("Pick the lower-risk one, state the assumption, note what to verify",
              "Apply both and hope one works", "Wait for someone else to decide",
              "Change unrelated code to see what happens"), "A", "SFIA Autonomy"),
        ],
        "C": [
            ("A script fails only for names containing an underscore. What does that suggest?",
             ("An incomplete check on the input format", "An incorrect network route",
              "A missing user account", "An expired licence"), "A", "SFIA PROG"),
            ("Three symptoms all disappear when one setting is reverted. What does that support?",
             ("A shared cause worth investigating further",
              "Three unrelated coincidences", "A hardware fault", "A user error"), "A", "SFIA Troubleshooting"),
        ],
    },
    "DEV": {
        "A": [],
        "B": [
            ("Two developers edit the same file on separate branches. What keeps the conflict out of production?",
             ("Reviewing the merged changes and running tests before release",
              "Deploying both versions to production", "Renaming the file",
              "Copying the file instead of merging"), "A", "SFIA PROG"),
            ("A shared configuration value is edited on a branch. What is safer?",
             ("Keep it in one versioned location so changes are reviewed together",
              "Email the value to each developer", "Paste it into each project",
              "Keep it only on the server"), "A", "SFIA Change control"),
        ],
        "C": [
            ("A release contains a setting that was never reviewed. Which control would have caught it?",
             ("Requiring peer review before the change is merged",
              "Larger commit messages", "More frequent backups", "Faster internet"), "A", "SFIA Change control"),
            ("A junior joins the team. Which practice most helps them contribute safely?",
             ("A small change with review, rather than a large unreviewed one",
              "Being given the hardest task first", "Working without review for speed",
              "Being given no tasks"), "A", "SFIA Autonomy"),
        ],
    },
    "COMM": {
        "A": [],
        "B": [
            ("A teammate sends a task with an unclear expected output. What is the best response?",
             ("Confirm the expected result in writing before starting",
              "Start immediately to save time", "Complete a different task",
              "Wait until the deadline"), "A", "SFIA Communication"),
            ("A non-technical stakeholder asks why a fix takes three days. What should you do?",
             ("Explain the reason without jargon and confirm they understand",
              "Reply with the technical log only", "Repeat the request louder",
              "Send a screenshot"), "A", "SFIA Communication"),
        ],
        "C": [
            ("Two team members disagree on who owns a deliverable. What resolves it?",
             ("Agreeing the owner explicitly and recording it",
              "Whoever shouts loudest", "Splitting the work silently",
              "Leaving it unassigned"), "A", "SFIA Collaboration"),
            ("A handover note says 'handle the usual issues'. Why is that weak?",
             ("It does not say what to do or how to tell when it is done",
              "It is too short to read", "It uses no acronyms",
              "It names a colleague"), "A", "SFIA Documentation"),
        ],
    },
    "DB": {
        "B": [
            ("An orders table has a student_id but no table of students. What problem does that create?",
             ("Student details repeat and cannot be referenced consistently",
              "Reports become slower", "Backups take less space",
              "Nothing, it is acceptable"), "A", "SFIA DBDS"),
            ("A database is backed up nightly but the restore was never tested. What is the risk?",
             ("The backup may be unusable when it is actually needed",
              "The backup is too small", "The restore is too slow to matter",
              "The database will be deleted"), "A", "SFIA DBAD"),
        ],
        "C": [
            ("Every intern account can delete student records. Which change is appropriate?",
             ("Give each account only the permissions its work requires",
              "Leave it, the school is small", "Share one admin account",
              "Remove all logins"), "A", "SFIA DBAD; least privilege"),
            ("A report slows down as data grows. What should be checked first?",
             ("Whether the filtered or joined columns have indexes",
              "Whether the report has a title", "Whether the data is spelled correctly",
              "Whether the screen is large enough"), "A", "SFIA DBDS"),
        ],
    },
    "WEB": {
        "B": [
            ("A form posts a value the server did not expect and the page breaks. What is most appropriate?",
             ("Validate the value on the server before using it",
              "Disable the form", "Add more styling",
              "Increase the server memory"), "A", "SFIA PROG; validation"),
            ("A page works on a laptop but its layout breaks on a phone. What is the likely cause?",
             ("The layout has no small-screen rules applied",
              "The server is offline", "The database is empty",
              "The image file is too small"), "A", "SFIA PROG"),
        ],
        "C": [
            ("A button submits the form twice when clicked quickly. What is the standard fix?",
             ("Disable the control while the request is in progress",
              "Delete the button", "Rename the form", "Refresh the page on click"), "A", "SFIA PROG"),
            ("A page fetches data but cannot display it. What should be checked first?",
             ("Whether the response format matches what the page expects",
              "Whether the logo is compressed", "Whether the site has a footer",
              "Whether the page has a title"), "A", "SFIA PROG; integration"),
        ],
    },
    "OS": {
        "B": [
            ("A workstation is unusually slow and its disk is nearly full. What should be checked?",
             ("What is consuming the space, before deleting anything",
              "Replace the disk immediately", "Reinstall the operating system",
              "Turn off the screen"), "A", "SFIA OS"),
            ("A user cannot save to a shared folder they used last week. What is the first thing to verify?",
             ("Whether their access permissions have changed",
              "Whether the monitor is on", "Whether the file is empty",
              "Whether the room is quiet"), "A", "SFIA OS; permissions"),
        ],
        "C": [
            ("Two programs need the same resource at once. What usually resolves it?",
             ("Scheduling the access so one waits", "Deleting both programs",
              "Renaming one program", "Turning the machine off"), "A", "SFIA OS"),
            ("A machine will not start after an update. What is the most useful first action?",
             ("Check the most recent change and whether it can be rolled back",
              "Buy a new machine", "Delete all files", "Change the screen size"), "A", "SFIA OS"),
        ],
    },
    "SUPP": {
        "B": [
            ("A user calls about an error they cannot describe well. What should the support person do?",
             ("Ask questions until the symptom is clear", "Guess and close the call",
              "Ask the user to reinstall", "Escalate at once"), "A", "SFIA Communication"),
            ("A fixed fault reappears a month later. Why record it?",
             ("So the recurrence and its fix are known to the next person",
              "To fill a quota", "To blame the user", "To avoid further contact"), "A", "SFIA Documentation"),
        ],
        "C": [
            ("A user asks what a repair will cost. What is the honest response?",
             ("Explain what is known and what still needs checking",
              "Quote a confident figure immediately", "End the conversation",
              "Blame the manufacturer"), "A", "SFIA Customer care"),
            ("An issue is resolved with nothing written down. What is the consequence?",
             ("The next occurrence must be diagnosed from scratch",
              "Nothing at all", "The next fix is applied faster",
              "The user is guaranteed not to return"), "A", "SFIA Documentation"),
        ],
    },
}
