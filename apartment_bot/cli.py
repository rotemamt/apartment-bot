import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from apartment_bot.adapters.base import Listing
from apartment_bot.adapters.telegram_source import TelegramChannelAdapter
from apartment_bot.adapters.yad2 import Yad2Adapter
from apartment_bot.filters.engine import load_config, match_listing
from apartment_bot.storage import db
from apartment_bot.telegram import state
from apartment_bot.telegram.notifier import send_listing_alert

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
DB_PATH = ROOT / "listings.db"

load_dotenv(ROOT / ".env")


def process_listings(listings: list[Listing], config: dict, conn, bot_token: str | None, chat_id: str | None, paused: bool) -> int:
    new_matches = 0
    for listing in listings:
        result = match_listing(listing, config)
        is_new = db.upsert_listing(conn, listing, matched_features=result.matched_features, matched=result.matched)
        if is_new:
            tag = "MATCH" if result.matched else f"skip ({result.reason})"
            print(f"[new:{listing.source}] {listing.price} ILS, {listing.rooms} rooms -> {tag}")
            print(f"       {listing.url}")
            if result.matched:
                new_matches += 1
                if bot_token and chat_id and not paused:
                    send_listing_alert(bot_token, chat_id, listing, result.matched_features)
    return new_matches


def scan_yad2(config: dict, conn, bot_token: str | None, chat_id: str | None, paused: bool) -> int:
    known_urls = {row["url"] for row in db.get_listings(conn)}
    search_url = config["sources"]["yad2"]["search_url"]
    adapter = Yad2Adapter(search_url=search_url)
    listings = adapter.fetch_listings(known_urls=known_urls)
    print(f"Fetched {len(listings)} listings from Yad2.")
    return process_listings(listings, config, conn, bot_token, chat_id, paused)


def scan_telegram(config: dict, conn, bot_token: str | None, chat_id: str | None, paused: bool) -> int:
    channels = config.get("telegram", {}).get("channels") or []
    if not channels:
        print("No Telegram channels configured, skipping.")
        return 0
    adapter = TelegramChannelAdapter(channels=channels)
    listings = adapter.fetch_listings()
    print(f"Fetched {len(listings)} messages from Telegram.")
    return process_listings(listings, config, conn, bot_token, chat_id, paused)


def scan_all() -> None:
    config = load_config(str(CONFIG_PATH))
    conn = db.connect(str(DB_PATH))
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = config.get("telegram", {}).get("chat_id")
    paused = state.is_paused()

    total_matches = 0
    total_matches += scan_yad2(config, conn, bot_token, chat_id, paused)
    total_matches += scan_telegram(config, conn, bot_token, chat_id, paused)

    print(f"\n{total_matches} new listing(s) matched your filters across all sources.")


if __name__ == "__main__":
    scan_all()
