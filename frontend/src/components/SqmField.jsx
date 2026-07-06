export default function SqmField({ label, value, onChange, min = 0, max = 300, step = 5 }) {
  const disabled = value === null;

  return (
    <div className="range-field">
      <div className="range-field-header">
        <span>{label}</span>
        <span className="range-field-values">{disabled ? "—" : `${value} מ״ר ומעלה`}</span>
      </div>
      <div className="range-field-sliders">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          disabled={disabled}
          value={value ?? min}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      </div>
      <label className="range-field-toggle">
        <input type="checkbox" checked={disabled} onChange={() => onChange(disabled ? min : null)} />
        לא משנה לי
      </label>
    </div>
  );
}
