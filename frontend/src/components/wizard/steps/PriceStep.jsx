import RangeField from "../../RangeField";

export default function PriceStep({ filters, patch }) {
  return (
    <RangeField
      label="טווח מחיר"
      unit=" ₪"
      min={0}
      max={20000}
      step={100}
      valueMin={filters.price_min}
      valueMax={filters.price_max}
      onChangeMin={(v) => patch({ price_min: v })}
      onChangeMax={(v) => patch({ price_max: v })}
    />
  );
}
