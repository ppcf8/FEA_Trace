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
- **Status state machines** — WIP / PRODUCTION / DEPRECATED for versions; WIP / CONVERGED / DIVERGED / PARTIAL / ABORTED for runs
- **Promote to Production dialog** — promoting a version opens a dialog listing all runs grouped by iteration with checkboxes; selected runs are marked as production, a `promoted_at` timestamp is recorded and shown in the version metadata panel; reverting to WIP clears the timestamp and all run production flags automatically
- **Production artifact validation** — config-defined file extensions (input deck + output files) are always checked in the run subfolder when a run is marked production; extra per-run extensions can be added via a dedicated edit dialog
- **Session management** — save/load/save-as `.featrace` session files; dirty-state tracking with save-on-close prompt
- **Schema migration** — automatic and user-confirmed migration paths when opening older files
- **File locking** — concurrent write protection via `.lock` files (stale locks auto-cleared after 30 s)
- **Run folder auto-creation** — `03_Runs/{version_id}{iter_id}_Run_{run_id:02d}/` subfolder (e.g. `V01I01_Run_01`) created automatically when a new run is added
- **Run panel clipboard** — copy solver deck filename or full path to clipboard; open run folder in Explorer
- **Table sorting and filtering** — left-click column headings to sort (▲/▼); right-click for per-column filter popups with cascading Excel-style behaviour and date-only display for date columns; real-time search bar above each table
- **Project-grouped sidebar** — project codes are top-level tree nodes; entities are grouped beneath their project code and labelled by name only; project nodes are created/removed automatically
- **Sidebar expand / collapse** — `⊟` / `⊞` header buttons collapse or expand the full tree; right-click for a themed context menu (per-project, per-entity, or global)
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
│   │       └── copy_with_path.png       # Copy full path button icon
│   ├── core/
│   │   ├── models.py        # FEAProject — YAML I/O and CRUD
│   │   ├── session.py       # SessionManager — multi-entity session
│   │   └── migration.py     # Schema version migration
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
