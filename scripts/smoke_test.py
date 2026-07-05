"""Quick manual test: exercises the filter engine + SQLite storage with fake listings,
no network access needed. Run: python scripts/smoke_test.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from apartment_bot.adapters.base import Listing
from apartment_bot.filters.engine import load_config, match_listing
from apartment_bot.storage import db

FAKE_LISTINGS = [
    Listing(
        source="yad2", url="https://example.com/listing/1", external_id="1",
        price=6000, rooms=3, floor=2, sqm=70, address="תל אביב, פלורנטין",
        photo_url="https://example.com/1.jpg", posted_date="2026-06-30",
        raw_text="דירת 3 חדרים מהממת עם מרפסת ומעלית, קרובה לים",
    ),
    Listing(
        source="yad2", url="https://example.com/listing/2", external_id="2",
        price=15000, rooms=5, floor=1, sqm=120, address="תל אביב",
        raw_text="דירת יוקרה גדולה מאוד",
    ),
    Listing(
        source="yad2", url="https://example.com/listing/3", external_id="3",
        price=5000, rooms=2, floor=3, sqm=55, address="תל אביב",
        raw_text="מחפשים שותפים לדירה משותפת",
    ),
]


def main():
    config = load_config(str(Path(__file__).resolve().parent.parent / "config.yaml"))
    conn = db.connect(str(Path(__file__).resolve().parent.parent / "test.db"))

    for listing in FAKE_LISTINGS:
        result = match_listing(listing, config)
        is_new = db.upsert_listing(conn, listing, matched_features=result.matched_features)
        status = "MATCH" if result.matched else f"skip ({result.reason})"
        print(f"[{'new' if is_new else 'seen'}] {listing.url} price={listing.price} -> {status}")

    print("\nAll rows currently in DB:")
    for row in db.get_listings(conn):
        print(dict(row))


if __name__ == "__main__":
    main()
