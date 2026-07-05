"""Runs the Yad2 + Telegram scan on a loop, forever, per config.yaml's
poll_interval_minutes. This is what keeps the bot "always on" - run it via
systemd (see deploy/apartment-bot-scheduler.service) or as a Docker service.
"""
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apartment_bot.cli import CONFIG_PATH, scan_all
from apartment_bot.filters.engine import load_config


def main() -> None:
    while True:
        interval_minutes = load_config(str(CONFIG_PATH)).get("poll_interval_minutes", 12)
        try:
            scan_all()
        except Exception:
            print("Scan failed, will retry next cycle:")
            traceback.print_exc()
        print(f"Sleeping {interval_minutes} minutes until next scan...")
        time.sleep(interval_minutes * 60)


if __name__ == "__main__":
    main()
