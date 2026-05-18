# Freelance Opportunity Bot

This bot watches public feeds for freelance/project opportunities, filters them against your skills, scores the best matches, deduplicates old posts, and sends a daily/recurring report.

It is designed to run locally or on GitHub Actions. The default sources use public RSS feeds so the MVP avoids brittle scraping and login-gated platform automation.

## Features

- Fetch opportunities from multiple public feeds
- Score posts by skills, budget hints, urgency, and red flags
- Prefer trusted public sources with reliability scores
- Filter scam-prone posts and stale listings
- Store seen posts in SQLite to avoid duplicate alerts
- Generate `data/latest_report.md`
- Optional Telegram alerts
- Optional generic webhook alerts
- GitHub Actions schedule included

## Quick Start

```bash
python3 -m freelance_bot.main --dry-run
python3 -m freelance_bot.main
```

The first command previews matching opportunities without writing to the database. The second command saves new matches and sends notifications if secrets are configured.

Run the built-in tests with:

```bash
python3 -m unittest discover -s tests
```

## Configure Your Skills

Edit [config/settings.json](config/settings.json):

```json
{
  "skills": ["react", "next.js", "wordpress", "shopify", "automation"],
  "blocked_keywords": ["unpaid", "equity only"],
  "scam_keywords": ["application fee", "gift card", "telegram only"],
  "minimum_source_reliability": 55,
  "max_age_days": 45,
  "minimum_score": 35
}
```

Edit [config/sources.json](config/sources.json) to add more RSS or JSON feeds.
Each source can include a `reliability` score from 0-100. Official/public job-board APIs and RSS feeds should score higher; open community feeds should score lower unless you have a reason to trust them.

## Telegram Setup

1. Create a Telegram bot using `@BotFather`.
2. Send one message to your bot.
3. Get your chat id using:

```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates"
```

4. In GitHub repo settings, add these secrets:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## GitHub Hosting

This repo includes [.github/workflows/freelance-bot.yml](.github/workflows/freelance-bot.yml).

After pushing to GitHub:

1. Go to your repository on GitHub.
2. Open `Settings > Secrets and variables > Actions`.
3. Add Telegram secrets if you want alerts.
4. Enable Actions if GitHub asks.

The workflow runs every 3 hours and also supports manual runs from the Actions tab.

## Important Notes

- Some freelance platforms restrict scraping. Prefer official APIs, RSS feeds, email alerts, or public pages allowed by their terms.
- Upwork, Fiverr, LinkedIn, Indeed, and similar login-heavy platforms should be added through official APIs, email alert ingestion, or manual exports instead of browser scraping.
- Login-based automation can be added later, but it should be platform-specific and respectful of rate limits.
- For Upwork/Fiverr/Freelancer-style platforms, a safer next step is ingesting their email alerts or official APIs where available.
- The default filters block `[For Hire]` posts so you mainly see client-side opportunities, not other freelancers advertising themselves.
