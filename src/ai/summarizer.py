import logging

from openai import OpenAI

from src.config import settings

logger = logging.getLogger(__name__)


def summarize_article(title: str, content: str) -> str:
    """Generate an AI summary of a newspaper article."""
    if not content:
        return title

    if not settings.openai_api_key:
        return _fallback_summary(content)

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = f"""Summarize this local newspaper article in 2-3 concise sentences.
Focus on key events, people involved, and why it matters to the local community.

Title: {title}
Content: {content[:6000]}"""

    try:
        response = client.chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("AI summarization failed: %s", e)
        return _fallback_summary(content)


def _fallback_summary(content: str) -> str:
    sentences = content.replace("\n", " ").split(". ")
    return ". ".join(sentences[:3]).strip() + ("." if sentences else "")
