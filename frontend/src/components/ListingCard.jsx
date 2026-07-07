const SOURCE_LABELS = { yad2: "Yad2", telegram: "Telegram" };
const STATUS_OPTIONS = ["new", "seen", "interested", "rejected"];
const PREFERRED_FEATURE_LABELS = {
  elevator: "מעלית",
  renovated: "משופצת",
  pets_allowed: "חיות מחמד מותרות",
  parking: "חניה",
  no_brokerage_fee: "ללא דמי תיווך",
  balcony: "מרפסת",
};

function formatDate(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleDateString();
}

export default function ListingCard({ listing, onStatusChange }) {
  const posted = formatDate(listing.posted_date);

  return (
    <div className="listing-card">
      {listing.photo_url ? (
        <img className="listing-photo" src={listing.photo_url} alt="" loading="lazy" />
      ) : (
        <div className="listing-photo listing-photo-placeholder">No photo</div>
      )}
      <div className="listing-body">
        <div className="listing-header">
          <span className="listing-price">{listing.price != null ? `${listing.price.toLocaleString()} ₪` : "—"}</span>
          <span className={`source-badge source-${listing.source}`}>
            {SOURCE_LABELS[listing.source] || listing.source}
          </span>
        </div>
        <div className="listing-meta">
          {listing.rooms != null && <span>{listing.rooms} rooms</span>}
          {listing.floor != null && <span>floor {listing.floor}</span>}
          {listing.sqm != null && <span>{listing.sqm} m²</span>}
          {posted && <span>posted {posted}</span>}
        </div>
        {listing.address && <div className="listing-address">{listing.address}</div>}
        {listing.matched_features && listing.matched_features.length > 0 && (
          <div className="listing-features">✅ {listing.matched_features.join(", ")}</div>
        )}
        {listing.preferred_features && listing.preferred_features.length > 0 && (
          <div className="listing-preferred-features">
            {listing.preferred_features.map((f) => (
              <span key={f} className="preferred-feature-pill">
                {PREFERRED_FEATURE_LABELS[f] || f}
              </span>
            ))}
          </div>
        )}
        <a className="listing-link" href={listing.url} target="_blank" rel="noreferrer">
          View listing ↗
        </a>
        <div className="status-buttons">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s}
              className={`status-btn ${listing.status === s ? "active" : ""}`}
              onClick={() => onStatusChange(listing.id, s)}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
