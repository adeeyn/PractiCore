import re

import docx
import pdfplumber
import spacy
from spacy.matcher import PhraseMatcher

from .skill_taxonomy import SkillTaxonomy


class ResumeParser:
    """Extracts name, contact details, skills and career sections from a resume.

    The section extractor is deliberately heading-driven rather than a trained
    NER pipeline: resume layouts vary wildly, but the headings themselves
    ("EDUCATION", "CERTIFICATIONS", "EXPERIENCE", "PROJECTS") are consistent,
    and the small model already loaded for skill matching is enough to pull
    organisations and dates out of the block underneath each one.
    """

    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    PHONE_PATTERN = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'

    # Section headings, mapped to the parse() key each one fills. Order matters:
    # the first matching heading wins, so put the more specific patterns first.
    SECTION_HEADINGS = {
        "education": (
            r"educational\s+background", r"education", r"academic\s+(background|profile)",
            r"academic\s+performance", r"school", r"university", r"college",
        ),
        "certifications": (
            r"certificat\w*", r"licens\w*", r"training", r"courses", r"awards?",
            r"professional\s+development",
        ),
        "experience": (
            r"(work\s+|professional\s+|employment\s+|relevant\s+)?experience",
            r"employment(\s+history)?", r"internship(\s+history)?", r"work\s+history",
            r"job\s+history",
        ),
        "projects": (
            r"projects?", r"portfolio", r"personal\s+works?",
        ),
    }

    # Anything that is a heading for a part of the resume we do not extract.
    OTHER_HEADINGS = (
        r"summary", r"objective", r"profile", r"contact", r"personal\s+details?",
        r"skills?", r"technical\s+skills?", r"abilities", r"references?",
        r"languages?", r"interests?", r"hobbies", r"activities",
    )

    MAX_SECTION_ITEMS = 12

    def __init__(self, model_name="en_core_web_sm"):
        # Called from create_app before any app context exists, so the model name
        # must be passed in by the caller (it comes from Config.SPACY_MODEL).
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            raise RuntimeError(f"SpaCy model '{model_name}' not found. Run: python -m spacy download {model_name}")

        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.matcher.add("SKILLS", [self.nlp.make_doc(skill) for skill in SkillTaxonomy.all_skills()])

        # One compiled pattern per section, matched against a whole line.
        self._section_patterns = {
            key: re.compile(r"^\s*(?:%s)\s*[:\-–—]?\s*$" % "|".join(alternatives), re.IGNORECASE)
            for key, alternatives in self.SECTION_HEADINGS.items()
        }
        self._other_pattern = re.compile(
            r"^\s*(?:%s)\s*[:\-–—]?\s*$" % "|".join(self.OTHER_HEADINGS), re.IGNORECASE
        )

    # --- Text extraction ---

    @staticmethod
    def extract_text_from_pdf(file_stream):
        text = ""
        with pdfplumber.open(file_stream) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
        return text

    @staticmethod
    def extract_text_from_docx(file_stream):
        doc = docx.Document(file_stream)
        return "\n".join([p.text for p in doc.paragraphs if p.text])

    def extract_text(self, file_stream, filename):
        if filename.endswith(".pdf"):
            return self.extract_text_from_pdf(file_stream)
        if filename.endswith(".docx"):
            return self.extract_text_from_docx(file_stream)
        raise ValueError("Unsupported format")

    # --- Field extraction ---

    def extract_name(self, text):
        first_few_lines = "\n".join(text.split("\n")[:5])
        for ent in self.nlp(first_few_lines).ents:
            if ent.label_ == "PERSON":
                return ent.text.strip()
        return None

    def extract_skills(self, text):
        doc = self.nlp(text)
        return {doc[start:end].text for _, start, end in self.matcher(doc)}

    # --- Section extraction ---

    def split_sections(self, text):
        """Splits raw resume text into {section_key: [lines]}.

        A line is treated as a heading only when it is short and matches a known
        heading, so a body line like "My projects involved Python" is not mistaken
        for a section title.
        """
        sections = {key: [] for key in self.SECTION_HEADINGS}
        current = None
        previous_blank = True  # suppress headings that appear inside a bullet list

        for raw_line in (text or "").splitlines():
            line = raw_line.strip()
            if not line:
                previous_blank = True
                continue

            is_heading_candidate = previous_blank and len(line) <= 60
            matched_section = False
            if is_heading_candidate:
                for key, pattern in self._section_patterns.items():
                    if pattern.match(line):
                        current = key
                        matched_section = True
                        break
                if not matched_section and self._other_pattern.match(line):
                    # A known heading we do not extract: stop the current one
                    # so e.g. "SKILLS" does not keep collecting lines.
                    current = None
            previous_blank = False

            if current and not matched_section:
                # The heading itself is not an item; only the lines under it.
                sections[current].append(line)

        return sections

    @staticmethod
    def _bullets(lines):
        """Normalises lines into clean items, dropping the bullet characters."""
        items = []
        for line in lines:
            cleaned = re.sub(r"^[\s\-*•·▪◦–—]+", "", line).strip()
            cleaned = re.sub(r"\s{2,}", " ", cleaned)
            if cleaned:
                items.append(cleaned)
        return items

    def extract_sections(self, text):
        """Returns the four career sections as display-ready lists of strings.

        Falls back to a single summary line per section rather than returning
        nothing, so the student profile always has something truthful to show.
        """
        raw_sections = self.split_sections(text)
        extracted = {}

        for key, lines in raw_sections.items():
            items = self._bullets(lines)[: self.MAX_SECTION_ITEMS]
            if not items:
                extracted[key] = []
            elif key == "education":
                # Education lines are dense; one line is a whole entry.
                extracted[key] = items[:6]
            else:
                extracted[key] = items

        return extracted

    def parse(self, file_stream, filename):
        text = self.extract_text(file_stream, filename)

        email_match = re.search(self.EMAIL_PATTERN, text)
        phone_match = re.search(self.PHONE_PATTERN, text)
        found_skills = self.extract_skills(text)
        sections = self.extract_sections(text)

        return {
            "name": self.extract_name(text),
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
            "skills": list(found_skills),
            "categorized_skills": SkillTaxonomy.categorize(found_skills),
            # Career sections the CP2 NLP step promises. Kept as lists so the
            # upload response can render them without another split.
            "education": sections.get("education", []),
            "certifications": sections.get("certifications", []),
            "experience": sections.get("experience", []),
            "projects": sections.get("projects", []),
        }
