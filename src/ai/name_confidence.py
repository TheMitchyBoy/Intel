"""Confidence scoring for extracted person names."""

SOURCE_WEIGHTS: dict[str, float] = {
    "obituary": 0.96,
    "byline": 0.92,
    "author": 0.90,
    "title": 0.86,
    "ai": 0.82,
    "spacy": 0.68,
}

AUTO_CONFIRM_THRESHOLD = 0.90


def compute_confidence(sources: list[str]) -> float:
    if not sources:
        return 0.5
    weights = [SOURCE_WEIGHTS.get(s, 0.6) for s in sources]
    base = max(weights)
    bonus = min(0.12, 0.04 * (len(set(sources)) - 1))
    return round(min(1.0, base + bonus), 2)


def auto_review_status(confidence: float, sources: list[str]) -> str:
    if confidence >= AUTO_CONFIRM_THRESHOLD and len(set(sources)) >= 2:
        return "confirmed"
    return "pending"
