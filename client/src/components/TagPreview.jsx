import { useState } from "react";
import { Maximize2, Ruler, TriangleAlert } from "lucide-react";

// Preview shows the tag EXACTLY as it will print — text inside,
// zoomed to fit the panel (Fit) or at true millimetre size (1:1).
export default function TagPreview({
  tagSvg,
  widthMm = 110,
  heightMm = 12,
  serverBacked = false,
  warnings = [],
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

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-medium text-slate-400">
          {zoom === "real"
            ? "True physical size on screen — what your BAR printer will output"
            : "Zoomed preview — same layout and text as the printed label"}
        </span>
        <span className="flex items-center gap-0.5 rounded-lg border border-slate-200 bg-white p-0.5 shadow-sm">
          {seg("fit", Maximize2, "Fit", "Zoom tag to fit the panel")}
          {seg("real", Ruler, "1:1", "True millimetre size on screen (96 dpi)")}
        </span>
      </div>

      {warnings.length > 0 && (
        <div className="flex flex-col gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2.5">
          <div className="flex items-center gap-1.5 text-[13px] font-bold text-amber-900">
            <TriangleAlert size={14} />
            Text will print cut — fix before printing
          </div>
          {warnings.map((w, i) => (
            <div key={i} className="text-[13px] text-amber-900">
              <span className="font-semibold">{w.field}:</span> overflows by ~
              {w.overflowMm ?? w.overflow_mm} mm. Shorten it or use a wider tag.
            </div>
          ))}
        </div>
      )}

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
                  <div dangerouslySetInnerHTML={{ __html: tagSvg }} />
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center">
                <div className="tag-svg w-full max-w-[640px]" dangerouslySetInnerHTML={{ __html: tagSvg }} />
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
        Only filled fields print — blanks stay off the label automatically.
      </div>
    </div>
  );
}
