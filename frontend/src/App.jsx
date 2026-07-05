import { useEffect, useState } from "react";
import { getStats } from "./api";
import ListingsView from "./components/ListingsView";
import SettingsView from "./components/SettingsView";
import "./App.css";

export default function App() {
  const [tab, setTab] = useState("listings");
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, [tab]);

  return (
    <div className="app">
      <header className="app-header">
        <h1>🏠 Apartment Bot</h1>
        {stats && (
          <div className="stats">
            <span>{stats.total} tracked</span>
            <span>{stats.matched} matched</span>
            <span>{stats.matched_today} today</span>
          </div>
        )}
        <nav className="tabs">
          <button className={tab === "listings" ? "active" : ""} onClick={() => setTab("listings")}>
            Listings
          </button>
          <button className={tab === "settings" ? "active" : ""} onClick={() => setTab("settings")}>
            Settings
          </button>
        </nav>
      </header>
      <main>{tab === "listings" ? <ListingsView /> : <SettingsView />}</main>
    </div>
  );
}
