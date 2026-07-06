const KNOWN_CITIES = ["תל אביב-יפו", "רמת גן", "גבעתיים"];

export default function CityStep({ cities, onChange }) {
  const otherCity = cities.find((c) => !KNOWN_CITIES.includes(c)) || "";

  function toggleCity(city) {
    if (cities.includes(city)) {
      onChange(cities.filter((c) => c !== city));
    } else {
      onChange([...cities, city]);
    }
  }

  function setOtherCity(value) {
    const withoutOther = cities.filter((c) => KNOWN_CITIES.includes(c));
    onChange(value.trim() ? [...withoutOther, value.trim()] : withoutOther);
  }

  return (
    <div className="city-step">
      <div className="city-chips">
        {KNOWN_CITIES.map((city) => (
          <button
            key={city}
            type="button"
            className={`city-chip${cities.includes(city) ? " selected" : ""}`}
            onClick={() => toggleCity(city)}
          >
            {city}
          </button>
        ))}
      </div>
      <label className="city-other-label">
        עיר אחרת (לא זמינה עדיין עם מפת שכונות)
        <input
          type="text"
          placeholder="הקלד שם עיר..."
          value={otherCity}
          onChange={(e) => setOtherCity(e.target.value)}
        />
      </label>
    </div>
  );
}
