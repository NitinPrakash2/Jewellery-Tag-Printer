import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Eye, Printer, Settings as SettingsIcon, Tag } from "lucide-react";
import TagPreview from "../components/TagPreview.jsx";
import {
  Card,
  CardTitle,
  Notice,
  OutlineButton,
  PremiumSelect,
  groupPrinterOptions,
  PrimaryButton,
  Row,
  StatusPill,
  Stepper,
  TextInput,
} from "../components/ui.jsx";
import { buildTagSvg, computeLess, computeNet, tagWarnings } from "../lib/tagSvg.js";
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
  { label: "Custom (manual entry below)", value: "custom", w: 0, h: 0, tail: 0 },
  { label: "100 × 15 mm (65 body + 35 tail)", value: "100x15", w: 100, h: 15, tail: 35 },
  { label: "55 × 13 mm (fold tag)", value: "55x13", w: 55, h: 13, tail: 0 },
  { label: "100 × 12 mm (fits 104mm printers)", value: "100x12", w: 100, h: 12, tail: 0 },
  { label: "110 × 12 mm (fold tag)", value: "110x12", w: 110, h: 12, tail: 0 },
  { label: "25 × 15 mm", value: "25x15", w: 25, h: 15, tail: 0 },
  { label: "30 × 20 mm", value: "30x20", w: 30, h: 20, tail: 0 },
  { label: "40 × 25 mm", value: "40x25", w: 40, h: 25, tail: 0 },
  { label: "50 × 25 mm", value: "50x25", w: 50, h: 25, tail: 0 },
  { label: "110 × 15 mm", value: "110x15", w: 110, h: 15, tail: 0 },
];

const EMPTY = { purity_huid: "", product_name: "", gross_weight: "", less_weight: "", copies: "1" };

export default function PrintPage({ settings, onSettingsSaved, refreshHistorySignal }) {
  const [form, setForm] = useState(EMPTY);
  // Prefill copies from Settings → Application → Default copies (once).
  const copiesInitRef = useRef(false);
  useEffect(() => {
    if (!copiesInitRef.current && settings?.app?.default_copies) {
      const n = parseInt(settings.app.default_copies, 10);
      if (Number.isFinite(n) && n >= 1 && n <= 99) {
        copiesInitRef.current = true;
        setForm((f) => ({ ...f, copies: String(n) }));
      }
    }
  }, [settings]);
  const [purityMode, setPurityMode] = useState("preset"); // preset | custom
  const [errors, setErrors] = useState({});
  const [notice, setNotice] = useState(null);
  const [printing, setPrinting] = useState(false);
  const [printers, setPrinters] = useState([]);
  const [printerState, setPrinterState] = useState(null);
  const [serverPreview, setServerPreview] = useState(null);
  const [logoImageData, setLogoImageData] = useState(null);

  const shopName = settings?.shop?.name || "";
  const hasLogo = Boolean(settings?.shop?.logo_path);
  const printerName = settings?.printer?.selected || "";
  // Manual tag dimensions: typed locally for instant preview, saved on blur/Enter.
  // Tail = fold-only strip on the right (zero ink there, never prints).
  const [dimW, setDimW] = useState("");
  const [dimH, setDimH] = useState("");
  const [dimT, setDimT] = useState("");
  const [dimErr, setDimErr] = useState("");
  const [dimsSaved, setDimsSaved] = useState(false);
  function flashDimsSaved() {
    setDimsSaved(true);
    setTimeout(() => setDimsSaved(false), 2000);
  }  useEffect(() => {
    if (settings?.tag) {
      setDimW(settings.tag.width_mm ?? "");
      setDimH(settings.tag.height_mm ?? "");
      setDimT(settings.tag.tail_width_mm ?? "");
    }
  }, [settings?.tag?.width_mm, settings?.tag?.height_mm, settings?.tag?.tail_width_mm]);
  const tagW = Number(dimW) > 0 ? Number(dimW) : Number(settings?.tag?.width_mm) || 100;
  const tagH = Number(dimH) > 0 ? Number(dimH) : Number(settings?.tag?.height_mm) || 15;
  const tagT = dimT === "" ? Number(settings?.tag?.tail_width_mm ?? 35) || 0 : Math.max(0, Number(dimT) || 0);
  const tagPresetValue = useMemo(() => {
    const hit = TAG_SIZE_PRESETS.find((t) => t.value === `${tagW}x${tagH}`);
    return hit ? hit.value : "custom";
  }, [tagW, tagH]);

  // Real-time printer-aware suggestions: presets wider than the selected
  // printer's max print width are flagged, and a fitting size is suggested.
  const maxW = printerState?.max_print_width_mm || null;
  const tooWide = Boolean(maxW && tagW > maxW);
  const suggestedW = maxW ? Math.max(20, maxW - 4) : null;
  const presetOptions = useMemo(
    () =>
      TAG_SIZE_PRESETS.map((t) => ({
        value: t.value,
        label: maxW && t.w > maxW ? `${t.label} — too wide` : t.label,
      })),
    [maxW]
  );

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
    // Silent background refresh so the dropdown always mirrors Windows.
    const t = setInterval(() => {
      if (!document.hidden) loadPrinters();
    }, 12000);
    return () => clearInterval(t);
  }, [loadPrinters]);
  useEffect(() => {
    checkPrinter();
  }, [checkPrinter]);

  // Load logo image (data URI) from the server for live preview
  useEffect(() => {
    let cancelled = false;
    api
      .logoGet()
      .then((r) => {
        if (!cancelled) setLogoImageData(r.data_uri || null);
      })
      .catch(() => {
        if (!cancelled) setLogoImageData(null);
      });
    return () => {
      cancelled = true;
    };
  }, [settings?.shop?.logo_path]);

  // Net is automatic: net = gross - less. Live preview uses the same math.
  const netWeight = useMemo(
    () => computeNet(form.gross_weight, form.less_weight),
    [form.gross_weight, form.less_weight]
  );
  // Blank Less input hides the Less row from the label entirely.
  const showLess = String(form.less_weight ?? "").trim() !== "";
  const showGross = String(form.gross_weight ?? "").trim() !== "";
  const showNet = String(netWeight ?? "").trim() !== "";
  const tagSvg = useMemo(
    () =>
      buildTagSvg({
        purity_huid: form.purity_huid,
        product_name: form.product_name,
        gross_weight: form.gross_weight,
        net_weight: netWeight,
        shop_name: shopName,
        width_mm: tagW,
        height_mm: tagH,
        has_logo: hasLogo,
        logo_image: logoImageData,
        cal_x_mm: settings?.calibration?.offset_x_mm,
        cal_y_mm: settings?.calibration?.offset_y_mm,
        cal_scale: settings?.calibration?.scale,
        cal_rotate: settings?.calibration?.rotate_180,
        show_less: showLess,
        tail_mm: tagT,
        show_gross: showGross,
        show_net: showNet,
        show_lines: String(settings?.tag?.show_lines || "0").toLowerCase() === "1" ||
          String(settings?.tag?.show_lines || "").toLowerCase() === "true",
      }),
    [form.purity_huid, form.product_name, form.gross_weight, netWeight, shopName, tagW, tagH, tagT, hasLogo, logoImageData, settings, showLess, showGross, showNet]
  );
  // Live overflow warnings — same maths as the server, updated per keystroke.
  const liveWarnings = useMemo(
    () =>
      tagWarnings(tagW, tagH, {
        purity: form.purity_huid,
        product: form.product_name,
        gross: form.gross_weight ? `${form.gross_weight} g` : "",
        less: showLess && form.less_weight ? `${form.less_weight} g` : "",
        net: netWeight ? `${netWeight} g` : "",
        shop_l1: (shopName.trim().split(/\s+/)[0] || "").toUpperCase(),
        shop_l2: shopName.trim().split(/\s+/).slice(1).join(" ").toUpperCase(),
        initial: (shopName.trim()[0] || "").toUpperCase(),
      }, showLess, tagT, showGross, showNet),
    [form, netWeight, shopName, tagW, tagH, tagT, showLess, showGross, showNet]
  );
  // Enter moves to the next field (skips dropdowns/buttons).
  function handleEnterNext(e) {
    if (e.key !== "Enter") return;
    const t = e.target;
    if (!t || t.tagName !== "INPUT" || t.type === "button" || t.type === "submit") return;
    e.preventDefault();
    const card = t.closest("[data-enter-zone]");
    const scope = card || document;
    const inputs = Array.from(scope.querySelectorAll('input:not([disabled]):not([type="hidden"])'));
    const i = inputs.indexOf(t);
    if (i >= 0 && i < inputs.length - 1) {
      inputs[i + 1].focus();
      inputs[i + 1].select?.();
    } else if (e.target.form?.requestSubmit) {
      e.target.form.requestSubmit();
    }
  }
  const lessWeight = useMemo(
    () => computeLess(form.gross_weight, netWeight),
    [form.gross_weight, netWeight]
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
        less_weight: form.less_weight,
        net_weight: netWeight || undefined,
        copies: Number(form.copies) || 1,
      });
      if (res.ok) {
        setErrors({});
        setNotice({ kind: "success", text: res.message || "Printed successfully." });
        refreshHistorySignal?.();
      } else if (res.errors) {
        setErrors(res.errors);
        setNotice({ kind: "error", text: res.errors.__form || "Please fix the highlighted fields." });
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
        net_weight: netWeight || null,
        less_weight: form.less_weight || "",
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

  async function onPresetChange(value) {
    if (value === "custom") return;
    const hit = TAG_SIZE_PRESETS.find((t) => t.value === value);
    if (!hit) return;
    await applyDims(hit.w, hit.h, hit.tail);
  }

  async function applyDims(w, h, tail) {
    const t = tail === undefined ? tagT : tail;
    setDimW(String(w));
    setDimH(String(h));
    setDimT(String(t));
    setDimErr("");
    try {
      await api.settingsPut("tag", { width_mm: String(w), height_mm: String(h), tail_width_mm: String(t) });
      onSettingsSaved?.();
      setServerPreview(null);
      flashDimsSaved();
    } catch {
      setDimErr("Could not save tag size.");
    }
  }

  async function saveDims() {
    const w = parseFloat(dimW);
    const h = parseFloat(dimH);
    const t = dimT === "" ? tagT : parseFloat(dimT);
    if (!(w > 0 && w <= 500 && h > 0 && h <= 500)) {
      setDimErr("Width and height must be numbers between 0 and 500 mm.");
      return;
    }
    if (!(t >= 0 && t < w)) {
      setDimErr("Tail must be 0 or more, and less than the total width.");
      return;
    }
    setDimErr("");
    try {
      await api.settingsPut("tag", { width_mm: String(w), height_mm: String(h), tail_width_mm: String(t) });
      onSettingsSaved?.();
      setServerPreview(null);
      flashDimsSaved();
    } catch {
      setDimErr("Could not save tag size.");
    }
  }

  const shownTag = serverPreview?.tag_svg || tagSvg;
  const connected = printerState?.ok && printerState?.printer?.status !== "not-detected";

  return (
    <div className="flex flex-col gap-5">
      <div className="grid items-start gap-5 lg:grid-cols-[460px_minmax(0,1fr)]">
        {/* Left column */}
        <div className="flex flex-col gap-4">
          <Card>
            <CardTitle icon={Tag}>Tag Details</CardTitle>
            <div className="flex flex-col gap-4 px-5 py-4" data-enter-zone onKeyDown={handleEnterNext}>
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
                <TextInput value={form.product_name} onChange={set("product_name")} placeholder="e.g. Ring" data-error={!!errors.product_name} />
              </Row>
              <Row label="Gross Weight (G.Wt.)" error={errors.gross_weight}>
                <TextInput value={form.gross_weight} onChange={set("gross_weight")} placeholder="e.g. 2.146" inputMode="decimal" suffix="g" data-error={!!errors.gross_weight} />
              </Row>
              <Row label="Less Weight (L.Wt.)" error={errors.less_weight}>
                <TextInput value={form.less_weight} onChange={set("less_weight")} placeholder="e.g. 0.000" inputMode="decimal" suffix="g" data-error={!!errors.less_weight} />
              </Row>
              <Row label="Net Weight (auto)">
                <div className="flex h-10 items-center rounded-lg border border-slate-200 bg-slate-50 px-3 text-sm font-semibold text-slate-800">
                  {netWeight ? `${netWeight} g` : <span className="font-normal text-slate-400">—</span>}
                </div>
              </Row>
              <div className="-mt-2 text-xs text-slate-400">
                Tip: only filled fields print — leave any field blank to hide it. Press Enter to jump to the next field.
              </div>
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
                  options={groupPrinterOptions(printers)}
                />
              </Row>
              <Row label="Preset Size">
                <PremiumSelect value={tagPresetValue} onChange={onPresetChange} options={presetOptions} />
              </Row>
              <div>
                <div className="grid grid-cols-1 gap-1 sm:grid-cols-[150px_minmax(0,1fr)] sm:items-center sm:gap-3">
                  <span className="text-sm text-slate-600">Tag Size (mm)</span>
                  <div className="flex min-w-0 items-center gap-2">
                    <TextInput
                      value={dimW}
                      onChange={(e) => setDimW(e.target.value)}
                      onBlur={saveDims}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") e.target.blur();
                      }}
                      placeholder="W"
                      inputMode="decimal"
                      aria-label="Tag width in mm"
                    />
                    <span className="text-slate-400">×</span>
                    <TextInput
                      value={dimH}
                      onChange={(e) => setDimH(e.target.value)}
                      onBlur={saveDims}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") e.target.blur();
                      }}
                      placeholder="H"
                      inputMode="decimal"
                      aria-label="Tag height in mm"
                    />
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-1 gap-1 sm:grid-cols-[150px_minmax(0,1fr)] sm:items-center sm:gap-3">
                  <span className="text-sm text-slate-600">Tail (mm, fold only)</span>
                  <div className="flex min-w-0 items-center gap-2">
                    <TextInput
                      value={dimT}
                      onChange={(e) => setDimT(e.target.value)}
                      onBlur={saveDims}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") e.target.blur();
                      }}
                      placeholder="e.g. 35"
                      inputMode="decimal"
                      aria-label="Tail width in mm (no print here)"
                    />
                    <span className="whitespace-nowrap text-xs text-slate-400">
                      Body prints {Math.max(0, Math.round((tagW - tagT) * 10) / 10)} mm
                    </span>
                  </div>
                </div>
                {dimErr && <div className="mt-1 text-[13px] text-red-600 sm:pl-[162px]">{dimErr}</div>}
                {dimsSaved && !dimErr && (
                  <div className="mt-1 text-xs font-semibold text-green-600 sm:pl-[162px]">
                    Saved ✓ — Settings page will show the same values.
                  </div>
                )}
                {maxW && !tooWide && (
                  <div className="mt-1 text-xs text-slate-400 sm:pl-[162px]">
                    {printerName || "Printer"} prints max {maxW} mm wide — fits.
                  </div>
                )}
              </div>
              {tooWide && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-[13px] text-amber-900">
                  Tag is {tagW} mm wide but this printer prints max {maxW} mm — the right edge will be cut off.
                  <button
                    onClick={() => applyDims(suggestedW, tagH)}
                    className="ml-2 font-bold underline underline-offset-2 hover:text-amber-700"
                  >
                    Use {suggestedW}×{tagH} instead
                  </button>
                </div>
              )}
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
              tagSvg={shownTag}
              widthMm={tagW}
              heightMm={tagH}
              serverBacked={Boolean(serverPreview)}
              warnings={serverPreview?.warnings || liveWarnings}
            />
          </div>
        </Card>
      </div>
    </div>
  );
}
