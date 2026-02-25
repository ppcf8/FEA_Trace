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

---

## WIP

<!-- Add features currently being worked on. Format: **Feature** — description. -->

---

## Not Implemented

<!-- Add planned or desired features not yet started. Format: **Feature** — description. -->

- **Warning on session import** — the session file is stored with entities folder full path and when these file is shared with another user the path will probably change. As of now when the path on the session file is not found the app does nothing and sits at the welcome frame, but it would be better to prompt a warning and maybe allow the user to select the root folder where entities for that session are stored and updated the session file.

- **Project as naviagor tree first level** — the project code in used as suffix for the entity name on the navigator tree at the moment. I think it would be better to have the project as the tree's first level and inside it are all the respective entities. This is purely a UI/UX change, the backend architecture can remain the same.

- **Version Tab Intent to Description** — on the version tab change the "Intent" name to "Description". This could be just a UI/UX chang, but don't you think it is better to change the schema and necessary keywords in the code as well?

- **Promote to Production Enhancement** — when a version is promoted to production a timestamp should be added to the log file and displayed on the UI as well. Also a dialog should be popup with all the available runs, cascading by iteration of course, and the user asked to select which runs as production runs. With this the swicth button on the run tab can be substitued by a production status information field. Lastly, when a version is reverted to WIP the associated runs production status should be reverted as well and allow again edits to the metadata.

- **Entity Dialog Enhancement** — on the entity dialog the Project Code field should be the first. Also the Entity ID field, which is autogenerated, should be also editable in case of special situations.

- **Default Options** — some metadata is universal for a project, namely entity names and project codes, and it would be nice to add them as dropdowns on the entity dialog and also this default data could be imported in the file menu toolbar under the settings menu, from a structured external file or also could be edited directly through the app and saved. I guess this would create the need to have a settings configuration file to store the changes for each user. It is also important to note that the entity names fall inside each Project Code, so when the project code is selected on the dropdown the entity name's list should be filtered accordingly. These fields on the dialog should still have the possibility to input a new project code or entity name and update the defaults lit.

- **Add filters and sort to the tables on Entity tab, Version Tab, and Iteration tab**

- **Warning sign on naviagtor tree for missing run files**

- **Fix artifacts missing warnings** — when output file extensions are added they are not checked for missing files when the run is set as production. Also while in WIP this field should be editable. Maybe change the current text field with the add button to an add button that opens a dialog and allows the user to input the file extensions, one per line only. A similiar dialog would used to make the edits, and the edit button should follow the same style and activation logic as in the run metadata subframe.