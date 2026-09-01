import re
import spacy
import pdfplumber
import docx
from spacy.matcher import PhraseMatcher

# Load SpaCy model once at app startup
nlp = spacy.load("en_core_web_sm")

def extract_text_from_pdf(file_stream):
    text = ""
    with pdfplumber.open(file_stream) as pdf:
        for page in pdf.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    return text

def extract_text_from_docx(file_stream):
    doc = docx.Document(file_stream)
    return "\n".join([p.text for p in doc.paragraphs if p.text])

def parse_resume(file_stream, filename, skills_taxonomy=None):
    # 1. Extract plain text based on file type
    if filename.endswith('.pdf'):
        text = extract_text_from_pdf(file_stream)
    elif filename.endswith('.docx'):
        text = extract_text_from_docx(file_stream)
    else:
        raise ValueError("Unsupported file format. Please upload PDF or DOCX.")

    doc = nlp(text)

    # 2. Extract Contact Info
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    
    email_match = re.search(email_pattern, text)
    phone_match = re.search(phone_pattern, text)

    # 3. Extract Name using SpaCy NER
    extracted_name = None
    first_few_lines = "\n".join(text.split("\n")[:5])
    top_doc = nlp(first_few_lines)
    for ent in top_doc.ents:
        if ent.label_ == "PERSON":
            extracted_name = ent.text.strip()
            break

    # 4. Extract Skills using PhraseMatcher
    if not skills_taxonomy:
        skills_taxonomy = [
            "Python", "Java", "C++", "VB.NET", "JavaScript", "HTML", "CSS", 
            "React", "Node.js", "SQL", "PostgreSQL", "MongoDB", "Git", "Docker",
            "Machine Learning", "Data Analysis", "Flask", "Django", "UI/UX", "NLP"
        ]

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp.make_doc(skill) for skill in skills_taxonomy]
    matcher.add("SKILLS", patterns)

    matches = matcher(doc)
    found_skills = set()
    for match_id, start, end in matches:
        found_skills.add(doc[start:end].text)

    return {
        "name": extracted_name,
        "email": email_match.group(0) if email_match else None,
        "phone": phone_match.group(0) if phone_match else None,
        "skills": list(found_skills)
    }