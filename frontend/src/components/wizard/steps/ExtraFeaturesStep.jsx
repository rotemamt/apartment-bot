import FeatureCardGrid from "../../FeatureCardGrid";

export const EXTRA_FEATURES_OPTIONS = [
  { value: "elevator", label: "מעלית", icon: "🛗" },
  { value: "renovated", label: "משופצת", icon: "✨" },
  { value: "pets_allowed", label: "חיות מחמד מותרות", icon: "🐾" },
  { value: "parking", label: "חניה", icon: "🅿️" },
  { value: "no_brokerage_fee", label: "ללא דמי תיווך", icon: "🚫" },
  { value: "balcony", label: "מרפסת", icon: "🌿" },
];

export default function ExtraFeaturesStep({ filters, patch }) {
  return (
    <>
      <p className="wizard-note">
        הפיצ׳רים האלה לא יסננו דירות — רק נסמן לך אילו מהם קיימים במודעה.
      </p>
      <FeatureCardGrid
        options={EXTRA_FEATURES_OPTIONS}
        value={filters.preferred_keywords}
        onChange={(v) => patch({ preferred_keywords: v })}
        multiple
        columns={2}
      />
    </>
  );
}
