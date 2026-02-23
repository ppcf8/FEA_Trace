# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
pip install -r requirements.txt
python main.py
```

No build system or test runner is configured.

## Architecture

FEA Trace is a Python desktop application (CustomTkinter GUI) for tracking Finite Element Analysis project metadata. It follows a strict three-layer separation:

- **`schema.py`** — Authoritative data schema with dataclasses and validation. All data structures live here.
- **`app/core/`** — Business logic: `models.py` (FEAProject persistence), `session.py` (multi-entity sessions), `migration.py` (schema versioning).
- **`app/gui/`** — Presentation: `main_window.py` (root controller), `sidebar.py` (nav tree), `frames/` (one panel per hierarchy level), `dialogs/` (modal forms for data entry), `theme.py` (all visual tokens and the `StatusDot` widget).

### Data Hierarchy

Every entity is stored in a folder as `version_log.yaml`:

```
EntityRecord
└── VersionRecord  (V01, V02…)
    └── IterationRecord  (I01, I02…)  — carries solver_type + analysis_types
        └── RunRecord  (with ArtifactRecord list)
```

`schema.py` defines all dataclasses, status enums, and valid status transitions. `app/config.py` holds constants (filenames, lock timeout, required production artifacts per solver, sidebar width, timestamp format).

**Schema history:** `1.0.0` had a `RepresentationRecord` level between Version and Iteration. `2.0.0` (current) merges it into Iteration. Auto-migration `1.0.0 → 2.0.0` is registered in `app/core/migration.py`.

### Status State Machines

**Version:** WIP ↔ PRODUCTION ↔ DEPRECATED (all transitions valid except DEPRECATED → PRODUCTION directly).

**Run:** WIP → CONVERGED / DIVERGED / PARTIAL / ABORTED; reverting any terminal state back to WIP requires a reason (captured via `RevertReasonDialog`).

### UI Layout

Single-window layout: fixed 240 px sidebar on the left, content panel filling the rest.

```
┌─────────────────────────────────────────────────┐
│  Toolbar (row 0): Title | Session label | ☰ File │
├──────────────┬──────────────────────────────────┤
│   Sidebar    │  Content panel — one frame raised │
│  (col 0)     │  at a time via .tkraise():        │
│              │    WelcomeFrame                   │
│  NAVIGATOR   │    EntityFrame                    │
│  Entity tree │    VersionFrame                   │
│              │    IterationFrame                 │
│              │    RunFrame                       │
├──────────────┴──────────────────────────────────┤
│  Status bar (row 2): message | schema version   │
└─────────────────────────────────────────────────┘
```

**Sidebar tree hierarchy:**
```
ProjectCode · EntityName          ← right-click → "Close Entity"
 └─ V01  ● WIP
     └─ I01  IMPLICIT
         └─ Run 01  ● Converged  ★
```

All content frames are created once at startup, stacked with `.grid(row=0, col=0, sticky="nsew")`, and switched by calling `frame.load(project, ...)` then `.tkraise()`. Sidebar selection routes through `MainWindow._on_sidebar_select` → `show_entity / show_version / show_iteration / show_run`.

**WelcomeFrame** shows three quick-access buttons: **New Entity**, **Open Entity**, **Open Session** (the last delegates to `MainWindow._on_open_session`).

**File menu** uses `CTkMenuBar` + `CustomDropdownMenu` from the `CTkMenuBar` package (see `requirements.txt`). Menus: File (New Entity, Open Entity, New Session, Open Session, Save Session, Save Session As…) and Settings > Appearance (System / Light / Dark).

**Dialogs** are `CTkToplevel` windows with `grab_set()`. All pre-fill "Created By" using `os.getlogin()` with `try/except OSError` fallback to `os.environ.get("USERNAME", "")`.

**TTK styling note**: `ttk.Style(self).theme_use("clam")` is called in `MainWindow.__init__` before layout build so that custom heading/row colours are honoured on Windows (the default `vista` theme ignores them). All table frames use named styles (e.g. `"Entity.Treeview"`) via `apply_table_style()` from `theme.py`.

### Key Implementation Details

- **File locking**: writes use `version_log.yaml.lock`; stale locks (>30 s) are auto-overridden.
- **Session persistence**: sessions saved as `.featrace` files (JSON under the hood); default directory is `~/Documents/FEA_Trace/`. `SessionManager` (`app/core/session.py`) tracks `is_dirty` — set on any entity add/remove/set, cleared on load/save/save_as.
- **`StatusDot` canvas widget** (`theme.py`) — used instead of emoji for Windows compatibility.
- **`FEAProject`** (`core/models.py`) owns YAML I/O, CRUD, and transition validation. GUI frames call `FEAProject` methods; they do not touch YAML directly.
- **ID generation**: entity IDs strip vowels and truncate to 12 chars; version/iter/run IDs are auto-incremented zero-padded numbers.
- **Production artifact validation**: `config.REQUIRED_PRODUCTION_ARTIFACTS` maps each solver type to mandatory file extensions that must be present before marking a run as production.
- **Save-on-close prompt**: `MainWindow` registers `WM_DELETE_WINDOW → _on_closing`. If entities are open and the session is dirty or has no file, a Yes/No/Cancel dialog is shown before closing. Cancel aborts; Yes triggers save/save-as (and aborts close if the save-as dialog is then dismissed).
- **App version**: `APP_VERSION` in `app/config.py` is decoupled from `SCHEMA_VERSION` and set independently. Current app version: `2.0.0`; schema version: `2.0.0`.
- **Window icon**: `fea_trace.ico` placed at project root; loaded via `self.iconbitmap("fea_trace.ico")` in `MainWindow.__init__`. `main.py` calls `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(...)` before window creation so the taskbar also shows the app icon (harmless no-op when compiled to an `.exe`).
