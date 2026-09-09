import { useCallback, useEffect, useRef, useState } from "react";
import { Cable, CheckCircle2, Circle, Download, Loader2, Play, RefreshCw, Usb } from "lucide-react";
import { api } from "../services/api.js";

/**
 * Live USB watchdog: polls every 3s. The moment a barcode printer is
 * plugged into USB, this panel names it, identifies the model, and shows
 * exactly what to do next — all in plain language.
 */
export default function UsbLivePanel({ printerName, widthMm, heightMm, onPrinterList, onAutoSelect, notify }) {
  const [live, setLive] = useState(null);
  const [help, setHelp] = useState(null);
  const [settingUp, setSettingUp] = useState(false);
  const [setupDone, setSetupDone] = useState(false);
  const [checking, setChecking] = useState(false);
  const timer = useRef(null);

  const poll = useCallback(async () => {
    try {
      const data = await api.usbLive(printerName);
      setLive(data);
      // Auto-select: a real printer arrived and nothing usable is selected.
      const VIRTUAL = ["microsoft print to pdf", "onenote", "fax", "xps document"];
      const installed = data.installed || [];
      const real = installed.filter(
        (n) => !VIRTUAL.some((v) => n.toLowerCase().includes(v))
      );
      const sel = printerName || "";
      const selMissing =
        !sel || /not detected/i.test(sel) || !installed.includes(sel);
      if (selMissing && real.length > 0) {
        const det = String(data.detected_model || "").toLowerCase();
        const tok = det.split(/[\s\-_()]+/).find((t) => t.length > 2);
        const pick =
          (tok && real.find((n) => n.toLowerCase().includes(tok))) || real[0];
        if (pick) onAutoSelect?.(pick);
      }
    } catch {
      setLive((prev) => prev || { available: false });
    }
  }, [printerName, onAutoSelect]);

  useEffect(() => {
    poll();
    timer.current = setInterval(poll, 3000);
    return () => clearInterval(timer.current);
  }, [poll]);

  // Manual refresh with visible spin so the user sees it working.
  async function manualPoll() {
    setChecking(true);
    const started = Date.now();
    try {
      await poll();
    } finally {
      const wait = Math.max(0, 700 - (Date.now() - started));
      setTimeout(() => setChecking(false), wait);
    }
  }

  useEffect(() => {
    api.driverHelp().then(setHelp).catch(() => {});
  }, []);

  useEffect(() => {
    setSetupDone(false);
  }, [printerName, widthMm, heightMm]);

  async function runSetup() {
    setSettingUp(true);
    notify?.(null);
    try {
      const r = await api.printersSetup({
        printer_name: printerName,
        width_mm: widthMm,
        height_mm: heightMm,
      });
      if (r.ok) {
        setSetupDone(true);
        notify?.({ kind: "success", text: r.message || "Setup complete." });
      } else {
        notify?.({ kind: "error", text: r.message || "Setup needs attention." });
      }
      onPrinterList?.();
      poll();
    } catch {
      notify?.({ kind: "error", text: "Could not reach the server." });
    } finally {
      setSettingUp(false);
    }
  }

  const devices = live?.usb_devices || [];
  const usbOk = devices.length > 0;
  const driverOk = Boolean(live?.driver_installed);
  const drivers = help?.drivers ? Object.entries(help.drivers) : [];
  const matchedKey = live?.driver_key || null;
  const matched = matchedKey ? help?.drivers?.[matchedKey] : null;
  const showDrivers = matched ? [[matchedKey, matched]] : drivers;

  const step = (ok, title, sub) => (
    <li className="flex items-start gap-2 text-[13px]">
      {ok ? (
        <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-green-600" />
      ) : (
        <Circle size={15} className="mt-0.5 shrink-0 text-slate-300" />
      )}
      <span>
        <span className={`font-semibold ${ok ? "text-slate-800" : "text-slate-500"}`}>{title}</span>
        {sub && <span className="block text-xs font-normal text-slate-400">{sub}</span>}
      </span>
    </li>
  );

  return (
    <div className="rounded-xl border border-slate-200 bg-gradient-to-b from-slate-50 to-white p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-60" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
          </span>
          <span className="text-sm font-bold text-slate-800">USB Printer — Live</span>
          <span className="text-[11px] font-medium text-slate-400">checking every 3s</span>
        </div>
        <button
          onClick={manualPoll}
          disabled={checking}
          title="Check now"
          className="rounded-lg border border-slate-200 bg-white p-1.5 text-slate-500 shadow-sm transition hover:bg-slate-50 active:scale-90 disabled:opacity-60"
        >
          <RefreshCw size={13} className={checking ? "animate-spin" : ""} />
        </button>
      </div>

      {!live ? (
        <p className="mt-2 flex items-center gap-1.5 text-[13px] text-slate-400">
          <Loader2 size={14} className="animate-spin" /> Watching USB ports…
        </p>
      ) : live.available === false ? (
        <p className="mt-2 text-[13px] text-slate-500">
          USB watching is unavailable on this machine. Use Run Setup below instead.
        </p>
      ) : !usbOk ? (
        <div className="mt-2.5 flex items-start gap-2.5 rounded-lg border border-dashed border-slate-300 bg-white p-3">
          <Usb size={18} className="mt-0.5 shrink-0 text-slate-400" />
          <p className="text-[13px] text-slate-600">
            <span className="font-semibold text-slate-800">No USB printer plugged in.</span>
            <span className="block text-xs text-slate-400">
              Connect your barcode printer with the USB cable and switch it on — it will appear here automatically.
            </span>
          </p>
        </div>
      ) : (
        <div className="mt-2.5 rounded-lg border border-slate-200 bg-white p-3">
          <div className="flex flex-wrap items-center gap-2">
            <Cable size={15} className="text-slate-500" />
            <span className="text-[13px] font-bold text-slate-800">
              {live.detected_model || devices[0].name}
            </span>
            {matched ? (
              <span className="rounded-full bg-slate-900 px-2 py-px text-[11px] font-semibold text-white">
                {matched.name}
              </span>
            ) : (
              <span className="rounded-full bg-slate-100 px-2 py-px text-[11px] font-medium text-slate-500">
                Unknown model — generic setup
              </span>
            )}
          </div>
          {devices.length > 1 && (
            <p className="mt-1 text-xs text-slate-400">+ {devices.length - 1} more USB device(s)</p>
          )}
        </div>
      )}

      {live?.available !== false && (
        <ul className="mt-3 flex flex-col gap-1.5">
          {step(usbOk, "Printer plugged into USB", usbOk ? undefined : "Waiting for you to plug it in…")}
          {step(driverOk, "Driver installed", driverOk ? undefined : "Needed once — guide below")}
          {step(setupDone, "Label size ready", setupDone ? `${widthMm} × ${heightMm} mm set` : "Press Run Setup")}
        </ul>
      )}

      {!driverOk && usbOk && showDrivers.length > 0 && (
        <div className="mt-2.5 flex flex-col gap-2">
          {showDrivers.map(([key, d]) => (
            <div key={key} className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <div className="text-[13px] font-bold text-amber-900">
                Install the {d.name} driver once:
              </div>
              <ol className="mt-1 list-decimal pl-5 text-[13px] text-amber-900">
                {d.steps.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ol>
              {d.note && <div className="mt-1 text-[13px] font-semibold text-amber-900">Note: {d.note}</div>}
              <a
                href={d.download_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex min-h-[34px] items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-1.5 text-[13px] font-semibold text-white shadow-sm transition hover:bg-slate-700"
              >
                <Download size={14} /> Download {d.name} Driver
              </a>
            </div>
          ))}
        </div>
      )}

      {usbOk && (
        <button
          onClick={runSetup}
          disabled={settingUp}
          className="mt-3 inline-flex min-h-[34px] items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-1.5 text-[13px] font-semibold text-white shadow-sm transition hover:bg-slate-700 disabled:opacity-50"
        >
          {settingUp ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
          {settingUp ? "Setting up…" : setupDone ? "Run Setup Again" : "Run Setup"}
        </button>
      )}
    </div>
  );
}
