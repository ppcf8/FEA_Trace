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

**Schema history:** `1.0.0` had a `RepresentationRecord` level between Version and Iteration. `2.0.0` merges it into Iteration. `2.1.0` removes the redundant `design_changes` field from `IterationRecord`. `2.2.0` renames `VersionRecord.intent` → `description`. `2.3.0` (current) adds `promoted_at: str` to `VersionRecord`. All migrations `1.0.0 → 2.3.0` are registered in `app/core/migration.py`; major migrations require user confirmation, minor ones are auto-applied.

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
ProjectCode                       ← right-click → Expand / Collapse (per-project)
 └─ EntityName                    ← right-click → Expand / Collapse / Close Entity
     └─ V01  ● WIP
         └─ I01  IMPLICIT
             └─ Run 01  ● Converged  ★
```

Project codes are the top-level tree nodes (`tag_project`, bold size 12). Entities (labelled by name only, `tag_entity`, bold size 11) appear beneath their project node. Multiple entities sharing the same project code are grouped under one node. Project nodes are created on demand and removed automatically when their last entity is closed.

`⊟` / `⊞` buttons in the NAVIGATOR header collapse/expand the whole tree. Right-click on a project node → per-project Expand / Collapse. Right-click on an entity node → per-entity Expand / Collapse + Close Entity. Right-click on empty space or a child node → global Expand All / Collapse All. The context menu is a `tk.Menu` styled with `tokens()` colours (not `CustomDropdownMenu`, which is widget-anchored only).

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
- **Run input file autocheck**: every time `RunFrame` loads or its state changes, the solver deck, config-required output files, and user-defined extras are checked on disk inside `03_Runs/VxxIxx_Run_##/`. All runs use `_check_production_artifacts()`. `RunFrame._get_warnings(i, run, run_id, is_production)` returns `(warnings, title, is_critical)`; `_show_warnings(..., is_critical)` renders the panel in red (`#FEE2E2`/`#7F1D1D`) for production runs with missing artifacts and amber (`#FEF3C7`/`#5C3A1E`) for non-production warnings.
- **Edit metadata**: each detail frame (Entity, Version, Iteration) has an Edit button placed at the top-right corner of its metadata panel via `place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=8)` (using `place()` rather than `grid()` to reliably reach the panel corner). Clicking opens a pre-filled `CTkToplevel` edit dialog (`app/gui/dialogs/edit_*.py`). `FEAProject` exposes `update_entity_metadata`, `update_version_metadata`, and `update_iteration_metadata` methods. `update_iteration_metadata` regenerates `filename_base` only when `solver_type` changes.
- **Edit production locking**: the Edit button on VersionFrame and IterationFrame is disabled when the parent version status is not WIP. On RunFrame, both the comments Edit button and the Artifacts Edit button are disabled when `run.artifacts.is_production` is `True` **or** when the parent version is not WIP; `lock = is_production or not is_version_wip` is evaluated in `load()` and updated immediately in `_on_production_toggle`. When the version is not WIP the production toggle switch is also replaced by a read-only label.
- **Version audit trail**: `EditVersionDialog` splits `version.notes` into user notes (editable) and system revert entries (lines starting with `[REVERTED`). Revert entries are shown in a separate read-only `CTkTextbox` (`state="disabled"`) and are always appended unchanged after user notes on save — they cannot be tampered with through the UI.
- **RunFrame inline comment editing**: the Comments textbox defaults to `state="disabled"` (read-only). An Edit button at the panel top-right switches to edit mode: textbox becomes active and Edit is replaced by Save + Cancel buttons (swapped via `grid_remove()` / `grid()`). Cancel restores the pre-edit text stored in `_original_comments`. `load()` always resets to view mode.
- **Run subfolder naming**: run subfolders inside `03_Runs/` are named `{version_id}{iter_id}_Run_{run_id:02d}` (e.g. `V01I01_Run_01`). The helper `_run_subfolder(version_id, iter_id, run_id)` in `models.py` centralises this. This prevents collisions when multiple versions or iterations each have a `Run_01`.
- **IterationFrame — Open Models Folder**: the action bar has an **"Open Models Folder"** button that opens `{entity_path}/02_Models/` in the OS file explorer. Shows a status-bar warning if the folder does not exist. `MODELS_FOLDER = "02_Models"` is defined in `app/config.py`.
- **Table sort and filter** (`entity_frame.py`, `version_frame.py`, `iteration_frame.py`): each summary table supports left-click-to-sort (▲/▼ in heading text via `_update_heading`) and right-click-to-filter (⊿ in heading text when active). Filter state lives in `self._col_filters: dict[str, set[str]]`. Module-level `_NO_FILTER_COLS` (frozenset) suppresses the popup for text-heavy columns; `_DATE_COLS` (frozenset) enables date-only display and a ↓/↑ sort toggle inside the popup. `_open_filter_popup` builds candidate rows by applying all other active filters plus the search query first (cascading/dependent filters). A `self._search_var: ctk.StringVar` drives a real-time search bar (label + entry + ✕); `trace_add("write", ...)` triggers `_refresh_table`. Both search and column filters combine as AND. All state is reset in `load()`.
- **Production artifact validation**: `config.REQUIRED_PRODUCTION_ARTIFACTS` maps each solver type to required extensions — the first item is the input deck (matches `SOLVER_EXTENSIONS`), remaining items are output files. `_check_production_artifacts()` always validates every config-required extension inside `03_Runs/VxxIxx_Run_##/`. Users may define extra per-run extensions via `EditArtifactsDialog` (stored in `run.artifacts.output`, checked after config items, deduplicated). The Output Files label on `RunFrame` shows config output extensions plus user extras combined. The Artifacts Edit button follows the same production-locking pattern as the comments Edit button.
- **Run artifacts Edit button**: the Artifacts panel on `RunFrame` has an Edit button at the panel top-right (`place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=8)`, icon + label). Opens `EditArtifactsDialog` — a `CTkToplevel` with a multi-line textbox (one extension per line, case-sensitive, leading dot auto-added). Saves to `run.artifacts.output` via `update_run_comments()`. Disabled when `run.artifacts.is_production` is `True`; re-enabled immediately in `_on_production_toggle`.
- **Missing entity paths on session open**: `SessionManager.peek(path)` is a read-only method that returns `(valid_paths, missing_paths)` without touching session state. `_on_open_session` calls `peek()` first; if any paths are missing it shows `MissingEntitiesDialog` (`app/gui/dialogs/missing_entities_dialog.py`). The dialog supports **Remap Root Folder…** (uses `os.path.commonpath` of parent dirs + `Path.relative_to` to rebase missing paths onto a new root; loops until all resolved or user gives up), **Load Anyway** (proceeds with whatever is found + already remapped), and **Cancel** (aborts entirely). `_on_open_session` then calls `load()` to commit session state and overrides `_entities` via `set_entities(final_paths)` when the resolved list differs — marking the session dirty. The load loop iterates over `final_paths` directly (not `session.entities`) to avoid `remove_entity` side-effects from the close loop.
- **Save-on-close prompt**: `MainWindow` registers `WM_DELETE_WINDOW → _on_closing`. If entities are open and the session is dirty or has no file, a Yes/No/Cancel dialog is shown before closing. Cancel aborts; Yes triggers save/save-as (and aborts close if the save-as dialog is then dismissed).
- **Promote to Production**: clicking "Promote to Production" on `VersionFrame` opens `PromoteToProductionDialog` (`app/gui/dialogs/promote_to_production_dialog.py`) — a `CTkToplevel` listing every run grouped by iteration with checkboxes (pre-checked from existing `is_production` flags). On confirm, `FEAProject.promote_version_to_production(version_id, production_run_ids)` is called: it validates the transition, clears all existing `is_production` flags, marks only the selected `(iter_id, run_id)` pairs, records a `promoted_at` timestamp, calls `_write()`, and returns per-run artifact warnings. `VersionFrame` shows a "Promoted On" metadata row (hidden when `promoted_at` is empty, shown via `grid()`/`grid_remove()`). Reverting to WIP via `update_version_status()` clears `promoted_at` and resets all `run.artifacts.is_production` to `False`. **Promotion guards in `_on_confirm()`:** (1) if any run across all iterations still has `RunStatus.WIP`, the `_error_label` (row 4) is populated with their identifiers and the dialog stays open; (2) if no runs are checked, the same label shows "at least one run must be selected" and the dialog stays open. **Production switch guard:** `RunFrame._on_production_toggle()` blocks toggling ON when `run.status == RunStatus.WIP` — the switch is reverted to `False` and a status-bar message is shown; toggling OFF is unaffected.
- **App version**: `APP_VERSION` in `app/config.py` is decoupled from `SCHEMA_VERSION` and set independently. Current app version: `2.0.0`; schema version: `2.3.0`.
- **Window icon**: `assets/icons/fea_trace.ico`; loaded via `self.iconbitmap((Path(__file__).parent.parent / "assets" / "icons" / "fea_trace.ico").as_posix())` in `MainWindow.__init__`. `.as_posix()` is required — Tcl interprets backslashes as escape characters. `main.py` calls `ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(...)` before window creation so the taskbar also shows the app icon (harmless no-op when compiled to an `.exe`).
- **Assets**: static files (icons, images) live under `app/assets/icons/`. PNG icons are loaded via `CTkImage` with an absolute path anchored to `Path(__file__)` so they resolve correctly regardless of working directory. `Pillow` is a direct dependency (listed in `requirements.txt`) — `from PIL import Image` is used in frames that load icons.
