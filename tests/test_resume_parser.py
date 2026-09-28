"""Resume section-splitting tests.

Uses the real ResumeParser logic but stubs out the spaCy model, so these run
without downloading en_core_web_sm.
"""
from practicore.services.resume_parser import ResumeParser


def _parser_without_spacy():
    """Builds a ResumeParser without loading a spaCy model or touching current_app."""
    parser = ResumeParser.__new__(ResumeParser)
    import re

    parser._section_patterns = {
        key: re.compile(r"^\s*(?:%s)\s*[:\-–—]?\s*$" % "|".join(alternatives), re.IGNORECASE)
        for key, alternatives in ResumeParser.SECTION_HEADINGS.items()
    }
    parser._other_pattern = re.compile(
        r"^\s*(?:%s)\s*[:\-–—]?\s*$" % "|".join(ResumeParser.OTHER_HEADINGS), re.IGNORECASE
    )
    return parser


SAMPLE = """Juan Dela Cruz
juan@student.tsu.edu.ph

EDUCATION
BSIT-Web and Mobile Applications, Tarlac State University, 2024

CERTIFICATIONS
Google IT Support

EXPERIENCE
Intern, ABC Tech - 2023

PROJECTS
Student Information System

SKILLS
Python, HTML, CSS, MySQL
"""


class TestSectionSplitting:
    def test_each_section_is_found(self):
        sections = _parser_without_spacy().split_sections(SAMPLE)
        assert len(sections["education"]) == 1
        assert len(sections["certifications"]) == 1
        assert len(sections["experience"]) == 1
        assert len(sections["projects"]) == 1

    def test_heading_itself_is_not_an_item(self):
        sections = _parser_without_spacy().split_sections(SAMPLE)
        for key, lines in sections.items():
            for line in lines:
                assert line.upper() != key.upper(), f"heading leaked into {key}: {line!r}"

    def test_content_lines_are_captured_verbatim(self):
        sections = _parser_without_spacy().split_sections(SAMPLE)
        assert "Tarlac State University" in sections["education"][0]
        assert "Google IT Support" in sections["certifications"][0]

    def test_known_other_heading_ends_the_previous_section(self):
        # "SKILLS" must not be swallowed by the PROJECTS section.
        sections = _parser_without_spacy().split_sections(SAMPLE)
        joined = " ".join(sections["projects"]).lower()
        assert "python" not in joined
        assert "html" not in joined

    def test_body_line_containing_a_keyword_is_not_a_heading(self):
        text = "EXPERIENCE\nMy projects involved Python\n"
        sections = _parser_without_spacy().split_sections(text)
        # "My projects involved Python" is a body line, not a PROJECTS heading.
        assert sections["projects"] == []
        assert len(sections["experience"]) == 1

    def test_bullets_are_stripped(self):
        text = "PROJECTS\n- Student Information System\n* Capstone App\n"
        items = ResumeParser._bullets(_parser_without_spacy().split_sections(text)["projects"])
        assert items == ["Student Information System", "Capstone App"]

    def test_text_with_no_headings_yields_nothing(self):
        sections = _parser_without_spacy().split_sections("Just a paragraph of text.\n")
        assert all(lines == [] for lines in sections.values())

    def test_empty_text_is_safe(self):
        sections = _parser_without_spacy().split_sections("")
        assert all(lines == [] for lines in sections.values())
