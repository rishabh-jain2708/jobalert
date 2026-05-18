from __future__ import annotations

import argparse

from .config import load_settings, load_sources
from .notify import notify
from .reporting import build_report, write_report
from .scoring import score_opportunities
from .sources import fetch_all
from .storage import init_db, save_new


def main() -> int:
    parser = argparse.ArgumentParser(description="Find and rank freelance opportunities.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to the database or send alerts.")
    parser.add_argument("--sources", default="config/sources.json", help="Path to source config JSON.")
    parser.add_argument("--min-score", type=int, default=None, help="Override minimum score.")
    args = parser.parse_args()

    settings = load_settings()
    sources = load_sources(args.sources)
    minimum_score = args.min_score if args.min_score is not None else int(settings["minimum_score"])

    fetched, errors = fetch_all(sources)
    scored = score_opportunities(
        fetched,
        skills=settings["skills"],
        blocked_keywords=settings["blocked_keywords"],
        must_include_any=settings.get("must_include_any", []),
        title_include_any=settings.get("title_include_any", []),
        scam_keywords=settings.get("scam_keywords", []),
        minimum_source_reliability=int(settings.get("minimum_source_reliability", 0)),
        max_age_days=settings.get("max_age_days"),
    )
    matches = [item for item in scored if item.score >= minimum_score]
    matches = matches[: int(settings.get("max_results_per_run", 15))]

    if args.dry_run:
        report_items = matches
    else:
        connection = init_db(settings["database_path"])
        report_items = save_new(connection, matches)
        connection.close()

    report = build_report(report_items, errors)
    write_report(settings["report_path"], report)

    if not args.dry_run:
        notify(report_items, report)

    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
