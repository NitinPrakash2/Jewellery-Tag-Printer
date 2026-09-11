# Jewellery Tag Printer — Real-Time Printing & Deploy Guide

> What this document covers: (1) how printing works in real time after deploy,
> (2) first-time setup on the shop PC, (3) everything built so far.

---

## 1. How it works in real time (end to end)

Every print follows the same live pipeline — no batch jobs, no background queues.
The operator fills the form, presses PRINT, and paper comes out within seconds:

```
Operator enters: Purity, Item, Gross Wt, Less Wt  →  Net auto-calculates
        ↓  (instant, in the browser)
Live preview updates on every keystroke (same SVG the printer will get)
        ↓  PRINT TAG pressed
POST /api/print  →  server validates in milliseconds
        ↓
Server renders the fold-tag SVG (back + dashed fold line + front, body-only)
  - Less Wt = Gross − Net, formatted to 3 decimals
  - Shop logo embedded as base64 (or monogram fallback if missing)
        ↓
SVG rasterized to a bitmap at the printer's native 203 DPI
  - Exact physical size: e.g. 110×12 mm → 879×96 pixels
  - Millimetres on screen = millimetres on paper (1:1 preview proves it)
        ↓
Bitmap spooled through the Windows printer driver → PAPER OUT
        ↓
History row saved with timestamp (reprint creates a NEW row, never edits)
```

**Key real-time behaviours:**

| Moment | What happens live |
|---|---|
| Typing in the form | Preview tag + Net weight + Less readout update instantly (no server round-trip) |
| Preview button | Server renders the canonical SVG — byte-identical to what will print |
| Printer selected | App reads live Windows status (ready / offline / out of paper / cover open) in plain words |
| Tag wider than printer | Warning + one-click fitting size appears the moment dims or printer change |
| Print pressed | Validation → raster → spool → history, with success/failure reported from the spooler, never assumed |
| Logo uploaded | Embedded into the very next preview and print (base64, no file-path dependency) |
| Printer unplugged mid-day | Status pill turns red, print button reports "not ready" instead of fake success |

---

## 2. Printer compatibility (real time, any brand)

The app prints through the **Windows printer driver**, not through brand-specific
command languages (no ZPL/TSPL/EPL anywhere). Consequence: **any barcode printer
with a Windows driver works** — TVS, DCode, Zebra, TSC, Honeywell.

| Printer | DPI | Max print width | Status |
|---|---|---|---|
| DCode DC 423 Pro | 203 | **104 mm** | Verified driver source, wizard integrated |
| TVS LP 46 Neo | 203 | **108 mm** | Verified driver source, wizard integrated |
| Other 203 DPI barcode printers | 203 | Varies | Works via driver; width limit matched by name, otherwise unrestricted |

Rules enforced live:
- Raster always renders at 203 DPI (thermal barcode standard).
- If the tag is wider than the selected printer's maximum, the app warns
  immediately and offers a one-click fitting size (e.g. 100×12 for DCode).
- Label size is created in Windows automatically by the Setup wizard —
  the operator never opens Windows Settings.

---

## 3. Deploy guide (shop PC or any Windows PC)

### 3.1 Prerequisites

- Windows 10/11
- Python 3.13 (from python.org)
- PostgreSQL 16/17/18 (note the password you set during install)
- Node.js 20+ (needed once, to build the client)

### 3.2 Server setup

```powershell
cd C:\Jewellery-Tag-Printer\server
pip install -r requirements.txt
```

Create the database (use your own password):

```powershell
$env:PGPASSWORD="your-password"
psql -U postgres -h localhost -d postgres -c "CREATE DATABASE jewellery_tags;"
```

Create `server/.env` (copy from `server/.env.example`). If the password
contains `#` write `%23`, if it contains `@` write `%40`:

```
DATABASE_URL=postgresql+psycopg2://postgres:your-password@localhost:5432/jewellery_tags
```

Run migrations and start the server:

```powershell
$env:DATABASE_URL="postgresql+psycopg2://postgres:your-password@localhost:5432/jewellery_tags"
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### 3.3 Client (build once, then serve)

```powershell
cd C:\Users\nitin\Desktop\Jewellery-Tag-Printer\client
npm install
npm run build
```

This produces `client/dist/`. Serve it with any static server
(e.g. `npx serve dist -l 5173`), or pack it into the `.exe` later.

### 3.4 Shop LAN mode — one live URL for every laptop (recommended)

The server also serves the built app, so a single URL opens the full
application from any laptop on the shop WiFi. Printing always happens on
the PC the printer is USB-connected to.

One-time (Administrator PowerShell in `server/`):

```powershell
.\allow-lan.ps1
```

Daily (double-click `server/start-lan.bat`, after putting the real DB
password in it once):

```bat
set DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/jewellery_tags
set CORS_ORIGINS=*
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then any laptop on the same WiFi opens `http://<shop-pc-ip>:8000`
(the server log prints the exact address at startup). No `npm`/Vite needed
on those laptops — just a browser.

> Security: LAN mode has no login — anyone on the shop network can print.
> Perfect for one shop; never expose port 8000 directly to the internet
> without adding authentication.

### 3.5 Daily operation (single PC)

1. PostgreSQL starts automatically with Windows.
2. Run the server (3.2 command or `start-lan.bat`).
3. Open `http://localhost:8000` in the browser. Done.

> Note: the Vite dev server hot-reloads the client automatically, but the
> API server (uvicorn) must be **restarted** after any change inside `server/`.

---

## 4. First-time printer setup (for a non-technical user)

1. Plug the printer in via USB and switch it on.
2. Open the app → **Settings → Printer Setup — One Click → Run Setup**.
3. **Printer not listed?** The wizard shows the official driver download button
   (TVS: tvselectronics.in, DCode: dcodeinternational.in) with 3 simple steps.
   Install it, then press **"I installed it — Refresh"**.
4. Select the printer → **Run Setup** (creates the exact label size in Windows
   automatically — no admin rights needed, verified) → **Test Print**.
5. If the print is slightly shifted, adjust **Calibration** offsets and test again.

After that, daily work is: fill 5 fields → **Print Tag** → collect the label.

---

## 5. Troubleshooting (plain language)

| Symptom | Meaning / Fix |
|---|---|
| Printer not connected | Driver missing, USB unplugged, or power off. Follow the wizard's driver steps. |
| Out of paper | Label roll is empty — load a new roll. |
| Printer cover is open | Close the printer cover fully and retry. |
| Printer is off or unplugged | Switch the printer on and check the USB cable. |
| Right edge is cut off | Tag is wider than the printer's maximum (DCode: 104 mm). Press "Use … instead". |
| Print is slightly shifted | Settings → Calibration: try 0.5–1 mm offsets + Test Print. |
| Print too light / thin text | Windows printer Printing preferences → raise Density/Darkness. All label text prints bold by design. |
| Red "server offline" dot | The server terminal was closed — restart it (3.2 / 3.4). |
| Dropdown hides behind cards | Fixed — menus render in a top layer and flip upward near the screen bottom. |

---

## 6. What is built so far

**Server (Python + FastAPI + PostgreSQL + SQLAlchemy + Alembic):**
- Print API: validate → render SVG → rasterize → spool → save history
- History: search/filter (name, purity, today/yesterday/week/month), view, reprint (always a new row)
- Settings APIs: shop / printer / tag / calibration / app (validated, shop-friendly errors)
- Printer APIs: discovery, live status, test print, one-click setup (auto label size), driver-help links, per-printer max-width limits
- Logo upload API (PNG/JPG/SVG ≤ 2 MB, content-validated, stored in managed folder, embedded base64 at render time; missing logo never crashes)
- Auto-fit layout engine (`app/tag/layout.py`, mirrored in the client): the user enters W×H only, every font is computed to fit and centre its zone — no textLength hacks (print rasters ignore those), so preview and paper agree
- Less Wt input with automatic Net calculation (`net = gross − less`); legacy `net_weight` payloads still accepted
- Rotating log files, no hard-coded secrets, **52 automated tests — all passing**

**Client (React + JavaScript + Vite + Tailwind CSS):**
- PRINT: 5-field form, instant fold-tag preview (Fit + 1:1 true-millimetre modes), PRINT TAG, server Preview
- HISTORY: table, live search/filter, view dialog, one-click reprint
- SETTINGS: printer (one-click setup wizard, live plain-language status, test print), tag dimensions (manual + presets), shop (name + drag-drop logo), calibration, app preferences
- Printer-aware preset suggestions in real time (too-wide presets flagged, one-click fitting size)
- Premium dropdowns (top-layer portal menu, group headers: Installed / Not installed), slim SaaS layout with proper scrolling, Manish Ornaments branding + favicon

**Deliberately not built (out of scope):** barcode/QR fields, inventory, billing,
login/auth, cloud sync, `.exe` packaging (comes after hardware sign-off).

---

## 7. Before production sign-off

- [ ] Run Test Print on the real shop printer and confirm alignment on real label stock
- [ ] Confirm the exact label size with the real media (current label: 100×15 mm total = 65 mm printable body + 35 mm fold-only tail with zero ink)
- [ ] Settle calibration offsets (horizontal/vertical mm) if needed
- [ ] Then: PySide6 desktop shell + PyInstaller `.exe` packaging

---

## 8. Desktop .exe (no installs, no code sharing) — DONE

`server/dist/ManishTagPrinter/` is the shippable app (~640 MB unzipped,
mostly Qt WebEngine; zips much smaller).

**What's inside:** backend API + built UI + SQLite database file
(auto-created next to the exe on first run) + desktop window. Double-click
`ManishTagPrinter.exe` — no Python, PostgreSQL, Node or browser needed.

**How it was verified:** `ManishTagPrinter.exe --smoke-test` boots the frozen
backend and checks `/`, `/api/health`, `/api/printers`, `/api/settings`
(SMOKE PASS, exit 0). Rebuild any time with:

```powershell
cd server
python -m PyInstaller --noconfirm --clean --name ManishTagPrinter --windowed --onedir --add-data "..\client\dist;client\dist" --add-data "alembic.ini;." --add-data "alembic;alembic" --add-data "C:\Users\nitin\AppData\Local\Programs\Python\Python313\Lib\site-packages\reportlab\fonts;reportlab/fonts" --add-binary "C:\Windows\System32\mfc140u.dll;." --hidden-import sqlalchemy.dialects.sqlite.pysqlite --hidden-import sqlalchemy.dialects.postgresql.psycopg2 desktop.py
```

**Dual-database rule (one codebase, two targets):**

| Target | DATABASE_URL | Client |
|---|---|---|
| `.exe` (friend/shop, zero-install) | `sqlite:///./app_data/tagprinter.db` (automatic when frozen) | Bundled inside, opens in app window |
| Deploy: API on Render + client on Vercel | `postgresql+...` (Render env var) | `VITE_API_URL=https://your-api.onrender.com` at client build time + Render `CORS_ORIGINS=https://your-app.vercel.app` |

All 69 tests pass on **both** backends. SQLite note: timestamps come back
timezone-naive (SQLite has no TIMESTAMPTZ) — ordering/search unaffected.

**Known frozen-exe lessons (don't regress):**
- Pass the FastAPI app OBJECT to uvicorn (import strings fail when frozen).
- `log_config=None` on uvicorn (its dictConfig breaks when frozen).
- PyInstaller 6 puts datas under `_internal/` — paths go through `sys._MEIPASS`
  (`CLIENT_DIST_DIR` env override exists for this).
