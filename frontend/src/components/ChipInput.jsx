import { useState } from "react";

export default function ChipInput({ label, hint, values, onChange, skippable = true }) {
  const [draft, setDraft] = useState("");
  const disabled = skippable && values === null;
  const chips = values || [];

  function addChip() {
    const v = draft.trim();
    if (v && !chips.includes(v)) onChange([...chips, v]);
    setDraft("");
  }

  function removeChip(v) {
    onChange(chips.filter((c) => c !== v));
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addChip();
    }
  }

  return (
    <div className="chip-field">
      <div className="range-field-header">
        <span>{label}</span>
      </div>
      {hint && <p className="chip-hint">{hint}</p>}
      {!disabled && (
        <>
          <div className="chip-list">
            {chips.map((v) => (
              <span key={v} className="chip">
                {v}
                <button type="button" onClick={() => removeChip(v)} aria-label="הסר">×</button>
              </span>
            ))}
          </div>
          <input
            type="text"
            className="chip-input"
            placeholder="הקלד ולחץ Enter..."
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={addChip}
          />
        </>
      )}
      {skippable && (
        <label className="range-field-toggle">
          <input type="checkbox" checked={disabled} onChange={() => onChange(disabled ? [] : null)} />
          לא משנה לי
        </label>
      )}
    </div>
  );
}
