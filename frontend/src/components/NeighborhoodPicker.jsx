import { useEffect, useState } from "react";
import { getNeighborhoods } from "../api";

export default function NeighborhoodPicker({ selected, onChange }) {
  const [byCity, setByCity] = useState({});

  useEffect(() => {
    getNeighborhoods().then(setByCity).catch(() => {});
  }, []);

  function toggle(name) {
    if (selected.includes(name)) {
      onChange(selected.filter((n) => n !== name));
    } else {
      onChange([...selected, name]);
    }
  }

  return (
    <div className="neighborhood-picker">
      {Object.entries(byCity).map(([city, neighborhoods]) => (
        <div key={city} className="neighborhood-city-group">
          <div className="neighborhood-city-name">{city}</div>
          <div className="neighborhood-list">
            {neighborhoods.map((name) => (
              <label key={name} className="neighborhood-item">
                <input type="checkbox" checked={selected.includes(name)} onChange={() => toggle(name)} />
                {name}
              </label>
            ))}
          </div>
        </div>
      ))}
      {selected.length > 0 && (
        <button type="button" className="neighborhood-clear" onClick={() => onChange([])}>
          Clear all ({selected.length} selected)
        </button>
      )}
    </div>
  );
}
