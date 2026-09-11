import { useCallback, useEffect, useRef, useState } from "react";
import { Activity, Pause, Play, Trash2 } from "lucide-react";
import { api } from "../services/api.js";

const SOURCE_STYLE = {
  PRINTER: "bg-amber-100 text-amber-900 ring-amber-200",
  PRINT: "bg-green-100 text-green-900 ring-green-200",
  USB: "bg-blue-100 text-blue-900 ring-blue-200",
  APP: "bg-slate-200 text-slate-800 ring-slate-300",
  SERVER: "bg-red-100 text-red-900 ring-red-200",
  DATABASE: "bg-orange-100 text-orange-900 ring-orange-200",
};

function fmtTime(iso) {
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return "";
  }
}

/**
 * Live error monitor: polls the server event feed every 4 seconds and shows
 * WHERE each problem is (app / printer / usb / server / database) in plain
 * words a non-technical user can read — and forward for fixing.
 */
export default function ErrorMonitor() {
  const [events, setEvents] = useState([]);
  const [live, setLive] = useState(true);
  const timer = useRef(null);

  const load = useCallback(async () => {
    try {
      const r = await api.diagEvents(100);
      setEvents(r.events || []);
    } catch {
      /* server unreachable — feed simply stays as-is */
    }
  }, []);

  useEffect(() => {
    load();
    if (!live) return undefined;
    timer.current = setInterval(load, 4000);
    return () => clearInterval(timer.current);
  }, [load, live]);

  async function clearAll() {
    try {
      await api.diagClear();
    } catch {
      /* ignore */
    }
    setEvents([]);
  }

  const errors = events.filter((e) => e.level === "error" || e.level === "critical");

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <div className="flex items-center gap-2">
          <Activity size={16} className="text-slate-500" />
          <span className="text-[15px] font-bold text-slate-800">Live Error Monitor</span>
          {live ? (
            <span className="flex items-center gap-1.5 text-[11px] font-medium text-slate-400">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-green-500" />
              </span>
              watching
            </span>
          ) : (
            <span className="text-[11px] font-medium text-slate-400">paused</span>
          )}
        </div>
        <div className="flex gap-1.5">
          <button
            onClick={() => setLive((v) => !v)}
            title={live ? "Pause live feed" : "Resume live feed"}
            className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 shadow-sm transition hover:bg-slate-50 active:scale-90"
          >
            {live ? <Pause size={13} /> : <Play size={13} />}
          </button>
          <button
            onClick={clearAll}
            title="Clear all events"
            className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 shadow-sm transition hover:bg-slate-50 hover:text-red-600 active:scale-90"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      <div className="max-h-64 overflow-y-auto px-2 py-2">
        {events.length === 0 ? (
          <p className="px-2 py-6 text-center text-[13px] text-slate-400">
            All quiet — no errors recorded. Print, test or set up and activity will appear here.
          </p>
        ) : (
          <ul className="flex flex-col">
            {events.map((e, i) => (
              <li
                key={`${e.ts}-${i}`}
                className="flex items-start gap-2 rounded-lg px-2 py-1.5 hover:bg-slate-50"
              >
                <span
                  className={`mt-0.5 inline-block h-2 w-2 shrink-0 rounded-full ${
                    e.level === "error" || e.level === "critical" ? "bg-red-500" : "bg-green-500"
                  }`}
                />
                <span className="w-16 shrink-0 text-xs text-slate-400">{fmtTime(e.ts)}</span>
                <span
                  className={`shrink-0 rounded px-1.5 py-px text-[10px] font-bold tracking-wide ring-1 ring-inset ${
                    SOURCE_STYLE[e.source] || SOURCE_STYLE.APP
                  }`}
                >
                  {e.source}
                </span>
                <span className="min-w-0 flex-1 text-[13px] text-slate-700">{e.message}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="border-t border-slate-100 px-4 py-2 text-xs text-slate-400">
        {errors.length === 0
          ? "No errors right now."
          : `${errors.length} error(s) need attention — newest first. Show this screen when asking for help.`}
      </div>
    </div>
  );
}
