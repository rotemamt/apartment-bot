import FeatureCardGrid from "../../FeatureCardGrid";

export const PROPERTY_TYPE_OPTIONS = [
  { value: "דירה שלמה", label: "דירה שלמה" },
  { value: "דירה לשותפים", label: "דירה המיועדת לשותפים" },
  { value: "חדר בדירת שותפים", label: "חדר בדירת שותפים" },
  { value: "סאבלט", label: "סאבלט" },
];

export const SAFE_ROOM_OPTIONS = [
  { value: 'ממ"ד', label: 'ממ"ד' },
  { value: 'ממ"ק', label: 'ממ"ק' },
  { value: "מקלט", label: "מקלט" },
];

export default function PropertyTypeStep({ filters, patch }) {
  return (
    <>
      <div className="settings-section-label">סוג הדירה</div>
      <FeatureCardGrid
        options={PROPERTY_TYPE_OPTIONS}
        value={filters.property_type}
        onChange={(v) => patch({ property_type: v })}
        columns={2}
      />
      <div className="settings-section-label">מרחב מוגן</div>
      <FeatureCardGrid
        options={SAFE_ROOM_OPTIONS}
        value={filters.safe_room}
        onChange={(v) => patch({ safe_room: v })}
        multiple
        columns={2}
      />
    </>
  );
}
