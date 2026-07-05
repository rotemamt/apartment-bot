import { useEffect, useState } from "react";
import { getConfig, updateConfig } from "../api";

const LIST_FIELDS = ["cities", "required_keywords", "excluded_keywords"];
const NUMBER_FIELDS = ["price_min", "price_max", "rooms_min", "rooms_max", "floor_min", "floor_max", "min_sqm"];

function toFormState(filters) {
  const form = {};
  for (const key of NUMBER_FIELDS) {
    form[key] = filters[key] ?? "";
  }
  for (const key of LIST_FIELDS) {
    form[key] = (filters[key] || []).join(", ");
  }
  return form;
}

export default function SettingsView() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    getConfig().then((config) => setForm(toFormState(config.filters || {})));
  }, []);

  if (!form) return <div>Loading settings...</div>;

  function handleChange(key, value) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    const payload = {};
    for (const key of NUMBER_FIELDS) {
      payload[key] = form[key] === "" ? null : Number(form[key]);
    }
    for (const key of LIST_FIELDS) {
      payload[key] = form[key]
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
    }
    try {
      await updateConfig(payload);
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
      <div className="settings-grid">
        <label>
          Min price (₪)
          <input value={form.price_min} onChange={(e) => handleChange("price_min", e.target.value)} type="number" />
        </label>
        <label>
          Max price (₪)
          <input value={form.price_max} onChange={(e) => handleChange("price_max", e.target.value)} type="number" />
        </label>
        <label>
          Min rooms
          <input value={form.rooms_min} onChange={(e) => handleChange("rooms_min", e.target.value)} type="number" step="0.5" />
        </label>
        <label>
          Max rooms
          <input value={form.rooms_max} onChange={(e) => handleChange("rooms_max", e.target.value)} type="number" step="0.5" />
        </label>
        <label>
          Min floor
          <input value={form.floor_min} onChange={(e) => handleChange("floor_min", e.target.value)} type="number" />
        </label>
        <label>
          Max floor
          <input value={form.floor_max} onChange={(e) => handleChange("floor_max", e.target.value)} type="number" />
        </label>
        <label>
          Min m²
          <input value={form.min_sqm} onChange={(e) => handleChange("min_sqm", e.target.value)} type="number" />
        </label>
      </div>
      <label className="full-width">
        Cities (comma separated)
        <input value={form.cities} onChange={(e) => handleChange("cities", e.target.value)} />
      </label>
      <label className="full-width">
        Required keywords (comma separated - ALL must appear)
        <input value={form.required_keywords} onChange={(e) => handleChange("required_keywords", e.target.value)} />
      </label>
      <label className="full-width">
        Excluded keywords (comma separated - ANY excludes the listing)
        <input value={form.excluded_keywords} onChange={(e) => handleChange("excluded_keywords", e.target.value)} />
      </label>
      <button type="submit" disabled={saving}>
        {saving ? "Saving..." : "Save filters"}
      </button>
      {message && <div className="save-message">{message}</div>}
    </form>
  );
}
