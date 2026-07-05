import { useEffect, useState } from "react";
import { getStats, getConfig } from "./api";
import ListingsView from "./components/ListingsView";
import SettingsView from "./components/SettingsView";
import "./App.css";

const tg = window.Telegram?.WebApp;
const runningInTelegram = Boolean(tg?.initData);

export default function App() {
  const [tab, setTab] = useState(runningInTelegram ? "settings" : "listings");
  const [stats, setStats] = useState(null);
  const [authorized, setAuthorized] = useState(!runningInTelegram);

  useEffect(() => {
    if (tg) {
      tg.ready();
      tg.expand();
    }
    if (runningInTelegram) {
      getConfig()
        .then((config) => {
          const ownerId = String(config.telegram?.chat_id || "");
          const userId = String(tg.initDataUnsafe?.user?.id || "");
          setAuthorized(ownerId !== "" && ownerId === userId);
        })
        .catch(() => setAuthorized(false));
    }
  }, []);

  useEffect(() => {
    getStats().then(setStats).catch(() => {});
  }, [tab]);

  if (!authorized) {
    return <div className="app"><p>Not authorized.</p></div>;
  }

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
