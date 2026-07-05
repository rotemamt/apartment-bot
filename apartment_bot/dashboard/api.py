import json
import sys
from pathlib import Path
from typing import Literal, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from apartment_bot.filters.engine import load_config
from apartment_bot.storage import db
from apartment_bot.telegram.config_editor import update_filters

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT / "config.yaml"
DB_PATH = ROOT / "listings.db"

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
):
    conn = db.connect(str(DB_PATH))
    try:
        rows = db.get_listings(
            conn, status=status, source=source, matched_only=matched_only, sort_by=sort_by, order=order
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return [row_to_dict(r) for r in rows]


@app.post("/api/listings/{listing_id}/status")
def api_set_status(listing_id: int, body: StatusUpdate):
    conn = db.connect(str(DB_PATH))
    if db.get_listing(conn, listing_id) is None:
        raise HTTPException(status_code=404, detail="listing not found")
    db.set_status(conn, listing_id, body.status)
    return row_to_dict(db.get_listing(conn, listing_id))


@app.get("/api/stats")
def api_stats():
    conn = db.connect(str(DB_PATH))
    total = conn.execute("SELECT COUNT(*) AS c FROM listings").fetchone()["c"]
    matched = conn.execute("SELECT COUNT(*) AS c FROM listings WHERE matched=1").fetchone()["c"]
    return {
        "total": total,
        "matched": matched,
        "matched_today": db.count_matched_today(conn),
    }


@app.get("/api/neighborhoods")
def api_neighborhoods():
    return {"תל אביב": TEL_AVIV_NEIGHBORHOODS}


@app.get("/api/config")
def api_get_config():
    return load_config(str(CONFIG_PATH))


@app.put("/api/config")
def api_update_config(body: FiltersUpdate):
    # exclude_unset (not "is not None") so a field explicitly sent as null
    # (e.g. "doesn't matter" clearing floor_max) is distinguishable from a
    # field simply omitted from a partial update.
    updates = body.model_dump(exclude_unset=True)
    if updates:
        update_filters(str(CONFIG_PATH), updates)
    return load_config(str(CONFIG_PATH))
