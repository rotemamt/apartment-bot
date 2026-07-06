import json
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
    send_message_with_buttons,
    send_text,
)

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
    "/setprice מינימום מקסימום - עדכון טווח מחיר (למשל: /setprice 4000 8000)"
)

# Onboarding wizard: one question per step, driven by users.onboarding_step.
ONBOARDING_STEPS = ["city", "price", "rooms", "keywords"]
SKIP_WORDS = {"skip", "דלג", "-"}
STEP_PROMPTS = {
    "city": "באיזו עיר תרצה לחפש דירה? (למשל: תל אביב). אפשר לכתוב 'דלג' כדי לא להגביל.",
    "price": "מה טווח המחיר הרצוי בש\"ח? (למשל: 4000 8000). אפשר לכתוב 'דלג'.",
    "rooms": "כמה חדרים? טווח מינימום-מקסימום (למשל: 2 4). אפשר לכתוב 'דלג'.",
    "keywords": "מילות מפתח נדרשות, מופרדות בפסיק (למשל: ממ\"ד). אפשר לכתוב 'דלג'.",
}
WELCOME_TEXT = "ברוכים הבאים! בוא נגדיר את הסינון שלך לפני שהבקשה תישלח לאישור.\n\n"


def get_updates(offset: int | None, timeout: int = 25) -> list:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resp = requests.get(f"{API}/getUpdates", params=params, timeout=timeout + 10)
    resp.raise_for_status()
    return resp.json()["result"]


def _fmt(value) -> str:
    return "ללא הגבלה" if value is None else str(value)


def _fmt_filters(f: dict) -> str:
    lines = [
        f"מחיר: {_fmt(f.get('price_min'))}-{_fmt(f.get('price_max'))} ₪",
        f"חדרים: {_fmt(f.get('rooms_min'))}-{_fmt(f.get('rooms_max'))}",
        f"קומה: {_fmt(f.get('floor_min'))}-{_fmt(f.get('floor_max'))}",
        f"מ״ר מינ׳: {_fmt(f.get('min_sqm'))}",
        f"ערים: {', '.join(f.get('cities') or [])}",
        f"מילות מפתח נדרשות (הכל): {', '.join(f.get('required_keywords') or []) or '-'}",
        f"מילות מפתח לשלילה (כל אחת מספיקה): {', '.join(f.get('excluded_keywords') or []) or '-'}",
    ]
    return "\n".join(lines)


def _parse_onboarding_answer(step: str, text: str) -> dict | None:
    """Returns a filters-dict patch, {} for an explicit skip, or None if the
    input couldn't be parsed (caller should re-prompt)."""
    text = text.strip()
    if text.lower() in SKIP_WORDS:
        return {}

    if step == "city":
        cities = [c.strip() for c in text.split(",") if c.strip()]
        return {"cities": cities} if cities else None

    if step == "price":
        parts = text.split()
        if len(parts) == 2 and all(p.isdigit() for p in parts):
            return {"price_min": int(parts[0]), "price_max": int(parts[1])}
        return None

    if step == "rooms":
        parts = text.split()
        try:
            return {"rooms_min": float(parts[0]), "rooms_max": float(parts[1])}
        except (ValueError, IndexError):
            return None

    if step == "keywords":
        kws = [k.strip() for k in text.split(",") if k.strip()]
        return {"required_keywords": kws} if kws else None

    return {}


def _handle_onboarding_step(conn, user, text: str) -> None:
    step = user["onboarding_step"]
    chat_id = user["telegram_chat_id"]
    parsed = _parse_onboarding_answer(step, text)
    if parsed is None:
        send_text(BOT_TOKEN, chat_id, "לא הבנתי, נסה שוב.\n\n" + STEP_PROMPTS[step])
        return

    idx = ONBOARDING_STEPS.index(step)
    next_step = ONBOARDING_STEPS[idx + 1] if idx + 1 < len(ONBOARDING_STEPS) else None
    db.update_user_onboarding_step(conn, user["id"], next_step, filters_patch=parsed)

    if next_step:
        send_text(BOT_TOKEN, chat_id, STEP_PROMPTS[next_step])
    else:
        db.complete_onboarding(conn, user["id"])
        send_text(BOT_TOKEN, chat_id, "תודה! הבקשה שלך נשלחה למנהל לאישור.")
        _notify_admins_of_pending_request(conn, user["id"])


def _notify_admins_of_pending_request(conn, user_id: int) -> None:
    user = db.get_user_by_id(conn, user_id)
    filters = json.loads(user["filters"])
    text = (
        f"בקשת הצטרפות חדשה מ-{user['telegram_username'] or user['telegram_chat_id']}"
        f" (chat_id {user['telegram_chat_id']}):\n\n{_fmt_filters(filters)}"
    )
    buttons = [[
        {"text": "✅ אשר", "callback_data": f"approve:{user_id}"},
        {"text": "❌ דחה", "callback_data": f"deny:{user_id}"},
    ]]
    for admin in db.get_admins(conn):
        send_message_with_buttons(BOT_TOKEN, admin["telegram_chat_id"], text, buttons)


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
        send_text(BOT_TOKEN, chat_id, _fmt_filters(db.get_user_filters(conn, user["id"])))
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
            db.create_user(conn, chat_id, status="onboarding", onboarding_step=ONBOARDING_STEPS[0])
            send_text(BOT_TOKEN, chat_id, WELCOME_TEXT + STEP_PROMPTS[ONBOARDING_STEPS[0]])
        return

    if user["status"] == "onboarding":
        _handle_onboarding_step(conn, user, text)
        return
    if user["status"] == "pending_approval":
        send_text(BOT_TOKEN, chat_id, "הבקשה שלך עדיין ממתינה לאישור מנהל.")
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
