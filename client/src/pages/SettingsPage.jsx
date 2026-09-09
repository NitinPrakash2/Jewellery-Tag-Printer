import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
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
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLocal(settings || {});
  }, [settings]);

  useEffect(() => {
    api.printers().then((r) => setPrinters(r.printers || [])).catch(() => {});
  }, []);

  const setVal = (cat, key) => (e) =>
    setLocal((s) => ({ ...s, [cat]: { ...(s[cat] || {}), [key]: e.target.value } }));
  const setSel = (cat, key) => (value) =>
    setLocal((s) => ({ ...s, [cat]: { ...(s[cat] || {}), [key]: value } }));

  async function save(cat) {
    setSaving(true);
    setNotice(null);
    try {
      await api.settingsPut(cat, local[cat] || {});
      setNotice({ kind: "success", text: `${cat} settings saved.` });
      onSaved?.();
    } catch (e) {
      setNotice({ kind: "error", text: e?.message || `Could not save ${cat} settings.` });
    } finally {
      setSaving(false);
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

  const saveBtn =
    "rounded-lg bg-gradient-to-r from-indigo-600 to-indigo-700 px-4 py-2 text-[13px] font-semibold text-white shadow-[0_4px_12px_rgba(79,70,229,0.3)] transition duration-200 hover:from-indigo-500 hover:to-indigo-600 active:scale-[0.98] disabled:opacity-50";

  return (
    <div className="flex flex-col gap-5">
      {notice && <Notice kind={notice.kind}>{notice.text}</Notice>}

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
          <button onClick={() => save("printer")} disabled={saving} className={saveBtn}>Save</button>
        </div>
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
        <div><button onClick={() => save("tag")} disabled={saving} className={saveBtn}>Save</button></div>
      </Section>

      <Section title="Shop Information">
        <Field label="Shop name (prints on back side)">
          <TextInput value={local?.shop?.name || ""} onChange={setVal("shop", "name")} placeholder="XYZ JEWELLERS" />
        </Field>
        <Field label="Logo path (optional — app never crashes if missing)">
          <TextInput value={local?.shop?.logo_path || ""} onChange={setVal("shop", "logo_path")} placeholder="C:\…\logo.png" />
        </Field>
        <div><button onClick={() => save("shop")} disabled={saving} className={saveBtn}>Save</button></div>
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
        <div className="flex flex-wrap gap-2.5">
          <button onClick={testPrint} className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition duration-200 hover:bg-slate-50">Test print</button>
          <button onClick={() => save("calibration")} disabled={saving} className={saveBtn}>Save</button>
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
        <div><button onClick={() => save("app")} disabled={saving} className={saveBtn}>Save</button></div>
      </Section>
    </div>
  );
}
