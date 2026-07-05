from datetime import datetime
from html import escape

import requests

from apartment_bot.adapters.base import Listing

API_BASE = "https://api.telegram.org/bot{token}/{method}"
SOURCE_LABELS = {"yad2": "Yad2", "telegram": "Telegram"}


def _format_posted_date(posted_date: str | None) -> str | None:
    if not posted_date:
        return None
    try:
        return datetime.fromisoformat(posted_date).strftime("%d.%m.%Y")
    except ValueError:
        return posted_date


def format_caption(listing: Listing, matched_features: list[str]) -> str:
    rooms = f"{listing.rooms:g}" if listing.rooms is not None else "?"
    lines = [
        f"🏠 <b>{listing.price:,} ₪</b> | {rooms} חדרים",
        f"📍 {escape(listing.address or 'כתובת לא ידועה')}",
        f"🔖 {SOURCE_LABELS.get(listing.source, listing.source)}",
    ]
    posted = _format_posted_date(listing.posted_date)
    if posted:
        lines.append(f"📅 פורסם: {posted}")
    if matched_features:
        lines.append("✅ " + ", ".join(escape(f) for f in matched_features))
    lines.append(f'<a href="{escape(listing.url)}">לצפייה במודעה</a>')
    return "\n".join(lines)


def send_listing_alert(bot_token: str, chat_id: str, listing: Listing, matched_features: list[str]) -> None:
    caption = format_caption(listing, matched_features)
    if listing.photo_url:
        url = API_BASE.format(token=bot_token, method="sendPhoto")
        payload = {"chat_id": chat_id, "photo": listing.photo_url, "caption": caption, "parse_mode": "HTML"}
    else:
        url = API_BASE.format(token=bot_token, method="sendMessage")
        payload = {"chat_id": chat_id, "text": caption, "parse_mode": "HTML"}
    resp = requests.post(url, data=payload, timeout=15)
    resp.raise_for_status()


def send_text(bot_token: str, chat_id: str, text: str) -> None:
    url = API_BASE.format(token=bot_token, method="sendMessage")
    resp = requests.post(url, data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=15)
    resp.raise_for_status()
