# FEA Trace

A desktop application for tracking Finite Element Analysis (FEA) project metadata. Built with Python and CustomTkinter.

## Overview

FEA Trace organises simulation work into a structured hierarchy:

```
Entity  (a component or assembly)
└── Version  (V01, V02 …)
    └── Iteration  (I01, I02 …  — carries solver type and analysis types)
        └── Run  (with artifact list and status)
```

Each entity is persisted as a `version_log.yaml` file in its own folder. Multiple entities can be open simultaneously in a single session (`.featrace` file).

## Features

- **Full hierarchy CRUD** — create and navigate entities, versions, iterations, and runs
- **Status state machines** — WIP / PRODUCTION / DEPRECATED for versions and iterations; WIP / CONVERGED / DIVERGED / PARTIAL / ABORTED for runs; each iteration can be promoted to PRODUCTION independently
- **Promote to Production dialog** — promotion is an iteration-level action; clicking "Promote to Production" on an iteration opens a dialog listing that iteration's runs with checkboxes; on confirm the iteration is marked PRODUCTION with a `promoted_at` timestamp and an auto-generated audit note; a follow-up prompt offers to also mark the parent version as PRODUCTION (requires at least one PRODUCTION iteration); reverting to WIP clears the timestamp and all run production flags; promotion is blocked when any run in the iteration is still in WIP status or no runs are selected
- **Artifact validation for all runs** — config-defined file extensions (input deck + output files) are checked in the run subfolder for every run; the warning panel turns red when a production run has missing artifacts, amber for non-production; extra per-run extensions can be added via a dedicated edit dialog
- **Session management** — save/load/save-as `.featrace` session files; dirty-state tracking with save-on-close prompt; missing-path warning on open with an optional root-folder remap dialog
- **Schema migration** — automatic and user-confirmed migration paths when opening older files
- **File locking** — concurrent write protection via `.lock` files (stale locks auto-cleared after 30 s)
- **Run deletion** — delete a run via the **Delete Run** button on the Run panel, right-click on a run node in the sidebar, or right-click a row in the Runs table on the Iteration panel; a confirmation dialog warns whether the run folder will be moved to the Recycle Bin (local drives) or permanently deleted (network drives); deletion is blocked for production-marked runs
- **Run folder auto-creation** — `03_Runs/{version_id}{iter_id}_Run_{run_id:02d}/` subfolder (e.g. `V01I01_Run_01`) created automatically when a new run is added
- **Run panel clipboard** — copy solver deck filename or full path to clipboard; open run folder in Explorer
- **Table sorting and filtering** — left-click column headings to sort (▲/▼); right-click for per-column filter popups with cascading Excel-style behaviour and date-only display for date columns; real-time search bar above each table
- **Project-grouped sidebar** — project codes are top-level tree nodes; entities are grouped beneath their project code and labelled by name only; project nodes are created/removed automatically
- **Sidebar expand / collapse** — `⊟` / `⊞` header buttons collapse or expand the full tree; right-click for a themed context menu (per-project, per-entity, or global)
- **Project-code and entity-name presets** — save frequently-used project codes, entity names, and entity IDs as presets; New/Edit Entity dialogs show dropdown lists that filter by project code and auto-fill the entity ID; a Yes/No prompt on confirm offers to save new values; **Settings → Manage Presets…** provides a two-panel CRUD editor with add, edit (combined name + ID dialog), delete, and JSON import; persisted to `~/Documents/FEA_Trace/settings.json`
- **Send output with communication log** — a **"Send Output"** button on the Version panel opens a compose dialog: select which runs to share (WIP runs excluded), edit subject / recipients / body, open a draft in the system mail client via `mailto:`, or import a sent `.eml` file; saving the record stores a `CommunicationRecord` in the YAML, copies the `.eml` to `05_Communications/`, appends a `[Sent Output]` audit note to the version and each referenced iteration, and updates the EntityFrame's Communications panel (sorted most-recent-first); additional `.eml` files can be attached later via the Communication Detail popup
- **Version source files and assembly tracking** — attach `.step` / `.stp` CAD files directly to a
  version (copied into `01_Source/{version_id}/`) or link versions from other open entities as
  assembly components; relationships persisted in the YAML and displayed in a read-only Assembly
  Components table on the Version panel; "Open Source Folder" button opens the folder in Explorer
- **Appearance** — System / Light / Dark theme switching via Settings menu

## Requirements

- Python 3.10+
- Windows (developed and tested on Windows 11)

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
python main.py
```

## Building/Compilation

FEA Trace can be compiled into a standalone Windows executable using PyInstaller.

### Using the Spec File (Recommended)

```bash
pyinstaller fea_trace.spec
```

### Using Command-Line Flags

```bash
pyinstaller --onefile --windowed --icon=app/assets/icons/fea_trace.ico --hidden-import=PIL --hidden-import=CustomTkinter --hidden-import=yaml --add-data "app/assets;app/assets" main.py
```

The compiled executable will be located in the `dist/` folder as `FEA_Trace.exe`.

### Prerequisites

- PyInstaller: `pip install pyinstaller`
- All dependencies from `requirements.txt` must be installed

## Project Structure

```
fea_trace_app/
├── main.py                  # Entry point
├── schema.py                # Data schema — dataclasses, enums, validation
├── app/
│   ├── config.py            # Constants (paths, timeouts, solver artifacts…)
│   ├── assets/
│   │   └── icons/
│   │       ├── fea_trace.ico            # Application icon
│   │       ├── copy.png                 # Copy filename / base button icon
│   │       ├── copy_with_path.png       # Copy full path button icon
│   │       └── delete.png               # Delete Run button icon
│   ├── core/
│   │   ├── models.py        # FEAProject — YAML I/O and CRUD
│   │   ├── session.py       # SessionManager — multi-entity session
│   │   ├── migration.py     # Schema version migration
│   │   └── settings.py      # SettingsManager — user presets persistence
│   └── gui/
│       ├── main_window.py   # Root controller
│       ├── sidebar.py       # Navigation tree
│       ├── theme.py         # Visual tokens, StatusDot widget
│       ├── frames/          # One content panel per hierarchy level
│       └── dialogs/         # Modal forms for data entry
└── requirements.txt
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `customtkinter` | Modern Tkinter UI framework |
| `Pillow` | Image loading for PNG icon buttons (`CTkImage`) |
| `CTkMenuBar` | Menu bar and dropdown menus |
| `PyYAML` | YAML persistence |
| `packaging` | Schema version comparison |
| `send2trash` | Move deleted run folders to the OS Recycle Bin |
