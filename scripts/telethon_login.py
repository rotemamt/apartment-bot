"""One-time interactive login for the Telegram userbot (Telethon).

Run this yourself, directly in your own terminal:
    source venv/bin/activate
    python scripts/telethon_login.py

Telegram will text you a login code - type it in when prompted. This only
needs to be done once; it saves a session file (telethon_session.session)
that every future run reuses automatically.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from telethon.sync import TelegramClient

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

api_id = int(os.environ["TELEGRAM_API_ID"])
api_hash = os.environ["TELEGRAM_API_HASH"]
session_path = str(ROOT / "telethon_session")

with TelegramClient(session_path, api_id, api_hash) as client:
    me = client.get_me()
    print(f"Logged in as: {me.first_name} (@{me.username})")
    print(f"Session saved to: {session_path}.session")
