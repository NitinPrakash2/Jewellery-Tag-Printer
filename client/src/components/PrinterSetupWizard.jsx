import { useEffect, useState } from "react";
import { CheckCircle2, Download, Loader2, Play, Printer, RefreshCw, XCircle } from "lucide-react";
import { api } from "../services/api.js";

/**
 * One-click printer setup for non-technical users:
 * detect printer -> auto-create label size -> readiness check -> test print.
 * If no printer exists, shows driver-install guidance instead.
 */
export default function PrinterSetupWizard({ printerName, widthMm, heightMm, onPrinterList, notify }) {
  const [steps, setSteps] = useState([]);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(false);
  const [help, setHelp] = useState(null);
  const [checking, setChecking] = useState(false);

  async function handleInstalledRefresh() {
    setChecking(true);
    const started = Date.now();
    try {
      await onPrinterList?.();
    } finally {
      const wait = Math.max(0, 800 - (Date.now() - started));
      setTimeout(() => setChecking(false), wait);
    }
  }

  useEffect(() => {
    api.driverHelp().then(setHelp).catch(() => {});
  }, []);

  async function run() {
    setRunning(true);
    setDone(false);
    setSteps([]);
    notify?.(null);
    try {
      const r = await api.printersSetup({
        printer_name: printerName,
        width_mm: widthMm,
        height_mm: heightMm,
      });
      setSteps(r.steps || []);
      setDone(true);
      if (!r.ok && !r.steps?.length) {
        // No printer at all -> fetch driver guidance.
        const h = await api.driverHelp().catch(() => null);
        setHelp(h);
        notify?.({ kind: "error", text: r.message || "No printer found." });
      } else {
        notify?.({
          kind: r.ok ? "success" : "error",
          text: r.message || (r.ok ? "Setup complete." : "Setup needs attention."),
        });
      }
      onPrinterList?.();
    } catch {
      notify?.({ kind: "error", text: "Could not reach the server." });
    } finally {
      setRunning(false);
    }
  }

  async function testPrint() {
    notify?.(null);
    try {
      const r = await api.testPrint(printerName);
      notify?.({ kind: r.ok ? "success" : "error", text: r.message });
    } catch {
      notify?.({ kind: "error", text: "Could not reach the server." });
    }
  }

  const drivers = help?.drivers ? Object.values(help.drivers) : [];
  const lname = String(printerName || "").toLowerCase();
  const matched =
    drivers.find((d) => (d.match || []).some((m) => lname.includes(m))) || null;
  // No printer chosen yet -> show every known driver; otherwise the match.
  const shown = matched ? [matched] : drivers;

  return (
    <div className="rounded-xl border border-slate-200 bg-gradient-to-b from-slate-50 to-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Printer size={16} className="text-slate-600" />
          <span className="text-sm font-bold text-slate-800">Printer Setup — One Click</span>
        </div>
        <div className="flex gap-2">
          <button
            onClick={run}
            disabled={running}
            className="inline-flex min-h-[34px] items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-1.5 text-[13px] font-semibold text-white shadow-sm transition hover:bg-slate-700 disabled:opacity-50"
          >
            {running ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
            {running ? "Setting up…" : "Run Setup"}
          </button>
          {done && (
            <button
              onClick={testPrint}
              className="inline-flex min-h-[34px] items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-[13px] font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
            >
              Test Print
            </button>
          )}
        </div>
      </div>

      {steps.length > 0 && (
        <ul className="mt-3 flex flex-col gap-1.5">
          {steps.map((s, i) => (
            <li key={`${s.key}-${i}`} className="flex items-start gap-2 text-[13px]">
              {s.ok ? (
                <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-green-600" />
              ) : (
                <XCircle size={15} className="mt-0.5 shrink-0 text-red-500" />
              )}
              <span className={s.ok ? "text-slate-700" : "font-medium text-red-700"}>{s.message}</span>
            </li>
          ))}
        </ul>
      )}

      {(done && steps.length === 0 && shown.length > 0) ||
      (!running && shown.length > 0 && (!printerName || /not detected/i.test(printerName))) ? (
        <div className="mt-3 flex flex-col gap-2.5">
          {(matched ? [matched] : shown).map((driver) => (
            <div key={driver.name} className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <div className="text-[13px] font-bold text-amber-900">
                No printer found — install the {driver.name} driver once:
              </div>
              <ol className="mt-1.5 flex list-decimal flex-col gap-1 pl-5 text-[13px] text-amber-900">
                {driver.steps.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ol>
              {driver.note && (
                <div className="mt-1.5 text-[13px] font-semibold text-amber-900">Note: {driver.note}</div>
              )}
              <div className="mt-2.5 flex flex-wrap gap-2">
                <a
                  href={driver.download_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex min-h-[34px] items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-1.5 text-[13px] font-semibold text-white shadow-sm transition hover:bg-slate-700"
                >
                  <Download size={14} />
                  Download {driver.name} Driver
                </a>
                <button
                  onClick={handleInstalledRefresh}
                  disabled={checking}
                  className="inline-flex min-h-[34px] items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3.5 py-1.5 text-[13px] font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50 active:scale-95 disabled:opacity-60"
                >
                  <RefreshCw size={14} className={checking ? "animate-spin" : ""} />
                  {checking ? "Checking…" : "I installed it — Refresh"}
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {!done && steps.length === 0 && (
        <p className="mt-2 text-xs text-slate-400">
          Finds your printer, creates the {widthMm} × {heightMm} mm label size in Windows automatically, and
          checks readiness. No Windows Settings needed.
        </p>
      )}
    </div>
  );
}
