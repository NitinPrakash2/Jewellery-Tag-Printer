import { useCallback, useEffect, useRef, useState } from "react";
import { BookOpen, Check, RefreshCw } from "lucide-react";
import LogoDropzone from "../components/LogoDropzone.jsx";
import ErrorMonitor from "../components/ErrorMonitor.jsx";
import PrinterSetupWizard from "../components/PrinterSetupWizard.jsx";
import UsbLivePanel from "../components/UsbLivePanel.jsx";
import { Card, Field, Notice, PremiumSelect, groupPrinterOptions, TextInput } from "../components/ui.jsx";
import { api } from "../services/api.js";

function Section({ title, children }) {
  return (
    <Card className="p-5">
      <h3 className="mb-4 text-base font-bold text-slate-900">{title}</h3>
      <div className="flex flex-col gap-4">{children}</div>
    </Card>
  );
}

// Plain-language printer status for non-technical users.
function PrinterStatusCard({ status }) {
  const st = String(status?.printer?.status || status?.status || "unknown");
  const maxW = status?.max_print_width_mm || null;
  let tone = "ok";
  let title = "Ready to print";
  let hint = "Press Test print to confirm paper comes out correctly.";
  if (st.includes("not-detected") || st.includes("not-found")) {
    tone = "warn";
    title = "Printer not connected";
    hint = "Install the driver (see Printer Setup above), connect USB, power on — then press Run Setup.";
  } else if (st.includes("out of paper")) {
    tone = "bad";
    title = "Out of paper";
    hint = "Load labels/ribbon in the printer and try again.";
  } else if (st.includes("door open")) {
    tone = "bad";
    title = "Printer cover is open";
    hint = "Close the printer cover properly and try again.";
  } else if (st.startsWith("offline") || st === "offline") {
    tone = "bad";
    title = "Printer is off or unplugged";
    hint = "Switch the printer on and check the USB cable, then try again.";
  } else if (st.startsWith("error") || st.includes("paper problem")) {
    tone = "bad";
    title = "Printer reports an error";
    hint = "Check paper, ribbon and power on the printer, then try again.";
  }
  const styles =
    tone === "ok"
      ? "border-green-200 bg-green-50"
      : tone === "warn"
        ? "border-amber-200 bg-amber-50"
        : "border-red-200 bg-red-50";
  const dot = tone === "ok" ? "bg-green-500" : tone === "warn" ? "bg-amber-400" : "bg-red-500";
  const text = tone === "ok" ? "text-green-800" : tone === "warn" ? "text-amber-900" : "text-red-800";
  return (
    <div className={`rounded-xl border px-4 py-3 ${styles}`}>
      <div className="flex flex-wrap items-center gap-2">
        <span className={`inline-block h-2.5 w-2.5 rounded-full ${dot}`} />
        <span className={`text-sm font-bold ${text}`}>{title}</span>
        {maxW && <span className="text-xs font-medium text-slate-500">· prints up to {maxW} mm wide</span>}
      </div>
      <div className={`mt-1 text-[13px] ${text}`}>{hint}</div>
    </div>
  );
}

export default function SettingsPage({ settings, onSaved, onGoHelp }) {
  const [local, setLocal] = useState(settings || {});
  const [printers, setPrinters] = useState([]);
  const [status, setStatus] = useState(null);
  const [notice, setNotice] = useState(null);
  const [noticeCat, setNoticeCat] = useState(null);
  const [saving, setSaving] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [savedCat, setSavedCat] = useState(null);
  const [logoUri, setLogoUri] = useState(null);
  // Guard: never clobber the user's unsaved edits when settings reload
  // (e.g. after a logo upload) — tracked PER CATEGORY so other sections
  // still sync live (e.g. tail saved from the Print page appears here).
  // A category's flag clears on its successful save.
  const dirtyRef = useRef({});
  const savedTimer = useRef(null);
  // Printers already auto-selected this session (don't nag / re-fire).
  const autoTriedRef = useRef(new Set());

  useEffect(() => {
    if (!settings) return;
    setLocal((prev) => {
      const next = { ...(settings || {}) };
      for (const cat of Object.keys(dirtyRef.current)) {
        if (dirtyRef.current[cat] && prev[cat]) next[cat] = prev[cat];
      }
      return next;
    });
  }, [settings]);

  useEffect(() => () => clearTimeout(savedTimer.current), []);

  useEffect(() => {
    api.logoGet().then((r) => setLogoUri(r.data_uri || null)).catch(() => setLogoUri(null));
  }, []);

  // Silent background refresh: the printer dropdown updates by itself
  // when a printer is installed/connected — no Refresh click needed.
  useEffect(() => {
    api.printers().then((r) => setPrinters(r.printers || [])).catch(() => {});
    const t = setInterval(() => {
      api.printers().then((r) => setPrinters(r.printers || [])).catch(() => {});
    }, 6000);
    return () => clearInterval(t);
  }, []);

  const setVal = (cat, key) => (e) => {
    dirtyRef.current[cat] = true;
    setLocal((s) => ({ ...s, [cat]: { ...(s[cat] || {}), [key]: e.target.value } }));
  };
  const setSel = (cat, key) => (value) => {
    dirtyRef.current[cat] = true;
    setLocal((s) => ({ ...s, [cat]: { ...(s[cat] || {}), [key]: value } }));
  };

  function flashSaved(cat) {
    setSavedCat(cat);
    clearTimeout(savedTimer.current);
    savedTimer.current = setTimeout(() => setSavedCat(null), 2500);
  }

  function SaveBtn({ cat }) {
    const done = savedCat === cat;
    const busy = saving === cat;
    return (
      <button
        onClick={() => save(cat)}
        disabled={busy}
        className={`inline-flex min-h-[34px] items-center gap-1.5 rounded-lg px-4 py-1.5 text-[13px] font-medium text-white shadow-sm transition disabled:cursor-not-allowed disabled:opacity-50 ${
          done ? "bg-green-600 hover:bg-green-600" : "bg-slate-900 hover:bg-slate-700"
        }`}
      >
        {done && <Check size={14} strokeWidth={3} />}
        {busy ? "Saving…" : done ? "Saved" : "Save"}
      </button>
    );
  }

  function SectionNotice({ cat }) {
    if (noticeCat !== cat || !notice) return null;
    return <Notice kind={notice.kind}>{notice.text}</Notice>;
  }

  async function save(cat) {
    setSaving(cat);
    setNotice(null);
    setNoticeCat(null);
    try {
      await api.settingsPut(cat, local[cat] || {});
      dirtyRef.current[cat] = false;
      setNotice({ kind: "success", text: `${cat} settings saved.` });
      setNoticeCat(cat);
      flashSaved(cat);
      onSaved?.();
    } catch (e) {
      setNotice({ kind: "error", text: e?.message || `Could not save ${cat} settings.` });
      setNoticeCat(cat);
    } finally {
      setSaving(null);
    }
  }

  async function refreshPrinters() {
    setScanning(true);
    try {
      const r = await api.printers();
      const list = r.printers || [];
      setPrinters(list);
      const real = list.filter((p) => p.status !== "not-detected");
      if (real.length > 0) {
        setNotice({
          kind: "success",
          text: `Found ${real.length} printer(s): ${real.map((p) => p.name).join(", ")}`,
        });
      } else {
        setNotice({
          kind: "error",
          text: "No printer found yet — check USB cable and power, then try again.",
        });
      }
      setNoticeCat(null);
    } catch {
      setNotice({ kind: "error", text: "Could not refresh printer list." });
      setNoticeCat(null);
    } finally {
      setScanning(false);
    }
  }

  // Auto-select a newly connected printer (any brand). Fires once per
  // printer per session; manual choices are never overridden twice.
  const handleAutoSelect = useCallback(
    async (name) => {
      if (!name || autoTriedRef.current.has(name)) return;
      autoTriedRef.current.add(name);
      try {
        await api.settingsPut("printer", { selected: name });
        // Sync just the printer key — preserve other unsaved edits.
        setLocal((s) => ({ ...s, printer: { ...(s.printer || {}), selected: name } }));
        setNotice({ kind: "success", text: `${name} connected — selected automatically.` });
        setNoticeCat(null);
        onSaved?.();
      } catch {
        /* silent: user can still select manually */
      }
    },
    [onSaved]
  );

  async function checkStatus() {
    try {
      setStatus(await api.printerStatus(local?.printer?.selected));
    } catch {
      setStatus({ ok: false, message: "Could not reach the server." });
    }
  }

  async function testPrint() {
    setNotice(null);
    try {
      const r = await api.testPrint(local?.printer?.selected);
      setNotice({ kind: r.ok ? "success" : "error", text: r.message });
    } catch {
      setNotice({ kind: "error", text: "Could not reach the server." });
    }
  }

  return (
    <div className="flex flex-col gap-5">
      {noticeCat === null && notice && <Notice kind={notice.kind}>{notice.text}</Notice>}

      <Section title="Printer Configuration">
        <button
          onClick={onGoHelp}
          className="flex items-center justify-between gap-2 rounded-xl border border-slate-900 bg-slate-900 px-4 py-2.5 text-left text-sm font-semibold text-white shadow-sm transition hover:bg-slate-700 active:scale-[0.99]"
        >
          <span className="flex items-center gap-2">
            <BookOpen size={16} />
            How to connect printer? Step-by-step guide
          </span>
          <span aria-hidden>→</span>
        </button>
        <UsbLivePanel
          printerName={local?.printer?.selected || ""}
          widthMm={local?.tag?.width_mm || ""}
          heightMm={local?.tag?.height_mm || ""}
          onPrinterList={refreshPrinters}
          onAutoSelect={handleAutoSelect}
          notify={(n) => {
            setNotice(n);
            setNoticeCat(null);
          }}
        />
        <PrinterSetupWizard
          printerName={local?.printer?.selected || ""}
          widthMm={local?.tag?.width_mm || ""}
          heightMm={local?.tag?.height_mm || ""}
          onPrinterList={refreshPrinters}
          notify={(n) => {
            setNotice(n);
            setNoticeCat(null);
          }}
        />
        <Field label="Selected printer">
          <div className="flex gap-2">
            <PremiumSelect
              value={local?.printer?.selected || ""}
              onChange={(v) => setSel("printer", "selected")(v)}
              placeholder="— Select printer —"
              options={groupPrinterOptions(printers)}
              className="flex-1"
            />
            <button onClick={refreshPrinters} disabled={scanning} title="Refresh printer list" className="rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 shadow-sm transition duration-200 hover:border-slate-400 hover:bg-slate-50 disabled:opacity-50">
              <RefreshCw size={17} className={`text-slate-600 ${scanning ? "animate-spin" : ""}`} />
            </button>
          </div>
        </Field>
        <div className="flex flex-wrap gap-2.5">
          <button onClick={checkStatus} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition duration-200 hover:bg-slate-50">Check status</button>
          <button onClick={testPrint} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition duration-200 hover:bg-slate-50">Test print</button>
          <SaveBtn cat="printer" />
          <SectionNotice cat="printer" />
        </div>
        {status && <PrinterStatusCard status={status} />}
        <ErrorMonitor />
      </Section>

      <Section title="Tag Dimensions">
        <p className="mb-2 text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200/60 rounded-lg px-3 py-2">⚠️ NEEDS HARDWARE VALIDATION — confirm with real label stock</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Width (mm)">
            <TextInput value={local?.tag?.width_mm || ""} onChange={setVal("tag", "width_mm")} inputMode="decimal" placeholder="100" />
          </Field>
          <Field label="Height (mm)">
            <TextInput value={local?.tag?.height_mm || ""} onChange={setVal("tag", "height_mm")} inputMode="decimal" placeholder="15" />
          </Field>
          <Field label="Tail (mm, fold only — no print)">
            <TextInput value={local?.tag?.tail_width_mm || ""} onChange={setVal("tag", "tail_width_mm")} inputMode="decimal" placeholder="35" />
          </Field>
          <Field label="Orientation">
            <PremiumSelect
              value={local?.tag?.orientation || "landscape"}
              onChange={setSel("tag", "orientation")}
              options={[
                { value: "landscape", label: "Landscape" },
                { value: "portrait", label: "Portrait" },
              ]}
            />
          </Field>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <SaveBtn cat="tag" />
          <SectionNotice cat="tag" />
        </div>
      </Section>

      <Section title="Shop Information">
        <Field label="Shop name (prints on back side)">
          <TextInput value={local?.shop?.name || ""} onChange={setVal("shop", "name")} placeholder="XYZ JEWELLERS" />
        </Field>
        <div>
          <span className="mb-1 block text-[13px] font-medium text-slate-600">Shop logo (prints on the tag)</span>
          <LogoDropzone
            dataUri={logoUri}
            onChanged={(uri, path) => {
              setLogoUri(uri);
              // Keep local in sync so a later Save doesn't blank the logo path.
              // Other unsaved edits (e.g. shop name) are preserved.
              setLocal((s) => ({ ...s, shop: { ...(s.shop || {}), logo_path: path || "" } }));
              onSaved?.();
            }}
            onError={(msg) => {
              setNotice({ kind: "error", text: msg });
              setNoticeCat("shop");
            }}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <SaveBtn cat="shop" />
          <SectionNotice cat="shop" />
        </div>
      </Section>

      <Section title="Print Calibration">
        <p className="mb-3 text-xs text-slate-600 font-medium">Adjust offsets in millimetres to fine-tune print alignment:</p>
        <div className="rounded-lg border border-slate-200 bg-slate-50 px-3.5 py-3 text-[13px] leading-relaxed text-slate-600">
          <span className="font-bold text-slate-800">How to use:</span> If the print comes out slightly shifted left-right or up-down, fix it here.
          <span className="font-semibold text-slate-800"> Horizontal offset</span> moves the print left-right (positive = right, negative = left),
          <span className="font-semibold text-slate-800"> Vertical offset</span> moves it up-down (positive = down, negative = up).
          First press <span className="font-semibold text-slate-800">Test print</span>, see how far it is shifted, enter that number in mm,
          press <span className="font-semibold text-slate-800">Save</span>, then Test print again to confirm.
          Keep <span className="font-semibold text-slate-800">Scale</span> at 1.0 — touch it only if the whole print looks too small or too big.
          These values apply to every print automatically, no need to enter them again.
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Horizontal offset">
            <TextInput value={local?.calibration?.offset_x_mm || ""} onChange={setVal("calibration", "offset_x_mm")} inputMode="decimal" placeholder="0" />
          </Field>
          <Field label="Vertical offset">
            <TextInput value={local?.calibration?.offset_y_mm || ""} onChange={setVal("calibration", "offset_y_mm")} inputMode="decimal" placeholder="0" />
          </Field>
          <Field label="Scale">
            <TextInput value={local?.calibration?.scale || ""} onChange={setVal("calibration", "scale")} inputMode="decimal" placeholder="1.0" />
          </Field>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <button onClick={testPrint} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition duration-200 hover:bg-slate-50">Test print</button>
          <SaveBtn cat="calibration" />
          <SectionNotice cat="calibration" />
        </div>
      </Section>

      <Section title="Application Preferences">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Field label="Default copies (prefilled on the Print page)">
            <TextInput value={local?.app?.default_copies || ""} onChange={setVal("app", "default_copies")} inputMode="numeric" placeholder="1" />
          </Field>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <SaveBtn cat="app" />
          <SectionNotice cat="app" />
        </div>
      </Section>
    </div>
  );
}
