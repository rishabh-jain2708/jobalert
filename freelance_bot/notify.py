from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from .models import Opportunity


def notify(opportunities: list[Opportunity], report: str) -> list[str]:
    results = []
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        results.append(safe_send("telegram", send_telegram, opportunities))
    if os.getenv("WEBHOOK_URL"):
        results.append(safe_send("webhook", send_webhook, report))
    return results


def safe_send(name: str, sender, payload) -> str:
    try:
        return sender(payload)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError) as exc:
        return f"{name} failed: {describe_notification_error(name, exc)}"


def describe_notification_error(name: str, exc: BaseException) -> str:
    if name == "telegram" and isinstance(exc, urllib.error.HTTPError):
        if exc.code == 404:
            return "Telegram API returned 404. Check TELEGRAM_BOT_TOKEN in GitHub Actions secrets."
        if exc.code == 400:
            return "Telegram API returned 400. Check TELEGRAM_CHAT_ID and make sure you messaged the bot once."
        return f"Telegram API returned HTTP {exc.code}: {exc.reason}"
    return str(exc)


def send_telegram(opportunities: list[Opportunity]) -> str:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    text = telegram_message(opportunities)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()
    return "telegram sent"


def send_webhook(report: str) -> str:
    payload = json.dumps({"text": report[:3500]}).encode("utf-8")
    request = urllib.request.Request(
        os.environ["WEBHOOK_URL"],
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()
    return "webhook sent"


def telegram_message(opportunities: list[Opportunity]) -> str:
    if not opportunities:
        return "No new matching freelance opportunities found."

    lines = ["New freelance opportunities:"]
    for item in opportunities[:10]:
        reasons = ", ".join(item.reasons[:2]) if item.reasons else "matched filters"
        lines.extend(
            [
                "",
                f"{item.title}",
                f"Score: {item.score} | {item.source}",
                f"Why: {reasons}",
                item.url,
            ]
        )
    return "\n".join(lines)
