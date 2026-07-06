import { useEffect, useState } from "react";
import { getFilters, updateFilters } from "../api";
import CityStep from "./wizard/steps/CityStep";
import NeighborhoodMap from "./NeighborhoodMap";
import PriceStep from "./wizard/steps/PriceStep";
import RoomsFloorStep from "./wizard/steps/RoomsFloorStep";
import SizeKeywordsStep from "./wizard/steps/SizeKeywordsStep";

const DEFAULT_FILTERS = {
  price_min: null, price_max: null,
  rooms_min: null, rooms_max: null,
  floor_min: null, floor_max: null,
  min_sqm: null,
  cities: [], neighborhoods: [],
  required_keywords: [], excluded_keywords: [],
};

const MAP_SUPPORTED_CITIES = ["תל אביב-יפו", "רמת גן", "גבעתיים"];

export default function SettingsView() {
  const [filters, setFilters] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    getFilters().then((f) => setFilters({ ...DEFAULT_FILTERS, ...(f || {}) }));
  }, []);

  if (!filters) return <div>טוען הגדרות...</div>;

  function patch(partial) {
    setFilters((prev) => ({ ...prev, ...partial }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    try {
      await updateFilters(filters);
      setMessage("נשמר בהצלחה.");
    } catch (err) {
      setMessage(`שגיאה: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }

  const mappableCities = filters.cities.filter((c) => MAP_SUPPORTED_CITIES.includes(c));

  return (
    <form className="settings-form" onSubmit={handleSave}>
      <h2>הגדרות סינון</h2>

      <section className="settings-section">
        <div className="settings-section-label">עיר</div>
        <CityStep cities={filters.cities} onChange={(v) => patch({ cities: v })} />
      </section>

      {mappableCities.length > 0 && (
        <section className="settings-section">
          <div className="settings-section-label">שכונות</div>
          <NeighborhoodMap
            cities={mappableCities}
            selected={filters.neighborhoods}
            onChange={(v) => patch({ neighborhoods: v })}
          />
        </section>
      )}

      <section className="settings-section">
        <PriceStep filters={filters} patch={patch} />
      </section>

      <section className="settings-section">
        <RoomsFloorStep filters={filters} patch={patch} />
      </section>

      <section className="settings-section">
        <SizeKeywordsStep filters={filters} patch={patch} />
      </section>

      <button type="submit" className="settings-save-btn" disabled={saving}>
        {saving ? "שומר..." : "שמירת הגדרות"}
      </button>
      {message && <div className="save-message">{message}</div>}
    </form>
  );
}
