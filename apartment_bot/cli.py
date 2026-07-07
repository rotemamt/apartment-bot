import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

import json

from apartment_bot.adapters.base import Listing
from apartment_bot.adapters.telegram_source import TelegramChannelAdapter
from apartment_bot.adapters.yad2 import Yad2Adapter
from apartment_bot.bootstrap import bootstrap_owner_from_config
from apartment_bot.filters.engine import load_config, match_listing
from apartment_bot.storage import db
from apartment_bot.telegram import state
from apartment_bot.telegram.notifier import send_listing_alert

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
DB_PATH = ROOT / "listings.db"

load_dotenv(ROOT / ".env")


def process_listings(listings: list[Listing], conn, users: list, bot_token: str | None) -> int:
    """Cache each listing once globally, then evaluate it against every
    approved user's own filters independently."""
    new_matches = 0
    for listing in listings:
        is_new_globally = db.upsert_listing(conn, listing)
        row = conn.execute("SELECT id FROM listings WHERE url = ?", (listing.url,)).fetchone()
        listing_id = row["id"]

        if is_new_globally:
            print(f"[new:{listing.source}] {listing.price} ILS, {listing.rooms} rooms")
            print(f"       {listing.url}")

        for user in users:
            user_filters = {"filters": json.loads(user["filters"])}
            result = match_listing(listing, user_filters)
            is_new_for_user = db.upsert_user_listing(
                conn, user["id"], listing_id, result.matched, result.matched_features, result.preferred_features
            )
            if is_new_for_user and result.matched and bot_token:
                if not db.get_user_listing_alert_sent(conn, user["id"], listing_id):
                    send_listing_alert(
                        bot_token, user["telegram_chat_id"], listing,
                        result.matched_features, result.preferred_features,
                    )
                    db.mark_alert_sent(conn, user["id"], listing_id)
                    new_matches += 1
    return new_matches


def scan_yad2(config: dict, conn, users: list, bot_token: str | None) -> int:
    known_urls = {row["url"] for row in db.get_listings(conn)}
    search_url = config["sources"]["yad2"]["search_url"]
    adapter = Yad2Adapter(search_url=search_url)
    listings = adapter.fetch_listings(known_urls=known_urls)
    print(f"Fetched {len(listings)} listings from Yad2.")
    return process_listings(listings, conn, users, bot_token)


def scan_telegram(config: dict, conn, users: list, bot_token: str | None) -> int:
    channels = config.get("telegram", {}).get("channels") or []
    if not channels:
        print("No Telegram channels configured, skipping.")
        return 0
    adapter = TelegramChannelAdapter(channels=channels)
    listings = adapter.fetch_listings()
    print(f"Fetched {len(listings)} messages from Telegram.")
    return process_listings(listings, conn, users, bot_token)


def scan_all() -> None:
    config = load_config(str(CONFIG_PATH))
    conn = db.connect(str(DB_PATH))
    bootstrap_owner_from_config(conn, str(CONFIG_PATH), state_paused=state.is_paused())
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    users = db.get_active_users(conn)

    total_matches = 0
    total_matches += scan_yad2(config, conn, users, bot_token)
    total_matches += scan_telegram(config, conn, users, bot_token)

    print(f"\n{total_matches} new listing(s) matched across all users and sources.")


if __name__ == "__main__":
    scan_all()
