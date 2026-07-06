"""One-time script: convert an Overpass query result (ways/relations tagged
place=neighbourhood/suburb/quarter) into the GeoJSON FeatureCollection served
by GET /api/neighborhoods. Not called by the running app - run manually
whenever the neighborhood boundary data needs refreshing."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "apartment_bot" / "dashboard" / "data" / "neighborhoods.geojson"


def way_to_ring(way: dict) -> list[list[float]]:
    return [[node["lon"], node["lat"]] for node in way["geometry"] if node]


def way_to_feature(way: dict, city: str) -> dict | None:
    tags = way.get("tags", {})
    name = tags.get("name:he") or tags.get("name")
    if not name or not way.get("geometry"):
        return None
    ring = way_to_ring(way)
    if len(ring) < 4 or ring[0] != ring[-1]:
        ring.append(ring[0])
    return {
        "type": "Feature",
        "properties": {"name": name, "city": city, "has_geometry": True},
        "geometry": {"type": "Polygon", "coordinates": [ring]},
    }


def relation_to_feature(rel: dict, ways_by_id: dict, city: str) -> dict | None:
    tags = rel.get("tags", {})
    name = tags.get("name:he") or tags.get("name")
    if not name:
        return None
    outer_rings = []
    for member in rel.get("members", []):
        if member.get("type") == "way" and member.get("role") == "outer":
            geom = member.get("geometry")
            if geom:
                ring = [[n["lon"], n["lat"]] for n in geom]
                if len(ring) >= 4:
                    if ring[0] != ring[-1]:
                        ring.append(ring[0])
                    outer_rings.append(ring)
    if not outer_rings:
        return None
    coords = [[ring] for ring in outer_rings]
    geom_type = "Polygon" if len(coords) == 1 else "MultiPolygon"
    geometry = {"type": "Polygon", "coordinates": coords[0]} if geom_type == "Polygon" \
        else {"type": "MultiPolygon", "coordinates": coords}
    return {
        "type": "Feature",
        "properties": {"name": name, "city": city, "has_geometry": True},
        "geometry": geometry,
    }


# Overpass's bbox query pulls in neighbourhoods from all 3 target cities plus
# some neighbours (Bat Yam, Kfar Ganim/Petah Tikva, Or Yehuda). A pure lat/lon
# bbox can't cleanly separate Ramat Gan/Givatayim (they're small and
# interleaved with Tel Aviv), so known real-world names are assigned
# explicitly; anything left over falls back to a coarse Tel Aviv bbox, and
# names matching neither a known city nor the bbox are dropped (out of scope).
GIVATAYIM_NAMES = {
    "כפר גנים א'", "כפר גנים ב'", "בת גנים", "בורוכוב",
}
RAMAT_GAN_NAMES = {
    "בר אילן", "רמת חן", "נחלת גנים", "הבורסה", "יהלום",
    "חרוזים", "ראשונים", "חשמונאים", "עליות", "סיטי", "רמת יצחק",
    "רמת עמידר", "רמת אפעל", "נווה יהושע", "צנחנים", "אורות", "כפיר",
    "רמת שקמה", "כפר אז\"ר", "שיכון ותיקים", "קריית קריניצי", "תל גנים",
}
EXCLUDE_NAMES = {"בת ים", "אונו הצעירה", "אם המושבות החדשה", "נוה מונוסון"}

# Official neighborhood lists (municipality/Wikipedia) with no matching OSM
# polygon in our Overpass pull - included as list-only entries (has_geometry
# False) so the picker's list view is complete even where the map can't
# show a shape yet.
NO_GEOMETRY_NEIGHBORHOODS = {
    "גבעתיים": [
        "שינקין", "פועלי הרכבת", "גבעת רמב\"ם", "גבעת קוזלובסקי",
        "קריית יוסף", "ארלוזורוב", "שיכון המורים",
    ],
    "רמת גן": [
        "קריית בורוכוב", "תל בנימין", "תל השומר", "מרום נווה",
        "גני ארמונים", "הגפן", "הברושים",
    ],
}

CITY_BOUNDS = {
    "תל אביב-יפו": (32.03, 34.73, 32.14, 34.83),
}


def classify_city(lat: float, lon: float, name: str | None = None) -> str | None:
    if name in EXCLUDE_NAMES:
        return None
    if name in GIVATAYIM_NAMES:
        return "גבעתיים"
    if name in RAMAT_GAN_NAMES:
        return "רמת גן"
    for city, (min_lat, min_lon, max_lat, max_lon) in CITY_BOUNDS.items():
        if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
            return city
    return None


def centroid_of_way(way: dict) -> tuple[float, float] | None:
    geom = way.get("geometry") or []
    if not geom:
        return None
    lats = [n["lat"] for n in geom if n]
    lons = [n["lon"] for n in geom if n]
    return sum(lats) / len(lats), sum(lons) / len(lons)


def main(raw_path: str) -> None:
    data = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    elements = data["elements"]
    ways_by_id = {e["id"]: e for e in elements if e["type"] == "way"}

    features = []
    seen_names = set()
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name:he") or tags.get("name")

        if el["type"] == "way":
            centroid = centroid_of_way(el)
            if not centroid:
                continue
            city = classify_city(*centroid, name=name)
            if not city:
                continue
            feat = way_to_feature(el, city)
        elif el["type"] == "relation":
            # approximate relation centroid from its outer way members
            outer_ways = [m for m in el.get("members", []) if m.get("type") == "way" and m.get("role") == "outer"]
            if not outer_ways or not outer_ways[0].get("geometry"):
                continue
            g = outer_ways[0]["geometry"]
            lat = sum(n["lat"] for n in g) / len(g)
            lon = sum(n["lon"] for n in g) / len(g)
            city = classify_city(lat, lon, name=name)
            if not city:
                continue
            feat = relation_to_feature(el, ways_by_id, city)
        else:
            continue

        if not feat:
            continue
        key = (feat["properties"]["name"], feat["properties"]["city"])
        if key in seen_names:
            continue
        seen_names.add(key)
        features.append(feat)

    for city, names in NO_GEOMETRY_NEIGHBORHOODS.items():
        for name in names:
            key = (name, city)
            if key in seen_names:
                continue
            seen_names.add(key)
            features.append({
                "type": "Feature",
                "properties": {"name": name, "city": city, "has_geometry": False},
                "geometry": None,
            })

    fc = {"type": "FeatureCollection", "features": features}
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(fc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {len(features)} features to {OUT_PATH}")
    by_city = {}
    for f in features:
        by_city.setdefault(f["properties"]["city"], []).append(f["properties"]["name"])
    for city, names in by_city.items():
        print(f"{city}: {len(names)} neighborhoods")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "overpass_result.json")
