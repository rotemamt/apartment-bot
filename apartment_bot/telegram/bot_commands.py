import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import requests
from dotenv import load_dotenv

from apartment_bot.bootstrap import bootstrap_owner_from_config
from apartment_bot.storage import db
from apartment_bot.telegram import state
from apartment_bot.telegram.notifier import (
    answer_callback_query,
    edit_message,
    send_message_with_web_app_button,
    send_text,
)
from apartment_bot.telegram.onboarding import format_filters

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config.yaml"
DB_PATH = ROOT / "listings.db"

load_dotenv(ROOT / ".env")
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{BOT_TOKEN}"
MINI_APP_URL = os.environ.get("MINI_APP_URL", "https://apartmentbot.duckdns.org")

HELP_TEXT = (
    "פקודות זמינות:\n"
    "/status - כמה התאמות חדשות היום\n"
    "/pause - השהיית התראות\n"
    "/resume - חידוש התראות\n"
    "/filters - הצגת הגדרות הסינון הנוכחיות\n"
    "/setprice מינימום מקסימום - עדכון טווח מחיר (למשל: /setprice 4000 8000)"
)
START_TEXT = "ברוכים הבאים! לחצו כדי להגדיר את הסינון שלכם."
PENDING_TEXT = "הבקשה שלך עדיין ממתינה לאישור מנהל."


def get_updates(offset: int | None, timeout: int = 25) -> list:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resp = requests.get(f"{API}/getUpdates", params=params, timeout=timeout + 10)
    resp.raise_for_status()
    return resp.json()["result"]


def _handle_command(conn, user, cmd: str, parts: list[str]) -> None:
    chat_id = user["telegram_chat_id"]
    if cmd == "/pause":
        db.set_user_paused(conn, user["id"], True)
        send_text(BOT_TOKEN, chat_id, "⏸️ מושהה. לא יישלחו התראות חדשות עד /resume.")
    elif cmd == "/resume":
        db.set_user_paused(conn, user["id"], False)
        send_text(BOT_TOKEN, chat_id, "▶️ פעיל שוב.")
    elif cmd == "/status":
        count_today = db.count_user_matched_today(conn, user["id"])
        paused = "כן ⏸️" if user["paused"] else "לא ▶️"
        send_text(BOT_TOKEN, chat_id, f"מושהה: {paused}\nהתאמות חדשות היום: {count_today}")
    elif cmd == "/filters":
        send_text(BOT_TOKEN, chat_id, format_filters(db.get_user_filters(conn, user["id"])))
    elif cmd == "/setprice":
        if len(parts) != 3 or not all(p.isdigit() for p in parts[1:]):
            send_text(BOT_TOKEN, chat_id, "שימוש: /setprice 4000 8000")
            return
        lo, hi = int(parts[1]), int(parts[2])
        db.update_user_filters(conn, user["id"], {"price_min": lo, "price_max": hi})
        send_text(BOT_TOKEN, chat_id, f"✅ טווח מחיר עודכן: {lo}-{hi} ₪")
    elif cmd in ("/help", "/start"):
        send_text(BOT_TOKEN, chat_id, HELP_TEXT)
    else:
        send_text(BOT_TOKEN, chat_id, "פקודה לא מוכרת. שלח /help")


def handle_message(chat_id, text: str, conn) -> None:
    chat_id = str(chat_id)
    text = (text or "").strip()
    cmd = text.split()[0].lower() if text else ""
    user = db.get_user_by_chat_id(conn, chat_id)

    if user is None:
        if cmd in ("/start", "/help"):
            db.create_user(conn, chat_id, status="onboarding")
            send_message_with_web_app_button(BOT_TOKEN, chat_id, START_TEXT, "בוא נתחיל 🐾", MINI_APP_URL)
        return

    # All filter/city/etc. collection now happens in the Mini App wizard
    # (POST /api/onboarding), not via chat - a lingering "onboarding" status
    # here just means they haven't finished/submitted the wizard yet.
    if user["status"] in ("onboarding", "pending_approval"):
        if cmd in ("/start", "/help"):
            send_message_with_web_app_button(BOT_TOKEN, chat_id, START_TEXT, "המשך הרשמה 🐾", MINI_APP_URL)
        elif user["status"] == "pending_approval":
            send_text(BOT_TOKEN, chat_id, PENDING_TEXT)
        return
    if user["status"] == "blocked":
        return  # silently ignore

    _handle_command(conn, user, cmd, text.split())


def _handle_callback_query(conn, callback_query: dict) -> None:
    query_id = callback_query["id"]
    data = callback_query.get("data", "")
    from_chat_id = str(callback_query["from"]["id"])
    message = callback_query.get("message") or {}
    origin_chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    admin = db.get_user_by_chat_id(conn, from_chat_id)
    if not admin or not admin["is_admin"]:
        answer_callback_query(BOT_TOKEN, query_id, "אין הרשאה.")
        return

    action, _, target_id_str = data.partition(":")
    if action not in ("approve", "deny") or not target_id_str.isdigit():
        answer_callback_query(BOT_TOKEN, query_id)
        return

    target = db.get_user_by_id(conn, int(target_id_str))
    if target is None:
        answer_callback_query(BOT_TOKEN, query_id, "המשתמש לא נמצא.")
        return

    if action == "approve":
        db.set_user_status(conn, target["id"], "approved")
        answer_callback_query(BOT_TOKEN, query_id, "אושר")
        if origin_chat_id and message_id:
            edit_message(BOT_TOKEN, origin_chat_id, message_id, f"✅ אושר: {target['telegram_chat_id']}")
        send_text(BOT_TOKEN, target["telegram_chat_id"], "✅ אושרת! תתחיל לקבל התראות. שלח /help לרשימת הפקודות.")
    else:
        db.set_user_status(conn, target["id"], "blocked")
        answer_callback_query(BOT_TOKEN, query_id, "נדחה")
        if origin_chat_id and message_id:
            edit_message(BOT_TOKEN, origin_chat_id, message_id, f"❌ נדחה: {target['telegram_chat_id']}")
        send_text(BOT_TOKEN, target["telegram_chat_id"], "בקשתך נדחתה על ידי המנהל.")


def main() -> None:
    conn = db.connect(str(DB_PATH))
    bootstrap_owner_from_config(conn, str(CONFIG_PATH), state_paused=state.is_paused())
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
            try:
                if "callback_query" in update:
                    _handle_callback_query(conn, update["callback_query"])
                else:
                    msg = update.get("message", {})
                    text = msg.get("text")
                    chat_id = msg.get("chat", {}).get("id")
                    if text and chat_id:
                        handle_message(chat_id, text, conn)
            except Exception as e:
                # A bad update must never crash the whole listener - a crash
                # here means the offset update above never reaches Telegram,
                # so the same update gets redelivered forever on restart.
                print("error handling update, skipping:", e)


if __name__ == "__main__":
    main()
