import RangeField from "../../RangeField";

export default function RoomsFloorStep({ filters, patch }) {
  return (
    <>
      <RangeField
        label="מספר חדרים"
        unit=""
        min={1}
        max={8}
        step={0.5}
        valueMin={filters.rooms_min}
        valueMax={filters.rooms_max}
        onChangeMin={(v) => patch({ rooms_min: v })}
        onChangeMax={(v) => patch({ rooms_max: v })}
      />
      <RangeField
        label="קומה"
        unit=""
        min={0}
        max={30}
        step={1}
        valueMin={filters.floor_min}
        valueMax={filters.floor_max}
        onChangeMin={(v) => patch({ floor_min: v })}
        onChangeMax={(v) => patch({ floor_max: v })}
      />
    </>
  );
}
