from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .models import Opportunity

URGENT_KEYWORDS = ("urgent", "asap", "immediately", "quick", "today", "this week")
QUALITY_KEYWORDS = ("long term", "ongoing", "contract", "fixed price", "hourly", "retainer")


def score_opportunities(
    opportunities: list[Opportunity],
    skills: list[str],
    blocked_keywords: list[str],
    must_include_any: list[str] | None = None,
    title_include_any: list[str] | None = None,
    scam_keywords: list[str] | None = None,
    minimum_source_reliability: int = 0,
    max_age_days: int | None = None,
) -> list[Opportunity]:
    scored = []
    for opportunity in opportunities:
        score, reasons = score_one(
            opportunity,
            skills,
            blocked_keywords,
            must_include_any or [],
            title_include_any or [],
            scam_keywords or [],
            minimum_source_reliability,
            max_age_days,
        )
        opportunity.score = score
        opportunity.reasons = reasons
        if score > 0:
            scored.append(opportunity)
    return sorted(scored, key=lambda item: item.score, reverse=True)


def score_one(
    opportunity: Opportunity,
    skills: list[str],
    blocked_keywords: list[str],
    must_include_any: list[str],
    title_include_any: list[str] | None = None,
    scam_keywords: list[str] | None = None,
    minimum_source_reliability: int = 0,
    max_age_days: int | None = None,
) -> tuple[int, list[str]]:
    title_text = normalized(opportunity.title)
    text = normalized(f"{opportunity.title} {opportunity.description}")
    reasons: list[str] = []

    blocked = [word for word in blocked_keywords if normalized(word) in text]
    if blocked:
        return 0, [f"blocked keyword: {', '.join(blocked)}"]

    risk_words = [word for word in scam_keywords or [] if normalized(word) in text]
    if risk_words:
        return 0, [f"risk keyword: {', '.join(risk_words[:3])}"]

    if opportunity.reliability < minimum_source_reliability:
        return 0, [f"source reliability below minimum: {opportunity.reliability}"]

    if max_age_days is not None and is_older_than(opportunity.published_at, max_age_days):
        return 0, [f"older than {max_age_days} days"]

    if must_include_any and not any(normalized(word) in text for word in must_include_any):
        return 0, ["missing required keyword"]

    if title_include_any and not any(normalized(word) in title_text for word in title_include_any):
        return 0, ["title is outside target roles"]

    score = 10
    if opportunity.reliability >= 85:
        score += 10
        reasons.append("trusted source")
    elif opportunity.reliability >= 70:
        score += 5
        reasons.append("established source")

    matched_skills = [skill for skill in skills if normalized(skill) in text]
    if matched_skills:
        score += min(len(matched_skills) * 14, 56)
        reasons.append(f"skill match: {', '.join(matched_skills[:5])}")

    urgent_matches = [word for word in URGENT_KEYWORDS if word in text]
    if urgent_matches:
        score += 8
        reasons.append("urgent timing")

    quality_matches = [word for word in QUALITY_KEYWORDS if word in text]
    if quality_matches:
        score += 10
        reasons.append(f"good project signal: {quality_matches[0]}")

    if opportunity.budget:
        score += 12
        reasons.append(f"budget signal: {opportunity.budget}")

    if len(opportunity.description) > 180:
        score += 5
        reasons.append("detailed brief")

    if not matched_skills:
        score -= 20
        reasons.append("weak skill match")

    return max(score, 0), reasons


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def is_older_than(value: str, days: int) -> bool:
    if not value:
        return False
    try:
        published = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if published.tzinfo is None:
        published = published.replace(tzinfo=timezone.utc)
    return published < datetime.now(timezone.utc) - timedelta(days=days)
