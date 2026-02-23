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
    └── RepresentationRecord  (IMPLICIT / EXPLICIT / MBD)
        └── IterationRecord  (I01, I02…)
            └── RunRecord  (with ArtifactRecord list)
```

`schema.py` defines all dataclasses, status enums, and valid status transitions. `app/config.py` holds constants (filenames, lock timeout, required production artifacts per solver, sidebar width, timestamp format).

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
│              │    RepresentationFrame             │
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
     └─ R01  IMPLICIT
         └─ I01
             └─ Run 01  ● Converged  ★
```

All content frames are created once at startup, stacked with `.grid(row=0, col=0, sticky="nsew")`, and switched by calling `frame.load(project, ...)` then `.tkraise()`. Sidebar selection routes through `MainWindow._on_sidebar_select` → `show_entity / show_version / show_representation / show_iteration / show_run`.

**File menu** is a custom `CTkFrame` dropdown placed via `.place()` below the toolbar button; dismissed via a `<ButtonRelease-1>` binding on the root window.

**Dialogs** are `CTkToplevel` windows with `grab_set()`. All pre-fill "Created By" using `os.getlogin()` with `try/except OSError` fallback to `os.environ.get("USERNAME", "")`.

**TTK styling note**: `ttk.Style(self).theme_use("clam")` is called in `MainWindow.__init__` before layout build so that custom heading/row colours are honoured on Windows (the default `vista` theme ignores them). All table frames use named styles (e.g. `"Entity.Treeview"`) via `apply_table_style()` from `theme.py`.

### Key Implementation Details

- **File locking**: writes use `version_log.yaml.lock`; stale locks (>30 s) are auto-overridden.
- **Session persistence**: open entity paths saved to `~/Documents/FEA_Trace/session.json`.
- **`StatusDot` canvas widget** (`theme.py`) — used instead of emoji for Windows compatibility.
- **`FEAProject`** (`core/models.py`) owns YAML I/O, CRUD, and transition validation. GUI frames call `FEAProject` methods; they do not touch YAML directly.
- **ID generation**: entity IDs strip vowels and truncate to 12 chars; version/rep/iter/run IDs are auto-incremented zero-padded numbers.
- **Production artifact validation**: `config.REQUIRED_PRODUCTION_ARTIFACTS` maps each solver type to mandatory file extensions that must be present before marking a run as production.
