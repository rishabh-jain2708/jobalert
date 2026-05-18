from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def project_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return ROOT / path


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def load_settings() -> dict[str, Any]:
    configured = os.getenv("FREELANCE_BOT_SETTINGS", "config/settings.json")
    settings = load_json(project_path(configured))
    settings["database_path"] = str(project_path(settings["database_path"]))
    settings["report_path"] = str(project_path(settings["report_path"]))
    return settings


def load_sources(path: str = "config/sources.json") -> list[dict[str, Any]]:
    return load_json(project_path(path))

