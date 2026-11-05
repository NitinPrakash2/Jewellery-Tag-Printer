# Manish Ornaments — Jewellery Tag Printer · Handoff Summary

> Is document ko kisi bhi naye AI agent ko de sakte ho. Ye project ka poora history,
> architecture, build/print pipeline, testing tarika aur current warnings cover karta hai.

---

## 1. What this app is

A Windows desktop app for a jewellery shop ("Manish Ornaments") that prints price/weight
tags on a **real barcode/label printer** (thermal, 203 DPI) over USB.

- Shop owner enters: Purity/HUID, Product name, Gross Wt, Less Wt, Net Wt.
- App renders a **fold tag**: printable body + fold-only tail that must get **zero ink**.
- Labels are printed **server-side on the same PC** (cloud can't reach the USB printer).
- Delivered to a non-technical friend as a **zero-install `.exe`** (PyInstaller onedir) inside a zip.

Non-negotiables (user's rules):
1. Frontend **React + JavaScript + Vite** (NOT TypeScript), Tailwind, lucide-react.
2. Backend **FastAPI + SQLAlchemy + Alembic**.
3. **Dual DB**: PostgreSQL for dev/deploy, SQLite when frozen (`.exe`). `DATABASE_URL` decides.
   No seed data, ever.
4. **Light mode only**. Max **99 copies**. `net = gross − less`.
5. **Blank fields must not exist anywhere** — not in preview, not in print, not in history.
   Stored as `NULL`, row is omitted entirely (no blank gap, no dash).
6. Tag is **100 × 15 mm** by default = **65 mm printable body + 35 mm fold-only tail**,
   tail gets **ZERO ink**. Width/height/tail editable (manual + presets), real physical mm.
7. All UI text/guides in **English** (user speaks Hinglish; the app UI stays English).
8. Any barcode printer must work — auto-detect + auto-select; per-brand driver links in Settings.

---

## 2. Repo layout

```
Jewellery-Tag-Printer/
├── client/                     # React + Vite + Tailwind
│   └── src/
│       ├── pages/              # PrintPage, HistoryPage, SettingsPage, HelpPage
│       ├── components/         # TagPreview, UsbLivePanel, PremiumSelect, etc.
│       ├── lib/tagSvg.js       # CLIENT MIRROR of server layout + SVG renderer
│       └── services/           # API client
└── server/                     # FastAPI backend + PySide6 desktop shell
    ├── app/
    │   ├── api/                # routes_print, routes_printers, routes_settings, routes_history...
    │   ├── database/           # session/engine, SQLite/Postgres switching
    │   ├── domain/             # validation, models
    │   ├── printing/           # raster.py, windows_spool.py, calibration.py, adapters
    │   ├── services/           # print_service, settings_service, logo_service, history_service
    │   └── tag/               # layout.py (ALL the maths), renderer.py (SVG), units.py
    ├── alembic/versions/       # 0001_initial, 0002_nullable_weights
    ├── tests/                  # 111 tests
    ├── desktop.py              # frozen exe entry: boots uvicorn + PySide6 window (+ smoke test)
    └── dist/ManishTagPrinter/  # built exe
```

**Key idea:** the tag is generated twice — client-side `tagSvg.js` for instant preview,
server-side `renderer.py` for the real print. Both must stay **pixel-for-pixel identical**.
Any layout change must be applied in BOTH files (they are mirrors).

---

## 3. How the tag layout engine works (`server/app/tag/layout.py`)

Everything is in **millimetres**; only W × H × tail are user input, everything else derives.

- `body_w = w − tail`, `fold_x = body_w / 2` (fold crease down the middle of printable body).
- Back side: logo zone at `fold_x * 0.27`, item zone at `fold_x * 0.76`, `iw = fold_x * 0.42`.
- **Auto-fit fonts, no `textLength`** (browsers honour `textLength`, print rasters ignore it —
  this was the original "looks fine on screen, cut on paper" bug). Instead we compute a real
  font size that fits: `font = min(height_budget, zone_width / (chars × avg_char_width))`.
  - `CHAR_W = {sans: 0.55, serif: 0.62}`, bold adds `×1.06`, letter-spacing is budgeted too.
- Item name and purity share **ONE font size** (min of both fits) so the two lines match.
- Weight rows: each row is `"Gross Wt. : 1.234 g"`, only filled rows exist.
- `layout_warnings()` returns overflow in **mm** per field for live UI warnings.

`units.py`: `mm_to_dots(mm)` at 203 DPI (100 mm → 799 px, 15 mm → 120 px).

---

## 4. Rendering & the "solid lines" feature (`renderer.py` + `tagSvg.js`)

Final design requested by the shop owner:
- **No border, no fold line, no divider, no gold rule** on the printed tag.
- Product prints as just `Ring` — the `ITEM - ` prefix was removed.
- Gross / Less / Net stay **bold**.

But the shop owner still needs to *see* where the content area is in the preview. So:

| Settings → Tag → "Print border & divider lines" | Preview | Paper |
|---|---|---|
| **OFF (default, `show_lines = "0"`)** | dashed grey `#94a3b8`, 0.25 mm, `data-preview-only="true"` | **nothing prints** |
| **ON (`show_lines = "1"`)** | solid black border + fold line + divider + gold rule | all lines print |

Why alignment is safe: **positions are identical in both modes**; only stroke style changes.
Verified by tests asserting the same geometry with lines on/off.

Mechanics:
1. `build_tag_svg(..., show_lines: bool = False)` emits either solid elements or
   `data-preview-only="true"` dashed elements.
2. `raster.py::strip_preview_only(svg)` runs a regex **before rasterising**:
   `re.sub(r"<[^>]*data-preview-only=\"true\"[^>]*/?>", "", svg)` → guides never reach the printer.
3. Preview shows the raw SVG (guides visible); print path strips them.
4. Same trick is used for the **tail outline** (fold area) — it must never print.
5. Setting lives in `settings_service.py` (`"show_lines": "0"` default, validated to `0/1/true/false`),
   is read in `print_service.py` + `routes_print.py`, rendered in `SettingsPage.jsx`
   (checkbox "Print border & divider lines"), mirrored in `PrintPage.jsx` → `buildTagSvg`.

Settings are stored in DB (`settings` table, category `tag`):
`width_mm, height_mm, tail_width_mm, orientation, show_lines`.

---

## 5. Printing pipeline (the part that actually matters)

```
SVG (mm, auto-fit fonts)
  → strip_preview_only()               # remove dashed guides + tail outline
  → cairosvg → PNG @203 DPI            # 100x15 mm → 799x120 px
  → Pillow: L → threshold 200 → mode "1"          # pure 1-bit, no greys
  → GDI SetDIBitsToDevice(1-bpp DIB)   # 1:1, top-left, NO resampling
  → spool (copies 1..99)
```

Files: `printing/raster.py`, `printing/windows_spool.py`, `printing/lp46neo_adapter.py`,
`printing/calibration.py`, `services/print_service.py`.

`PRINT_MODE = "1-bit-dib"` is reported by `/api/health` and shown at the bottom of the
Help page together with the exe build timestamp — that is how you prove which build a
shop PC is actually running.

### Where the print diagnostic is visible (support path)
Every print adds a green **PRINT** line to Settings → **Live Error Monitor**:

```
Print bitmap 799x120 dots -> driver page 799x120 dots, 100x15 mm, 1-bit no-dither
```

That line comes from `print_size_message()` in `windows_spool.py` and is pushed with
`diagnostics.record("PRINT", "info", ...)`. If the driver page is smaller than the bitmap
the message appends `(driver page smaller: edge clipped, NOT rescaled)`. The shop can
screenshot this instead of finding files, which is what the handoff procedure relies on.

Files on disk (still written, for deeper debugging):
- `<exe folder>\_internal\logs\app.log` — everything, including the same size line
- `<exe folder>\logs\stdout.log` — startup/console output

**Test Print uses the configured tag size** (`/api/printers/test` reads settings
`tag.width_mm/height_mm`), so it exercises the same driver form and dot count as real
tags — never the old hard-coded 50x25 mm page.

### Fixes that must NOT be regressed
1. **1-bit DIB blit via `SetDIBitsToDevice`**, not Pillow's `Dib.draw`.
   Pillow draws with `StretchDIBits`, where the driver may halftone/dither the bitmap —
   that is the dotted/blurry text bug. A native 1-bpp DIB has exactly one bit per dot:
   nothing to dither. Verified by a GDI roundtrip test (bits come back pixel-identical).
2. **Threshold to mode "1"**, never RGB. Any grey lets the driver halftone.
3. **DIB header must declare 203 dpi**: `biXPelsPerMeter = biYPelsPerMeter = 7992`.
   With `0`, Unidrv label drivers assume screen dpi and rescale the bitmap, which
   reintroduces halftoning even for 1-bpp data.
4. **DEVMODE comes from GetPrinter level 8 (per-user), not level 2 (defaults).**
   Level 2 throws away the shop's printer preferences (density/speed/media) on every
   job. Also force `dmDitherType = DMDITHER_NONE` and `dmColor = DMCOLOR_MONOCHROME`
   (value first, then set the matching `dmFields` bit).
5. **`_fit_box` returns a top-left 1:1 rect** `(0, 0, w, h)`; never upscale.
   Thermal heads feed from the top edge; centering/upscaling pushes ink onto the next label.
6. **Exact page size via DEVMODE** before `CreateDC`:
   `PaperSize = DMPAPER_USER (256)`, `PaperWidth/Length` in **tenths of a mm**,
   `FormName = form_name_for(w, h)`, plus `ensure_label_size()` to register the custom form.
   Without this the driver keeps an old form and every label drifts onto the next one.
7. **Font normalisation** in `raster.py`: map every font to `Helvetica` / `Times-Roman`
   so cairo never needs missing system fonts; bundle reportlab `.pfb` fonts in PyInstaller.
8. **Virtual printers filtered** out of the list (PDF/XPS/OneNote/Fax etc.).
9. Width limits: DCode 104 mm, TVS 108 mm → warn + suggest fitting size.

### Test Print is the quality oracle
`print_test` renders at the configured tag size and includes a **solid black bar**
(`_test_tag_svg`). If the bar prints solid but text is dotted → bitmap path bug.
If the bar itself is dotted → the driver/printer is halftoning or density is low;
no app-side bitmap change can fix that (check driver Dithering/Density).

### Rendering: supersample before thresholding
`svg_to_png_bytes` renders at `3x` dpi and downscales with Lanczos (`SUPERSAMPLE` in
`raster.py`). A direct 203 dpi render gave stair-stepped curves (G/S/0/8) that looked
like dropped ink on the thermal head. The final bitmap is still thresholded to pure
1-bit in the spooler, so no greys reach the driver. Cost: ~0.5 s per tag.

### Never hand the driver a bigger bitmap than its page
The driver's printable area is a few dots smaller than the label (TVS: 779x120 px for
100x15 mm). Handing over 799x120 makes it shrink the image ~2.5%, which puts a ragged
vertical phase through some glyphs (looks dotted). `print_png` therefore **crops the
blank margin** so `bitmap == driver page`, 1:1. `_is_blank()` guards this: the crop is
only allowed when the trimmed strip contains no ink (otherwise we warn and keep it).
Measured on the shop printer: 799x120 → 779x120, and the removed 20 dots are blank tail.

### Calibration (the real alignment tool — not code changes)
Settings → Calibration: `offset_x_mm`, `offset_y_mm`, `scale`, `rotate_180`.
Applied identically in server renderer and client preview (SVG `<g transform>`), so what you
see is what prints. `rotate_180` fixes an upside-down tag.

---

## 6. How smoke testing was done (3 layers)

### Layer 1 - Unit/integration tests (111 tests)
```powershell
cd server
$env:DATABASE_URL="postgresql+psycopg2://postgres:nitin12%40%23@localhost:5432/jewellery_tags_test"
python -m pytest tests -q
# expected: 101 passed
```
Covers: API, validators, renderer geometry, lines toggle, calibration, logo upload/transparency,
raster sizes, spool `_fit_box`, USB detection, diagnostics, desktop DB migration, LAN.

> `Win32 exception occurred releasing IUnknown` after pytest = harmless pywin32 teardown noise.
> PowerShell red `NativeCommandError` lines during python runs = stderr noise, not failure.

### Layer 2 — Live API smoke (real server, real raster math)
Run the backend on a spare port, then hit the real endpoints:

```powershell
cd server
$env:DATABASE_URL="postgresql+psycopg2://postgres:nitin12%40%23@localhost:5432/jewellery_tags"
$env:CORS_ORIGINS="*"
$api = Start-Process python -ArgumentList "-m","uvicorn","app.main:app","--host","127.0.0.1","--port","8123" -PassThru
Start-Sleep -Seconds 8
python <path>\full_smoke.py
Stop-Process -Id $api.Id -Force
```

The smoke script (`full_smoke.py`) does:
1. `GET /api/settings/tag` → assert `show_lines == "0"`.
2. `POST /api/settings/logo` (multipart upload) → assert ok.
3. `POST /api/tag/render` with worst-case data → assert in SVG:
   `<image` + `data:image/png;base64` (logo embedded), no `stroke="black" stroke-width="0.4"`
   (no solid border), `data-preview-only="true"` present (guides), `Less Wt.` absent,
   `ITEM -` absent, product name present.
4. Rasterise exactly like the printer: `svg_to_png_bytes(svg, 100, 15)` →
   assert size `(799, 120)` and `dark pixels > 500` (not blank).
5. Flip `show_lines` to `"1"` → assert solid border appears.
6. Cleanup: lines back to `"0"`, logo deleted.

Result at the time of writing: **FULL SMOKE: PASS**, raster `799×120`, **3720 dark pixels**,
`dark outside body (x ≥ 519) = 0`, vertical ink span `22–103 of 120`.

That last check is the important one: it proves **the app emits zero ink in the 35 mm tail**
and nothing outside the body — i.e. any spill onto the next label is a **printer feed/form**
problem, not a design problem.

### Layer 3 — Frozen exe smoke (catches PyInstaller-only breakage)
```powershell
cd server
Remove-Item -Recurse -Force ".\dist\ManishTagPrinter\app_data" -ErrorAction SilentlyContinue
$p = Start-Process -FilePath ".\dist\ManishTagPrinter\ManishTagPrinter.exe" -ArgumentList "--smoke-test" -Wait -PassThru
echo "EXIT:$($p.ExitCode)"
Get-Content ".\dist\ManishTagPrinter\smoke-result.txt"
```
`desktop.py --smoke-test` boots the real backend in-process with SQLite, then checks:
- DB init, uvicorn thread alive, waits for readiness
- `GET /` → 200, `/api/health` → 200 + `db_ok: true`, `/api/printers` → 200, `/api/settings` → 200
- `_smoke_raster()`: `build_tag_svg(...)` → `svg_to_png_bytes()` → asserts `(799, 120)`
- writes `smoke-result.txt` with `SMOKE PASS` + `EXIT:0`

Expected output:
```
SMOKE OK  / -> 200
SMOKE OK  /api/health -> 200
SMOKE health: {'ok': True, 'app': 'jewellery-tag-printer', 'env': 'dev', 'db_ok': True}
SMOKE OK  /api/printers -> 200
SMOKE OK  /api/settings -> 200
SMOKE raster -> (799, 120) (want (799, 120))
SMOKE PASS
EXIT:0
```

> Always delete `app_data/` + `smoke-result.txt` from the dist folder after a smoke run,
> otherwise the friend's zip ships with a test database.

---

## 7. Build & package

### Client
```powershell
cd client
npm run build        # -> client/dist
```

### Exe (from `server/`)
```powershell
python -m PyInstaller --noconfirm --clean --name ManishTagPrinter --windowed --onedir ^
  --add-data "..\client\dist;client\dist" ^
  --add-data "alembic.ini;." ^
  --add-data "alembic;alembic" ^
  --add-data "C:\Users\nitin\AppData\Local\Programs\Python\Python313\Lib\site-packages\reportlab\fonts;reportlab/fonts" ^
  --add-binary "C:\Windows\System32\mfc140u.dll;." ^
  --hidden-import sqlalchemy.dialects.sqlite.pysqlite ^
  --hidden-import sqlalchemy.dialects.postgresql.psycopg2 ^
  desktop.py
```
Then run the exe smoke test (Layer 3), clean `app_data`, then zip:
```powershell
Copy-Item "..\FRIEND_SETUP.md" ".\dist\ManishTagPrinter\FRIEND_SETUP.txt" -Force
Compress-Archive -Path ".\dist\ManishTagPrinter" -DestinationPath "C:\Users\nitin\Desktop\Printer.zip" -Force
```

### Frozen-exe lessons (don't regress)
- Pass the **app object** to uvicorn (`uvicorn.Server(uvicorn.Config(app, ...))`), not an import string.
- `log_config=None` (no logging config file inside the bundle).
- PyInstaller 6 puts datas under `_internal` → resolve with `sys._MEIPASS` / `CLIENT_DIST_DIR`.
- `--windowed` means `sys.stdout is None` → restore it to `logs/stdout.log`.
- Bundle reportlab `.pfb` fonts + normalize font names to Helvetica/Times.
- SQLite auto-migrate creates a `.bak` before altering.

---

## 8. App behaviour details already implemented

- PRINT / HISTORY / SETTINGS / HELP pages; light theme only.
- Preview modes: **Fit** and **1:1** (true size on screen).
- Live overflow warnings in mm, per field.
- Press **Enter** to jump to the next field; max 99 copies.
- Premium custom portal dropdowns (not native `<select>`), debounced history search.
- Settings: shop name + logo dropzone, tag dimensions + presets, printer setup wizard,
  calibration (X/Y offset, scale, rotate 180°), driver download links per brand (TVS/DCode...),
  USB live panel, error monitor, test print.
- History stores `NULL` for blanks and hides blank fields in the table.
- Friend's printer: **`SNBC TVSE LP 46 NEO BPLE`** (matched via tvs/tvse/bple/snbc/lp46),
  plug-and-play TVS driver.

---

## 9. Repo state / regression history (read before rebuilding)

The git history on this repo is messy: several commits after "build 10" look like normal
feature commits but actually **revert** critical printing fixes. The dotted, blurry print
that reached the shop came from exactly that: the working tree behind the zip had lost the
pure-B&W threshold and the 1:1 draw path.

Current state (fixed):
- `windows_spool.py` blits a native **1-bit DIB** via `SetDIBitsToDevice` (no dithering possible).
- `lp46neo_adapter.py` passes the label size to the spooler.
- `layout.py` / `tagSvg.js` only changed the row pitch (blank-field gap fix).
- Layout typography is identical to "build 10".

Before any future rebuild:
1. `git diff` and confirm `windows_spool.py` still contains `_blit_1bit`, `mode="1"`
   and the DEVMODE block; confirm `PRINT_MODE = "1-bit-dib"` exists.
2. Run the new exe and confirm `/api/health` returns `print_mode: "1-bit-dib"`.
3. Only then zip. Never ship a build whose `print_mode` is missing/old.

---

## 10. Blank field spacing (done)

When **Less Wt is blank**, Gross and Net used to spread to `0.30h` / `0.80h` — a phantom empty
row in the middle. Fixed with a constant pitch and a centred block:

- `pitch = h * 0.25`, `row_ys = h * 0.55 + (i - (n-1)/2) * pitch`
- 3 rows → `0.30 / 0.55 / 0.80` (unchanged), 2 rows → `0.425 / 0.675`, 1 row → `0.55`
- Applied identically in `layout.py` and `tagSvg.js`
- Locked by `test_blank_less_leaves_no_gap`
- Add a test: 2 rows → gap equals 1 row pitch; 3 rows → same pitch.

---

## 11. Gotchas / debugging notes

- **Stale server on port 8000** is the #1 cause of "my change did nothing". Check with
  `Get-NetTCPConnection -LocalPort 8000 -State Listen` and kill the PID.
- Backend changes need a **uvicorn restart** (no auto-reload in the packaged app).
- Real printer tests must run on the shop PC (USB); the cloud copy can only preview.
- `styles.css` / UI: heavy `drop-shadow` filters caused scroll lag — they were removed.
  Keep effects cheap; history search is debounced; printer polling is calmed down.
- Blank field rule is enforced at three places: request validation → DB `NULL` → renderer
  omits the row. A regression here shows as `None`/`0.000` on paper.
- `ITEM -` prefix and the plain `textLength` hack are **removed on purpose**; don't re-add.

---

## 12. Quick file reference

| Concern | File |
|---|---|
| All tag maths / fonts / warnings | `server/app/tag/layout.py` |
| Server SVG (source of truth for print) | `server/app/tag/renderer.py` |
| Client SVG mirror (preview) | `client/src/lib/tagSvg.js` |
| SVG → 203 DPI PNG, guide stripping, fonts | `server/app/printing/raster.py` |
| Windows GDI spool, `_fit_box`, DEVMODE, forms | `server/app/printing/windows_spool.py` |
| Calibration transforms | `server/app/printing/calibration.py` |
| Print orchestration / copies / history | `server/app/services/print_service.py` |
| Tag settings + `show_lines` validation | `server/app/services/settings_service.py` |
| Logo upload, transparency→white flatten | `server/app/services/logo_service.py` |
| Tag size presets / warnings / Enter-next | `client/src/pages/PrintPage.jsx` |
| Printer setup, calibration, lines checkbox | `client/src/pages/SettingsPage.jsx` |
| Frozen exe entry + `--smoke-test` | `server/desktop.py` |
| Printer detection + driver help | `server/app/api/routes_printers.py` |
