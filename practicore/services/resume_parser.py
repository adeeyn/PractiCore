import re

import docx
import pdfplumber
import spacy
from spacy.matcher import PhraseMatcher

from .skill_taxonomy import SkillTaxonomy


class ResumeParser:
    """Extracts name, contact details and skills from a PDF/DOCX resume."""

    EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    PHONE_PATTERN = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'

    def __init__(self, model_name="en_core_web_sm"):
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            raise RuntimeError(f"SpaCy model '{model_name}' not found. Run: python -m spacy download {model_name}")

        self.matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        self.matcher.add("SKILLS", [self.nlp.make_doc(skill) for skill in SkillTaxonomy.all_skills()])

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

    def parse(self, file_stream, filename):
        text = self.extract_text(file_stream, filename)

        email_match = re.search(self.EMAIL_PATTERN, text)
        phone_match = re.search(self.PHONE_PATTERN, text)
        found_skills = self.extract_skills(text)

        return {
            "name": self.extract_name(text),
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0) if phone_match else None,
            "skills": list(found_skills),
            "categorized_skills": SkillTaxonomy.categorize(found_skills),
        }
