import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import requests
from dotenv import load_dotenv

from apartment_bot.filters.engine import load_config
from apartment_bot.storage import db
from apartment_bot.telegram import state
from apartment_bot.telegram.config_editor import set_filter_value
from apartment_bot.telegram.notifier import send_text

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config.yaml"
DB_PATH = ROOT / "listings.db"

load_dotenv(ROOT / ".env")
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{BOT_TOKEN}"

HELP_TEXT = (
    "פקודות זמינות:\n"
    "/status - כמה התאמות חדשות היום\n"
    "/pause - השהיית התראות\n"
    "/resume - חידוש התראות\n"
    "/filters - הצגת הגדרות הסינון הנוכחיות\n"
    "/setprice <מינימום> <מקסימום> - עדכון טווח מחיר"
)


def get_updates(offset: int | None, timeout: int = 25) -> list:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resp = requests.get(f"{API}/getUpdates", params=params, timeout=timeout + 10)
    resp.raise_for_status()
    return resp.json()["result"]


def _fmt(value) -> str:
    return "ללא הגבלה" if value is None else str(value)


def handle_message(chat_id, text: str, authorized_chat_id: str) -> None:
    if str(chat_id) != str(authorized_chat_id):
        return  # ignore anyone who isn't the configured owner

    parts = text.strip().split()
    cmd = parts[0].lower() if parts else ""

    if cmd == "/pause":
        state.set_paused(True)
        send_text(BOT_TOKEN, chat_id, "⏸️ מושהה. לא יישלחו התראות חדשות עד /resume.")
    elif cmd == "/resume":
        state.set_paused(False)
        send_text(BOT_TOKEN, chat_id, "▶️ פעיל שוב.")
    elif cmd == "/status":
        conn = db.connect(str(DB_PATH))
        count_today = db.count_matched_today(conn)
        paused = "כן ⏸️" if state.is_paused() else "לא ▶️"
        send_text(BOT_TOKEN, chat_id, f"מושהה: {paused}\nהתאמות חדשות היום: {count_today}")
    elif cmd == "/filters":
        f = load_config(str(CONFIG_PATH)).get("filters", {})
        lines = [
            f"מחיר: {_fmt(f.get('price_min'))}-{_fmt(f.get('price_max'))} ₪",
            f"חדרים: {_fmt(f.get('rooms_min'))}-{_fmt(f.get('rooms_max'))}",
            f"קומה: {_fmt(f.get('floor_min'))}-{_fmt(f.get('floor_max'))}",
            f"מ״ר מינ׳: {_fmt(f.get('min_sqm'))}",
            f"ערים: {', '.join(f.get('cities') or [])}",
            f"מילות מפתח נדרשות (הכל): {', '.join(f.get('required_keywords') or []) or '-'}",
            f"מילות מפתח לשלילה (כל אחת מספיקה): {', '.join(f.get('excluded_keywords') or []) or '-'}",
        ]
        send_text(BOT_TOKEN, chat_id, "\n".join(lines))
    elif cmd == "/setprice":
        if len(parts) != 3 or not all(p.isdigit() for p in parts[1:]):
            send_text(BOT_TOKEN, chat_id, "שימוש: /setprice 4000 8000")
            return
        lo, hi = int(parts[1]), int(parts[2])
        set_filter_value(str(CONFIG_PATH), "price_min", lo)
        set_filter_value(str(CONFIG_PATH), "price_max", hi)
        send_text(BOT_TOKEN, chat_id, f"✅ טווח מחיר עודכן: {lo}-{hi} ₪")
    elif cmd in ("/help", "/start"):
        send_text(BOT_TOKEN, chat_id, HELP_TEXT)
    else:
        send_text(BOT_TOKEN, chat_id, "פקודה לא מוכרת. שלח /help")


def main() -> None:
    authorized_chat_id = load_config(str(CONFIG_PATH))["telegram"]["chat_id"]
    offset = None
    print("Bot command listener running. Ctrl+C to stop.")
    while True:
        try:
            updates = get_updates(offset)
        except requests.RequestException as e:
            print("network error:", e)
            time.sleep(5)
            continue
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            text = msg.get("text")
            chat_id = msg.get("chat", {}).get("id")
            if text and chat_id:
                handle_message(chat_id, text, authorized_chat_id)


if __name__ == "__main__":
    main()
