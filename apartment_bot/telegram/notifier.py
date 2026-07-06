import json
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


def send_message_with_buttons(bot_token: str, chat_id: str, text: str, buttons: list[list[dict]]) -> int:
    """Send a message with an inline keyboard. Returns the sent message_id
    (needed later to edit the message once a button is tapped)."""
    url = API_BASE.format(token=bot_token, method="sendMessage")
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps({"inline_keyboard": buttons}),
    }
    resp = requests.post(url, data=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()["result"]["message_id"]


def send_message_with_web_app_button(bot_token: str, chat_id: str, text: str, button_text: str, url: str) -> None:
    """Send a message with a single button that opens the Mini App directly
    (Telegram's `web_app` inline button type, distinct from a plain URL
    button - it opens inside Telegram rather than an external browser)."""
    api_url = API_BASE.format(token=bot_token, method="sendMessage")
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.dumps({"inline_keyboard": [[{"text": button_text, "web_app": {"url": url}}]]}),
    }
    resp = requests.post(api_url, data=payload, timeout=15)
    resp.raise_for_status()


def answer_callback_query(bot_token: str, callback_query_id: str, text: str = "") -> None:
    url = API_BASE.format(token=bot_token, method="answerCallbackQuery")
    resp = requests.post(url, data={"callback_query_id": callback_query_id, "text": text}, timeout=15)
    resp.raise_for_status()


def edit_message(bot_token: str, chat_id: str, message_id: int, text: str) -> None:
    """Replace a message's text and drop its inline keyboard (used after
    an admin taps Approve/Deny, so the buttons can't be tapped twice)."""
    url = API_BASE.format(token=bot_token, method="editMessageText")
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "HTML"}
    resp = requests.post(url, data=payload, timeout=15)
    resp.raise_for_status()
