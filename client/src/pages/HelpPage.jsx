import { useEffect, useState } from "react";
import {
  BookOpen,
  Cable,
  CheckCircle2,
  Download,
  ListChecks,
  MousePointerClick,
  Printer,
  Ruler,
  Settings2,
  TestTube2,
  TriangleAlert,
} from "lucide-react";
import { Card, CardTitle } from "../components/ui.jsx";
import { api } from "../services/api.js";

function Step({ n, icon: Icon, title, children }) {
  return (
    <div className="flex gap-4 rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_8px_rgba(15,23,42,0.05)]">
      <div className="flex flex-col items-center">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-sm font-bold text-white">
          {n}
        </span>
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <Icon size={16} className="text-slate-500" />
          <h3 className="text-[15px] font-bold text-slate-900">{title}</h3>
        </div>
        <div className="mt-1.5 flex flex-col gap-2 text-sm leading-relaxed text-slate-600">{children}</div>
      </div>
    </div>
  );
}

function TroubleRow({ problem, fix }) {
  return (
    <div className="grid grid-cols-1 gap-1 border-b border-slate-100 px-4 py-3 last:border-0 sm:grid-cols-[220px_minmax(0,1fr)] sm:gap-3">
      <span className="text-sm font-semibold text-slate-800">{problem}</span>
      <span className="text-sm text-slate-600">{fix}</span>
    </div>
  );
}

export default function HelpPage({ onGoSettings }) {
  const [drivers, setDrivers] = useState([]);

  useEffect(() => {
    api
      .driverHelp()
      .then((h) => setDrivers(h?.drivers ? Object.values(h.drivers) : []))
      .catch(() => {});
  }, []);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 pb-4">
      <Card>
        <CardTitle icon={BookOpen}>How to Connect Printer</CardTitle>
        <div className="px-5 py-4">
          <p className="text-sm leading-relaxed text-slate-600">
            Follow these steps once per computer. After setup, daily printing is just: fill the
            form → <span className="font-semibold text-slate-800">Print Tag</span> → collect the label.
            You never need to open Windows Settings — the app handles the technical parts.
          </p>
        </div>
      </Card>

      <Step n="1" icon={Cable} title="Plug the printer in (USB + power)">
        <p>
          Connect your barcode printer to this computer with the USB cable and switch the printer
          <span className="font-semibold"> ON</span>. Keep the computer connected to the internet.
        </p>
        <p className="rounded-lg bg-slate-50 px-3 py-2 text-[13px]">
          Tip: open <span className="font-semibold">Settings → Printer Configuration</span> and watch the
          green <span className="font-semibold">USB Printer — Live</span> panel. Your printer's name appears
          there by itself within a few seconds of plugging it in.
        </p>
      </Step>

      <Step n="2" icon={Download} title="Install the driver (one time only)">
        <p>
          A driver teaches Windows how to talk to your printer. It is installed
          <span className="font-semibold"> on this computer</span> (not inside the app), once — then it stays forever.
          Pick your brand below:
        </p>
        <div className="flex flex-col gap-2.5">
          {drivers.map((d) => (
            <div key={d.name} className="rounded-xl border border-slate-200 bg-slate-50/60 p-3.5">
              <div className="text-sm font-bold text-slate-800">{d.name}</div>
              <ol className="mt-1 list-decimal pl-5 text-[13px] text-slate-600">
                {d.steps.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ol>
              {d.note && <div className="mt-1 text-[13px] font-semibold text-amber-700">Note: {d.note}</div>}
              <a
                href={d.download_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-flex min-h-[34px] items-center gap-1.5 rounded-lg bg-slate-900 px-3.5 py-1.5 text-[13px] font-semibold text-white shadow-sm transition hover:bg-slate-700 active:scale-95"
              >
                <Download size={14} /> Download {d.name} Driver
              </a>
            </div>
          ))}
          {drivers.length === 0 && (
            <p className="text-[13px] text-slate-400">Loading driver links… (needs the server running)</p>
          )}
        </div>
        <p className="rounded-lg bg-slate-50 px-3 py-2 text-[13px]">
          TVS LP 46 Neo is mostly <span className="font-semibold">plug-and-play</span>: USB + power + internet is
          often enough — Windows installs it by itself. DCode needs its installer run once.
        </p>
      </Step>

      <Step n="3" icon={MousePointerClick} title="Select your printer in the app">
        <p>
          Go to <span className="font-semibold">Settings → Printer Configuration → Selected printer</span>.
          A newly connected printer is usually <span className="font-semibold">selected automatically</span>;
          otherwise pick it from the list (real printers appear under
          <span className="font-semibold"> “Installed on this PC”</span>) and press <span className="font-semibold">Save</span>.
        </p>
      </Step>

      <Step n="4" icon={Settings2} title="Run Setup (automatic label size)">
        <p>
          Press <span className="font-semibold">Run Setup</span>. The app creates your exact label size
          (e.g. 110 × 12 mm) in Windows by itself and makes it the printer's default.
          Each step shows ✓ as it completes. No admin rights needed in most cases.
        </p>
        <p className="rounded-lg bg-slate-50 px-3 py-2 text-[13px]">
          Width limits are enforced live: DCode prints max <span className="font-semibold">104 mm</span>,
          TVS max <span className="font-semibold">108 mm</span>. If your tag is wider, the app warns and
          offers a fitting size in one click.
        </p>
      </Step>

      <Step n="5" icon={TestTube2} title="Test print, then go live">
        <p>
          Press <span className="font-semibold">Test Print</span>. A small test label should come out.
          If it prints slightly shifted, open <span className="font-semibold">Settings → Print Calibration</span>,
          adjust the offset by 0.5–1 mm, and test again.
        </p>
      </Step>

      <Card>
        <CardTitle icon={ListChecks}>Daily printing</CardTitle>
        <div className="px-5 py-4 text-sm leading-relaxed text-slate-600">
          <span className="font-semibold text-slate-800">PRINT tab →</span> Purity, Product, Gross + Less weights
          (Net is automatic) → Copies → <span className="font-semibold text-slate-800">PRINT TAG</span>.
          Every print is saved in <span className="font-semibold text-slate-800">HISTORY</span> with date and time —
          press the printer icon on any row to reprint it.
        </div>
      </Card>

      <Card>
        <CardTitle icon={TriangleAlert}>If something goes wrong</CardTitle>
        <div className="py-1">
          <TroubleRow problem="Printer not connected" fix="Install the driver (Step 2), check USB cable and power, then press Refresh." />
          <TroubleRow problem="Out of paper" fix="The label roll is empty — load a new roll." />
          <TroubleRow problem="Cover open" fix="Close the printer cover fully and retry." />
          <TroubleRow problem="Print too light / thin text" fix="Windows Settings → Printers → your printer → Printing preferences → raise Density/Darkness, then Test Print again." />
          <TroubleRow problem="Right edge cut off" fix="Tag is wider than the printer's maximum. Use the suggested fitting size." />
          <TroubleRow problem="Print comes out upside-down / mirrored" fix="Settings → Print Calibration → tick Rotate print 180°, Save, then Test print. Preview rotates too so you can confirm." />
          <TroubleRow problem="Print slightly shifted" fix="Settings → Calibration: try 0.5–1 mm offsets + Test Print." />
          <TroubleRow problem="Red server dot" fix="The server window was closed — start it again, then refresh this page." />
        </div>
      </Card>

      <div className="flex flex-wrap items-center gap-2.5">
        <button
          onClick={onGoSettings}
          className="inline-flex min-h-[42px] items-center gap-2 rounded-xl bg-slate-900 px-5 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-slate-700 active:scale-[0.98]"
        >
          <Printer size={15} /> Go to Printer Settings
        </button>
        <span className="flex items-center gap-1.5 text-[13px] text-green-700">
          <CheckCircle2 size={14} /> Setup is one-time per computer — daily use needs nothing technical.
        </span>
      </div>
    </div>
  );
}
