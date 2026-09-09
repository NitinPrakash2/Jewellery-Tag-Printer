import { useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Minus, Plus } from "lucide-react";

export function Field({ label, error, children }) {
  return (
    <label className="block">
      <span className="mb-2 block text-[13px] font-semibold text-slate-700">{label}</span>
      {children}
      {error && <span className="mt-1.5 block text-[12px] font-medium text-red-600">{error}</span>}
    </label>
  );
}

// Horizontal label/control row: stacked on small screens, aligned grid on sm+
export function Row({ label, error, children }) {
  return (
    <div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[150px_minmax(0,1fr)] sm:items-center sm:gap-3">
        <span className="text-sm font-semibold text-slate-700">{label}</span>
        <div className="min-w-0">{children}</div>
      </div>
      {error && <div className="mt-1.5 text-[12px] font-medium text-red-600 sm:pl-[162px]">{error}</div>}
    </div>
  );
}

const CONTROL =
  "h-10 rounded-lg border bg-white text-sm text-slate-900 shadow-sm outline-none transition duration-200";

export function TextInput(props) {
  return (
    <input
      {...props}
      className={`${CONTROL} w-full px-3.5 focus:border-slate-700 focus:ring-[3px] focus:ring-slate-200 ${
        props["data-error"] ? "border-red-400 hover:border-red-500" : "border-slate-300 hover:border-slate-400"
      } ${props.className || ""}`}
    />
  );
}

export function PrimaryButton({ children, small, ...props }) {
  const size = small ? "min-h-[34px] px-4 py-1.5 text-[13px]" : "min-h-[44px] px-5 py-2.5 text-sm";
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-slate-700 to-slate-800 font-semibold text-white shadow-[0_8px_16px_rgba(15,23,42,0.3)] transition duration-200 hover:from-slate-600 hover:to-slate-700 hover:shadow-[0_10px_20px_rgba(15,23,42,0.4)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none ${size} ${props.className || ""}`}
    >
      {children}
    </button>
  );
}

export function OutlineButton({ children, small, ...props }) {
  const size = small ? "min-h-[34px] px-4 py-1.5 text-[13px]" : "min-h-[44px] px-5 py-2.5 text-sm";
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white font-semibold text-slate-700 shadow-sm transition duration-200 hover:border-slate-400 hover:bg-slate-50 hover:shadow-md active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 ${size} ${props.className || ""}`}
    >
      {children}
    </button>
  );
}

export function Card({ children, className = "" }) {
  return (
    <div className={`rounded-xl border border-slate-200/60 bg-gradient-to-br from-white to-slate-50/50 shadow-[0_2px_12px_rgba(15,23,42,0.08)] backdrop-blur-sm ${className}`}>{children}</div>
  );
}

export function CardTitle({ icon: Icon, children }) {
  return (
    <div className="flex items-center gap-2.5 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white px-4 py-3.5">
      {Icon && <Icon size={18} className="text-slate-700" />}
      <h2 className="text-[15px] font-bold text-slate-900">{children}</h2>
    </div>
  );
}

export function Notice({ kind = "error", children }) {
  const styles =
    kind === "success"
      ? "border-green-200/60 bg-gradient-to-r from-green-50 to-emerald-50 text-green-800 shadow-[0_2px_8px_rgba(34,197,94,0.1)]"
      : "border-red-200/60 bg-gradient-to-r from-red-50 to-rose-50 text-red-800 shadow-[0_2px_8px_rgba(239,68,68,0.1)]";
  return <div className={`rounded-lg border px-4 py-3 text-[13px] font-medium backdrop-blur-sm ${styles}`}>{children}</div>;
}

// Premium custom dropdown: button trigger + floating menu with check marks.
export function PremiumSelect({ value, onChange, options, placeholder = "— Select —", className = "" }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const close = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    const onKey = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", onKey);
    };
  }, [open ]);

  const selected = options.find((o) => String(o.value) === String(value));

  return (
    <div ref={ref} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`${CONTROL} flex w-full items-center justify-between gap-2 bg-gradient-to-b from-white to-slate-50 px-3.5 text-left hover:shadow-md ${
          open
            ? "border-slate-900 shadow-md ring-[3px] ring-slate-900/10"
            : "border-slate-300 hover:border-slate-500"
        } ${selected ? "text-slate-900" : "text-slate-400"}`}
      >
        <span className="truncate font-medium">{selected ? selected.label : placeholder}</span>
        <span
          className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full transition-colors duration-200 ${
            open ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-500"
          }`}
        >
          <ChevronDown size={14} className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
        </span>
      </button>
      {open && (
        <div className="menu-in menu-scroll absolute z-30 mt-2 max-h-64 w-full overflow-auto rounded-xl border border-slate-200/90 bg-white/95 p-1.5 shadow-[0_20px_50px_rgba(15,23,42,0.22)] backdrop-blur-md">
          {options.map((o) => {
            const active = String(o.value) === String(value);
            return (
              <button
                key={String(o.value)}
                type="button"
                onClick={() => {
                  onChange(o.value);
                  setOpen(false);
                }}
                className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition duration-150 ${
                  active
                    ? "bg-slate-900 font-semibold text-white shadow-[0_4px_12px_rgba(15,23,42,0.35)]"
                    : "font-medium text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                <span className="truncate">{o.label}</span>
                {active && <Check size={15} strokeWidth={3} className="shrink-0 text-amber-300" />}
              </button>
            );
          })}
          {options.length === 0 && (
            <div className="px-3 py-2.5 text-[13px] text-slate-400">No options available</div>
          )}
        </div>
      )}
    </div>
  );
}

// Connection status pill
export function StatusPill({ ok, text }) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-[13px] font-semibold ring-1 ring-inset transition duration-200 ${
        ok
          ? "bg-gradient-to-r from-green-50 to-emerald-50 text-green-700 ring-green-200/60 shadow-[0_2px_8px_rgba(34,197,94,0.1)]"
          : "bg-gradient-to-r from-amber-50 to-orange-50 text-amber-700 ring-amber-200/60 shadow-[0_2px_8px_rgba(251,146,60,0.1)]"
      }`}
    >
      <span className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? "bg-green-500" : "bg-amber-400"}`} />
      {text}
    </span>
  );
}

// Number stepper (copies)
export function Stepper({ value, onChange, min = 1, max = 99 }) {
  const clamp = (n) => {
    if (Number.isNaN(n)) return min;
    return Math.max(min, Math.min(max, n));
  };
  return (
    <div className="flex h-10 w-32 items-stretch overflow-hidden rounded-lg border border-slate-300 bg-gradient-to-br from-white to-slate-50 shadow-sm transition focus-within:border-slate-700 focus-within:ring-[3px] focus-within:ring-slate-200 hover:border-slate-400 hover:shadow-md">
      <input
        value={value}
        onChange={(e) => onChange(String(clamp(parseInt(e.target.value, 10))))}
        inputMode="numeric"
        className="w-full bg-transparent px-3 text-sm font-semibold text-slate-900 outline-none"
      />
      <div className="flex flex-col border-l border-slate-200 bg-gradient-to-b from-slate-100 to-slate-50">
        <button
          type="button"
          onClick={() => onChange(String(clamp((parseInt(value, 10) || min) + 1)))}
          className="flex flex-1 items-center justify-center px-1.5 text-slate-600 transition duration-150 hover:bg-slate-200 hover:text-slate-800"
          title="Increase"
        >
          <Plus size={14} className="font-bold" />
        </button>
        <button
          type="button"
          onClick={() => onChange(String(clamp((parseInt(value, 10) || min) - 1)))}
          className="flex flex-1 items-center justify-center border-t border-slate-200 px-1.5 text-slate-600 transition duration-150 hover:bg-slate-200 hover:text-slate-800"
          title="Decrease"
        >
          <Minus size={14} className="font-bold" />
        </button>
      </div>
    </div>
  );
}
