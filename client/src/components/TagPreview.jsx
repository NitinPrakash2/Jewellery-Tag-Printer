import { useState } from "react";
import { Maximize2, Ruler } from "lucide-react";

// Display-only: strip <text> so the tag shell stays clean at any size.
// The printer still receives the full label WITH text (server output).
function stripText(svg) {
  return String(svg || "").replace(/<text[\s\S]*?<\/text>/g, "");
}

export default function TagPreview({
  tagSvg,
  widthMm = 110,
  heightMm = 12,
  serverBacked = false,
  data = {},
}) {
  const [zoom, setZoom] = useState("fit");

  const seg = (id, Icon, label, hint) => (
    <button
      key={id}
      type="button"
      title={hint}
      onClick={() => setZoom(id)}
      className={`flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-semibold transition ${
        zoom === id ? "bg-slate-900 text-white shadow-sm" : "text-slate-500 hover:bg-slate-200/70 hover:text-slate-800"
      }`}
    >
      <Icon size={13} />
      {label}
    </button>
  );

  const rows = [
    ["Purity", data.purity_huid],
    ["Item", data.product_name],
    ["Gross", data.gross_weight ? `${data.gross_weight} g` : ""],
    ["Less", data.lessWeight || ""],
    ["Net", data.net_weight ? `${data.net_weight} g` : ""],
  ];

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-medium text-slate-400">
          {zoom === "real"
            ? "True physical size on screen — what your BAR printer will output"
            : "Back + fold + front on one label — scaled to fit panel"}
        </span>
        <span className="flex items-center gap-0.5 rounded-lg border border-slate-200 bg-white p-0.5 shadow-sm">
          {seg("fit", Maximize2, "Fit", "Scale tag to fit the panel")}
          {seg("real", Ruler, "1:1", "True millimetre size on screen (96 dpi)")}
        </span>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
          <span className="text-[13px] font-semibold text-slate-700">Fold Tag (Back + Front)</span>
          <span className="flex items-center gap-1.5">
            {serverBacked && (
              <span className="rounded-full bg-slate-900 px-2 py-px text-[11px] font-semibold text-white">
                Server
              </span>
            )}
            <span className="rounded-full bg-slate-100 px-2 py-px text-[11px] font-medium text-slate-500">
              {widthMm} × {heightMm} mm
            </span>
          </span>
        </div>
        <div className="border-t border-slate-100 bg-slate-50/60 px-4 py-5">
          {tagSvg ? (
            zoom === "real" ? (
              <div className="overflow-x-auto pb-1">
                <div className="tag-real mx-auto" style={{ width: `${widthMm}mm`, minWidth: `${widthMm}mm` }}>
                  <div dangerouslySetInnerHTML={{ __html: stripText(tagSvg) }} />
                </div>
                <div className="mt-3 flex justify-center">
                  <Readout rows={rows} />
                </div>
              </div>
            ) : (
              <div className="flex flex-wrap items-center justify-center gap-6">
                <div className="tag-svg w-full max-w-[560px] flex-1" dangerouslySetInnerHTML={{ __html: stripText(tagSvg) }} />
                <Readout rows={rows} />
              </div>
            )
          ) : (
            <div className="flex items-center justify-center">
              <span className="py-6 text-[13px] text-slate-400">Enter details to preview</span>
            </div>
          )}
        </div>
      </div>

      <div className="text-right text-xs text-slate-400">
        Tag text is printed inside the label — shown here outside for clarity.
      </div>
    </div>
  );
}

function Readout({ rows }) {
  return (
    <dl className="grid min-w-36 grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-[13px]">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="font-medium text-slate-400">{k}</dt>
          <dd className="truncate font-semibold text-slate-800" title={v || "—"}>
            {v || <span className="font-normal text-slate-300">—</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}
