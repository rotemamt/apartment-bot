export default function RangeField({ label, unit, min, max, step = 1, valueMin, valueMax, onChangeMin, onChangeMax }) {
  const disabled = valueMin === null && valueMax === null;

  function toggleImportant() {
    if (disabled) {
      onChangeMin(min);
      onChangeMax(max);
    } else {
      onChangeMin(null);
      onChangeMax(null);
    }
  }

  return (
    <div className="range-field">
      <div className="range-field-header">
        <span>{label}</span>
        <span className="range-field-values">
          {disabled ? "—" : `${valueMin ?? min}${unit} - ${valueMax ?? max}${unit}`}
        </span>
      </div>
      <div className="range-field-sliders">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          value={valueMin ?? min}
          onChange={(e) => onChangeMin(Math.min(Number(e.target.value), valueMax ?? max))}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          value={valueMax ?? max}
          onChange={(e) => onChangeMax(Math.max(Number(e.target.value), valueMin ?? min))}
        />
      </div>
      <label className="range-field-toggle">
        <input type="checkbox" checked={disabled} onChange={toggleImportant} />
        לא משנה לי
      </label>
    </div>
  );
}
