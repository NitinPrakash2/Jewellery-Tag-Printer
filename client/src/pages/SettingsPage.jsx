import { useEffect, useRef, useState } from "react";
import { Check, RefreshCw } from "lucide-react";
import LogoDropzone from "../components/LogoDropzone.jsx";
import { Card, Field, Notice, PremiumSelect, TextInput } from "../components/ui.jsx";
import { api } from "../services/api.js";

function Section({ title, children }) {
  return (
    <Card className="p-5">
      <h3 className="mb-4 text-base font-bold text-slate-900">{title}</h3>
      <div className="flex flex-col gap-4">{children}</div>
    </Card>
  );
}

export default function SettingsPage({ settings, onSaved }) {
  const [local, setLocal] = useState(settings || {});
  const [printers, setPrinters] = useState([]);
  const [status, setStatus] = useState(null);
  const [notice, setNotice] = useState(null);
  const [noticeCat, setNoticeCat] = useState(null);
  const [saving, setSaving] = useState(null);
  const [savedCat, setSavedCat] = useState(null);
  const [logoUri, setLogoUri] = useState(null);
  // Guard: never clobber the user's unsaved edits when settings reload
  // (e.g. after a logo upload). Cleared on successful save.
  const dirtyRef = useRef(false);
  const savedTimer = useRef(null);

  useEffect(() => {
    if (!dirtyRef.current) setLocal(settings || {});
  }, [settings]);

  useEffect(() => () => clearTimeout(savedTimer.current), []);

  useEffect(() => {
    api.logoGet().then((r) => setLogoUri(r.data_uri || null)).catch(() => setLogoUri(null));
  }, []);

  useEffect(() => {
    api.printers().then((r) => setPrinters(r.printers || [])).catch(() => {});
  }, []);

  const setVal = (cat, key) => (e) => {
    dirtyRef.current = true;
    setLocal((s) => ({ ...s, [cat]: { ...(s[cat] || {}), [key]: e.target.value } }));
  };
  const setSel = (cat, key) => (value) => {
    dirtyRef.current = true;
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
      dirtyRef.current = false;
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
    try {
      const r = await api.printers();
      setPrinters(r.printers || []);
    } catch {
      setNotice({ kind: "error", text: "Could not refresh printer list." });
    }
  }

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
        <Field label="Selected printer">
          <div className="flex gap-2">
            <PremiumSelect
              value={local?.printer?.selected || ""}
              onChange={(v) => setSel("printer", "selected")(v)}
              placeholder="— Select printer —"
              options={printers.map((p) => ({ value: p.name, label: p.name }))}
              className="flex-1"
            />
            <button onClick={refreshPrinters} title="Refresh printer list" className="rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 shadow-sm transition duration-200 hover:border-slate-400 hover:bg-slate-50">
              <RefreshCw size={17} className="text-slate-600" />
            </button>
          </div>
        </Field>
        <div className="flex flex-wrap gap-2.5">
          <button onClick={checkStatus} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition duration-200 hover:bg-slate-50">Check status</button>
          <button onClick={testPrint} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition duration-200 hover:bg-slate-50">Test print</button>
          <SaveBtn cat="printer" />
          <SectionNotice cat="printer" />
        </div>
        <SectionNotice cat="printer" />
        {status && <div className="text-sm bg-slate-50 rounded-lg p-3 text-slate-700 border border-slate-200/60 font-mono">{JSON.stringify(status)}</div>}
      </Section>

      <Section title="Tag Dimensions">
        <p className="mb-2 text-xs font-semibold text-amber-700 bg-amber-50 border border-amber-200/60 rounded-lg px-3 py-2">⚠️ NEEDS HARDWARE VALIDATION — confirm with real label stock</p>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Width (mm)">
            <TextInput value={local?.tag?.width_mm || ""} onChange={setVal("tag", "width_mm")} inputMode="decimal" placeholder="50" />
          </Field>
          <Field label="Height (mm)">
            <TextInput value={local?.tag?.height_mm || ""} onChange={setVal("tag", "height_mm")} inputMode="decimal" placeholder="25" />
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
          <Field label="Theme">
            <PremiumSelect
              value={local?.app?.theme || "light"}
              onChange={setSel("app", "theme")}
              options={[
                { value: "light", label: "Light" },
                { value: "dark", label: "Dark" },
              ]}
            />
          </Field>
          <Field label="Default copies">
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
