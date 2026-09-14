# resume_parser.py
import re
import spacy
from spacy.matcher import Matcher, PhraseMatcher

# Load English model
nlp = spacy.load("en_core_web_sm")

class ResumeParser:
    def __init__(self, skills_list=None):
        self.nlp = nlp
        
        # Default skill set dictionary if none provided
        if skills_list is None:
            skills_list = [
                "Python", "Java", "C++", "JavaScript", "HTML", "CSS", "React",
                "Node.js", "SQL", "PostgreSQL", "MongoDB", "Git", "Docker",
                "Machine Learning", "Data Analysis", "Flask", "Django", "UI/UX"
            ]
            
        # Initialize PhraseMatcher for skills matching
        self.skills_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
        patterns = [self.nlp.make_doc(skill) for skill in skills_list]
        self.skills_matcher.add("SKILLS", patterns)

    def extract_email(self, text):
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    def extract_phone(self, text):
        # Matches standard international and local phone number formats
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        match = re.search(phone_pattern, text)
        return match.group(0) if match else None

    def extract_name(self, doc):
        # 1. First heuristic: Assume candidate name is near the top lines
        first_few_lines = doc.text.split("\n")[:5]
        top_text = "\n".join(first_few_lines)
        top_doc = self.nlp(top_text)
        
        for ent in top_doc.ents:
            if ent.label_ == "PERSON":
                return ent.text.strip()
                
        # 2. Fallback: Search the full document entities
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text.strip()
                
        return None

    def extract_skills(self, doc):
        matches = self.skills_matcher(doc)
        skills = set()
        for match_id, start, end in matches:
            span = doc[start:end]
            skills.add(span.text)
        return list(skills)

    def parse(self, text):
        doc = self.nlp(text)
        
        return {
            "name": self.extract_name(doc),
            "email": self.extract_email(text),
            "phone": self.extract_phone(text),
            "skills": self.extract_skills(doc)
        }