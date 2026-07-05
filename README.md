# Apartment Bot

Monitors Yad2 and Telegram channels for new rental listings in Israel, filters
them against your criteria, sends you Telegram alerts, and gives you a web
dashboard to browse/triage matches.

## How it works

- **Yad2 adapter** (`apartment_bot/adapters/yad2.py`) - Yad2 sits behind
  Radware bot-detection that blocks plain HTTP requests and even normal
  browser automation (Playwright/Selenium, headless or headed). It's fetched
  using [`nodriver`](https://github.com/ultrafunkamsterdam/nodriver), which
  avoids the Chrome DevTools automation signatures that get detected - but it
  **must run headed** (a real, visible Chrome window; headless mode trips a
  separate, stricter check). On a server with no screen, `scripts/entrypoint_headed.sh`
  starts a virtual display (Xvfb) so this still works unattended.
- **Telegram channel adapter** (`apartment_bot/adapters/telegram_source.py`) -
  uses [Telethon](https://docs.telethon.dev) logged in as your own Telegram
  account (not a bot) to read public channels, since a bot can only read
  channels/groups it's explicitly added to.
- **Filter engine** (`apartment_bot/filters/engine.py`) - matches each
  listing against `config.yaml` (price, rooms, floor, sqm, city, required/
  excluded keywords).
- **Storage** - SQLite (`listings.db`), deduplicated by URL.
- **Telegram bot** (`apartment_bot/telegram/`) - sends alerts on new matches;
  responds to `/pause`, `/resume`, `/status`, `/filters`, `/setprice <min> <max>`.
- **Dashboard** - FastAPI backend (`apartment_bot/dashboard/api.py`) + React
  frontend (`frontend/`): card view, filters/sort, status triage
  (new/seen/interested/rejected), settings page, map view.

## First-run setup

### 1. Python environment

```
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m nodriver install   # not required - nodriver drives a real Chrome you already have
```

You need an actual Chrome or Chromium browser installed on the machine (nodriver
doesn't bundle one, unlike Playwright). On macOS, Google Chrome or Chromium works.
On Linux servers, `sudo apt install chromium xvfb`.

### 2. `.env` file

Create `/Apartment-bot/.env`:

```
TELEGRAM_BOT_TOKEN=            # from @BotFather, see step 3
TELEGRAM_API_ID=               # from https://my.telegram.org, see step 4
TELEGRAM_API_HASH=
```

(`SCRAPER_API_KEY` was used during an earlier abandoned approach and isn't
needed - remove it if present.)

### 3. Telegram bot (for alerts + commands)

1. Message **@BotFather** on Telegram, send `/newbot`, follow the prompts.
2. Put the token it gives you into `.env` as `TELEGRAM_BOT_TOKEN`.
3. Send your new bot any message (e.g. "hi") so it has a chat to reply to.
4. Find your chat ID:
   ```
   python3 -c "
   import os, requests
   from dotenv import load_dotenv
   load_dotenv()
   token = os.environ['TELEGRAM_BOT_TOKEN']
   print(requests.get(f'https://api.telegram.org/bot{token}/getUpdates').json())
   "
   ```
   Look for `"chat":{"id": ...}` in the output.
5. Put that id into `config.yaml` under `telegram.chat_id`.

### 4. Telegram channel monitoring (Telethon userbot)

**Important**: this logs in as your actual Telegram account (not a scoped bot
token) - see the security note below before proceeding.

1. Go to https://my.telegram.org, log in with your phone number.
2. "API development tools" → create an app (any name, platform "Desktop") →
   copy the `api_id` and `api_hash` into `.env`.
3. Run the one-time interactive login **yourself**, directly in your terminal
   (it'll text you a login code you need to type in):
   ```
   python scripts/telethon_login.py
   ```
   This saves `telethon_session.session`, reused by every future run - you
   only do this once.

**Security note:** Telethon's session has the same access as your Telegram
account itself (all chats, not just public channels) - that's inherent to
how Telegram's user-account API works, not something this code restricts.
`apartment_bot/adapters/telegram_source.py` is the *only* place in the
codebase that touches this session, and it only calls `get_messages()` for
the channel usernames listed in `config.yaml`. You can revoke access anytime
via Telegram → Settings → Devices.

### 5. Configure your search

Edit `config.yaml`: price/room/floor/sqm ranges, cities, required/excluded
keywords, and the list of Telegram channels to monitor (usernames without
`@`, e.g. `"jeremy_public"`). All of this is also editable later via the
dashboard settings page or the bot's `/setprice` command.

## Running locally (no Docker)

Three independent processes:

```
# 1. One-off scan (or loop it yourself)
python -m apartment_bot.cli

# 2. Keeps re-scanning forever on the configured interval
python scripts/run_scheduler.py

# 3. Bot command listener (/pause /resume /status /filters /setprice)
python -m apartment_bot.telegram.bot_commands

# 4. Dashboard backend
uvicorn apartment_bot.dashboard.api:app --port 8000

# 5. Dashboard frontend (separate terminal)
cd frontend && npm install && npm run dev
```

## Running with Docker

```
touch listings.db bot_state.json   # Docker creates directories, not files, for missing bind-mount targets
docker compose up --build -d
```

Services: `api` (port 8000), `frontend` (port 3000, proxies `/api` to `api`),
`scheduler` (the always-on scanner), `bot` (command listener). All share
`config.yaml` and `listings.db` via bind mounts so edits from one show up in
the others immediately.

## Deploying to a server (e.g. EC2)

Either run via Docker Compose (above - simplest, but note the scheduler image
includes Chromium + Xvfb and is a few hundred MB), or install directly and
use the provided systemd units in `deploy/`:

```
sudo apt install chromium xvfb
# adjust paths/user in the .service files first, then:
sudo cp deploy/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now apartment-bot-scheduler apartment-bot-commands apartment-bot-api
```

EC2 IPs are commonly flagged by bot-detection services as datacenter
traffic; if the Yad2 scan starts silently returning nothing/failing after
moving off your home network, that's the likely cause and would need a
residential proxy in front of the scan (not currently built in).
