import hashlib
import hmac
import json
import os
import sys
from pathlib import Path
from typing import Literal, Optional
from urllib.parse import parse_qsl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apartment_bot.storage import db

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config.yaml"
DB_PATH = ROOT / "listings.db"

load_dotenv(ROOT / ".env")
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# Tel Aviv-Yafo neighborhood names as they actually appear in Yad2 listing
# addresses (observed from real scraped data) - used to power the
# neighborhood picker in the settings UI/Mini App.
TEL_AVIV_NEIGHBORHOODS = [
    "לב תל אביב", "הצפון הישן - צפון", "הצפון הישן - דרום",
    "הצפון החדש - כיכר המדינה", "הצפון החדש - דרום", "פלורנטין",
    "נווה צדק", "כרם התימנים", "שפירא", "קרית שלום", "יד אליהו",
    "רמת אביב ג'", "רמת אביב החדשה", "נאות אפקה ב'", "אפקה", "בבלי",
    "נווה אביבים", "תל ברוך צפון", "גבעת הרצל", "אזור המלאכה יפו",
    "עג'מי", "צפון יפו", "המושבה האמריקאית-גרמנית", "נווה שאנן",
    "התקוה", "בית יעקב", "נווה צה\"ל", "גני שרונה", "קרית הממשלה",
    "פארק צמרת", "צמרות איילון", "מונטיפיורי", "הרכבת", "נחלת יצחק",
    "ביצרון ורמת ישראל", "המשתלה", "ניר אביב",
]

app = FastAPI(title="Apartment Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_init_data(init_data: str) -> dict:
    """Verify Telegram Mini App initData server-side.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        raise HTTPException(status_code=401, detail="malformed initData")
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=401, detail="invalid initData signature")
    return parsed


def get_current_user(x_telegram_init_data: str = Header(...)):
    parsed = _validate_init_data(x_telegram_init_data)
    try:
        tg_user = json.loads(parsed["user"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=401, detail="missing user in initData")

    conn = db.connect(str(DB_PATH))
    user = db.get_user_by_chat_id(conn, str(tg_user["id"]))
    print(f"[DEBUG auth] tg_user id={tg_user['id']!r} found_user={dict(user) if user else None}")
    if user is None or user["status"] != "approved":
        raise HTTPException(status_code=403, detail="not authorized")
    return user


def row_to_dict(row) -> dict:
    d = dict(row)
    d["matched"] = bool(d.get("matched"))
    try:
        d["matched_features"] = json.loads(d.get("matched_features") or "[]")
    except (TypeError, ValueError):
        d["matched_features"] = []
    return d


class StatusUpdate(BaseModel):
    status: Literal["new", "seen", "interested", "rejected"]


class FiltersUpdate(BaseModel):
    price_min: Optional[int] = None
    price_max: Optional[int] = None
    rooms_min: Optional[float] = None
    rooms_max: Optional[float] = None
    floor_min: Optional[int] = None
    floor_max: Optional[int] = None
    min_sqm: Optional[int] = None
    cities: Optional[list[str]] = None
    neighborhoods: Optional[list[str]] = None
    required_keywords: Optional[list[str]] = None
    excluded_keywords: Optional[list[str]] = None


@app.get("/api/listings")
def api_get_listings(
    status: Optional[str] = None,
    source: Optional[str] = None,
    matched_only: bool = False,
    sort_by: str = "first_seen_at",
    order: str = "desc",
    user=Depends(get_current_user),
):
    conn = db.connect(str(DB_PATH))
    try:
        rows = db.get_user_listings(
            conn, user["id"], status=status, source=source,
            matched_only=matched_only, sort_by=sort_by, order=order,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [row_to_dict(r) for r in rows]


@app.post("/api/listings/{listing_id}/status")
def api_set_status(listing_id: int, body: StatusUpdate, user=Depends(get_current_user)):
    conn = db.connect(str(DB_PATH))
    if db.get_user_listing(conn, user["id"], listing_id) is None:
        raise HTTPException(status_code=404, detail="listing not found")
    db.set_user_listing_status(conn, user["id"], listing_id, body.status)
    return row_to_dict(db.get_user_listing(conn, user["id"], listing_id))


@app.get("/api/stats")
def api_stats(user=Depends(get_current_user)):
    conn = db.connect(str(DB_PATH))
    rows = db.get_user_listings(conn, user["id"])
    matched = sum(1 for r in rows if r["matched"])
    return {
        "total": len(rows),
        "matched": matched,
        "matched_today": db.count_user_matched_today(conn, user["id"]),
    }


@app.get("/api/neighborhoods")
def api_neighborhoods():
    return {"תל אביב": TEL_AVIV_NEIGHBORHOODS}


@app.get("/api/filters")
def api_get_filters(user=Depends(get_current_user)):
    conn = db.connect(str(DB_PATH))
    return db.get_user_filters(conn, user["id"])


@app.put("/api/filters")
def api_update_filters(body: FiltersUpdate, user=Depends(get_current_user)):
    # exclude_unset (not "is not None") so a field explicitly sent as null
    # (e.g. "doesn't matter" clearing floor_max) is distinguishable from a
    # field simply omitted from a partial update.
    updates = body.model_dump(exclude_unset=True)
    conn = db.connect(str(DB_PATH))
    if updates:
        db.update_user_filters(conn, user["id"], updates)
    return db.get_user_filters(conn, user["id"])
