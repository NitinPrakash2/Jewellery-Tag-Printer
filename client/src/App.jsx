import { useCallback, useEffect, useState } from "react";
import { History, Printer, Settings } from "lucide-react";
import HistoryPage from "./pages/HistoryPage.jsx";
import PrintPage from "./pages/PrintPage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import { shopInitials } from "./lib/tagSvg.js";
import { api } from "./services/api.js";

const TABS = [
  { id: "print", label: "PRINT", icon: Printer },
  { id: "history", label: "HISTORY", icon: History },
  { id: "settings", label: "SETTINGS", icon: Settings },
];

export default function App() {
  const [tab, setTab] = useState("print");
  const [settings, setSettings] = useState(null);
  const [serverOk, setServerOk] = useState(null);
  const [historyKey, setHistoryKey] = useState(0);

  const loadSettings = useCallback(async () => {
    try {
      setSettings(await api.settingsAll());
    } catch {
      setSettings(null);
    }
  }, []);

  useEffect(() => {
    api.health()
      .then((h) => setServerOk(Boolean(h.db_ok)))
      .catch(() => setServerOk(false));
    loadSettings();
  }, [loadSettings]);

  const shopName = settings?.shop?.name || "MK JEWELLERS";
  const mono = shopInitials(shopName) || "MK";

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gradient-to-br from-slate-50 via-blue-50 to-slate-100 text-slate-900">
      {/* Brand header */}
      <header className="z-20 shrink-0 border-b border-slate-200/50 bg-gradient-to-r from-white via-blue-50/40 to-white shadow-[0_2px_20px_rgba(79,70,229,0.08)] backdrop-blur-md">
        <div className="flex w-full flex-wrap items-center justify-between gap-4 px-7 py-5">
          <div className="flex items-center gap-4">
            <div
              className="flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 font-serif text-2xl font-black italic text-white shadow-lg"
              style={{ fontFamily: "Georgia,serif" }}
            >
              {mono}
            </div>
            <span>
              <span
                className="block text-[28px] font-bold leading-tight text-slate-900"
                style={{ fontFamily: "Georgia,serif" }}
              >
                Jewellery Tag Printer
              </span>
              <span className="mt-1 block text-[11px] font-bold tracking-[0.4em] text-indigo-600">
                PREMIUM PRECISION
              </span>
            </span>
          </div>
          <div className="text-right">
            <div
              className="text-[26px] font-bold tracking-wide text-slate-900"
              style={{ fontFamily: "Georgia,serif" }}
            >
              {shopName.toUpperCase()}
            </div>
            <div className="text-[11px] font-bold tracking-[0.4em] text-indigo-600">
              TRUST IN EVERY CARAT
            </div>
          </div>
        </div>
        <div className="flex w-full items-center gap-1 px-7 pb-3">
          {TABS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-[13px] font-semibold transition duration-200 ${
                tab === id
                  ? "bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-[0_4px_12px_rgba(79,70,229,0.3)]"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
          <span className="ml-auto flex items-center gap-2.5 text-xs font-medium text-slate-600">
            <span
              className={`inline-block h-2.5 w-2.5 rounded-full shadow-md ${serverOk ? "bg-green-500" : "bg-red-500"}`}
              title={serverOk ? "Server connected" : "Server not reachable"}
            />
            {serverOk == null ? "connecting…" : serverOk ? "server ok" : "offline"}
          </span>
        </div>
      </header>

      <main className="min-h-0 w-full flex-1 overflow-y-auto px-4 py-6 sm:px-7">
        {serverOk === false && (
          <div className="mb-5 rounded-lg border border-red-200/60 bg-gradient-to-r from-red-50 to-rose-50 px-4 py-3 text-sm font-medium text-red-800 shadow-[0_2px_8px_rgba(239,68,68,0.1)]">
            Cannot reach the API server. Start it with: <code className="rounded bg-red-100/50 px-2 py-1 font-mono text-xs">uvicorn app.main:app</code> in the server folder.
          </div>
        )}
        {tab === "print" && (
          <PrintPage
            settings={settings}
            onSettingsSaved={loadSettings}
            refreshHistorySignal={() => setHistoryKey((k) => k + 1)}
          />
        )}
        {tab === "history" && (
          <HistoryPage reloadKey={historyKey} onReprintLoaded={() => setHistoryKey((k) => k + 1)} />
        )}
        {tab === "settings" && <SettingsPage settings={settings} onSaved={loadSettings} />}
      </main>
    </div>
  );
}
