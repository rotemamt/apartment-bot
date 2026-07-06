export default function WizardShell({ stepIndex, totalSteps, title, subtitle, onBack, onContinue, continueLabel, continueDisabled, children }) {
  return (
    <div className="wizard-shell">
      <div className="wizard-header">
        <span className="wizard-step-counter">שלב {stepIndex + 1} מתוך {totalSteps}</span>
        <div className="wizard-dots">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <span key={i} className={`wizard-dot${i === stepIndex ? " active" : i < stepIndex ? " done" : ""}`} />
          ))}
        </div>
      </div>

      <div className="wizard-card">
        <h2 className="wizard-title">{title}</h2>
        {subtitle && <p className="wizard-subtitle">{subtitle}</p>}
        <div className="wizard-body">{children}</div>
      </div>

      <div className="wizard-actions">
        <button type="button" className="wizard-btn-back" onClick={onBack} disabled={stepIndex === 0}>
          חזרה
        </button>
        <button type="button" className="wizard-btn-continue" onClick={onContinue} disabled={continueDisabled}>
          {continueLabel || "המשך"}
        </button>
      </div>
    </div>
  );
}
