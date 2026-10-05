"""Initials for the avatar/logo circles, derived from a name.

Kept in its own dependency-free module because it is read by every layer that
shows a logo or an initials badge: the repositories that shape the rows, the
employer/admin routes, and the recommendation service. An earlier version of
this rule was copy-pasted into four places and had already drifted apart, so a
company could show one set of initials on the profile page and another on the
student's recommendation card.
"""

# Words taken from a name when building initials. "Tech Solution Inc." -> "TS"
# and "Juan Dela Cruz" -> "JD": the first two words only, because a third or
# fourth letter makes the badge unreadable at 11-17px.
INITIAL_WORDS = 2

# Shown when a name is blank. A badge still needs to render something.
FALLBACK_INITIALS = "?"


def initials_for(name, words=INITIAL_WORDS, fallback=FALLBACK_INITIALS):
    """'Juan Dela Cruz' -> 'JD', 'Tech Solution Inc.' -> 'TS', 'Globex' -> 'G'.

    Case is raised so a lower-case company name still reads as an acronym, and
    blank input never yields an empty badge.
    """
    parts = [part for part in (name or "").split() if part]
    return "".join(part[0] for part in parts[:words]).upper() or fallback