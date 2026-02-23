# FEA Trace

A desktop application for tracking Finite Element Analysis (FEA) project metadata. Built with Python and CustomTkinter.

## Overview

FEA Trace organises simulation work into a structured hierarchy:

```
Entity  (a component or assembly)
└── Version  (V01, V02 …)
    └── Representation  (IMPLICIT / EXPLICIT / MBD)
        └── Iteration  (I01, I02 …)
            └── Run  (with artifact list and status)
```

Each entity is persisted as a `version_log.yaml` file in its own folder. Multiple entities can be open simultaneously in a single session (`.featrace` file).

## Features

- **Full hierarchy CRUD** — create and navigate entities, versions, representations, iterations, and runs
- **Status state machines** — WIP / PRODUCTION / DEPRECATED for versions; WIP / CONVERGED / DIVERGED / PARTIAL / ABORTED for runs
- **Production artifact validation** — per-solver required file extensions must be present before promoting a run
- **Session management** — save/load/save-as `.featrace` session files; dirty-state tracking with save-on-close prompt
- **Schema migration** — automatic and user-confirmed migration paths when opening older files
- **File locking** — concurrent write protection via `.lock` files (stale locks auto-cleared after 30 s)
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

## Project Structure

```
fea_trace_app/
├── main.py                  # Entry point
├── fea_trace.ico            # Application icon
├── schema.py                # Data schema — dataclasses, enums, validation
├── app/
│   ├── config.py            # Constants (paths, timeouts, solver artifacts…)
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
| `CTkMenuBar` | Menu bar and dropdown menus |
| `PyYAML` | YAML persistence |
| `packaging` | Schema version comparison |
