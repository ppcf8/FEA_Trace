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

- **Navigator tree sync** — Sidebar tree highlight automatically follows the content
  panel: every `show_entity / show_version / show_iteration / show_run` call sets
  `_current_node` and calls `Sidebar.select_node()`, which programmatically selects
  and scrolls to the matching node without re-triggering the selection callback
  (guarded by `_suppress_select`). `refresh_sidebar` restores the selection after
  rebuilding the subtree.
  `app/gui/sidebar.py`, `app/gui/main_window.py` _(2026-02-24)_

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

- **Run input file autocheck** — The solver deck (`.fem` / `.rad` / `.xml`) is
  always checked on disk when a Run panel is displayed or its state changes, regardless
  of run status. For non-production runs an **"⚠  Input File Not Found"** warning panel
  appears when the file is absent. For production runs the existing
  **"⚠  Production Artifact Warnings"** panel is shown instead (covering both the solver
  deck and the `.h3d` output file). `_check_input_file()` added to `app/core/models.py`;
  `RunFrame` gains `_get_warnings()` helper and a dynamic warning-panel title.
  `app/core/models.py`, `app/gui/frames/run_frame.py` _(2026-02-24)_

- **Run panel clipboard & folder actions** — Solver Deck row gains two PNG icon
  buttons: copy filename to clipboard (`copy.png`) and copy full path to clipboard
  (`copy_with_path.png`). An **Open Folder** button opens the `Run_##` subfolder in
  Windows Explorer; shows a status-bar message if the folder does not exist yet.
  `app/gui/frames/run_frame.py` _(2026-02-23)_

- **Iteration panel copy icon** — Filename Base "Copy" text button replaced with
  `copy.png` icon button for visual consistency with the Run panel.
  `app/gui/frames/iteration_frame.py` _(2026-02-23)_

- **Open Models Folder on IterationFrame** — Action bar button opens
  `{entity_path}/02_Models/` in the OS file explorer. Shows a status-bar warning if
  the folder does not exist. `MODELS_FOLDER = "02_Models"` constant added to
  `app/config.py`.
  `app/gui/frames/iteration_frame.py`, `app/config.py` _(2026-02-25)_

- **Edit metadata dialogs** — Pre-filled `CTkToplevel` edit dialogs for Entity, Version,
  and Iteration records (`EditEntityDialog`, `EditVersionDialog`, `EditIterationDialog`).
  Each dialog mirrors its corresponding creation dialog but pre-fills current values and
  uses a "Save" button. `FEAProject` gains `update_entity_metadata`,
  `update_version_metadata`, and `update_iteration_metadata` methods.
  `EditIterationDialog` disables the Solver Type selector when runs already exist;
  `update_iteration_metadata` regenerates `filename_base` only when solver type changes.
  Edit buttons are placed at the metadata panel top-right corner via
  `place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=8)`.
  `app/core/models.py`, `app/gui/dialogs/edit_entity_dialog.py`,
  `app/gui/dialogs/edit_version_dialog.py`, `app/gui/dialogs/edit_iteration_dialog.py`,
  `app/gui/frames/entity_frame.py`, `app/gui/frames/version_frame.py`,
  `app/gui/frames/iteration_frame.py` _(2026-02-25)_

- **Edit button production locking** — Version and Iteration Edit buttons are disabled
  when the parent version status is not WIP, and re-enabled immediately on revert to WIP.
  Run Edit button is disabled when `run.artifacts.is_production` is `True`; updates
  immediately on Production switch toggle via `_on_production_toggle` (not only on
  tab switch).
  `app/gui/frames/version_frame.py`, `app/gui/frames/iteration_frame.py`,
  `app/gui/frames/run_frame.py` _(2026-02-25)_

- **Version audit trail protection** — `EditVersionDialog` splits `version.notes` into
  user-editable notes and immutable system revert entries (lines prefixed `[REVERTED`).
  Revert entries are shown in a separate read-only `CTkTextbox` (`state="disabled"`) and
  are always appended unchanged after user notes on save — they cannot be tampered with
  through the UI.
  `app/gui/dialogs/edit_version_dialog.py` _(2026-02-25)_

- **Warning sign on navigator tree for missing run files** — Run nodes in the sidebar tree show a
  trailing `⚠` suffix when required files are absent on disk. Non-production runs check the solver
  deck via `_check_input_file`; production runs check both the solver deck and output artifacts via
  `_check_production_artifacts`, mirroring `RunFrame._get_warnings()`.
  `app/gui/sidebar.py` _(2026-02-25)_

- **RunFrame inline comment editing** — Comments textbox is read-only by default
  (`state="disabled"`). An Edit button at the metadata panel top-right enters edit mode:
  the textbox becomes active and Edit swaps for Save + Cancel buttons (toggled via
  `grid_remove()` / `grid()`). Cancel restores `_original_comments`. Toggling the
  Production switch ON immediately cancels any active edit and disables the Edit button.
  `load()` always resets to view mode.
  `app/gui/frames/run_frame.py` _(2026-02-25)_

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

- **Run subfolder naming** — Run subfolders inside `03_Runs/` renamed from `Run_##` to
  `{version_id}{iter_id}_Run_{run_id:02d}` (e.g. `V01I01_Run_01`) to prevent name
  collisions when multiple versions or iterations each have a `Run_01`. The helper
  `_run_subfolder(version_id, iter_id, run_id)` in `models.py` centralises the format.
  `app/core/models.py` _(2026-02-24)_

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

- **Version "Intent" renamed to "Description"** — `VersionRecord.intent` renamed to `description`
  throughout schema, persistence, migration, and all UI labels. Schema bumped `2.1.0 → 2.2.0`;
  auto-migration renames the YAML key on first load. Labels updated in `VersionFrame`,
  `EntityFrame` versions table, `NewVersionDialog`, and `EditVersionDialog`.
  `schema.py`, `app/core/migration.py`, `app/core/models.py`,
  `app/gui/frames/version_frame.py`, `app/gui/frames/entity_frame.py`,
  `app/gui/dialogs/new_version_dialog.py`, `app/gui/dialogs/edit_version_dialog.py` _(2026-02-25)_

- **Entity dialog enhancements** — Project Code field moved to the top position in both
  `NewEntityDialog` and `EditEntityDialog`. Entity ID field in `NewEntityDialog` changed from a
  read-only preview label to an editable `CTkEntry`; still auto-fills from the entity name on each
  keystroke but accepts a manual override (auto-fill stops once the user edits the ID directly).
  `FEAProject.create()` gains an optional `entity_id` parameter.
  `app/gui/dialogs/new_entity_dialog.py`, `app/gui/dialogs/edit_entity_dialog.py`,
  `app/core/models.py`, `app/gui/main_window.py` _(2026-02-25)_

---

## WIP

<!-- Add features currently being worked on. Format: **Feature** — description. -->

---

## Not Implemented

<!-- Sorted easiest → hardest. Format: **Feature** — description. -->

- **Warning on session import** — when a loaded `.featrace` session file references entity paths
  that no longer exist (e.g. shared with another user), the app currently silently stays on the
  welcome screen. Should prompt a warning dialog and optionally let the user pick a new root folder
  to remap all entity paths in the session.

- **Add filters and sort to the tables on Entity tab, Version Tab, and Iteration tab** — clickable
  column headers to sort `ttk.Treeview` tables; optional text-filter widgets above each table.
  No model changes required; purely a GUI addition across `entity_frame.py`, `version_frame.py`,
  and `iteration_frame.py`.

- **Project as navigator tree first level** — restructure the sidebar tree so the project code is
  the root node and entities appear beneath it, rather than the current flat list with the project
  code as a label prefix. Purely a `sidebar.py` UI refactor; no schema or model changes needed.

- **Fix artifacts missing warnings** — output file extensions are not currently checked for
  existence when a run is marked production. The artifact list should also be editable in WIP mode
  via a dedicated dialog (add/edit extensions one per line) following the same Edit-button locking
  pattern used in `RunFrame` comments. Touches `run_frame.py`, `models.py`, and requires a new
  artifact-edit dialog.

- **Promote to Production Enhancement** — when a version is promoted to production: (1) record a
  `promoted_at` timestamp in `VersionRecord` and display it in the UI; (2) show a dialog listing
  all runs (grouped by iteration) and let the user select which are production runs, replacing the
  per-run toggle switch with a read-only status field; (3) revert all associated run production
  flags when the version is reverted to WIP. Requires schema + migration changes, a new selection
  dialog, and updates to `version_frame.py` and `run_frame.py`.

- **Default Options** — add project-code and entity-name dropdowns (with free-text fallback) to
  the entity dialogs, populated from a user-level settings config file. The config should be
  importable from a structured external file and editable directly in the app (Settings menu).
  Entity name list must filter by the selected project code. Introduces a new persistence layer
  (`settings.json` or similar) and a settings editor dialog.