"""Shared person name validation and normalization."""

import re
from difflib import SequenceMatcher

# Exact names that are never people (lowercase keys)
SKIP_EXACT_NAMES = {
    "email print copy", "facebook twitter", "positivity", "local news",
    "ketchikan daily news", "daily news", "ketchikan daily news staff",
    "alaska", "ketchikan", "sitka", "juneau", "anchorage", "fairbanks",
    "america", "american", "united states", "washington", "oregon",
    "seattle", "portland", "hawaii", "canada", "russia", "china",
    "congress", "senate", "legislature",
    "borough", "assembly", "school", "hospital", "legion",
}

# Substrings that disqualify a name
SKIP_NAME_FRAGMENTS = (
    "daily news", "associated press", "staff writer", "staff photo",
    "facebook", "twitter", "whatsapp", "email", "print", "copy", "save",
    "ketchikan", "legion post", "borough assembly", "high school",
    "alaska", "sitka", "juneau", "anchorage", "public media",
    "united states", "daily news sports", "daily news staff",
)

# Single-word place / org names (lowercase)
SKIP_SINGLE_NAMES = {
    "alaska", "ketchikan", "sitka", "juneau", "anchorage", "fairbanks",
    "america", "washington", "hawaii", "canada", "borough", "legislature",
    "congress", "senate", "school", "hospital", "positivity",
}

# Common nicknames -> canonical first name (lowercase)
NICKNAME_CANONICAL: dict[str, str] = {
    "rob": "robert", "bob": "robert", "bobby": "robert",
    "bill": "william", "will": "william", "billy": "william",
    "jim": "james", "jimmy": "james", "jamie": "james",
    "mike": "michael", "mick": "michael",
    "dick": "richard", "rick": "richard", "rich": "richard",
    "liz": "elizabeth", "beth": "elizabeth", "betty": "elizabeth",
    "kate": "katherine", "kathy": "katherine", "kat": "katherine",
    "tom": "thomas", "tommy": "thomas",
    "dan": "daniel", "danny": "daniel",
    "ej": "e.j.", "ed": "edward", "ted": "edward",
}

FUZZY_MATCH_THRESHOLD = 0.88


def normalize_person_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip())
    if name.isupper() and " " in name:
        name = name.title()
    return name


def person_name_key(name: str) -> str:
    return normalize_person_name(name).lower()


def is_valid_person_name(name: str, *, allow_single_word: bool = False) -> bool:
    if not name or len(name) < 3 or len(name) > 80:
        return False

    normalized = normalize_person_name(name)
    lower = normalized.lower()
    parts = normalized.split()

    if lower in SKIP_EXACT_NAMES:
        return False
    if any(skip in lower for skip in SKIP_NAME_FRAGMENTS):
        return False
    if " for the" in lower or lower.endswith(" for"):
        return False
    if len(parts) < 2 and not allow_single_word:
        return False
    if len(parts) == 1 and parts[0].lower() in SKIP_SINGLE_NAMES:
        return False
    if not re.search(r"[A-Za-z]{2,}", normalized):
        return False

    # Reject all-caps single tokens that look like places (e.g. ALASKA)
    if len(parts) == 1 and normalized.isupper() and len(normalized) > 3:
        return False

    return True


def is_likely_place_name(name: str) -> bool:
    lower = person_name_key(name)
    if lower in SKIP_EXACT_NAMES or lower in SKIP_SINGLE_NAMES:
        return True
    return any(skip in lower for skip in ("alaska", "ketchikan", "borough", "assembly"))


def _canonical_tokens(name: str) -> list[str]:
    parts = person_name_key(name).split()
    if not parts:
        return []
    first = NICKNAME_CANONICAL.get(parts[0], parts[0])
    return [first, *parts[1:]]


def fuzzy_name_key(name: str) -> str:
    """Normalized key used for fuzzy deduplication."""
    return " ".join(_canonical_tokens(name))


def names_are_similar(a: str, b: str, threshold: float = FUZZY_MATCH_THRESHOLD) -> bool:
    if person_name_key(a) == person_name_key(b):
        return True
    key_a = fuzzy_name_key(a)
    key_b = fuzzy_name_key(b)
    if key_a == key_b:
        return True
    if SequenceMatcher(None, key_a, key_b).ratio() >= threshold:
        return True
    # Last name + similar first name (handles Ej Haas / EJ Haas)
    parts_a = key_a.split()
    parts_b = key_b.split()
    if len(parts_a) >= 2 and len(parts_b) >= 2:
        if parts_a[-1] == parts_b[-1]:
            first_ratio = SequenceMatcher(None, parts_a[0], parts_b[0]).ratio()
            if first_ratio >= 0.8:
                return True
    return False


def pick_better_display_name(current: str, candidate: str) -> str:
    """Prefer title-cased full names over ALL CAPS fragments."""
    current = normalize_person_name(current)
    candidate = normalize_person_name(candidate)
    if candidate.istitle() and not current.istitle():
        return candidate
    if len(candidate) > len(current):
        return candidate
    return current
