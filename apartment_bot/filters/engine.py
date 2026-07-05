import re
from dataclasses import dataclass

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


@dataclass
class MatchResult:
    matched: bool
    matched_features: list[str]
    reason: str = ""


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

    return MatchResult(True, matched_features, "matched")
