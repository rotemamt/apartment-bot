import { useEffect, useState } from "react";
import { getStats } from "./api";
import ListingsView from "./components/ListingsView";
import SettingsView from "./components/SettingsView";
import "./App.css";

const tg = window.Telegram?.WebApp;
const runningInTelegram = Boolean(tg?.initData);

// "checking" | "authorized" | "pending" | "denied"
export default function App() {
  const [tab, setTab] = useState("settings");
  const [stats, setStats] = useState(null);
  const [authState, setAuthState] = useState(runningInTelegram ? "checking" : "denied");

  useEffect(() => {
    if (tg) {
      tg.ready();
      tg.expand();
    }
    if (!runningInTelegram) return;
    getStats()
      .then((s) => {
        setStats(s);
        setAuthState("authorized");
      })
      .catch((err) => {
        setAuthState(err.status === 403 ? "pending" : "denied");
      });
  }, []);

  useEffect(() => {
    if (authState === "authorized") {
      getStats().then(setStats).catch(() => {});
    }
  }, [tab, authState]);

  if (authState === "checking") {
    return <div className="app"><p>Loading...</p></div>;
  }
  if (authState === "pending") {
    return <div className="app"><p>הבקשה שלך ממתינה לאישור מנהל. שלח /start לבוט אם עוד לא עשית זאת.</p></div>;
  }
  if (authState === "denied") {
    return <div className="app"><p>Not authorized. Open this from the Telegram bot.</p></div>;
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
