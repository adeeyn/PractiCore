"""Validation for the Partner Company Account Creation page (CP2 Figure 21).

Kept out of the view so the rules can be tested without a request context, and
so the same rules could be reused by a CLI or a seeder.
"""
import re

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+(\.[^@\s.]+)+$")
PHONE_RE = re.compile(r"^[0-9+\-\s().]{6,30}$")

TEXT_FIELDS = (
    "company_name", "location", "industry", "about", "required_skills",
    "contact_name", "contact_position", "contact_phone", "website",
    "company_size", "email",
)

# Only the fields CP2 calls "required company information" are mandatory.
# Everything else is optional so a partner company is not blocked from
# registering over a missing website or company size.
REQUIRED_FIELDS = ("company_name", "location", "contact_name", "email", "password")

MAX_LENGTHS = {
    "company_name": 150, "location": 100, "industry": 120,
    "contact_name": 100, "contact_position": 100, "contact_phone": 30,
    "website": 150, "company_size": 50, "email": 120,
}


def collect(form):
    """Trims every text field so ' a ' and 'a' are the same company."""
    data = {key: (form.get(key) or "").strip() for key in TEXT_FIELDS}
    data["password"] = (form.get("password") or "").strip()
    data["confirm_password"] = (form.get("confirm_password") or "").strip()
    data["is_hiring"] = bool(form.get("is_hiring"))
    return data


def validate(data, student_email_domain):
    """Returns (cleaned_data, error_message). error is None when valid.

    Messages are written for the person filling the form: they say what is
    wrong and, where it helps, what to do about it. No internal detail leaks.
    """
    for field in REQUIRED_FIELDS:
        if not data.get(field):
            label = field.replace("_", " ").capitalize()
            return None, "%s is required." % label

    if len(data["password"]) < 6:
        return None, "Password must be at least 6 characters."

    if data.get("confirm_password") and data["confirm_password"] != data["password"]:
        return None, "Passwords do not match."

    email = data["email"].lower()
    if not EMAIL_RE.match(email):
        return None, "Enter a valid email address."

    # A school-domain address belongs to a student, not a company.
    if email.endswith("@" + student_email_domain.lower()):
        return None, "A student school email cannot be used for a partner company."

    if data.get("contact_phone") and not PHONE_RE.match(data["contact_phone"]):
        return None, "Enter a valid contact number (digits, spaces, + or - only)."

    for field, limit in MAX_LENGTHS.items():
        if len(data.get(field) or "") > limit:
            label = field.replace("_", " ").capitalize()
            return None, "%s must be %d characters or fewer." % (label, limit)

    data["email"] = email
    return data, None