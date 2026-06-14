"""Shared person name validation and normalization."""

import re

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
