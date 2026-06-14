import json
import logging
import re
from collections import Counter

from openai import OpenAI

from src.ai.person_names import (
    is_likely_place_name,
    is_valid_person_name,
    normalize_person_name,
    person_name_key,
)
from src.config import settings

logger = logging.getLogger(__name__)

_nlp = None

BYLINE_RE = re.compile(
    r"\bBy\s+([A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+)*)\s+"
    r"(?:Daily News|For the Daily News|Associated Press|Alaska Public Media)",
    re.IGNORECASE,
)

OPINION_URL_MARKERS = ("/opinion/", "/editorials/", "/columns/", "/commentary/")

WRITER_ROLE_MARKERS = (
    "staff writer", "sports editor", "managing editor", "editor in chief",
    "reporter", "correspondent", "daily news", "contributing writer",
)

TITLE_NAME_RE = re.compile(
    r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b(?:\s+(?:hits|fields|wins|arrested|charged|dies|died|honored))"
)


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
    return normalize_person_name(name)


def _is_valid_name(name: str, *, allow_single_word: bool = False) -> bool:
    return is_valid_person_name(name, allow_single_word=allow_single_word)


def is_opinion_or_editorial(url: str = "") -> bool:
    """True when the article is an opinion, editorial, or column."""
    lower = url.lower()
    return any(marker in lower for marker in OPINION_URL_MARKERS)


def _strip_bylines(text: str) -> str:
    if not text:
        return ""
    return BYLINE_RE.sub("", text).strip()


def _byline_names_in_text(text: str) -> set[str]:
    return {
        person_name_key(match.group(1))
        for match in BYLINE_RE.finditer(text)
        if _is_valid_name(_normalize_name(match.group(1)))
    }


def _is_writer_role(role: str) -> bool:
    lower = role.lower()
    return any(marker in lower for marker in WRITER_ROLE_MARKERS)


def _filter_writer_names(people: list[dict], *, excluded_names: set[str]) -> list[dict]:
    filtered: list[dict] = []
    for person in people:
        name_key = person_name_key(person["full_name"])
        if name_key in excluded_names:
            continue
        if _is_writer_role(person.get("role_context", "")):
            continue
        if is_likely_place_name(person["full_name"]):
            continue
        filtered.append(person)
    return filtered


def extract_names_from_author(author: str) -> list[dict]:
    if not author:
        return []
    lower = author.lower().strip()
    if "daily news" in lower and "by" not in lower:
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

    if "obituar" in url.lower() or "/obituaries/" in url.lower():
        name = re.sub(r"\s*\([^)]+\)", "", title).strip()
        name = _normalize_name(name)
        if _is_valid_name(name, allow_single_word=True):
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
    place_names = {
        person_name_key(ent.text)
        for ent in doc.ents
        if ent.label_ in ("GPE", "LOC", "FAC", "ORG")
    }

    found: list[str] = []
    for ent in doc.ents:
        if ent.label_ != "PERSON":
            continue
        name = _normalize_name(ent.text)
        key = person_name_key(name)
        if key in place_names or is_likely_place_name(name):
            continue
        if _is_valid_name(name):
            found.append(name)

    counts = Counter(found)
    return [{"full_name": name, "mention_count": count} for name, count in counts.most_common()]


def extract_names_ai(title: str, content: str, *, include_writers: bool = False) -> list[dict]:
    if not settings.openai_api_key:
        return []

    writer_rule = (
        "Include columnists and opinion writers when they are the author."
        if include_writers
        else "Do NOT include journalists, reporters, editors, or staff writers — only people mentioned in the story."
    )

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f"""Analyze this local newspaper article and extract all people mentioned.
For each person, provide their full name, mention count, and their role/context.

Return JSON: {{"people": [{{"full_name": "Jane Doe", "mention_count": 2, "role_context": "City Mayor"}}]}}
Only include real people (not organizations, cities, states, or places like Alaska or Ketchikan).
{writer_rule}

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
            and _is_valid_name(_normalize_name(p["full_name"]))
            and not is_likely_place_name(_normalize_name(p["full_name"]))
        ]
    except Exception as e:
        logger.error("AI name extraction failed: %s", e)
        return []


def _merge_people(*sources: list[dict]) -> list[dict]:
    merged: dict[str, dict] = {}
    for people in sources:
        for person in people:
            name = _normalize_name(person["full_name"])
            if not _is_valid_name(name) or is_likely_place_name(name):
                continue
            key = person_name_key(name)
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
    opinion = is_opinion_or_editorial(url)
    byline_names_to_exclude = _byline_names_in_text(content)
    body = content if opinion else _strip_bylines(content)

    text = f"{title}. {body}"
    if author and opinion:
        text = f"{author}. {text}"

    author_names = extract_names_from_author(author) if opinion else []
    byline_names = extract_names_from_bylines(text) if opinion else []
    title_names = extract_names_from_title(title, url)
    ai_names = (
        extract_names_ai(title, body, include_writers=opinion)
        if settings.openai_api_key
        else []
    )
    spacy_names = extract_names_spacy(text)

    if not opinion:
        spacy_names = _filter_writer_names(spacy_names, excluded_names=byline_names_to_exclude)
        ai_names = _filter_writer_names(ai_names, excluded_names=byline_names_to_exclude)

    return _merge_people(author_names, byline_names, title_names, ai_names, spacy_names)
