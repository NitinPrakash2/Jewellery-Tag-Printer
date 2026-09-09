import { useRef, useState } from "react";
import { ImagePlus, Loader2, Trash2, UploadCloud } from "lucide-react";
import { api } from "../services/api.js";

const ACCEPT = ".png,.jpg,.jpeg,.svg";
const MAX_BYTES = 2 * 1024 * 1024;

export default function LogoDropzone({ dataUri, onChanged, onError }) {
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);

  async function upload(file) {
    if (!file) return;
    if (!/\.(png|jpe?g|svg)$/i.test(file.name)) {
      onError?.("Logo must be a PNG, JPG or SVG image.");
      return;
    }
    if (file.size > MAX_BYTES) {
      onError?.("Logo is too large (max 2 MB).");
      return;
    }
    setBusy(true);
    try {
      const up = await api.logoUpload(file);
      const r = await api.logoGet();
      onChanged?.(r.data_uri || null, up.logo_path || r.logo_path || "");
    } catch (e) {
      onError?.(e?.message || "Logo upload failed.");
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await api.logoDelete();
      onChanged?.(null, "");
    } catch (e) {
      onError?.(e?.message || "Could not remove logo.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          upload(e.dataTransfer.files?.[0]);
        }}
        className={`flex cursor-pointer items-center gap-4 rounded-xl border-2 border-dashed p-4 transition ${
          dragging
            ? "border-slate-900 bg-slate-900/[0.04]"
            : "border-slate-300 bg-slate-50/60 hover:border-slate-500 hover:bg-slate-50"
        }`}
      >
        {dataUri ? (
          <img
            src={dataUri}
            alt="Shop logo"
            className="h-16 w-16 shrink-0 rounded-lg border border-slate-200 bg-white object-contain p-1"
          />
        ) : (
          <span className="flex h-16 w-16 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-300">
            <ImagePlus size={26} />
          </span>
        )}
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5 text-sm font-semibold text-slate-800">
            {busy ? (
              <Loader2 size={15} className="animate-spin" />
            ) : (
              <UploadCloud size={15} className="text-slate-500" />
            )}
            {busy ? "Uploading…" : dataUri ? "Drop a new logo or click to replace" : "Drag & drop logo here, or click to browse"}
          </span>
          <span className="mt-0.5 block truncate text-xs text-slate-400">
            PNG, JPG or SVG from your device · max 2 MB · prints on the tag
          </span>
        </span>
        {dataUri && (
          <button
            type="button"
            title="Remove logo"
            disabled={busy}
            onClick={(e) => {
              e.stopPropagation();
              remove();
            }}
            className="rounded-lg border border-slate-200 bg-white p-2 text-slate-400 shadow-sm transition hover:border-red-300 hover:text-red-600"
          >
            <Trash2 size={15} />
          </button>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          upload(e.target.files?.[0]);
          e.target.value = "";
        }}
      />
    </div>
  );
}
