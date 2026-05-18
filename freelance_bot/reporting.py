from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .models import Opportunity


def build_report(opportunities: list[Opportunity], errors: list[str] | None = None) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Freelance Opportunities", "", f"Generated: {timestamp}", ""]

    if not opportunities:
        lines.extend(["No new matching opportunities found.", ""])
    else:
        for index, item in enumerate(opportunities, start=1):
            lines.extend(
                [
                    f"## {index}. {item.title}",
                    "",
                    f"- Source: {item.source}",
                    f"- Reliability: {item.reliability}/100",
                    f"- Score: {item.score}",
                    f"- Budget: {item.budget or 'Not specified'}",
                    f"- Location: {item.location or 'See listing'}",
                    f"- Published: {item.published_at or 'Unknown'}",
                    f"- Link: {item.url}",
                    f"- Why: {', '.join(item.reasons) if item.reasons else 'Matched filters'}",
                    "",
                ]
            )
            if item.description:
                lines.extend([trim(item.description, 450), ""])

    if errors:
        lines.extend(["## Source Errors", ""])
        lines.extend(f"- {error}" for error in errors)
        lines.append("")

    return "\n".join(lines)


def write_report(report_path: str, content: str) -> None:
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def trim(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."
