"""The 130-item PRACTICORE researcher competency question bank.

    flask --app app seed-master-bank

Provenance
----------
The content is the real researcher document, generated into
`master_bank_document.py` (see that module's header). Every item is marked
"Researcher-developed: Yes" and "Pending expert review/pilot testing" in the
source, so every row is stored as source_type 'Researcher-Developed' and none is
claimed as 'Validation-Approved'.

Nothing here is labelled 'CP2'. The document's own scope note states that the CP2
PDF and a prior question bank were NOT available to its authors, so it "does not
invent CP2 findings or claim that a prior question bank was reviewed". Recording
CP2 as a source would be a fabricated citation.

Answer-key verification
-----------------------
The source document records BOTH a "Correct Answer" letter and an explanation that
restates the correct option. On audit, 64 of the 130 items had a letter that
contradicted their own explanation - for example PROG-001 is published as "A"
("Store only one value") for the purpose of a loop, while its explanation says
"Repeat instructions" (option B).

verify_keys() adjudicates each item:
  VERIFIED   the published letter is supported by the explanation -> used as-is.
  CORRECTED  the published letter has no support and another option matches the
             explanation decisively -> the applied key follows the explanation, and
             the published letter is preserved in question_key_corrections so the
             change is auditable and reversible.
  UNRESOLVED the evidence is not decisive -> stored with is_active = 0 and never
             served, pending researcher adjudication.

Randomisation
-------------
balanced_rows() rotates the CORRECT option to a fresh position, which is what stops a
student scoring well by always picking one letter. Only the option POSITION changes:
wording, competency, difficulty and answer-key identity are all preserved.
"""
import random
import re

from .master_bank_document import ITEMS as DOCUMENT_ITEMS

# How each document competency maps onto PractiCore's canonical competency codes.
# The document's 13 constructs map onto the taxonomy that already exists, so no
# second competing set of competency records is created.
DOCUMENT_COMPETENCY_MAP = {
    "PROG": "PROG",   # Programming Fundamentals
    "WEB": "WEB",     # Web Development
    "DB": "DB",       # Database & SQL
    "TEST": "PROG",   # testing sits inside PROG's remit in the existing taxonomy
    "SUP": "SUPP",    # Technical Support
    "NET": "NET",     # Networking & IT Infrastructure
    "OS": "OS",       # Operating Systems
    "SEC": "SEC",     # Cybersecurity Fundamentals
    "DOC": "EVID",    # Evidence & Professional Practice
    "COMM": "COMM",   # Communication & Teamwork
    "TEAM": "COMM",   # Communication & Teamwork
    "PROB": "PROB",   # Problem Solving & Analytical Thinking
    "PROF": "EVID",   # Evidence & Professional Practice
}

QUESTION_TYPES = (
    "Multiple Choice", "True/False", "Scenario-Based Multiple Choice",
    "Code Output Prediction", "Debugging", "Short Answer", "Ordering/Sequence",
)

DIFFICULTIES = ("easy", "medium", "hard")

SOURCE_TYPE = "Researcher-Developed"
SOURCE_DOCUMENT = "PractiCore_Final_Research_Based_Question_Bank.docx"

# key_status values stored in assessment_questions.key_status.
KEY_VERIFIED = "Verified"
KEY_CORRECTED = "Corrected"
KEY_UNRESOLVED = "Unresolved"

# Tokens too generic to identify an option.
_STOP = {"a", "an", "the", "is", "are", "to", "of", "and", "in", "on", "for", "with",
         "it", "this", "that", "by", "as", "be", "not", "or", "will", "when", "from"}

def _tokens(text):
    words = re.findall(r"[a-z0-9]+", str(text or "").lower())
    return {w for w in words if w not in _STOP and len(w) > 2}


def _overlap(option, explanation):
    """Share of the option's own words that the explanation repeats."""
    o, e = _tokens(option), _tokens(explanation)
    if not o:
        return 0.0
    return len(o & e) / len(o)


def verify_keys(items=None):
    """Classifies every item's published key against its own explanation.

    Returns {question_code: {status, recorded, applied, recorded_text,
    applied_text, rule}}. A key is only CORRECTED when the published option has
    essentially NO support in the explanation AND a different option matches it
    decisively - anything weaker is UNRESOLVED, because guessing an answer key is far
    worse than declining to serve the item.
    """
    items = DOCUMENT_ITEMS if items is None else items
    report = {}
    for item in items:
        options = item["options"]
        recorded = item["correct_option"]
        scores = [_overlap(opt, item["explanation"]) for opt in options]
        order = sorted(range(len(options)), key=lambda n: -scores[n])
        best, runner = order[0], order[1]
        rec_n = "ABCD".index(recorded)

        if best == rec_n:
            status, applied = KEY_VERIFIED, recorded
        elif scores[rec_n] == 0.0 and scores[best] >= 0.5 and scores[best] > scores[runner]:
            status, applied = KEY_CORRECTED, "ABCD"[best]
        else:
            status, applied = KEY_UNRESOLVED, recorded

        rec_text = options[rec_n] if 0 <= rec_n < len(options) else ""
        app_text = ""
        if applied in "ABCD":
            app_n = "ABCD".index(applied)
            app_text = options[app_n] if app_n < len(options) else ""

        report[item["code"]] = {
            "status": status,
            "recorded": recorded,
            "applied": applied,
            "recorded_text": rec_text,
            "applied_text": app_text,
            "rule": "explanation-token-match",
        }
    return report


def _canonical_competency(item):
    return DOCUMENT_COMPETENCY_MAP.get(item["code"].split("-")[0], "PROG")


def _standard_ref(item):
    """The document's own citation, so provenance survives into the database."""
    parts = [item.get("framework") or "", item.get("source_title") or ""]
    ref = " ".join(p for p in parts if p).strip()
    return ref[:100] or "PractiCore research bank"


def balanced_rows():
    """One dict per item, shaped for assessment_questions.

    The correct option is rotated deterministically (seeded by the item's own code)
    so a student cannot score by always picking the same letter, and so re-seeding
    produces identical rows.
    """
    verification = verify_keys()
    rows = []
    for item in DOCUMENT_ITEMS:
        info = verification[item["code"]]
        options = list(item["options"])
        applied = info["applied"]

        if applied in "ABCD" and len(options) > 1:
            correct_text = options["ABCD".index(applied)]
            target = random.Random(item["code"]).randrange(len(options))
            rotated = [o for o in options if o != correct_text]
            rotated.insert(target, correct_text)
            options = rotated
            correct_option = "ABCD"[target]
        else:
            correct_option = applied

        while len(options) < 4:
            options.append("")

        rows.append({
            "question_code": item["code"],
            "competency": _canonical_competency(item),
            "doc_competency": item["code"].split("-")[0],
            "doc_type": item.get("doc_type"),
            "question_type": item["type"],
            "difficulty": item["difficulty"],
            "question_text": item["question_text"],
            "option_a": options[0], "option_b": options[1],
            "option_c": options[2], "option_d": options[3],
            "correct_option": correct_option,
            "explanation": item["explanation"],
            "standard_ref": _standard_ref(item),
            "pathway": item.get("pathways"),
            "target_role": item.get("roles"),
            "source_type": SOURCE_TYPE,
            "key_status": info["status"],
            # An UNRESOLVED key is stored but never served, so a student can never be
            # marked wrong by an answer the bank was unable to verify.
            "is_active": 0 if info["status"] == KEY_UNRESOLVED else 1,
            "recorded_option": info["recorded"],
            "recorded_option_text": info["recorded_text"],
            "applied_option_text": info["applied_text"],
            "correction_rule": info["rule"],
        })
    return rows


def answer_key_distribution(rows=None):
    rows = balanced_rows() if rows is None else rows
    counts = {"A": 0, "B": 0, "C": 0, "D": 0}
    for row in rows:
        counts[row["correct_option"]] = counts.get(row["correct_option"], 0) + 1
    return counts


def counts_per_competency(active_only=False):
    counts = {}
    for row in balanced_rows():
        if active_only and not row["is_active"]:
            continue
        counts[row["competency"]] = counts.get(row["competency"], 0) + 1
    return counts


def counts_per_type():
    counts = {}
    for row in balanced_rows():
        counts[row["question_type"]] = counts.get(row["question_type"], 0) + 1
    return counts


def counts_per_difficulty():
    counts = {}
    for row in balanced_rows():
        counts[row["difficulty"]] = counts.get(row["difficulty"], 0) + 1
    return counts


def key_status_summary():
    """{'Verified': n, 'Corrected': n, 'Unresolved': n} for the CLI report."""
    summary = {KEY_VERIFIED: 0, KEY_CORRECTED: 0, KEY_UNRESOLVED: 0}
    for info in verify_keys().values():
        summary[info["status"]] += 1
    return summary


def corrections():
    """The CORRECTED items only, shaped for question_key_corrections."""
    explanations = {r["question_code"]: r["explanation"] for r in balanced_rows()}
    out = []
    for code, info in verify_keys().items():
        if info["status"] != KEY_CORRECTED:
            continue
        out.append({
            "question_code": code,
            "recorded_option": info["recorded"],
            "applied_option": info["applied"],
            "recorded_option_text": info["recorded_text"],
            "applied_option_text": info["applied_text"],
            "explanation": explanations.get(code),
            "rule": info["rule"],
        })
    return out


# The bank is a single module of items.
QUESTIONS = tuple(DOCUMENT_ITEMS)
