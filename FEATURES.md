# FEA Trace — Feature Log

Tracks implemented features chronologically within each category.
Format: **Feature name** — description. `Files touched.` _(date)_

---

## Session Management

- **Save-on-close prompt** — `WM_DELETE_WINDOW` handler shows Yes/No/Cancel when
  entities are open and the session is dirty or unsaved. Aborting the save-as dialog
  also cancels the close.
  `app/gui/main_window.py`, `app/core/session.py` _(2026-02-23)_

- **SessionManager.is_dirty tracking** — `_dirty` flag set on entity add/remove/set,
  cleared on load/save/save_as. Exposed via `is_dirty` property.
  `app/core/session.py` _(2026-02-23)_

- **Session save / load / save-as** — `.featrace` files (JSON); default dir
  `~/Documents/FEA_Trace/`. File menu: New Session, Open Session, Save Session,
  Save Session As….
  `app/core/session.py`, `app/gui/main_window.py` _(initial)_

---

## Welcome Screen

- **Open Session shortcut** — Third button on WelcomeFrame delegates to
  `MainWindow._on_open_session`; hint text updated.
  `app/gui/frames/welcome_frame.py` _(2026-02-23)_

---

## Navigation & Layout

- **Representation/Iteration merge (schema 2.0.0)** — Flattened hierarchy from
  `Version → Representation → Iteration → Run` to `Version → Iteration → Run`.
  `solver_type` and `analysis_types` absorbed into `IterationRecord`. Auto-migration
  `1.0.0 → 2.0.0` flattens existing YAML files in memory and rewrites them. Filename
  bases on disk are preserved unchanged. New filename format drops the `R##` segment:
  `{project}_{entity_id}_{version_id}{iter_id}_{solver_type}`.
  `schema.py`, `app/core/models.py`, `app/core/migration.py`,
  `app/gui/main_window.py`, `app/gui/sidebar.py`,
  `app/gui/frames/version_frame.py`, `app/gui/frames/iteration_frame.py`,
  `app/gui/frames/run_frame.py`, `app/gui/dialogs/new_iteration_dialog.py`,
  `app/gui/frames/entity_frame.py` _(2026-02-23)_

- **Sidebar expand / collapse** — `⊟` / `⊞` buttons in the NAVIGATOR header collapse
  or expand the entire tree. Right-click anywhere on the sidebar shows a themed context
  menu: on an entity node → **Expand / Collapse** (that entity) + **Close Entity**;
  on empty space or a child node → **Expand All / Collapse All** (global). Menu is
  styled with `tokens()` colours to match the current light/dark theme.
  `app/gui/sidebar.py` _(2026-02-24)_

- **Sidebar navigation tree** — Hierarchical tree: entity → version → iteration → run.
  Right-click on entity node → "Close Entity". Tag-based colour coding for
  WIP / PRODUCTION / DEPRECATED / run statuses.
  `app/gui/sidebar.py` _(initial)_

- **Frame switching** — All content frames created once at startup and stacked via
  `.grid`; switched with `.tkraise()`.
  `app/gui/main_window.py` _(initial)_

- **CTkMenuBar integration** — File and Settings menus via `CTkMenuBar` +
  `CustomDropdownMenu`; Appearance submenu (System / Light / Dark).
  `app/gui/main_window.py` _(initial)_

---

## Data & Persistence

- **Schema migration** — Auto and confirm-migration paths; `MigrationDialog` for
  user-confirmed upgrades; notes written to status bar.
  `app/core/migration.py`, `app/gui/dialogs/migration_dialog.py` _(initial)_

- **File locking** — Writes guarded by `version_log.yaml.lock`; stale locks
  (>30 s) auto-overridden.
  `app/core/models.py`, `app/config.py` _(initial)_

- **Production artifact validation** — Per-solver required extensions
  (`.fem`/`.h3d`, `.rad`/`.h3d`, `.xml`/`.h3d`) must be present before a run
  can be marked PRODUCTION.
  `app/config.py`, `app/core/models.py` _(initial)_

- **YAML persistence** — Full CRUD via `FEAProject` (`app/core/models.py`);
  GUI frames never touch YAML directly.
  `app/core/models.py` _(initial)_

---

## Status State Machines

- **Run status** — WIP → CONVERGED / DIVERGED / PARTIAL / ABORTED; reverting
  terminal states back to WIP requires a reason (`RevertReasonDialog`).
  `schema.py`, `app/core/models.py`, `app/gui/dialogs/revert_reason_dialog.py` _(initial)_

- **Version status** — WIP ↔ PRODUCTION ↔ DEPRECATED (DEPRECATED → PRODUCTION
  blocked).
  `schema.py`, `app/core/models.py` _(initial)_

---

## GUI Frames & Dialogs

- **EntityFrame** — Top-level entity info; lists versions; add version action.
  `app/gui/frames/entity_frame.py` _(initial)_

- **VersionFrame** — Shows version metadata and status transition controls.
  `app/gui/frames/version_frame.py` _(initial)_

- **IterationFrame** — Shows iteration metadata, filename base, run summary table;
  add / open run actions.
  `app/gui/frames/iteration_frame.py` _(initial)_

- **RunFrame** — Displays run metadata, artifact list, status transitions.
  `app/gui/frames/run_frame.py` _(initial)_

- **All creation dialogs** — NewEntityDialog, NewVersionDialog,
  NewIterationDialog, NewRunDialog — all pre-fill "Created By" from
  `os.getlogin()` with OSError fallback.
  `app/gui/dialogs/` _(initial)_

- **Hints for entity attributes** — Hover tooltips (600 ms delay) on all field
  labels in VersionFrame, IterationFrame, and RunFrame. Implemented via a `Tooltip`
  class and `add_hint()` helper in `theme.py`.
  `app/gui/theme.py`, `app/gui/frames/version_frame.py`,
  `app/gui/frames/iteration_frame.py`, `app/gui/frames/run_frame.py` _(2026-02-24)_

- **Version status badge styled as pill** — The top-left status badge on VersionFrame
  now matches the RunFrame style: coloured background pill (`corner_radius=6`,
  `padx=12`, `pady=4`, bold white text). Colours: WIP `#4A90D9`, Production `#2D8A4E`,
  Deprecated `#888888`.
  `app/gui/frames/version_frame.py` _(2026-02-24)_

- **Help menu with About dialog** — Help cascade added to the menubar (alongside
  File and Settings). About option opens a `CTkToplevel` modal showing app version,
  schema version, developer name, and email. `DEVELOPER_NAME` and `DEVELOPER_EMAIL`
  stored in `app/config.py`.
  `app/config.py`, `app/gui/main_window.py` _(2026-02-24)_

- **Run panel clipboard & folder actions** — Solver Deck row gains two PNG icon
  buttons: copy filename to clipboard (`copy.png`) and copy full path to clipboard
  (`copy_with_path.png`). An **Open Folder** button opens the `Run_##` subfolder in
  Windows Explorer; shows a status-bar message if the folder does not exist yet.
  `app/gui/frames/run_frame.py` _(2026-02-23)_

- **Iteration panel copy icon** — Filename Base "Copy" text button replaced with
  `copy.png` icon button for visual consistency with the Run panel.
  `app/gui/frames/iteration_frame.py` _(2026-02-23)_

---

## Infrastructure

- **App icon** — `assets/icons/fea_trace.ico` loaded via `iconbitmap()` with an absolute
  path in `MainWindow.__init__` (title bar); `SetCurrentProcessExplicitAppUserModelID`
  called in `main.py` before window creation so the taskbar also shows the app icon.
  No-op when compiled to `.exe`.
  `main.py`, `app/gui/main_window.py` _(2026-02-23)_

- **assets/icons/ folder** — Static assets (`.ico`, `.png`) consolidated under
  `app/assets/icons/`. All references use `Path(__file__)`-anchored absolute paths
  so they resolve correctly regardless of working directory.
  `app/assets/icons/`, `app/gui/main_window.py`, `app/gui/frames/run_frame.py`,
  `app/gui/frames/iteration_frame.py` _(2026-02-23)_

- **Run subfolder auto-creation** — `FEAProject.add_run()` calls
  `mkdir(parents=True, exist_ok=True)` on `03_Runs/Run_##/` after writing the YAML,
  so every new run immediately has a dedicated folder for solver input/output files.
  `app/core/models.py` _(2026-02-23)_

- **App version decoupled from schema version** — `APP_VERSION` in `app/config.py` set
  independently of `SCHEMA_VERSION`; bumped to `2.0.0`.
  `app/config.py` _(2026-02-23)_

- **TTK clam theme** — `ttk.Style(self).theme_use("clam")` called before layout
  build so custom heading/row colours are honoured on Windows.
  `app/gui/main_window.py` _(initial)_

- **StatusDot widget** — Canvas-based coloured dot used instead of emoji for
  Windows font compatibility.
  `app/gui/theme.py` _(initial)_

- **ID generation** — Entity IDs strip vowels, truncate to 12 chars; version /
  rep / iter / run IDs are zero-padded auto-incremented numbers.
  `app/core/models.py` _(initial)_

---

- **Remove design changes field** — Removed redundant `design_changes` field from `IterationRecord`;
  `description` field is sufficient. Schema bumped `2.0.0 → 2.1.0`; auto-migration strips field
  from existing YAML files. `NewIterationDialog` UI simplified (no Design Changes input box).
  Fixed `IterationFrame` Created By/Created On alignment.
  `schema.py`, `app/core/models.py`, `app/core/migration.py`, `app/gui/dialogs/new_iteration_dialog.py`,
  `app/gui/frames/iteration_frame.py`, `app/gui/frames/version_frame.py` _(2026-02-24)_

---

## WIP

<!-- Add features currently being worked on. Format: **Feature** — description. -->

---

## Not Implemented

<!-- Add planned or desired features not yet started. Format: **Feature** — description. -->
- **Run input file autocheck** — always autocheck input file for a run, no matter the status. In case of production runs which uses the artifacts feature keep the current logic.