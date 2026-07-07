import { useState } from "react";
import { postOnboarding } from "../../api";
import WizardShell from "./WizardShell";
import NameStep from "./steps/NameStep";
import CityStep from "./steps/CityStep";
import NeighborhoodStep from "./steps/NeighborhoodStep";
import PriceStep from "./steps/PriceStep";
import RoomsFloorStep from "./steps/RoomsFloorStep";
import PropertyTypeStep from "./steps/PropertyTypeStep";
import ExtraFeaturesStep from "./steps/ExtraFeaturesStep";
import SizeKeywordsStep from "./steps/SizeKeywordsStep";

const DEFAULT_FILTERS = {
  display_name: "",
  price_min: null, price_max: null,
  rooms_min: null, rooms_max: null,
  floor_min: null, floor_max: null,
  min_sqm: null,
  cities: [], neighborhoods: [],
  required_keywords: [], excluded_keywords: [],
  property_type: null, safe_room: [],
  preferred_keywords: [],
};

const STEPS = [
  {
    id: "name",
    title: "מה השם שלך?",
    subtitle: "כדי שנדע איך לפנות אליך",
    render: (filters, patch) => <NameStep value={filters.display_name} onChange={(v) => patch({ display_name: v })} />,
    canContinue: (filters) => filters.display_name.trim().length > 0,
  },
  {
    id: "city",
    title: "באיזו עיר תרצה לחפש דירה?",
    subtitle: "אפשר לבחור יותר מעיר אחת",
    render: (filters, patch) => <CityStep cities={filters.cities} onChange={(v) => patch({ cities: v })} />,
    canContinue: (filters) => filters.cities.length > 0,
  },
  {
    id: "neighborhoods",
    title: "אילו שכונות מעניינות אותך?",
    subtitle: "לחיצה על שכונה במפה מסמנת אותה. אפשר גם לדלג ולא להגביל.",
    render: (filters, patch) => (
      <NeighborhoodStep cities={filters.cities} neighborhoods={filters.neighborhoods} onChange={(v) => patch({ neighborhoods: v })} />
    ),
  },
  {
    id: "price",
    title: "מה טווח המחיר?",
    render: (filters, patch) => <PriceStep filters={filters} patch={patch} />,
  },
  {
    id: "rooms_floor",
    title: "חדרים וקומה",
    render: (filters, patch) => <RoomsFloorStep filters={filters} patch={patch} />,
  },
  {
    id: "property_type",
    title: "סוג הדירה וחדר בטוח",
    subtitle: "אפשר לדלג אם זה לא משנה לך",
    render: (filters, patch) => <PropertyTypeStep filters={filters} patch={patch} />,
  },
  {
    id: "extra_features",
    title: "עוד כמה דברים שיהיה נחמד שיהיו",
    subtitle: "לא נסנן דירות בלי הפיצ׳רים האלה — רק נסמן לך שהם קיימים",
    render: (filters, patch) => <ExtraFeaturesStep filters={filters} patch={patch} />,
  },
  {
    id: "size_keywords",
    title: "גודל ומילות מפתח",
    render: (filters, patch) => <SizeKeywordsStep filters={filters} patch={patch} />,
  },
];

export default function OnboardingWizard({ initialFilters, onSubmitted }) {
  const merged = { ...DEFAULT_FILTERS, ...(initialFilters || {}) };
  // older saved filters may have safe_room as a single string - normalize to an array
  if (merged.safe_room && !Array.isArray(merged.safe_room)) merged.safe_room = [merged.safe_room];
  const [filters, setFilters] = useState(merged);
  const [stepIndex, setStepIndex] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function patch(partial) {
    setFilters((prev) => ({ ...prev, ...partial }));
  }

  async function handleContinue() {
    const step = STEPS[stepIndex];
    if (step.canContinue && !step.canContinue(filters)) return;

    if (stepIndex < STEPS.length - 1) {
      setStepIndex(stepIndex + 1);
      return;
    }

    setSubmitting(true);
    setError("");
    try {
      await postOnboarding(filters);
      await onSubmitted();
    } catch (e) {
      setError("שגיאה בשליחת הבקשה. נסה שוב.");
    } finally {
      setSubmitting(false);
    }
  }

  function handleBack() {
    if (stepIndex > 0) setStepIndex(stepIndex - 1);
  }

  const step = STEPS[stepIndex];
  const isLast = stepIndex === STEPS.length - 1;
  const continueDisabled = submitting || (step.canContinue ? !step.canContinue(filters) : false);

  return (
    <div className="app">
      <WizardShell
        stepIndex={stepIndex}
        totalSteps={STEPS.length}
        title={step.title}
        subtitle={step.subtitle}
        onBack={handleBack}
        onContinue={handleContinue}
        continueLabel={isLast ? (submitting ? "שולח..." : "שליחת בקשה") : "המשך"}
        continueDisabled={continueDisabled}
      >
        {step.render(filters, patch)}
      </WizardShell>
      {error && <p className="wizard-error">{error}</p>}
    </div>
  );
}
