import re
from dataclasses import dataclass, field

import yaml

from apartment_bot.adapters.base import Listing

# Hebrew text uses several dash-like characters interchangeably (maqaf ־,
# hyphen -, en/em dash) e.g. "תל־אביב" vs "תל אביב" vs "תל-אביב" - normalize
# them all to a space so substring matching (cities, keywords) isn't
# punctuation-sensitive.
_DASH_RE = re.compile(r"[-־–—]")
# Same idea for quote characters: Hebrew abbreviations like ממ"ד are written
# with a plain ASCII quote ("), the proper Hebrew gershayim (״), or omitted
# entirely (ממד) depending on who typed it. Stripping them all makes these
# equivalent without needing every spelling listed as a separate synonym.
_QUOTE_RE = re.compile(r'["\'׳״]')
_WHITESPACE_RE = re.compile(r"\s+")

# Curated synonym lists for the wizard's single-select property/safe-room
# cards and the multi-select "nice to have" feature chips - keys are the
# canonical values the frontend sends, values are alternate spellings to
# search for in the listing's text blob.
PROPERTY_TYPE_SYNONYMS = {
    "דירה שלמה": ["דירה שלמה", "כל הדירה", "דירה מלאה"],
    "דירה לשותפים": ["לשותפים", "דרוש שותף", "דרושה שותפה", "roommate"],
    "חדר בדירת שותפים": ["חדר בדירת שותפים", "חדר בדירה משותפת"],
    "סאבלט": ["סאבלט", "sublet"],
}
SAFE_ROOM_SYNONYMS = {
    "מקלט": ["מקלט", "shelter"],
    'ממ"ד': ['ממ"ד', "מרחב מוגן דירתי", "mamad", "safe room"],
    'ממ"ק': ['ממ"ק', "מרחב מוגן קומתי", "mamak"],
}
PREFERRED_FEATURE_SYNONYMS = {
    "elevator": ["מעלית", "elevator"],
    "renovated": ["משופצת", "משופץ", "renovated"],
    "pets_allowed": ["חיות מחמד", "מותר בעלי חיים", "pet friendly"],
    "parking": ["חניה", "חנייה", "parking"],
    "no_brokerage_fee": ["ללא תיווך", "בלי תיווך", "ללא דמי תיווך", "no brokerage"],
    "balcony": ["מרפסת", "balcony"],
}


@dataclass
class MatchResult:
    matched: bool
    matched_features: list[str]
    reason: str = ""
    preferred_features: list[str] = field(default_factory=list)


def load_config(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _normalize(text: str) -> str:
    text = _DASH_RE.sub(" ", text)
    text = _QUOTE_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip().lower()


def _text_blob(listing: Listing) -> str:
    raw = " ".join(filter(None, [listing.address, listing.raw_text]))
    return _normalize(raw)


def match_listing(listing: Listing, config: dict) -> MatchResult:
    f = config.get("filters", {})
    blob = _text_blob(listing)

    price_min = f.get("price_min")
    price_max = f.get("price_max")
    if price_min is not None and (listing.price is None or listing.price < price_min):
        return MatchResult(False, [], f"price {listing.price} below min {price_min}")
    if price_max is not None and (listing.price is None or listing.price > price_max):
        return MatchResult(False, [], f"price {listing.price} above max {price_max}")

    cities = f.get("cities") or []
    if cities and not any(_normalize(city) in blob for city in cities):
        return MatchResult(False, [], "no city match")

    neighborhoods = f.get("neighborhoods") or []
    if neighborhoods and not any(_normalize(n) in blob for n in neighborhoods):
        return MatchResult(False, [], "no neighborhood match")

    rooms_min = f.get("rooms_min")
    rooms_max = f.get("rooms_max")
    if rooms_min is not None and (listing.rooms is None or listing.rooms < rooms_min):
        return MatchResult(False, [], f"rooms {listing.rooms} below min {rooms_min}")
    if rooms_max is not None and (listing.rooms is None or listing.rooms > rooms_max):
        return MatchResult(False, [], f"rooms {listing.rooms} above max {rooms_max}")

    # floor/sqm are often simply not mentioned in free-text sources (e.g. Telegram
    # posts) - treat "unknown" as "don't disqualify", unlike price/rooms which are
    # near-universally present and are deal-breakers when missing.
    floor_min = f.get("floor_min")
    floor_max = f.get("floor_max")
    if listing.floor is not None:
        if floor_min is not None and listing.floor < floor_min:
            return MatchResult(False, [], f"floor {listing.floor} below min {floor_min}")
        if floor_max is not None and listing.floor > floor_max:
            return MatchResult(False, [], f"floor {listing.floor} above max {floor_max}")

    min_sqm = f.get("min_sqm")
    if min_sqm is not None and listing.sqm is not None and listing.sqm < min_sqm:
        return MatchResult(False, [], f"sqm {listing.sqm} below min {min_sqm}")

    excluded_keywords = f.get("excluded_keywords") or []
    for kw in excluded_keywords:
        if _normalize(kw) in blob:
            return MatchResult(False, [], f"excluded keyword matched: {kw}")

    property_type = f.get("property_type")
    if property_type:
        synonyms = PROPERTY_TYPE_SYNONYMS.get(property_type, [property_type])
        if not any(_normalize(s) in blob for s in synonyms):
            return MatchResult(False, [], f"property_type mismatch: {property_type}")

    safe_room = f.get("safe_room") or []
    if isinstance(safe_room, str):  # older saved filters may have this as a single string
        safe_room = [safe_room]
    if safe_room:
        all_synonyms = [s for opt in safe_room for s in SAFE_ROOM_SYNONYMS.get(opt, [opt])]
        if not any(_normalize(s) in blob for s in all_synonyms):
            return MatchResult(False, [], f"safe_room mismatch: {safe_room}")

    # Each entry is a required feature; write it as "alt1/alt2/alt3" to accept
    # any spelling/synonym for that one feature (e.g. mamad has several common
    # spellings) - entries are ANDed together, alternatives within an entry
    # are ORed.
    required_keywords = f.get("required_keywords") or []
    matched_features = []
    for entry in required_keywords:
        alternatives = [alt.strip() for alt in entry.split("/") if alt.strip()]
        found = next((alt for alt in alternatives if _normalize(alt) in blob), None)
        if not found:
            return MatchResult(False, [], f"missing required keyword (any of): {entry}")
        matched_features.append(found)

    # Nice-to-have features never disqualify a listing - just record which
    # ones were actually detected so the UI/alert can flag them.
    preferred_keywords = f.get("preferred_keywords") or []
    preferred_features = []
    for key in preferred_keywords:
        synonyms = PREFERRED_FEATURE_SYNONYMS.get(key, [key])
        if any(_normalize(s) in blob for s in synonyms):
            preferred_features.append(key)

    return MatchResult(True, matched_features, "matched", preferred_features)
