# Jewellery Tag Printer — AI Agent Specification

## 1. Project Overview

We need to build a **Windows desktop application for jewellery tag printing**.

The application is intentionally simple. Its main purpose is to let a jewellery shop operator enter jewellery details, preview the tag, print it on a **TVS Electronics LP 46 Neo** label printer, and keep a history of what was printed.

This is **not an inventory or billing application**.

The application should feel like a polished, professional real-world shop utility: fast, minimal, reliable, and easy for a non-technical user.

---

## 2. FINAL TECH STACK

The implementation must use the following stack. Treat this section as an **architectural constraint** for the MVP.

### 2.1 Frontend / Desktop UI

**React + TypeScript**

- Use **React** for the complete application UI.
- Use **TypeScript** for all frontend code.
- Use **Vite** as the frontend build tool.
- The UI should be component-based and modular.

### 2.2 Styling / Design System

**Tailwind CSS**

- Use **Tailwind CSS as the primary styling system**.
- Prefer Tailwind utility classes for layout, spacing, typography, colors, borders, states, and responsiveness.
- Keep custom CSS to an absolute minimum.
- Do NOT create large global CSS files.
- Do NOT write repetitive component-specific CSS when the same result can be achieved with Tailwind utilities.
- Use reusable Tailwind-based components for common UI patterns.

### 2.3 UI Components

Use a modern reusable component library built around **Tailwind CSS**.

Preferred approach:

- **shadcn/ui** components where appropriate
- **Radix UI primitives** where shadcn/ui uses them
- **Lucide React** for icons

Use components such as:

- Button
- Input
- Label
- Select
- Dialog
- Dropdown Menu
- Tabs
- Card
- Table
- Tooltip
- Toast / Sonner
- Badge
- Separator
- Scroll Area

Do not build every basic UI component from scratch if an appropriate reusable component already exists.

### 2.4 Frontend State

Use a simple, maintainable state approach.

Preferred:

- React state/hooks for local form/UI state
- React Context only where shared state is genuinely required
- Avoid adding Redux or another heavy state library unless the implementation later proves it necessary

### 2.5 Backend / Application Server

**Python + FastAPI**

Use Python for application/business logic and the backend API layer.

FastAPI should handle:

- Print requests
- History APIs
- Settings APIs
- Printer-related APIs where appropriate
- Validation/business logic that belongs outside the UI

### 2.6 Desktop Shell / Local Hardware Bridge

Because the final application must run on Windows and communicate with a **USB-connected TVS LP 46 Neo**, use a lightweight desktop shell/local bridge around the React frontend.

Preferred:

**PySide6 WebEngine + React**

Architecture:

```text
React + TypeScript + Vite
            ↓
      PySide6 WebEngine
            ↓
       Python runtime
            ↓
       FastAPI / Services
        ↓          ↓
 PostgreSQL     Printer Service
                    ↓
             TVS LP 46 Neo
                    ↓
                   USB
```

The React UI remains the main user interface, while Python/PySide6 provides access to the local Windows environment and printer.

Do not use Electron unless explicitly approved later.

### 2.7 Database

**PostgreSQL**

Use PostgreSQL for:

- Print history
- Shop settings
- Printer settings
- Application settings

Do NOT use MongoDB.

### 2.8 Database Access

**SQLAlchemy**

Use SQLAlchemy ORM for database access.

Do not put raw SQL/database calls directly inside React components.

### 2.9 Database Migrations

**Alembic**

All schema changes must be managed through Alembic migrations.

### 2.10 Tag Rendering / Print Design

**SVG**

Use SVG as the canonical jewellery tag layout format.

The same tag data/layout should drive:

- Live preview
- Front-side rendering
- Back-side rendering
- Print output generation where technically appropriate

Use a shared tag-template model so preview and print do not become two unrelated implementations.

### 2.11 Printer Integration

Target:

**TVS Electronics LP 46 Neo**

Printer-specific logic must live in a dedicated Python printing layer/adapter.

The implementation must first validate the most reliable printing method for the actual LP 46 Neo:

- Windows printer driver path
- Or an officially/documentedly supported raw printer command path

Do not hard-code an unverified printer command language.

### 2.12 Packaging

**PyInstaller**

Package the Python/PySide6 application into a Windows executable.

The final product should be distributable as a normal Windows `.exe`.

### 2.13 Recommended supporting libraries

Use only where justified:

- `pydantic` / FastAPI validation models
- `httpx` if HTTP communication is required internally
- `python-dotenv` or equivalent configuration handling if needed
- `pytest` for tests
- `pytest-qt` for Qt/UI testing where appropriate
- `loguru` or Python's standard `logging` module for application logs

Do not add libraries without a clear project need.

---

## 2.14 Final Stack Summary

| Layer | Technology | Purpose |
|---|---|---|
| UI | **React + TypeScript** | Main application interface |
| Build | **Vite** | Frontend development/build |
| Styling | **Tailwind CSS** | Primary styling system |
| Components | **shadcn/ui + Radix UI** | Reusable UI components |
| Icons | **Lucide React** | UI icons |
| Desktop shell | **PySide6 + Qt WebEngine** | Windows application shell/local environment access |
| Backend/API | **Python + FastAPI** | Business logic and application API |
| Tag design | **SVG** | Exact tag template and rendering |
| Database | **PostgreSQL** | Print history/settings |
| ORM | **SQLAlchemy** | Database access |
| Migrations | **Alembic** | Schema migrations |
| Printer | **TVS LP 46 Neo** | Physical label printing |
| Packaging | **PyInstaller** | Windows `.exe` |

### 2.15 Styling Rules — IMPORTANT

The frontend must follow these rules:

1. **Tailwind CSS is the default styling method.**
2. Prefer Tailwind utility classes over custom CSS.
3. Use shadcn/ui components wherever suitable.
4. Keep custom `.css` files very small and rare.
5. Do not create a giant `App.css`.
6. Do not duplicate styles across components.
7. Extract repeated UI patterns into reusable React components.
8. Keep the design consistent through shared Tailwind tokens/components.
9. Use responsive layouts even though this is primarily a desktop application.
10. The UI should look like a polished production application, not a default Bootstrap/admin template.

### 2.16 Frontend Code Organization

Recommended:

```text
src/
├── components/
│   ├── ui/
│   ├── layout/
│   ├── print/
│   ├── history/
│   └── settings/
├── pages/
├── hooks/
├── services/
├── lib/
├── types/
├── assets/
└── styles/
```

Keep UI components presentational where possible.

API calls should live in `services/` rather than being scattered across UI components.

## 3. Target Printer

Target printer:

**TVS Electronics LP 46 Neo**

Important known specifications:

- Resolution: **203 DPI**
- Print speed: up to **6 IPS / 150 mm/s**
- Label printer
- Monochrome printing
- USB connectivity
- Windows-compatible driver/software

The exact production print mechanism must be validated against the real LP 46 Neo and its installed Windows driver.

Do NOT assume undocumented printer capabilities.

---

## 4. Product Scope

### The app MUST provide

1. Jewellery tag data entry
2. Live tag preview
3. Printing to LP 46 Neo
4. Print copies
5. Print history
6. Search/filter history
7. Reprint previous tags
8. Shop name/logo settings
9. Printer settings
10. Tag size settings
11. Print calibration/alignment
12. PostgreSQL persistence

### The app MUST NOT provide

- Barcode
- QR code
- Stock/inventory management
- Billing
- Invoice generation
- Sales
- Purchase
- Customer management
- Supplier management
- Accounting
- GST
- Warehouse management
- Product stock catalogue
- Unnecessary login/authentication
- Cloud features unless explicitly required later

Keep the MVP focused.

---

# 5. Main Print Screen

The main screen is the most important screen.

Use a clean two-column layout.

### Left side — Input Form

Fields:

#### Purity / HUID
Example:

`18kt HUID`

#### Product Name
Example:

`Ring`

#### Gross Weight
Example:

`2.146`

#### Net Weight
Example:

`2.146`

#### Copies
Example:

`1`

Then a primary action:

`PRINT TAG`

---

# 6. Tag Output

## Front Side

The front tag contains:

- Shop/jewellery logo
- Purity / HUID
- Product Name
- G.Wt.
- N.Wt.

Example:

```text
┌─────────────────────────┐
│          LOGO           │
│                         │
│       18kt HUID         │
│       Ring              │
│                         │
│ G.Wt.       2.146 g     │
│ N.Wt.       2.146 g     │
└─────────────────────────┘
```

## Back Side

The back contains:

- Shop Name

Example:

```text
┌─────────────────────────┐
│                         │
│      XYZ JEWELLERS      │
│                         │
└─────────────────────────┘
```

The exact visual layout should follow the supplied jewellery-tag reference as closely as practical.

Do not add extra information that the product owner did not request.

---

# 7. Live Preview

The preview must update immediately whenever the user changes:

- Purity/HUID
- Product Name
- Gross Weight
- Net Weight

The preview must represent the real physical tag as closely as possible.

Important:

**Preview dimensions are physical dimensions, not arbitrary screen dimensions.**

The template must have configurable:

- Width
- Height
- Orientation
- Margins
- Coordinates
- Font sizes
- Logo size
- Front/back layout

SVG should be the source format for the visual tag template.

---

# 8. Printing

Printing is the highest-risk technical area and must be designed carefully.

The print flow:

```text
User enters data
        ↓
Validation
        ↓
Live preview
        ↓
PRINT TAG
        ↓
Generate print output
        ↓
LP 46 Neo
        ↓
Print result
        ↓
Save history
```

The application must not report success simply because the Print button was clicked.

The print service should return a meaningful success/failure result from the selected printing path.

---

# 9. Printer Architecture

Do not put printer-specific code directly inside PySide6 widgets.

Use an abstraction such as:

```text
PrinterAdapter
    ├── discover_printers()
    ├── get_status()
    ├── print_front(...)
    ├── print_back(...)
    └── print_test(...)
```

Then create an LP 46 Neo-specific adapter.

The UI should call an application-level `PrintService`.

Suggested layering:

```text
PySide6 UI
    ↓
Application Services
    ↓
Print Service
    ↓
Printer Adapter
    ↓
Windows Printer / LP 46 Neo
```

This makes future printer changes easier.

---

# 10. LP 46 Neo Print Method

The implementation agent must first determine the most reliable supported print path.

Possible paths include:

1. Windows printer driver / normal Windows printing
2. Verified raw printer command path if officially supported and tested

Do NOT copy commands from another printer without evidence.

The final implementation should use the path that is actually validated on the LP 46 Neo.

Any unverified hardware behavior must be marked:

**NEEDS HARDWARE VALIDATION**

---

# 11. Front / Back Printing

The logical tag has two sides:

### Front
- Logo
- Purity/HUID
- Product Name
- G.Wt.
- N.Wt.

### Back
- Shop Name

Do NOT assume the LP 46 Neo supports automatic duplex printing.

The actual workflow may be:

- true supported two-sided printing
- separate front/back print passes
- re-feed/reposition workflow
- pre-printed back side

The implementation agent must investigate and test the actual hardware.

Until verified, treat the front/back mechanism as a hardware-dependent design point.

---

# 12. Physical Dimensions and DPI

Printer resolution is **203 DPI**.

For conversion from millimeters to printer dots:

```text
dots = round(mm × 203 / 25.4)
```

Approximate conversion:

```text
203 / 25.4 ≈ 7.992 dots/mm
```

All dimension/coordinate conversion should be centralized in one utility.

Never scatter DPI conversion formulas across the codebase.

---

# 13. Calibration

The application must support print alignment settings:

- Horizontal offset
- Vertical offset
- Scaling only if actually required

Units should preferably be **millimeters**.

Provide:

`TEST PRINT`

Calibration must be stored in PostgreSQL/settings and applied by the printing layer.

Actual calibration must be performed using a real LP 46 Neo and the real label media.

---

# 14. PostgreSQL Database

PostgreSQL is required because print history must remain available.

Use:

- SQLAlchemy ORM
- Alembic migrations

pgAdmin may be used for database administration during development.

### Database is NOT for inventory.

It is primarily for:

- Print history
- Shop settings
- Printer settings
- Application settings

---

# 15. Print History

Every successful print operation should be stored.

Recommended fields:

```text
id
purity_huid
product_name
gross_weight
net_weight
copies
printer_name
template_version
status
error_message
printed_at
```

Use `TIMESTAMPTZ` for `printed_at`.

Use `NUMERIC` for weight values instead of floating point.

A reprint should create a new history row.

Do not overwrite the original record.

---

# 16. History Screen

Create a dedicated `History` screen.

Columns:

- Date & Time
- Product Name
- Purity/HUID
- G.Wt.
- N.Wt.
- Copies
- Printer
- Status
- Actions

Actions:

- View
- Reprint

Search/filter:

- Product name
- Purity/HUID
- Today
- Yesterday
- This week
- This month
- Custom date range

Keep the screen simple and fast.

---

# 17. Reprint

When the user selects Reprint:

1. Load the saved data.
2. Put values into the print form.
3. Show the preview.
4. User confirms printing.
5. Print.
6. Create a NEW history entry if successful.

The old history entry must remain unchanged.

---

# 18. Settings

Create a Settings screen.

## Printer settings

- Selected printer
- Refresh printer list
- Printer status where available
- Test print

## Tag settings

- Tag width
- Tag height
- Orientation

Do not guess the default tag dimensions.

They should be configurable because the exact media size must be confirmed.

## Shop settings

- Shop name
- Shop logo

## Calibration settings

- Horizontal offset
- Vertical offset
- Scaling if validated
- Test print

## Application settings

- Theme
- Default copies

---

# 19. Logo

The shop should be able to select/change its logo.

Preferred formats:

- SVG
- PNG
- JPEG if necessary

The app should manage/copy the selected logo asset so it does not break simply because the user later moves the original file.

If the logo is missing, the application must not crash.

---

# 20. Validation

## Purity/HUID

- Required
- Reasonable maximum length

## Product Name

- Required
- Reasonable maximum length

## Gross Weight

- Required
- Numeric
- Appropriate positive/zero rule

## Net Weight

- Required
- Numeric
- Should normally not exceed Gross Weight

## Copies

- Integer
- Minimum 1
- Reasonable maximum

Validation errors must be understandable to a shop user.

---

# 21. Weight Display

Weights are treated as grams for the current product scope.

Example:

```text
G.Wt.  2.146 g
N.Wt.  2.146 g
```

Do not silently change decimal precision without a documented rule.

The exact precision should be configurable or clearly defined according to the shop's actual requirements before finalizing the database schema.

---

# 22. UI Design

The UI should be:

- Minimal
- Premium
- Professional
- Clean
- Fast
- Easy for non-technical users

Do not create an unnecessarily complex dashboard.

Main navigation:

```text
PRINT
HISTORY
SETTINGS
```

Print screen should make the Print button the obvious primary action.

Use clear labels rather than technical terminology.

---

# 23. Application Responsiveness

The UI must not freeze while:

- Printing
- Waiting for printer responses
- Performing potentially slow database operations
- Processing large logo assets

Use Qt worker/thread patterns appropriately.

Never put blocking printer operations directly on the main UI thread.

---

# 24. Logging

Use application logging.

Log:

- Application errors
- Printer failures
- Database errors
- Important print events
- Unexpected exceptions

Use rotating logs where appropriate.

Do not log database passwords or unnecessary sensitive data.

---

# 25. Error Handling

Handle at minimum:

- Printer not found
- Printer disconnected
- Printer offline
- Driver error
- Print failure
- Database unavailable
- Invalid database configuration
- Missing logo
- Invalid tag dimensions
- Invalid form input
- Corrupt settings

Messages should tell the operator what happened and, where practical, what to check.

---

# 26. Security

This is a local Windows application.

Use proportional security:

- Never hard-code PostgreSQL passwords
- Use configuration/environment settings
- Use SQLAlchemy parameterized queries/ORM
- Validate filesystem paths
- Do not add unnecessary authentication

---

# 27. Project Structure

Recommended structure:

```text
jewellery-tag-printer/
│
├── app/
│   ├── main.py
│   │
│   ├── ui/
│   │   ├── windows/
│   │   ├── views/
│   │   ├── widgets/
│   │   └── dialogs/
│   │
│   ├── domain/
│   │   ├── models/
│   │   ├── validators/
│   │   └── value_objects/
│   │
│   ├── services/
│   │   ├── print_service.py
│   │   ├── history_service.py
│   │   └── settings_service.py
│   │
│   ├── printing/
│   │   ├── printer_adapter.py
│   │   ├── lp46neo_adapter.py
│   │   ├── renderers/
│   │   └── calibration.py
│   │
│   ├── tag/
│   │   ├── renderer.py
│   │   ├── templates/
│   │   └── units.py
│   │
│   ├── database/
│   │   ├── session.py
│   │   ├── models.py
│   │   └── repositories/
│   │
│   ├── config/
│   └── utils/
│
├── assets/
├── migrations/
├── tests/
├── pyproject.toml
└── README.md
```

The exact structure may be improved, but separation of concerns must remain.

---

# 28. Development Order

Build in this order:

## Phase 1 — Hardware validation

Before committing to a production print implementation:

- Install LP 46 Neo driver
- Confirm Windows sees printer
- Identify actual media type
- Measure actual tag dimensions
- Test basic print
- Determine front/back workflow
- Confirm practical calibration

## Phase 2 — Project setup

- Python project
- PySide6
- PostgreSQL
- SQLAlchemy
- Alembic
- Logging
- Configuration

## Phase 3 — UI

- Main window
- Print screen
- History screen
- Settings screen

## Phase 4 — SVG tag engine

- Front SVG
- Back SVG
- Placeholders
- Logo
- Dimensions
- Typography

## Phase 5 — Live preview

Bind form data to the SVG preview.

## Phase 6 — Database

Implement:

- models
- migrations
- repositories
- settings
- history

## Phase 7 — Printing

Implement printer abstraction and LP 46 Neo adapter.

## Phase 8 — Calibration

Implement offsets and test printing.

## Phase 9 — History + Reprint

Implement search/filter and reprint.

## Phase 10 — Testing

Run UI, database, print, and real-hardware tests.

## Phase 11 — Packaging

Build Windows `.exe` using PyInstaller.

---

# 29. MVP Acceptance Criteria

The MVP is complete only when all of these are true:

### UI
- Print screen is polished
- Form works
- Live preview works
- History screen works
- Settings work

### Tag
- Front layout is correct
- Back layout is correct
- Logo renders
- Physical dimensions are correct

### Printing
- LP 46 Neo is selectable
- Test print works
- Real tag prints with correct alignment
- Copies work
- Printer errors are handled

### Database
- Successful print is stored with timestamp
- History can be searched/filtered
- Reprint works
- Reprint creates a new history record

### Deployment
- Application packages successfully as Windows `.exe`
- Application starts correctly on a clean supported Windows machine

---

# 30. What the AI Coding Agent Must NOT Do

The implementation agent must NOT:

- Add barcode features
- Add QR features
- Add inventory
- Add billing
- Add authentication unless explicitly requested
- Add cloud infrastructure unnecessarily
- Replace PostgreSQL with MongoDB
- Replace PySide6 with another UI framework
- Guess printer behavior
- Hard-code tag dimensions without confirmation
- Hard-code printer command syntax without validation
- Put all code in one giant file
- Put SQL directly inside UI widgets
- Put printer commands directly inside UI widgets
- Create unnecessary microservices

---

# 31. Important Hardware Questions

These must be validated before finalizing printing implementation:

1. Exact physical tag width/height?
2. Exact printable area?
3. Exact media type?
4. Is the tag physically printable on both sides?
5. How should the back be printed?
6. Does the selected driver expose the required print options?
7. Is a raw printer-command mode officially supported/appropriate?
8. What Windows print path gives the most reliable alignment?
9. What calibration values are required?
10. What printer/driver version is installed?

When information is unknown, do not guess.

Use:

`NEEDS HARDWARE VALIDATION`

---

# 32. Future Features

Future only; do not implement now:

- Barcode
- QR
- Inventory
- Product catalogue
- Billing
- Reports
- Excel export
- PDF export
- Multi-user
- Multi-shop
- Cloud sync

The architecture may leave clean extension points, but MVP must stay small.

---

# 33. Final Instruction to the AI Coding Agent

You are implementing a **real jewellery-shop Windows utility**, not a demo.

Read this file completely before modifying code.

Follow the requirements literally.

Prioritize:

1. Printing reliability
2. Physical tag accuracy
3. Simple user experience
4. Maintainable code
5. Correct print history
6. Clear error handling

Do not make product decisions that contradict this specification.

When a hardware detail is not confirmed, isolate it behind an abstraction and clearly mark it as:

`NEEDS HARDWARE VALIDATION`

Do not pretend unverified printer behavior is confirmed.

The finished application should be simple enough that a jewellery-shop employee can open it, enter five values, see the tag, press Print, and later find exactly what was printed and when.
