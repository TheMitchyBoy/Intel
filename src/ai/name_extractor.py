import json
import logging
from collections import Counter

from openai import OpenAI

from src.config import settings

logger = logging.getLogger(__name__)

_nlp = None


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


def extract_names_spacy(text: str) -> list[dict]:
    """Extract person names using spaCy NER."""
    if not text:
        return []

    nlp = _get_nlp()
    doc = nlp(text[:10000])
    names = [ent.text.strip() for ent in doc.ents if ent.label_ == "PERSON"]

    counts = Counter(names)
    return [
        {"full_name": name, "mention_count": count}
        for name, count in counts.most_common()
        if len(name) > 2 and " " in name
    ]


def extract_names_ai(title: str, content: str) -> list[dict]:
    """Use OpenAI to extract people and their roles from article text."""
    if not settings.openai_api_key:
        return []

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f"""Analyze this newspaper article and extract all people mentioned.
For each person, provide their full name, how many times they are mentioned, and their role/context in the article.

Return JSON array: [{{"full_name": "...", "mention_count": N, "role_context": "..."}}]
Only include real people (not organizations). Only include full names when possible.

Title: {title}
Content: {content[:4000]}"""

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
                "full_name": p["full_name"],
                "mention_count": p.get("mention_count", 1),
                "role_context": p.get("role_context", ""),
            }
            for p in people
            if p.get("full_name")
        ]
    except Exception as e:
        logger.error("AI name extraction failed: %s", e)
        return []


def extract_names(title: str, content: str) -> list[dict]:
    """Extract names using AI first, falling back to spaCy."""
    if settings.openai_api_key:
        ai_names = extract_names_ai(title, content)
        if ai_names:
            return ai_names

    spacy_names = extract_names_spacy(f"{title}. {content}")
    return [{**n, "role_context": ""} for n in spacy_names]
