from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Opportunity:
    source: str
    title: str
    url: str
    description: str = ""
    published_at: str = ""
    budget: str = ""
    source_url: str = ""
    reliability: int = 50
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
