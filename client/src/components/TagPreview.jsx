function SidePanel({ title, svg, widthMm, heightMm, badge }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
      <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
        <span className="text-[13px] font-semibold text-slate-700">{title}</span>
        <span className="flex items-center gap-1.5">
          {badge && (
            <span className="rounded-full bg-slate-900 px-2 py-px text-[11px] font-semibold text-white">
              {badge}
            </span>
          )}
          <span className="rounded-full bg-slate-100 px-2 py-px text-[11px] font-medium text-slate-500">
            {widthMm} × {heightMm} mm
          </span>
        </span>
      </div>
      <div className="flex items-center justify-center border-t border-slate-100 bg-slate-50/60 px-4 py-5">
        {svg ? (
          <div className="tag-svg w-full max-w-[360px]" dangerouslySetInnerHTML={{ __html: svg }} />
        ) : (
          <span className="py-6 text-[13px] text-slate-400">Enter details to preview</span>
        )}
      </div>
    </div>
  );
}

export default function TagPreview({ frontSvg, backSvg, widthMm = 50, heightMm = 25, serverBacked = false }) {
  return (
    <div className="flex flex-col gap-3">
      <SidePanel
        title="Front Side (Product Details)"
        svg={frontSvg}
        widthMm={widthMm}
        heightMm={heightMm}
        badge={serverBacked ? "Server" : null}
      />
      <SidePanel title="Back Side (Shop Name)" svg={backSvg} widthMm={widthMm} heightMm={heightMm} />
      <div className="text-right text-xs text-slate-400">
        {serverBacked
          ? "Preview rendered by server — exactly what will print."
          : "Actual print size may vary slightly based on your label and printer settings."}
      </div>
    </div>
  );
}
