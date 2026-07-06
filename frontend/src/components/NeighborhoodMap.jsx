import { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import { getNeighborhoods } from "../api";
import NeighborhoodPicker from "./NeighborhoodPicker";

const CENTER_BY_CITY = {
  "תל אביב-יפו": [32.0853, 34.7818],
  "רמת גן": [32.0684, 34.8248],
  "גבעתיים": [32.0723, 34.8125],
};

function centroidOfGeometry(geometry) {
  const coords = geometry.type === "Polygon" ? geometry.coordinates[0] : geometry.coordinates[0]?.[0];
  if (!coords || coords.length === 0) return null;
  const lat = coords.reduce((sum, [, y]) => sum + y, 0) / coords.length;
  const lon = coords.reduce((sum, [x]) => sum + x, 0) / coords.length;
  return [lat, lon];
}

export default function NeighborhoodMap({ cities, selected, onChange }) {
  const [featureCollection, setFeatureCollection] = useState(null);
  const [mode, setMode] = useState("map");
  const [search, setSearch] = useState("");

  useEffect(() => {
    getNeighborhoods().then(setFeatureCollection).catch(() => setFeatureCollection({ type: "FeatureCollection", features: [] }));
  }, []);

  const visibleFeatures = useMemo(() => {
    if (!featureCollection) return [];
    return featureCollection.features.filter((f) => {
      if (cities.length && !cities.includes(f.properties.city)) return false;
      if (search && !f.properties.name.includes(search)) return false;
      return true;
    });
  }, [featureCollection, cities, search]);

  const byCity = useMemo(() => {
    const grouped = {};
    for (const f of visibleFeatures) {
      grouped[f.properties.city] = grouped[f.properties.city] || [];
      grouped[f.properties.city].push(f.properties.name);
    }
    return grouped;
  }, [visibleFeatures]);

  const center = cities.length && CENTER_BY_CITY[cities[0]] ? CENTER_BY_CITY[cities[0]] : CENTER_BY_CITY["תל אביב-יפו"];

  // Leaflet's GeoJSON only calls onEachFeature once per layer, at mount -
  // a layer that isn't remounted keeps its ORIGINAL click handler forever,
  // which closes over whatever `selected` array existed at that moment.
  // Clicking such a stale layer would compute "add me to the old snapshot",
  // silently discarding every selection made since. A ref always reflects
  // the latest value regardless of which render's closure reads it.
  const selectedRef = useRef(selected);
  selectedRef.current = selected;

  function toggle(name) {
    const current = selectedRef.current;
    if (current.includes(name)) {
      onChange(current.filter((n) => n !== name));
    } else {
      onChange([...current, name]);
    }
  }

  // Leaflet sets these as raw SVG attributes, not CSS - hardcode the hex
  // values (CSS custom properties don't reliably resolve there).
  const ACCENT = "#d9622b";
  const NAVY = "#1c2333";

  function styleFeature(feature) {
    const isSelected = selectedRef.current.includes(feature.properties.name);
    return {
      color: isSelected ? ACCENT : NAVY,
      weight: isSelected ? 3 : 1.5,
      opacity: isSelected ? 1 : 0.5,
      fillColor: ACCENT,
      fillOpacity: isSelected ? 0.45 : 0.12,
    };
  }

  function onEachFeature(feature, layer) {
    // Permanent label (not just on hover) so names show like Shushu's map.
    layer.bindTooltip(feature.properties.name, {
      permanent: true,
      direction: "center",
      className: "neighborhood-label",
      interactive: false,
    });
    layer.on({
      mouseover: () => layer.setStyle({ fillOpacity: 0.6, weight: 3, color: ACCENT, opacity: 1 }),
      mouseout: () => layer.setStyle(styleFeature(feature)),
      click: () => toggle(feature.properties.name),
    });
  }

  if (!featureCollection) {
    return <div className="neighborhood-map-loading">טוען מפה...</div>;
  }

  const mappable = visibleFeatures.filter((f) => f.properties.has_geometry && f.geometry);

  return (
    <div className="neighborhood-map">
      <div className="neighborhood-map-controls">
        <input
          type="text"
          className="neighborhood-search"
          placeholder="חיפוש שכונה..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="neighborhood-view-toggle">
          <button type="button" className={mode === "map" ? "active" : ""} onClick={() => setMode("map")}>
            🗺️ מפה
          </button>
          <button type="button" className={mode === "list" ? "active" : ""} onClick={() => setMode("list")}>
            📋 רשימה
          </button>
        </div>
      </div>

      {mode === "map" ? (
        <div className="map-container">
          <MapContainer center={center} zoom={13} style={{ height: "360px", width: "100%" }}>
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {mappable.map((f) => (
              <GeoJSON
                // Re-mount (not just re-render) whenever this feature's own
                // selection flips - react-leaflet doesn't reliably reapply
                // style/handlers on prop changes to an already-mounted
                // GeoJSON layer, which was silently dropping every
                // selection except whichever one you'd last hovered.
                key={`${f.properties.name}-${selected.includes(f.properties.name)}`}
                data={f}
                style={styleFeature}
                onEachFeature={onEachFeature}
              />
            ))}
          </MapContainer>
        </div>
      ) : (
        <NeighborhoodPicker byCity={byCity} selected={selected} onChange={onChange} />
      )}

      {selected.length > 0 && (
        <button type="button" className="neighborhood-clear" onClick={() => onChange([])}>
          נקה הכל ({selected.length} נבחרו)
        </button>
      )}
    </div>
  );
}
