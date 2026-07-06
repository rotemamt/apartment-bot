import SqmField from "../../SqmField";
import ChipInput from "../../ChipInput";

export default function SizeKeywordsStep({ filters, patch }) {
  return (
    <>
      <SqmField label="גודל דירה מינימלי" value={filters.min_sqm} onChange={(v) => patch({ min_sqm: v })} />
      <ChipInput
        label="מילות מפתח נדרשות (חובה שיופיעו)"
        hint='לדוגמה: ממ"ד. אפשר להוסיף כמה מילים.'
        values={filters.required_keywords}
        onChange={(v) => patch({ required_keywords: v })}
      />
      <ChipInput
        label="מילות מפתח לשלילה (יפסלו מודעה)"
        hint="לדוגמה: שותפים"
        values={filters.excluded_keywords}
        onChange={(v) => patch({ excluded_keywords: v })}
      />
    </>
  );
}
