import os
import re
from pathlib import Path

from telethon.sync import TelegramClient

from apartment_bot.adapters.base import Listing, SourceAdapter

SESSION_PATH = str(Path(__file__).resolve().parent.parent.parent / "telethon_session")

PRICE_RE = re.compile(r"(?:₪\s*(\d[\d,]{2,6}))|(?:(\d[\d,]{2,6})\s*(?:₪|ש\"ח|שח|שקל))")
ROOMS_RE = re.compile(r"(\d(?:\.\d)?)\s*(?:חדרים|חד'|חד\.)")
FLOOR_RE = re.compile(r"קומה\s*(-?\d+)")
SQM_RE = re.compile(r"(\d{2,4})\s*(?:מ\"ר|מ'ר|מטר)")


def _extract_price(text: str) -> int | None:
    m = PRICE_RE.search(text)
    if not m:
        return None
    raw = m.group(1) or m.group(2)
    return int(raw.replace(",", ""))


def _extract_rooms(text: str) -> float | None:
    m = ROOMS_RE.search(text)
    return float(m.group(1)) if m else None


def _extract_floor(text: str) -> int | None:
    m = FLOOR_RE.search(text)
    return int(m.group(1)) if m else None


def _extract_sqm(text: str) -> int | None:
    m = SQM_RE.search(text)
    return int(m.group(1)) if m else None


class TelegramChannelAdapter(SourceAdapter):
    """Reads recent posts from a fixed list of public Telegram channels.

    This is the ONLY place in the codebase that talks to the Telegram user
    API (via Telethon). It only ever calls get_messages() for usernames in
    `self.channels` (from config.yaml) - nothing else, no dialog listing,
    no reading of any other chat. Every access is logged so it's visible
    which channel is being read.
    """

    name = "telegram"

    def __init__(self, channels: list[str], messages_per_channel: int = 30):
        if not channels:
            raise ValueError("TelegramChannelAdapter requires at least one channel username")
        self.channels = list(channels)
        self.messages_per_channel = messages_per_channel

    def fetch_listings(self) -> list[Listing]:
        api_id = int(os.environ["TELEGRAM_API_ID"])
        api_hash = os.environ["TELEGRAM_API_HASH"]

        listings: list[Listing] = []
        with TelegramClient(SESSION_PATH, api_id, api_hash) as client:
            for channel_username in self.channels:
                print(f"[telegram] fetching from @{channel_username} ...")
                messages = client.get_messages(channel_username, limit=self.messages_per_channel)
                for msg in messages:
                    if not msg.text:
                        continue
                    listing = self._message_to_listing(channel_username, msg)
                    listings.append(listing)
        return listings

    @staticmethod
    def _message_to_listing(channel_username: str, msg) -> Listing:
        text = msg.text
        photo_url = None
        if msg.photo:
            # Telegram photos aren't served over plain HTTP URLs; the dashboard/bot
            # would need to fetch bytes via Telethon. Left unset for now - a raw_text
            # link back to the channel post still lets you view the photo yourself.
            photo_url = None

        return Listing(
            source="telegram",
            external_id=f"{channel_username}_{msg.id}",
            url=f"https://t.me/{channel_username}/{msg.id}",
            price=_extract_price(text),
            rooms=_extract_rooms(text),
            floor=_extract_floor(text),
            sqm=_extract_sqm(text),
            address=None,  # free text - filter engine matches cities against raw_text instead
            photo_url=photo_url,
            posted_date=msg.date.isoformat() if msg.date else None,
            raw_text=text,
        )
