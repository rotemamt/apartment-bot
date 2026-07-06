from apartment_bot.filters.engine import load_config
from apartment_bot.storage import db


def bootstrap_owner_from_config(conn, config_path: str, state_paused: bool = False) -> None:
    """Turn the pre-multi-user config.yaml owner into the first admin user row.

    No-op once any user row exists. config.yaml itself is left untouched on
    disk (kept as a backup/reference) - only its values are copied in.
    """
    if db.get_any_user(conn) is not None:
        return

    config = load_config(config_path)
    chat_id = config.get("telegram", {}).get("chat_id")
    if not chat_id:
        return

    user_id = db.create_user(
        conn,
        telegram_chat_id=chat_id,
        status="approved",
        is_admin=True,
        filters=config.get("filters", {}),
    )
    if state_paused:
        db.set_user_paused(conn, user_id, True)
