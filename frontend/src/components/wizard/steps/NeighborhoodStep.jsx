import NeighborhoodMap from "../../NeighborhoodMap";

const MAP_SUPPORTED_CITIES = ["תל אביב-יפו", "רמת גן", "גבעתיים"];

export default function NeighborhoodStep({ cities, neighborhoods, onChange }) {
  const mappableCities = cities.filter((c) => MAP_SUPPORTED_CITIES.includes(c));

  if (mappableCities.length === 0) {
    return (
      <p className="wizard-note">
        מפת שכונות זמינה כרגע רק לתל אביב-יפו, רמת גן וגבעתיים. אפשר לדלג על השלב הזה.
      </p>
    );
  }

  return <NeighborhoodMap cities={mappableCities} selected={neighborhoods} onChange={onChange} />;
}
