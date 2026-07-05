import { useEffect, useState } from "react";
import { getListings, setListingStatus } from "../api";
import ListingCard from "./ListingCard";
import MapView from "./MapView";

export default function ListingsView() {
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("");
  const [source, setSource] = useState("");
  const [matchedOnly, setMatchedOnly] = useState(true);
  const [sortBy, setSortBy] = useState("first_seen_at");
  const [order, setOrder] = useState("desc");
  const [showMap, setShowMap] = useState(false);

  function load() {
    setLoading(true);
    setError(null);
    getListings({ status: status || undefined, source: source || undefined, matchedOnly, sortBy, order })
      .then(setListings)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }

  useEffect(load, [status, source, matchedOnly, sortBy, order]);

  async function handleStatusChange(id, newStatus) {
    const updated = await setListingStatus(id, newStatus);
    setListings((prev) => prev.map((l) => (l.id === id ? updated : l)));
  }

  return (
    <div>
      <div className="controls">
        <label>
          Status:
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            <option value="new">New</option>
            <option value="seen">Seen</option>
            <option value="interested">Interested</option>
            <option value="rejected">Rejected</option>
          </select>
        </label>
        <label>
          Source:
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">All</option>
            <option value="yad2">Yad2</option>
            <option value="telegram">Telegram</option>
          </select>
        </label>
        <label>
          Sort by:
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
            <option value="first_seen_at">Date found</option>
            <option value="price">Price</option>
            <option value="rooms">Rooms</option>
            <option value="posted_date">Date posted</option>
          </select>
        </label>
        <label>
          Order:
          <select value={order} onChange={(e) => setOrder(e.target.value)}>
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </label>
        <label>
          <input type="checkbox" checked={matchedOnly} onChange={(e) => setMatchedOnly(e.target.checked)} />
          Matches only
        </label>
        <label>
          <input type="checkbox" checked={showMap} onChange={(e) => setShowMap(e.target.checked)} />
          Show map
        </label>
        <button onClick={load}>Refresh</button>
      </div>

      {error && <div className="error">Error: {error}</div>}
      {loading && <div>Loading...</div>}

      {showMap && <MapView listings={listings} />}

      <div className="listing-grid">
        {listings.map((listing) => (
          <ListingCard key={listing.id} listing={listing} onStatusChange={handleStatusChange} />
        ))}
      </div>
      {!loading && listings.length === 0 && <div>No listings match these filters.</div>}
    </div>
  );
}
