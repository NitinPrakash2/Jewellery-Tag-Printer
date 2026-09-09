import { useCallback, useEffect, useMemo, useState } from "react";
import { Eye, Printer, RotateCcw, Settings as SettingsIcon, Tag, X } from "lucide-react";
import TagPreview from "../components/TagPreview.jsx";
import {
  Card,
  CardTitle,
  Notice,
  OutlineButton,
  PremiumSelect,
  PrimaryButton,
  Row,
  StatusPill,
  Stepper,
  TextInput,
} from "../components/ui.jsx";
import { buildBackSvg, buildFrontSvg, shopInitials } from "../lib/tagSvg.js";
import { api } from "../services/api.js";

const PURITY_OPTIONS = [
  "24kt HUID",
  "22kt HUID",
  "18kt HUID",
  "14kt HUID",
  "24kt",
  "22kt",
  "18kt",
  "14kt",
  "Silver 925",
  "Platinum PT950",
].map((p) => ({ value: p, label: p }));

const TAG_SIZE_PRESETS = [
  { label: "Custom (As per tag)", value: "custom" },
  { label: "25 × 15 mm", value: "25x15" },
  { label: "30 × 20 mm", value: "30x20" },
  { label: "40 × 25 mm", value: "40x25" },
  { label: "50 × 25 mm", value: "50x25" },
];

const EMPTY = { purity_huid: "", product_name: "", gross_weight: "", net_weight: "", copies: "1" };

export default function PrintPage({ settings, onSettingsSaved, refreshHistorySignal }) {
  const [form, setForm] = useState(EMPTY);
  const [purityMode, setPurityMode] = useState("preset"); // preset | custom
  const [errors, setErrors] = useState({});
  const [notice, setNotice] = useState(null);
  const [printing, setPrinting] = useState(false);
  const [printers, setPrinters] = useState([]);
  const [printerState, setPrinterState] = useState(null);
  const [serverPreview, setServerPreview] = useState(null);

  const shopName = settings?.shop?.name || "";
  const monogram = shopInitials(shopName);
  const hasLogo = Boolean(settings?.shop?.logo_path);
  const tagW = Number(settings?.tag?.width_mm) || 50;
  const tagH = Number(settings?.tag?.height_mm) || 25;
  const printerName = settings?.printer?.selected || "";
  const tagSizeValue = useMemo(() => {
    const hit = TAG_SIZE_PRESETS.find((t) => t.value === `${tagW}x${tagH}`);
    return hit ? hit.value : "custom";
  }, [tagW, tagH]);

  const set = (k) => (e) => {
    setForm((f) => ({ ...f, [k]: e.target.value }));
    setServerPreview(null);
  };

  const loadPrinters = useCallback(async () => {
    try {
      const r = await api.printers();
      setPrinters(r.printers || []);
    } catch {
      setPrinters([]);
    }
  }, []);

  const checkPrinter = useCallback(
    async (name) => {
      const target = name ?? printerName;
      if (!target) {
        setPrinterState(null);
        return;
      }
      try {
        setPrinterState(await api.printerStatus(target));
      } catch {
        setPrinterState({ ok: false, message: "Could not reach the server." });
      }
    },
    [printerName]
  );

  useEffect(() => {
    loadPrinters();
  }, [loadPrinters]);
  useEffect(() => {
    checkPrinter();
  }, [checkPrinter]);

  // Live preview — updates on every keystroke from the same canonical layout.
  const frontSvg = useMemo(
    () =>
      buildFrontSvg({
        purity_huid: form.purity_huid,
        product_name: form.product_name,
        gross_weight: form.gross_weight,
        net_weight: form.net_weight,
        monogram,
        width_mm: tagW,
        height_mm: tagH,
        has_logo: hasLogo,
      }),
    [form, monogram, tagW, tagH, hasLogo]
  );
  const backSvg = useMemo(
    () => buildBackSvg({ shop_name: shopName, width_mm: tagW, height_mm: tagH }),
    [shopName, tagW, tagH]
  );

  useEffect(() => {
    setNotice(null);
  }, [form]);

  async function onPrint() {
    setPrinting(true);
    setNotice(null);
    try {
      const res = await api.print({
        purity_huid: form.purity_huid,
        product_name: form.product_name,
        gross_weight: form.gross_weight,
        net_weight: form.net_weight,
        copies: Number(form.copies) || 1,
      });
      if (res.ok) {
        setErrors({});
        setNotice({ kind: "success", text: res.message || "Printed successfully." });
        refreshHistorySignal?.();
      } else if (res.errors) {
        setErrors(res.errors);
        setNotice({ kind: "error", text: res.message || "Please fix the highlighted fields." });
      } else {
        setNotice({ kind: "error", text: res.message || "Print failed. Check printer and try again." });
      }
    } catch {
      setNotice({ kind: "error", text: "Could not reach the server. Make sure it is running." });
    } finally {
      setPrinting(false);
    }
  }

  async function onPreview() {
    setNotice(null);
    try {
      const r = await api.renderTag({
        purity_huid: form.purity_huid,
        product_name: form.product_name,
        gross_weight: form.gross_weight || null,
        net_weight: form.net_weight || null,
      });
      setServerPreview(r);
      setNotice({ kind: "success", text: "Server preview loaded — exactly what will print." });
    } catch {
      setNotice({ kind: "error", text: "Could not load server preview." });
    }
  }

  async function onPrinterChange(value) {
    try {
      await api.settingsPut("printer", { selected: value });
      onSettingsSaved?.();
      checkPrinter(value);
    } catch {
      setNotice({ kind: "error", text: "Could not save printer." });
    }
  }

  async function onTagSizeChange(value) {
    if (value === "custom") return;
    const [w, h] = value.split("x");
    try {
      await api.settingsPut("tag", { width_mm: w, height_mm: h });
      onSettingsSaved?.();
      setServerPreview(null);
    } catch {
      setNotice({ kind: "error", text: "Could not save tag size." });
    }
  }

  function onClear() {
    setForm(EMPTY);
    setPurityMode("preset");
    setErrors({});
    setNotice(null);
    setServerPreview(null);
  }

  const shownFront = serverPreview?.front_svg || frontSvg;
  const shownBack = serverPreview?.back_svg || backSvg;
  const connected = printerState?.ok && printerState?.printer?.status !== "not-detected";

  return (
    <div className="flex flex-col gap-5">
      <div className="grid items-start gap-5 lg:grid-cols-[460px_minmax(0,1fr)]">
        {/* Left column */}
        <div className="flex flex-col gap-4">
          <Card>
            <CardTitle icon={Tag}>Tag Details</CardTitle>
            <div className="flex flex-col gap-4 px-5 py-4">
              <Row label="Purity" error={errors.purity_huid}>
                {purityMode === "preset" ? (
                  <PremiumSelect
                    value={PURITY_OPTIONS.some((o) => o.value === form.purity_huid) ? form.purity_huid : ""}
                    onChange={(v) => {
                      if (v === "__custom") {
                        setPurityMode("custom");
                      } else {
                        setForm((f) => ({ ...f, purity_huid: v }));
                        setServerPreview(null);
                      }
                    }}
                    placeholder="Select purity"
                    options={[...PURITY_OPTIONS, { value: "__custom", label: "Custom…" }]}
                  />
                ) : (
                  <TextInput
                    value={form.purity_huid}
                    onChange={set("purity_huid")}
                    placeholder="e.g. 18kt HUID"
                    data-error={!!errors.purity_huid}
                  />
                )}
              </Row>
              <Row label="Product Name" error={errors.product_name}>
                <TextInput value={form.product_name} onChange={set("product_name")} placeholder="Ring" data-error={!!errors.product_name} />
              </Row>
              <Row label="Gross Weight (G.Wt.)" error={errors.gross_weight}>
                <TextInput value={form.gross_weight} onChange={set("gross_weight")} placeholder="2.146" inputMode="decimal" data-error={!!errors.gross_weight} />
              </Row>
              <Row label="Net Weight (N.Wt.)" error={errors.net_weight}>
                <TextInput value={form.net_weight} onChange={set("net_weight")} placeholder="2.146" inputMode="decimal" data-error={!!errors.net_weight} />
              </Row>
            </div>
          </Card>

          <div className="flex gap-3">
            <PrimaryButton onClick={onPrint} disabled={printing} className="flex-1">
              <Printer size={17} />
              {printing ? "Printing…" : "Print Tag"}
            </PrimaryButton>
            <OutlineButton onClick={onPreview} className="flex-1">
              <Eye size={17} />
              Preview
            </OutlineButton>
          </div>
          {errors.copies && <span className="text-sm text-red-600 font-medium">{errors.copies}</span>}

          <Card>
            <CardTitle icon={SettingsIcon}>Print Settings</CardTitle>
            <div className="flex flex-col gap-4 px-5 py-4">
              <Row label="Copies">
                <Stepper value={form.copies} onChange={(v) => setForm((f) => ({ ...f, copies: v }))} />
              </Row>
              <Row label="Printer">
                <PremiumSelect
                  value={printerName}
                  onChange={onPrinterChange}
                  placeholder="Select printer"
                  options={printers.map((p) => ({ value: p.name, label: p.name }))}
                />
              </Row>
              <Row label="Tag Size">
                <PremiumSelect value={tagSizeValue} onChange={onTagSizeChange} options={TAG_SIZE_PRESETS} />
              </Row>
            </div>
          </Card>

          <div className="px-1">
            <StatusPill
              ok={connected}
              text={connected ? "Printer Connected" : printerName ? "Printer not detected" : "No printer selected"}
            />
          </div>
        </div>

        {/* Right column — preview */}
        <Card>
          <CardTitle icon={Eye}>Print Preview</CardTitle>
          <div className="px-5 py-4">
            {notice && (
              <div className="mb-4">
                <Notice kind={notice.kind}>{notice.text}</Notice>
              </div>
            )}
            <TagPreview
              frontSvg={shownFront}
              backSvg={shownBack}
              widthMm={tagW}
              heightMm={tagH}
              serverBacked={Boolean(serverPreview)}
            />
          </div>
        </Card>
      </div>

      {/* Footer bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200/60 bg-gradient-to-r from-white via-blue-50/30 to-white px-5 py-3.5 shadow-[0_2px_12px_rgba(79,70,229,0.06)]">
        <div className="text-[13px] font-medium tracking-wide text-slate-600">
          <span className="font-bold text-slate-900">{shopName || "MK JEWELLERS"}</span>
          <span className="mx-2 text-slate-300">•</span>
          EXCELLENCE IN EVERY TAG
        </div>
        <div className="flex gap-2">
          <OutlineButton small onClick={onClear} className="px-5">
            <RotateCcw size={14} />
            Clear
          </OutlineButton>
          <OutlineButton small onClick={() => window.close()} className="px-5">
            <X size={14} />
            Exit
          </OutlineButton>
        </div>
      </div>
    </div>
  );
}
