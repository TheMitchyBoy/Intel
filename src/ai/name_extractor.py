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

SKIP_NAME_FRAGMENTS = ("daily news", "associated press", "staff writer", "staff photo")


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
    # Title-case ALL CAPS bylines like "REED LOFSTEDT"
    if name.isupper() and " " in name:
        name = name.title()
    return name


def extract_names_from_bylines(text: str) -> list[dict]:
    """Extract reporter/subject names from newspaper bylines."""
    if not text:
        return []

    found: list[str] = []
    for match in BYLINE_RE.finditer(text):
        name = _normalize_name(match.group(1))
        if len(name) > 3 and not any(skip in name.lower() for skip in SKIP_NAME_FRAGMENTS):
            found.append(name)

    counts = Counter(found)
    return [{"full_name": name, "mention_count": count} for name, count in counts.most_common()]


def extract_names_spacy(text: str) -> list[dict]:
    """Extract person names using spaCy NER."""
    if not text:
        return []

    nlp = _get_nlp()
    doc = nlp(text[:10000])
    names = [_normalize_name(ent.text) for ent in doc.ents if ent.label_ == "PERSON"]

    counts = Counter(names)
    return [
        {"full_name": name, "mention_count": count}
        for name, count in counts.most_common()
        if len(name) > 2
    ]


def extract_names_ai(title: str, content: str) -> list[dict]:
    """Use OpenAI to extract people and their roles from article text."""
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
            if p.get("full_name")
        ]
    except Exception as e:
        logger.error("AI name extraction failed: %s", e)
        return []


def _merge_people(*sources: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for people in sources:
        for person in people:
            name = _normalize_name(person["full_name"])
            if not name or len(name) < 3:
                continue
            if any(skip in name.lower() for skip in SKIP_NAME_FRAGMENTS):
                continue
            if name in merged:
                merged[name]["mention_count"] = max(
                    merged[name]["mention_count"],
                    person.get("mention_count", 1),
                )
                if person.get("role_context") and not merged[name].get("role_context"):
                    merged[name]["role_context"] = person["role_context"]
            else:
                merged[name] = {
                    "full_name": name,
                    "mention_count": person.get("mention_count", 1),
                    "role_context": person.get("role_context", ""),
                }
    return list(merged.values())


def extract_names(title: str, content: str, author: str = "") -> list[dict]:
    """Extract names using bylines, AI, and spaCy — merge all results."""
    text = f"{title}. {content}"
    if author:
        text = f"{author}. {text}"

    byline_names = extract_names_from_bylines(text)
    ai_names = extract_names_ai(title, content) if settings.openai_api_key else []
    spacy_names = extract_names_spacy(text)

    return _merge_people(byline_names, ai_names, spacy_names)
