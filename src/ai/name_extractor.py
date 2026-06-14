import json
import logging
import re
from collections import Counter

from openai import OpenAI

from src.config import settings

logger = logging.getLogger(__name__)

_nlp = None

BYLINE_RE = re.compile(
    r"\bBy\s+([A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+)*)\s+"
    r"(?:Daily News|For the Daily News|Associated Press|Alaska Public Media)",
    re.IGNORECASE,
)

# Names in headlines like "Owen Mendoza hits for Post 3"
TITLE_NAME_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b(?:\s+(?:hits|fields|wins|arrested|charged|dies|died|honored))"
)

SKIP_NAME_FRAGMENTS = (
    "daily news", "associated press", "staff writer", "staff photo",
    "facebook", "twitter", "whatsapp", "email", "print", "copy", "save",
    "ketchikan", "legion post", "borough assembly", "high school",
)
SKIP_EXACT_NAMES = {
    "email print copy", "facebook twitter", "positivity", "local news",
    "ketchikan daily news", "daily news",
}


def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model not found, downloading...")
            from spacy.cli import download
            download("en_core_web_sm")
            _nlp = spacy.load("en_core_web_sm")
    return _nlp


def _normalize_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip())
    if name.isupper() and " " in name:
        name = name.title()
    return name


def _is_valid_name(name: str) -> bool:
    if not name or len(name) < 3 or len(name) > 80:
        return False
    lower = name.lower()
    if lower in SKIP_EXACT_NAMES:
        return False
    if any(skip in lower for skip in SKIP_NAME_FRAGMENTS):
        return False
    # Require at least one letter pair that looks like a name
    if not re.search(r"[A-Za-z]{2,}", name):
        return False
    return True


def extract_names_from_author(author: str) -> list[dict]:
    if not author or author.lower() in SKIP_EXACT_NAMES:
        return []
    return extract_names_from_bylines(author if author.lower().startswith("by") else f"By {author}")


def extract_names_from_bylines(text: str) -> list[dict]:
    if not text:
        return []

    found: list[str] = []
    for match in BYLINE_RE.finditer(text):
        name = _normalize_name(match.group(1))
        if _is_valid_name(name):
            found.append(name)

    counts = Counter(found)
    return [{"full_name": name, "mention_count": count} for name, count in counts.most_common()]


def extract_names_from_title(title: str, url: str = "") -> list[dict]:
    """Extract names from headlines and obituary titles."""
    if not title:
        return []

    found: list[str] = []

    # Obituaries: title is usually the person's name
    if "obituar" in url.lower() or "/obituaries/" in url.lower():
        name = re.sub(r"\s*\([^)]+\)", "", title).strip()
        name = _normalize_name(name)
        if _is_valid_name(name):
            return [{"full_name": name, "mention_count": 1, "role_context": "Obituary"}]

    for match in TITLE_NAME_RE.finditer(title):
        name = _normalize_name(match.group(1))
        if _is_valid_name(name):
            found.append(name)

    counts = Counter(found)
    return [{"full_name": name, "mention_count": count} for name, count in counts.most_common()]


def extract_names_spacy(text: str) -> list[dict]:
    if not text:
        return []

    nlp = _get_nlp()
    doc = nlp(text[:10000])
    names = [_normalize_name(ent.text) for ent in doc.ents if ent.label_ == "PERSON"]

    counts = Counter(names)
    return [
        {"full_name": name, "mention_count": count}
        for name, count in counts.most_common()
        if _is_valid_name(name)
    ]


def extract_names_ai(title: str, content: str) -> list[dict]:
    if not settings.openai_api_key:
        return []

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f"""Analyze this local newspaper article and extract all people mentioned.
For each person, provide their full name, mention count, and their role/context.

Return JSON: {{"people": [{{"full_name": "Jane Doe", "mention_count": 2, "role_context": "City Mayor"}}]}}
Only include real people (not organizations or places).

Title: {title}
Content: {content[:6000]}"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = response.choices[0].message.content
        data = json.loads(raw)

        if isinstance(data, dict):
            people = data.get("people", data.get("persons", []))
        else:
            people = data

        return [
            {
                "full_name": _normalize_name(p["full_name"]),
                "mention_count": p.get("mention_count", 1),
                "role_context": p.get("role_context", ""),
            }
            for p in people
            if p.get("full_name") and _is_valid_name(_normalize_name(p["full_name"]))
        ]
    except Exception as e:
        logger.error("AI name extraction failed: %s", e)
        return []


def _merge_people(*sources: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for people in sources:
        for person in people:
            name = _normalize_name(person["full_name"])
            if not _is_valid_name(name):
                continue
            key = name.lower()
            if key in merged:
                merged[key]["mention_count"] = max(
                    merged[key]["mention_count"],
                    person.get("mention_count", 1),
                )
                if person.get("role_context") and not merged[key].get("role_context"):
                    merged[key]["role_context"] = person["role_context"]
            else:
                merged[key] = {
                    "full_name": name,
                    "mention_count": person.get("mention_count", 1),
                    "role_context": person.get("role_context", ""),
                }
    return list(merged.values())


def extract_names(title: str, content: str, author: str = "", url: str = "") -> list[dict]:
    """Extract names using author, bylines, titles, AI, and spaCy."""
    text = f"{title}. {content}"
    if author:
        text = f"{author}. {text}"

    author_names = extract_names_from_author(author)
    byline_names = extract_names_from_bylines(text)
    title_names = extract_names_from_title(title, url)
    ai_names = extract_names_ai(title, content) if settings.openai_api_key else []
    spacy_names = extract_names_spacy(text)

    return _merge_people(author_names, byline_names, title_names, ai_names, spacy_names)
