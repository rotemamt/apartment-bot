import { useEffect, useRef, useState } from "react";
import { getMe, getStats } from "./api";
import ListingsView from "./components/ListingsView";
import SettingsView from "./components/SettingsView";
import OnboardingWizard from "./components/wizard/OnboardingWizard";
import PendingApprovalScreen from "./components/PendingApprovalScreen";
import "./App.css";

const tg = window.Telegram?.WebApp;
const runningInTelegram = Boolean(tg?.initData);
const PENDING_POLL_MS = 10000;

// "checking" | "new" | "onboarding" | "pending_approval" | "approved" | "blocked" | "denied"
export default function App() {
  const [tab, setTab] = useState("settings");
  const [stats, setStats] = useState(null);
  const [meState, setMeState] = useState(runningInTelegram ? "checking" : "denied");
  const [initialFilters, setInitialFilters] = useState(null);
  const pollRef = useRef(null);

  function refreshMe() {
    return getMe()
      .then((data) => {
        setMeState(data.status);
        setInitialFilters(data.filters ?? null);
        return data;
      })
      .catch(() => setMeState("denied"));
  }

  useEffect(() => {
    if (tg) {
      tg.ready();
      tg.expand();
    }
    if (!runningInTelegram) return;
    refreshMe();
  }, []);

  useEffect(() => {
    if (meState === "pending_approval") {
      pollRef.current = setInterval(refreshMe, PENDING_POLL_MS);
      return () => clearInterval(pollRef.current);
    }
  }, [meState]);

  useEffect(() => {
    if (meState === "approved") {
      getStats().then(setStats).catch(() => {});
    }
  }, [tab, meState]);

  if (meState === "checking") {
    return <div className="app app-center"><p>טוען...</p></div>;
  }
  if (meState === "denied") {
    return <div className="app app-center"><p>יש לפתוח את האפליקציה דרך הבוט בטלגרם.</p></div>;
  }
  if (meState === "new" || meState === "onboarding") {
    return <OnboardingWizard initialFilters={initialFilters} onSubmitted={refreshMe} />;
  }
  if (meState === "pending_approval") {
    return <PendingApprovalScreen />;
  }
  if (meState === "blocked") {
    return <div className="app app-center"><p>הבקשה שלך נדחתה על ידי המנהל.</p></div>;
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
