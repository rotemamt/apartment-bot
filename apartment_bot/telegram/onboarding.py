import json

from apartment_bot.storage import db
from apartment_bot.telegram.notifier import send_message_with_buttons


def format_value(value) -> str:
    return "ללא הגבלה" if value is None else str(value)


def format_filters(f: dict) -> str:
    lines = [
        f"מחיר: {format_value(f.get('price_min'))}-{format_value(f.get('price_max'))} ₪",
        f"חדרים: {format_value(f.get('rooms_min'))}-{format_value(f.get('rooms_max'))}",
        f"קומה: {format_value(f.get('floor_min'))}-{format_value(f.get('floor_max'))}",
        f"מ״ר מינ׳: {format_value(f.get('min_sqm'))}",
        f"ערים: {', '.join(f.get('cities') or [])}",
        f"שכונות: {', '.join(f.get('neighborhoods') or []) or '-'}",
        f"מילות מפתח נדרשות (הכל): {', '.join(f.get('required_keywords') or []) or '-'}",
        f"מילות מפתח לשלילה (כל אחת מספיקה): {', '.join(f.get('excluded_keywords') or []) or '-'}",
    ]
    return "\n".join(lines)


def notify_admins_of_pending_request(bot_token: str, conn, user_id: int) -> None:
    user = db.get_user_by_id(conn, user_id)
    filters = json.loads(user["filters"])
    text = (
        f"בקשת הצטרפות חדשה מ-{user['telegram_username'] or user['telegram_chat_id']}"
        f" (chat_id {user['telegram_chat_id']}):\n\n{format_filters(filters)}"
    )
    buttons = [[
        {"text": "✅ אשר", "callback_data": f"approve:{user_id}"},
        {"text": "❌ דחה", "callback_data": f"deny:{user_id}"},
    ]]
    for admin in db.get_admins(conn):
        send_message_with_buttons(bot_token, admin["telegram_chat_id"], text, buttons)
