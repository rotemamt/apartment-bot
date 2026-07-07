export default function NameStep({ value, onChange }) {
  return (
    <div className="name-step">
      <input
        type="text"
        className="name-step-input"
        placeholder="השם שלך"
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
        autoFocus
      />
    </div>
  );
}
