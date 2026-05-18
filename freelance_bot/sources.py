from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from typing import Any, Iterable

from .models import Opportunity

USER_AGENT = "freelance-opportunity-bot/0.1 (+https://github.com/)"
TAG_RE = re.compile(r"<[^>]+>")
MONEY_PATTERN = (
    r"(?:\$|usd\s*)\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?[kKmM])?"
    r"(?:\s?-\s?(?:\$|usd\s*)?\d[\d,]*(?:\.\d{1,2})?(?:\s?[kKmM])?)?"
    r"(?:\s?(?:usd|/hr|per hour|hourly|per year|yearly|annually))?"
)
BUDGET_RE = re.compile(
    rf"(?i)\b(?:budget|salary|compensation|comp|pay|rate|hourly|fixed price|fixed-price)\b"
    rf".{{0,80}}?({MONEY_PATTERN})|"
    rf"({MONEY_PATTERN}).{{0,45}}?\b(?:salary|compensation|budget|fixed price|fixed-price|/hr|per hour|hourly|per year|yearly|annually)\b"
)


class SourceError(RuntimeError):
    pass


def fetch_all(source_configs: list[dict[str, Any]]) -> tuple[list[Opportunity], list[str]]:
    opportunities: list[Opportunity] = []
    errors: list[str] = []

    for source in source_configs:
        try:
            opportunities.extend(fetch_source(source))
        except SourceError as exc:
            errors.append(str(exc))

    return opportunities, errors


def fetch_source(source: dict[str, Any]) -> list[Opportunity]:
    source_type = source.get("type")
    body = fetch_url(source["url"])

    if source_type == "rss":
        return parse_rss(source, body)
    if source_type == "json":
        payload = json.loads(body)
        return parse_json(source, payload)

    raise SourceError(f"{source.get('name', 'Unknown source')}: unsupported type {source_type!r}")


def fetch_url(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            return response.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        raise SourceError(f"{url}: {exc}") from exc


def parse_rss(source: dict[str, Any], body: str) -> list[Opportunity]:
    source_name = source["name"]
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        raise SourceError(f"{source_name}: invalid RSS/Atom feed") from exc

    entries = list(root.findall(".//item"))
    if not entries:
        entries = list(root.findall(".//{http://www.w3.org/2005/Atom}entry"))

    opportunities = []
    for entry in entries:
        title = first_text(entry, ["title", "{http://www.w3.org/2005/Atom}title"])
        url = first_text(entry, ["link"])
        if not url:
            link = entry.find("{http://www.w3.org/2005/Atom}link")
            url = link.attrib.get("href", "") if link is not None else ""
        description = first_text(
            entry,
            [
                "description",
                "summary",
                "content",
                "{http://www.w3.org/2005/Atom}summary",
                "{http://www.w3.org/2005/Atom}content",
            ],
        )
        published_at = first_text(
            entry,
            ["pubDate", "published", "updated", "{http://www.w3.org/2005/Atom}updated"],
        )
        if title and url:
            clean_description = clean_html(description)
            opportunities.append(
                Opportunity(
                    source=source_name,
                    title=html.unescape(title).strip(),
                    url=url.strip(),
                    description=clean_description,
                    published_at=normalize_date(published_at),
                    budget=extract_budget(f"{title} {clean_description}"),
                    source_url=source.get("source_url", source["url"]),
                    reliability=int(source.get("reliability", 50)),
                )
            )
    return opportunities


def parse_json(source: dict[str, Any], payload: Any) -> list[Opportunity]:
    items = resolve_items(payload, source.get("items_path", "$"))
    field_map = source.get("field_map", {})
    opportunities = []

    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(value_at(item, field_map.get("title", "title")) or "").strip()
        url = str(value_at(item, field_map.get("url", "url")) or "").strip()
        description = clean_html(str(value_at(item, field_map.get("description", "description")) or ""))
        published_at = str(value_at(item, field_map.get("published_at", "published_at")) or "")
        configured_budget = str(value_at(item, field_map.get("budget", "")) or "").strip()
        if title and url:
            budget = configured_budget or extract_budget(f"{title} {description}")
            opportunities.append(
                Opportunity(
                    source=source["name"],
                    title=title,
                    url=url,
                    description=description,
                    published_at=normalize_date(published_at),
                    budget=budget,
                    source_url=source.get("source_url", source["url"]),
                    reliability=int(source.get("reliability", 50)),
                    raw=item,
                )
            )
    return opportunities


def first_text(entry: ET.Element, names: Iterable[str]) -> str:
    for name in names:
        child = entry.find(name)
        if child is not None and child.text:
            return child.text
    return ""


def clean_html(value: str) -> str:
    no_tags = TAG_RE.sub(" ", html.unescape(value))
    return re.sub(r"\s+", " ", no_tags).strip()


def normalize_date(value: str) -> str:
    if not value:
        return ""
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError):
        return value.strip()


def extract_budget(text: str) -> str:
    match = BUDGET_RE.search(text)
    if not match:
        return ""
    return next(group.strip() for group in match.groups() if group)


def resolve_items(payload: Any, path: str) -> list[Any]:
    if path in ("", "$"):
        return payload if isinstance(payload, list) else []

    current = payload
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part, [])
        else:
            return []
    return current if isinstance(current, list) else []


def value_at(item: dict[str, Any], path: str) -> Any:
    current: Any = item
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current
