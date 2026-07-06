import { useEffect, useState } from "react";
import { getFilters, updateFilters } from "../api";
import RangeField from "./RangeField";
import NeighborhoodPicker from "./NeighborhoodPicker";

const KEYWORD_FIELDS = ["required_keywords", "excluded_keywords"];

function toFormState(filters) {
  return {
    price_min: filters.price_min ?? null,
    price_max: filters.price_max ?? null,
    rooms_min: filters.rooms_min ?? null,
    rooms_max: filters.rooms_max ?? null,
    floor_min: filters.floor_min ?? null,
    floor_max: filters.floor_max ?? null,
    min_sqm: filters.min_sqm ?? null,
    cities: filters.cities || [],
    neighborhoods: filters.neighborhoods || [],
    required_keywords: (filters.required_keywords || []).join(", "),
    excluded_keywords: (filters.excluded_keywords || []).join(", "),
  };
}

export default function SettingsView() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    getFilters().then((filters) => setForm(toFormState(filters || {})));
  }, []);

  if (!form) return <div>Loading settings...</div>;

  function set(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    const payload = {
      price_min: form.price_min,
      price_max: form.price_max,
      rooms_min: form.rooms_min,
      rooms_max: form.rooms_max,
      floor_min: form.floor_min,
      floor_max: form.floor_max,
      min_sqm: form.min_sqm,
      cities: form.cities,
      neighborhoods: form.neighborhoods,
      required_keywords: form.required_keywords.split(",").map((s) => s.trim()).filter(Boolean),
      excluded_keywords: form.excluded_keywords.split(",").map((s) => s.trim()).filter(Boolean),
    };
    try {
      await updateFilters(payload);
      setMessage("Saved.");
    } catch (err) {
      setMessage(`Error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="settings-form" onSubmit={handleSave}>
      <h2>Search Filters</h2>

      <RangeField
        label="Price" unit="₪" min={0} max={20000} step={100}
        valueMin={form.price_min} valueMax={form.price_max}
        onChangeMin={(v) => set("price_min", v)} onChangeMax={(v) => set("price_max", v)}
      />
      <RangeField
        label="Rooms" unit="" min={1} max={8} step={0.5}
        valueMin={form.rooms_min} valueMax={form.rooms_max}
        onChangeMin={(v) => set("rooms_min", v)} onChangeMax={(v) => set("rooms_max", v)}
      />
      <RangeField
        label="Floor" unit="" min={0} max={30} step={1}
        valueMin={form.floor_min} valueMax={form.floor_max}
        onChangeMin={(v) => set("floor_min", v)} onChangeMax={(v) => set("floor_max", v)}
      />

      <label className="full-width">
        Min m²
        <input
          value={form.min_sqm ?? ""}
          onChange={(e) => set("min_sqm", e.target.value === "" ? null : Number(e.target.value))}
          type="number"
        />
      </label>

      <label className="full-width">
        Cities (comma separated)
        <input
          value={form.cities.join(", ")}
          onChange={(e) => set("cities", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))}
        />
      </label>

      <div className="full-width">
        <div className="settings-section-label">Neighborhoods (optional - leave empty for whole city)</div>
        <NeighborhoodPicker selected={form.neighborhoods} onChange={(v) => set("neighborhoods", v)} />
      </div>

      <label className="full-width">
        Required keywords (comma separated - ALL must appear; use "/" for synonyms of the same feature)
        <input value={form.required_keywords} onChange={(e) => set("required_keywords", e.target.value)} />
      </label>
      <label className="full-width">
        Excluded keywords (comma separated - ANY excludes the listing)
        <input value={form.excluded_keywords} onChange={(e) => set("excluded_keywords", e.target.value)} />
      </label>
      <button type="submit" disabled={saving}>
        {saving ? "Saving..." : "Save filters"}
      </button>
      {message && <div className="save-message">{message}</div>}
    </form>
  );
}
