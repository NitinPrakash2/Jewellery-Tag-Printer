import { useCallback, useEffect, useState } from "react";
import { Eye, Printer, Search } from "lucide-react";
import { Card, Notice, PremiumSelect, TextInput } from "../components/ui.jsx";
import { api } from "../services/api.js";

const PRESETS = ["", "today", "yesterday", "week", "month"];

function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function HistoryPage({ reloadKey, onReprintLoaded }) {
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [q, setQ] = useState("");
  const [purity, setPurity] = useState("");
  const [preset, setPreset] = useState("");
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState(null);
  const [view, setView] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setNotice(null);
    try {
      const res = await api.history({ q, purity, preset, limit: 100 });
      setItems(res.items || []);
      setTotal(res.total ?? 0);
    } catch {
      setNotice("Could not load history. Make sure the server is running.");
    } finally {
      setLoading(false);
    }
  }, [q, purity, preset]);

  useEffect(() => {
    load();
  }, [load, reloadKey]);

  async function reprint(id) {
    setNotice(null);
    try {
      const res = await api.reprint(id);
      if (res.ok) {
        await load();
        onReprintLoaded?.();
      } else {
        setNotice(typeof res.message === "string" ? res.message : "Reprint failed.");
      }
    } catch {
      setNotice("Could not reach the server.");
    }
  }

  async function viewRow(id) {
    try {
      setView(await api.historyOne(id));
    } catch {
      setNotice("Could not load that entry.");
    }
  }

  return (
    <div className="flex flex-col gap-5">
      <Card className="p-5">
        <div className="flex flex-wrap items-end gap-4">
          <label className="flex min-w-56 flex-1 flex-col gap-2">
            <span className="text-sm font-semibold text-slate-700">Search product / purity</span>
            <div className="relative">
              <Search size={17} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
              <TextInput value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ring, 18kt…" className="pl-10" />
            </div>
          </label>
          <label className="flex flex-col gap-2">
            <span className="text-sm font-semibold text-slate-700">Purity/HUID</span>
            <TextInput value={purity} onChange={(e) => setPurity(e.target.value)} placeholder="HUID" />
          </label>
          <label className="flex w-48 flex-col gap-2">
            <span className="text-sm font-semibold text-slate-700">Date Range</span>
            <PremiumSelect
              value={preset}
              onChange={setPreset}
              placeholder="All time"
              options={[
                { value: "", label: "All time" },
                { value: "today", label: "Today" },
                { value: "yesterday", label: "Yesterday" },
                { value: "week", label: "This week" },
                { value: "month", label: "This month" },
              ]}
            />
          </label>
          <span className="pb-2 text-sm font-bold text-slate-600">{loading ? "Loading…" : `${total} record${total !== 1 ? "s" : ""}`}</span>
        </div>
      </Card>

      {notice && <Notice>{notice}</Notice>}

      <Card className="overflow-x-auto p-0">
        <div className="overflow-hidden rounded-xl border border-slate-200/60">
          <table className="w-full min-w-3xl text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200/60 bg-gradient-to-r from-slate-50 via-blue-50 to-slate-50 text-slate-700">
                {["Date & Time", "Product", "Purity/HUID", "G.Wt.", "N.Wt.", "Copies", "Printer", "Status", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 font-bold text-slate-800">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((r) => (
                <tr key={r.id} className="border-b border-slate-100/60 transition duration-150 last:border-0 hover:bg-gradient-to-r hover:from-blue-50/40 hover:to-indigo-50/20">
                  <td className="px-4 py-3 text-slate-600">{fmtDate(r.printed_at)}</td>
                  <td className="px-4 py-3 font-semibold text-slate-900">{r.product_name || "—"}</td>
                  <td className="px-4 py-3 text-slate-700">{r.purity_huid || "—"}</td>
                  <td className="px-4 py-3 text-slate-700">{r.gross_weight != null ? `${r.gross_weight} g` : "—"}</td>
                  <td className="px-4 py-3 text-slate-700">{r.net_weight != null ? `${r.net_weight} g` : "—"}</td>
                  <td className="px-4 py-3 font-semibold text-slate-900">{r.copies}</td>
                  <td className="px-4 py-3 text-slate-700">{r.printer_name}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-bold ring-1 ring-inset ${r.status === "success" ? "bg-gradient-to-r from-green-50 to-emerald-50 text-green-700 ring-green-200/60" : "bg-gradient-to-r from-red-50 to-rose-50 text-red-700 ring-red-200/60"}`}>
                      {r.status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button onClick={() => viewRow(r.id)} title="View details" className="rounded-lg border border-slate-200 bg-white p-2 transition duration-150 hover:bg-blue-50 hover:border-blue-300">
                        <Eye size={16} className="text-slate-600" />
                      </button>
                      <button onClick={() => reprint(r.id)} title="Reprint (creates new entry)" className="rounded-lg border border-slate-200 bg-white p-2 transition duration-150 hover:bg-indigo-50 hover:border-indigo-300">
                        <Printer size={16} className="text-slate-600" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {items.length === 0 && !loading && (
                <tr><td colSpan={9} className="px-4 py-12 text-center text-slate-400 font-medium">No records yet. Print a tag to see it here.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {view && (
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-bold text-slate-900">Entry Details #{view.id}</h3>
            <button onClick={() => setView(null)} className="rounded-lg px-3 py-1 text-sm font-medium text-slate-500 transition hover:bg-slate-100 hover:text-slate-900">Close</button>
          </div>
          <pre className="overflow-x-auto rounded-lg bg-gradient-to-br from-slate-900 to-slate-800 p-4 text-xs text-green-400 font-mono">{JSON.stringify(view, null, 2)}</pre>
        </Card>
      )}
    </div>
  );
}
