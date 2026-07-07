export default function FeatureCardGrid({ options, value, onChange, multiple = false, columns = 2 }) {
  function isSelected(optionValue) {
    return multiple ? (value || []).includes(optionValue) : value === optionValue;
  }

  function toggle(optionValue) {
    if (multiple) {
      const current = value || [];
      onChange(
        current.includes(optionValue)
          ? current.filter((v) => v !== optionValue)
          : [...current, optionValue]
      );
    } else {
      onChange(value === optionValue ? null : optionValue);
    }
  }

  return (
    <div className="feature-card-grid" style={{ "--fcg-columns": columns }}>
      {options.map((option) => {
        const selected = isSelected(option.value);
        return (
          <button
            key={option.value}
            type="button"
            className={`feature-card${selected ? " selected" : ""}`}
            onClick={() => toggle(option.value)}
          >
            {selected && <span className="feature-card-check">✓</span>}
            {option.icon && <span className="feature-card-icon">{option.icon}</span>}
            <span>{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
