import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

// react-leaflet's default marker icon paths break under Vite's asset bundling
// unless explicitly re-pointed at the bundled image URLs like this.
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const TEL_AVIV_CENTER = [32.0853, 34.7818];

export default function MapView({ listings }) {
  const withCoords = listings.filter((l) => l.latitude != null && l.longitude != null);

  return (
    <div className="map-container">
      <MapContainer center={TEL_AVIV_CENTER} zoom={12} style={{ height: "400px", width: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {withCoords.map((l) => (
          <Marker key={l.id} position={[l.latitude, l.longitude]}>
            <Popup>
              <strong>{l.price != null ? `${l.price.toLocaleString()} ₪` : "—"}</strong>
              <br />
              {l.address}
              <br />
              <a href={l.url} target="_blank" rel="noreferrer">
                View listing
              </a>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      {withCoords.length === 0 && (
        <div className="map-empty-note">No listings with location data in the current view.</div>
      )}
    </div>
  );
}
