# FEA Trace — Feature Log

Tracks implemented features chronologically within each category.
Format: **Feature name** — description. `Files touched.` _(date)_

---

## Session Management

- **Warning on session import (missing entity paths)** — `SessionManager.peek()` reads
  the session file without mutating state and classifies each stored path as valid or
  missing. If any paths are missing, `_on_open_session` shows `MissingEntitiesDialog`
  before committing the load. The dialog lists the unresolvable paths in a read-only
  textbox, shows a common-prefix hint, and offers three actions: **Remap Root Folder…**
  (pick a new parent directory; partially-resolved paths stay listed until all are found
  or the user gives up), **Load Anyway** (opens only the found + already-remapped
  entities), **Cancel** (aborts without touching session state). A successful remap
  marks the session dirty so the user is prompted to save the updated paths on close.
  `app/core/session.py`, `app/gui/main_window.py`,
  `app/gui/dialogs/missing_entities_dialog.py` _(2026-02-26)_

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

- **Project as navigator tree first level** — Project code nodes are now the top-level
  tree items; entity nodes appear beneath them, labelled by entity name only (no
  `ProjectCode ·` prefix). Entities sharing the same project code are grouped under
  one project node. Project nodes are created on demand and removed automatically when
  their last entity is closed. Right-click on a project node shows a per-project
  **Expand / Collapse** menu; right-click on an entity node keeps the existing
  **Expand / Collapse + Close Entity** options. A new `tag_project` style (bold, size 12)
  distinguishes project nodes from entity nodes. Purely a `sidebar.py` refactor — no
  schema or model changes.
  `app/gui/sidebar.py` _(2026-02-25)_

- **Sidebar expand / collapse** — `⊟` / `⊞` buttons in the NAVIGATOR header collapse
  or expand the entire tree. Right-click anywhere on the sidebar shows a themed context
  menu: on a project node → **Expand / Collapse** (that project); on an entity node →
  **Expand / Collapse** (that entity) + **Close Entity**; on empty space or a child
  node → **Expand All / Collapse All** (global). Menu is styled with `tokens()` colours
  to match the current light/dark theme.
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

- **Production artifact validation** — `REQUIRED_PRODUCTION_ARTIFACTS` in `config.py` maps
  each solver type to required file extensions; the first item is the input deck (matches
  `SOLVER_EXTENSIONS`), remaining items are output files. `_check_production_artifacts()`
  always validates every config-required extension inside `03_Runs/{version_id}{iter_id}_Run_{run_id:02d}/`.
  Users may add extra per-run extensions via `EditArtifactsDialog` (stored in
  `run.artifacts.output`); these are checked alongside config defaults (deduplicated).
  The sidebar `⚠` indicator and `RunFrame` warning panel both derive from the same check.
  `app/config.py`, `app/core/models.py`, `app/gui/sidebar.py`,
  `app/gui/frames/run_frame.py`, `app/gui/dialogs/edit_artifacts_dialog.py` _(2026-02-26)_

- **YAML persistence** — Full CRUD via `FEAProject` (`app/core/models.py`);
  GUI frames never touch YAML directly.
  `app/core/models.py` _(initial)_

---

## Status State Machines

- **Iteration production status — promote-to-production at iteration level** —
  `IterationStatus` gains a `PRODUCTION` state. Allowed transitions: `WIP → PRODUCTION`,
  `WIP → DEPRECATED`, `PRODUCTION → WIP` (reason required), `DEPRECATED → WIP` (reason
  required). Promotion is an iteration-level action: `IterationFrame` gains a
  **"Promote to Production"** button (green) that opens a refactored
  `PromoteToProductionDialog` scoped to a single iteration's runs. On confirm,
  `FEAProject.promote_iteration_to_production()` clears all existing `is_production` flags
  in the iteration, marks only the selected run IDs, sets `i.status = PRODUCTION`, records
  `i.promoted_at`, and auto-appends a `[Promoted to Production] on … by … — Runs: …`
  audit note (no user text required). After promotion, if the parent version is still WIP a
  Yes/No dialog offers to mark it as PRODUCTION too (requires at least one PRODUCTION
  iteration — enforced in `update_version_status`). `VersionFrame` keeps a **"Promote to
  Production"** button but blocks the transition unless at least one iteration is PRODUCTION.
  Reverting a PRODUCTION iteration to WIP clears `promoted_at` and all
  `run.artifacts.is_production` flags. `IterationFrame` shows a "Promoted On" metadata row
  and a green `● Production` status badge. Sidebar shows `● Production` suffix in green for
  PRODUCTION iterations. PRODUCTION iteration: Edit disabled, New Run disabled, Delete Run
  disabled, all Run-level edits locked. `promoted_at` moved from `VersionRecord` to
  `IterationRecord`. Note format updated: `[Reverted to WIP] from {status} on {date} by
  {user} — {reason}` and `[Promoted to Production] on {date} by {user} — Runs: …`. Both
  `EditVersionDialog` and `EditIterationDialog` display system audit notes in a read-only
  **"Audit Log"** section. Schema bumped `2.4.0 → 2.5.0`; auto-migration moves `promoted_at`
  from version to iteration and sets `status: "production"` on iterations that have
  production-flagged runs.
  `schema.py`, `app/core/migration.py`, `app/core/models.py`,
  `app/gui/frames/iteration_frame.py`, `app/gui/frames/version_frame.py`,
  `app/gui/frames/run_frame.py`, `app/gui/sidebar.py`,
  `app/gui/dialogs/promote_to_production_dialog.py`,
  `app/gui/dialogs/edit_version_dialog.py`,
  `app/gui/dialogs/edit_iteration_dialog.py` _(2026-03-02)_

- **Iteration deprecated status** — `IterationRecord` gains a `status: IterationStatus`
  field (`WIP` / `DEPRECATED`) and a `notes: list[str]` audit list. Allowed transitions:
  `WIP → DEPRECATED` and `DEPRECATED → WIP`; reverting to WIP requires a mandatory reason
  appended to `iteration.notes` as `[REVERTED to WIP from deprecated by … on …] reason`.
  `IterationFrame` gains a status badge pill in the header and a Change Status panel in the
  metadata section (mirrors `VersionFrame`); the Edit button and New Run button are disabled
  when the iteration is DEPRECATED or the parent version is not WIP. A Notes panel (between
  metadata and Runs table) displays the revert audit trail. The Runs table right-click
  "Delete Run" is also disabled for DEPRECATED iterations. The Versions table in
  `VersionFrame` gains a Status column showing coloured `● deprecated` / plain `WIP` tags.
  Deprecated iterations are excluded from `PromoteToProductionDialog` (both the checklist
  and the WIP-run pre-promotion guard). `RevertReasonDialog` generalised with an optional
  `entity_type` parameter (default `"Version"`). Schema bumped `2.3.0 → 2.4.0`; auto-migration
  adds `status: "WIP"` and `notes: []` to existing iterations.
  `schema.py`, `app/core/migration.py`, `app/core/models.py`,
  `app/gui/frames/iteration_frame.py`, `app/gui/frames/version_frame.py`,
  `app/gui/sidebar.py`, `app/gui/dialogs/promote_to_production_dialog.py`,
  `app/gui/dialogs/revert_reason_dialog.py` _(2026-02-27)_

- **Run WIP revert cascade to Iteration (and Version)** — When a run is reverted to WIP
  and its parent iteration is `PRODUCTION`, a `RevertReasonDialog` prompt for the iteration
  is shown **before** any changes are made. On confirm, the iteration is reverted to WIP
  (clearing `promoted_at` and all `is_production` flags). If the parent version is also
  `PRODUCTION`, a second `RevertReasonDialog` prompt cascades it to WIP too. All reasons
  are collected upfront — cancelling either dialog aborts the entire operation with no state
  changes. `FEAProject` gains `revert_iteration_to_wip(version_id, iter_id, reason)`.
  `app/core/models.py`, `app/gui/frames/run_frame.py` _(2026-03-04)_

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

- **Artifact warnings extended to all runs; production warnings in red** — All runs
  (not just production ones) now check config-required output artifacts and user-defined
  extras in addition to the input deck. `RunFrame._get_warnings()` uses
  `_check_production_artifacts()` for every run; the return value is extended to a
  3-tuple `(warnings, title, is_critical)`. `_show_warnings()` accepts `is_critical`:
  when `True` (production run), the panel is red (`#FEE2E2` / `#7F1D1D` background,
  `#991B1B` / `#FCA5A5` text); non-production warnings remain amber. `.T01` added to
  `REQUIRED_PRODUCTION_ARTIFACTS[EXPLICIT]` in `config.py`.
  `app/config.py`, `app/gui/frames/run_frame.py` _(2026-02-26)_

- **Mousehover hints for copy buttons** — `add_hint()` tooltips (600 ms) added to the
  filename-copy and path-copy icon buttons in `RunFrame`: `"Copy filename"` and
  `"Copy full path"`, matching the style of existing field-label hints.
  `app/gui/frames/run_frame.py` _(2026-03-04)_

- **"Audit Log" → "Log" label; add missing label on VersionFrame** — Renamed every
  `"Audit Log"` section header to `"Log"` in `IterationFrame`, `EditVersionDialog`, and
  `EditIterationDialog`. Added the missing `"Log"` `ctk.CTkLabel` above the audit
  `ttk.Treeview` in `VersionFrame` (previously the table appeared without a visible label).
  `app/gui/frames/version_frame.py`, `app/gui/frames/iteration_frame.py`,
  `app/gui/dialogs/edit_version_dialog.py`, `app/gui/dialogs/edit_iteration_dialog.py` _(2026-03-04)_

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

- **Audit log tables in VersionFrame and IterationFrame** — System audit notes
  (`[Promoted to Production]`, `[Reverted to WIP]`, legacy `[REVERTED`) are displayed as
  a read-only `ttk.Treeview` table instead of raw bullet text. `VersionFrame` shows four
  columns (Event, Date, By, Details); `IterationFrame` adds a fifth Runs column listing
  the promoted run numbers (e.g. `01, 02`) or `—` for Revert rows. The Event column is
  centred; all columns are autofitted to content via `autofit_tree_columns()`. The table
  defaults to 7 visible rows with a vertical scrollbar when the entry count exceeds that.
  Double-clicking any row opens `show_audit_detail_popup` — a resizable `CTkToplevel`
  showing all fields as labels with the Details field in a word-wrapped, fully resizable
  `CTkTextbox`. Shared helpers (`AUDIT_NOTE_PREFIXES`, `parse_audit_note`,
  `parse_audit_note_extended`, `autofit_tree_columns`, `show_audit_detail_popup`)
  centralised in `theme.py`; edit dialogs updated to import from there.
  `app/gui/theme.py`, `app/gui/frames/version_frame.py`,
  `app/gui/frames/iteration_frame.py`, `app/gui/dialogs/edit_version_dialog.py`,
  `app/gui/dialogs/edit_iteration_dialog.py` _(2026-03-02)_

- **Audit log fixed height + always-visible scrollbar** — Audit `ttk.Treeview` in
  `VersionFrame`, `IterationFrame`, `EditVersionDialog`, and `EditIterationDialog` changed
  from `height=7` (dynamic) to `height=5` (fixed). The vertical scrollbar is now always
  shown unconditionally (removed the `> 7 entries` guard). Treeview `sticky` changed from
  `"ew"` to `"nsew"` so it fills the grid cell and eliminates the vertical gap that
  appeared when the always-present `CTkScrollbar` requested more height than the treeview.
  `app/gui/frames/version_frame.py`, `app/gui/frames/iteration_frame.py`,
  `app/gui/dialogs/edit_version_dialog.py`, `app/gui/dialogs/edit_iteration_dialog.py` _(2026-03-04)_

- **Communications table searchbox** — Real-time `"Search:"` bar (label + `CTkEntry` + ✕
  clear button) added above the communications `ttk.Treeview` in `EntityFrame`. Identical
  in style and behaviour to the search bars on the Versions / Iterations / Runs summary
  tables. `_search_comms_var: ctk.StringVar` drives `_refresh_comms()`; combined AND with
  active column filters. State reset on `load()`.
  `app/gui/frames/entity_frame.py` _(2026-03-04)_

- **Mark Deprecated always requires a reason** — `WIP → DEPRECATED` transitions for both
  `VersionFrame` and `IterationFrame` now open `RevertReasonDialog` (with
  `mode="deprecate"`) before executing the status change. The confirmed reason is appended
  as a `[Deprecated] on {date} by {user} — {reason}` system note to `version.notes` /
  `iteration.notes`. `RevertReasonDialog` extended with a `mode` parameter
  (`"revert"` default, `"deprecate"`) that adapts the title, description text, and confirm
  button label. `AUDIT_NOTE_PREFIXES` updated with `"[Deprecated"`; `parse_audit_note` and
  `parse_audit_note_extended` updated to parse the new format into
  `("Deprecated", date, by, reason)` columns.
  `app/gui/frames/version_frame.py`, `app/gui/frames/iteration_frame.py`,
  `app/gui/dialogs/revert_reason_dialog.py`, `app/gui/theme.py`,
  `app/core/models.py` _(2026-03-04)_

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

- **Sort and filter for summary tables** — All three summary tables (Versions in EntityFrame,
  Iterations in VersionFrame, Runs in IterationFrame) support column sorting and per-column
  filtering. Left-click a heading to sort ascending/descending (▲/▼ indicator embedded in heading
  text; state resets on `load()`). Right-click a heading to open a per-column filter popup with
  checkboxes (⊿ indicator when active). Text-heavy columns (`description`, `iterations`, `runs`,
  `comments`) suppress the filter popup via a module-level `_NO_FILTER_COLS` frozenset — sort still
  works on those columns. Date columns (`created_on`, `date`) strip the time component in the popup
  and offer a ↓ Newest / ↑ Oldest toggle to reorder checkboxes. Filters cascade: the popup builds
  its value list from rows that already pass all other active filters and the current search query,
  mirroring Excel AutoFilter behaviour. A real-time "Search:" bar above each table filters across
  all columns simultaneously (✕ clear button included). Active column filters and search all combine
  as AND.
  `app/gui/frames/entity_frame.py`, `app/gui/frames/version_frame.py`,
  `app/gui/frames/iteration_frame.py` _(2026-02-25)_

- **RunFrame inline comment editing** — Comments textbox is read-only by default
  (`state="disabled"`). An Edit button at the metadata panel top-right enters edit mode:
  the textbox becomes active and Edit swaps for Save + Cancel buttons (toggled via
  `grid_remove()` / `grid()`). Cancel restores `_original_comments`. Toggling the
  Production switch ON immediately cancels any active edit and disables the Edit button.
  `load()` always resets to view mode.
  `app/gui/frames/run_frame.py` _(2026-02-25)_

- **Run output artifacts edit dialog** — The Artifacts panel on `RunFrame` gains an Edit
  button at the panel top-right (same `place(relx=1.0 …)` corner pattern, icon + label).
  Clicking opens `EditArtifactsDialog`: a `CTkToplevel` with a multi-line textbox for
  entering extra output extensions beyond config defaults, one per line, leading dot
  auto-added, case preserved. Saved to `run.artifacts.output` via `update_run_comments()`.
  The Output Files label displays config-required output extensions plus user extras
  combined. The Edit button is disabled when the run is marked as production and
  re-enabled immediately on toggle-off via `_on_production_toggle`.
  `app/gui/frames/run_frame.py`, `app/gui/dialogs/edit_artifacts_dialog.py` _(2026-02-26)_

- **Extra outputs — underscore-prefix variants** — `EditArtifactsDialog._on_save()` now
  treats entries starting with `_` as already-formatted suffixes (e.g. `_nl.out` → stored
  as `_nl.out`, matched as `{base}_nl.out`). Previously any entry not starting with `.`
  was blindly prefixed with `.`, turning `_nl.out` into `._nl.out`. Hint text updated to
  show the underscore format as a valid example.
  `app/gui/dialogs/edit_artifacts_dialog.py` _(2026-02-26)_

- **Promote to Production Enhancement** _(superseded by "Iteration production status" in schema 2.5.0)_ —
  Promoting a version to PRODUCTION now opens `PromoteToProductionDialog`: a `CTkToplevel` listing all
  runs grouped by iteration with checkboxes. Previously-flagged production runs are pre-checked. On
  confirm, `FEAProject.promote_version_to_production()` clears all existing `is_production` flags,
  marks only the selected `(iter_id, run_id)` pairs, records a `promoted_at` timestamp in
  `VersionRecord`, and returns per-run artifact warnings. The `VersionFrame` shows a "Promoted On"
  metadata row (hidden when `promoted_at` is empty). On `RunFrame`, the per-run toggle switch is
  replaced by a read-only label when the parent version is not WIP; the Edit and Artifacts Edit buttons
  are also locked. Reverting a version to WIP clears `promoted_at` and resets all `is_production` flags.
  Schema bumped `2.2.0 → 2.3.0`; auto-migration adds `promoted_at: ""` to existing version records.
  `schema.py`, `app/core/migration.py`, `app/core/models.py`,
  `app/gui/dialogs/promote_to_production_dialog.py`,
  `app/gui/frames/version_frame.py`, `app/gui/frames/run_frame.py` _(2026-02-27)_

- **Promote to Production — WIP and empty-selection guards** _(superseded by "Iteration production status" in schema 2.5.0)_ —
  `PromoteToProductionDialog._on_confirm()` now enforces two pre-conditions before allowing promotion:
  (1) every run in the version (regardless of checkbox state) must have a terminal status — if any run
  is still WIP, the existing `_error_label` (row 4, red) is populated with the offending run identifiers
  (e.g. `I01 Run 01`) and the dialog stays open; (2) at least one run checkbox must be checked — an
  empty selection surfaces the same label with a distinct message. The `RunFrame` production switch
  mirrors this rule: `_on_production_toggle()` blocks toggling a WIP run to production, reverts the
  switch to `False`, and shows a status-bar warning; toggling OFF is always permitted.
  `app/gui/dialogs/promote_to_production_dialog.py`, `app/gui/frames/run_frame.py` _(2026-02-26)_

- **Run deletion** — a **Delete Run** button (red, `delete.png` icon) appears in the `RunFrame`
  header; disabled when `run.artifacts.is_production` is `True`. A **"Delete Run…"** entry is also
  available via right-click on a run node in the sidebar and via right-click on a row in the Runs
  table of `IterationFrame` (disabled for production runs). All three surfaces delegate to
  `MainWindow.request_delete_run()`, which shows a Yes/No confirmation dialog. The dialog message
  adapts to the storage location: local drives warn that the folder will be **moved to the Recycle
  Bin**; network / UNC drives warn that it will be **permanently deleted** (no Recycle Bin
  available). Drive type is detected via `_supports_trash()` using `GetDriveTypeW` (UNC paths are
  always treated as network). On confirmation, `FEAProject.delete_run()` removes the record from
  `i.runs` and deletes the run folder: `send2trash` for local drives, `shutil.rmtree` for network
  drives. The view then navigates to the parent `IterationFrame` and the sidebar subtree is rebuilt.
  `send2trash>=1.8.0` added to `requirements.txt`.
  `app/core/models.py`, `app/gui/frames/run_frame.py`, `app/gui/frames/iteration_frame.py`,
  `app/gui/sidebar.py`, `app/gui/main_window.py`, `requirements.txt` _(2026-02-27)_

- **Project-code and entity-name presets** — Users can save frequently-used project codes, entity
  names, and entity IDs as presets backed by `~/Documents/FEA_Trace/settings.json`. The Project
  Code and Entity Name fields in the New/Edit Entity dialogs use `CTkComboBox`: the name list
  filters to the selected project's preset entries (falls back to the union of all names for
  free-typed codes), and selecting a preset name auto-fills the Entity ID field with the stored ID
  (if any). On confirm, if the entered project code or entity name is not already in presets a
  Yes/No prompt offers to save the new values (including entity ID). Presets are managed via
  **Settings → Manage Presets…**, a resizable two-panel `CTkToplevel`: left panel lists project
  codes (add / edit / delete); right panel lists entity names + entity IDs for the selected project
  (add / edit / delete; edit is accessible via button or double-click, opens a single combined
  name + ID dialog). An **Import from file…** action performs an additive merge from an external
  JSON file (handles both the old plain-string list format and the new `{name, id}` dict format).
  Persistence is handled by `SettingsManager` with a module-level lazy singleton
  `get_settings_manager()`; the manager is eagerly loaded on app startup.
  `app/core/settings.py`, `app/gui/dialogs/manage_presets_dialog.py`,
  `app/gui/dialogs/new_entity_dialog.py`, `app/gui/dialogs/edit_entity_dialog.py`,
  `app/gui/main_window.py` _(2026-03-02)_

- **Send output — email with communication log** — a **"Send Output"** button in the VersionFrame
  action bar opens `SendOutputDialog`: a two-section `CTkToplevel` where users select which
  runs to share (WIP runs disabled; iterations with only WIP runs shown with a "No sendable runs"
  notice) and compose the email (Subject pre-filled as
  `"FEA Trace — {project} / {entity_name} {version_id}"`, free-form To field, auto-generated body
  preview that is editable). **"Open Draft in Outlook"** opens the system mail client via a
  `mailto:` URI (`webbrowser.open`). **"Import Sent .eml…"** parses the file with the built-in `email` module and
  auto-fills To/Subject/Date fields. **"Save Record"** (enabled only when ≥ 1 run is selected and
  Subject + To are non-empty) copies the `.eml` file (collision-safe name) to
  `{entity_path}/05_Communications/`, builds a `CommunicationRecord`, appends a
  `[Sent Output] on {date} by {user} — To: {to} — Subject: {subject}` audit note to `version.notes`
  and to each referenced `iteration.notes`, and calls `FEAProject.add_communication()`. The audit
  note appears automatically in the VersionFrame and IterationFrame audit tables. Additional `.eml`
  files can be attached to an existing record via the **"+ Add .eml"** button in the Communication
  Detail popup (double-click a row in any comms table). EntityFrame shows a **Communications**
  panel (row 4, hidden when empty) with a `ttk.Treeview` listing all communications across all
  versions, sorted most-recent-first; columns: Date / By / Version / To / Subject / .eml (shows
  count). Schema bumped `2.5.0 → 2.6.0` (adds `CommunicationRecord` and
  `VersionRecord.communications`); then `2.6.0 → 2.7.0` (renames `eml_filename: str` →
  `eml_filenames: list[str]`); both are minor auto-applied migrations.
  `schema.py`, `app/core/migration.py`, `app/core/models.py`, `app/config.py`,
  `app/gui/theme.py`, `app/gui/frames/version_frame.py`, `app/gui/frames/entity_frame.py`,
  `app/gui/frames/iteration_frame.py`, `app/gui/dialogs/send_output_dialog.py` _(2026-03-03)_

- **Send Output dialog — email body refinement, Courier New clipboard, To field removal** —
  `_build_body()` revised to a structured plain-text report: `=` × 65 borders, header fields
  (`Project`, `Entity`, `Version`, `Description`) colon-aligned with 12-char label padding and
  multi-line continuation indent matching the value start column; an optional
  `--- Step files ---` section (scans `01_Source/{version_id}/` on disk, omitted when empty); and
  `--- Reported Results ---` grouped by iteration showing `[WIP]`/`[PRODUCTION]` status, last-run
  date, iteration description (always present), and selected run numbers only. The body textbox is
  **read-only** (`state="disabled"`) and **auto-regenerates** whenever run checkboxes or the
  Subject field change (`_on_selection_change`). **"Open Draft in Outlook"** no longer embeds the
  body in the `mailto:` URI; instead it places the body on the Windows clipboard as `CF_HTML`
  (a `<pre style="font-family: Courier New">` block) via `ctypes` (no extra dependency), so
  Ctrl+V in Outlook pastes in Courier New in both Classic and New Outlook. A **Copy** button
  (`copy.png`) in the Body header provides the same clipboard action on demand with a 2 s
  "Copied!" transient label. The **To** field is removed from the UI — recipients are added
  directly in Outlook; `_to_var` is kept internally and still populated from `.eml` import.
  **Save Record** no longer requires a To value.
  `app/gui/dialogs/send_output_dialog.py` _(2026-03-03)_

- **Communications table sort and filter** — The Communications `ttk.Treeview` in `EntityFrame`
  now supports the same sort/filter infrastructure as the Versions summary table. Left-click a
  heading to sort ascending / descending (▲ / ▼). Right-click a heading for a per-column filter
  popup (⊿ indicator when active); Subject and .eml columns suppress the filter popup. The Date
  column offers a ↓ Newest / ↑ Oldest toggle. The **To** column is multi-value: comma-separated
  recipients are split so each address appears as an independent filter option
  (`_COMMS_MULTI_VALUE_COLS`). Filters cascade (Excel AutoFilter behaviour). State resets on
  `load()`.
  `app/gui/frames/entity_frame.py` _(2026-03-03)_

- **Version source files and assembly components** — every version can now have `.step` /
  `.stp` CAD source files tracked against it. The **New Version** and **Edit Version** dialogs
  gain a "Source Files" section with two ways to add files: **Browse Files…** opens a standard
  file picker (files are copied into `{entity_path}/01_Source/{version_id}/`); **Add Assembly
  Component…** opens `SelectSourceVersionDialog` — a `Sidebar.Treeview`-styled tree picker that
  lists all other open entities and their versions (collapsed by default; entity nodes expandable
  via click or right-click context menu with Expand / Collapse / Expand All / Collapse All). Each
  version node shows its ID, a ★ for PRODUCTION versions, and the `.step` file count; deprecated
  or empty versions are greyed and unselectable. Multi-select is supported via ☐ / ☑ checkbox
  prefix in the node text (one version per entity; selecting a second version for the same entity
  unchecks the first). An **Add Entity…** button allows browsing to entities not in the current
  session. On confirm, all selected `.step` files are copied and the assembly relationship is
  persisted as a `SourceComponentRecord` (fields: `entity_path`, `entity_name`, `project_code`,
  `version_id`, `copied_files: list[str]`) in the YAML. **VersionFrame** gains an **"Open Source
  Folder"** button in the action bar (creates the folder if absent) and a read-only **"Assembly
  Components"** `ttk.Treeview` table (Project / Entity / Version / Files columns; hidden when
  empty). Schema bumped `2.7.0 → 2.8.0`; auto-migration adds `source_components: []` to all
  existing versions.
  `schema.py`, `app/core/migration.py`, `app/core/models.py`, `app/config.py`,
  `app/gui/main_window.py`, `app/gui/dialogs/new_version_dialog.py`,
  `app/gui/dialogs/edit_version_dialog.py`,
  `app/gui/dialogs/select_source_version_dialog.py`,
  `app/gui/frames/entity_frame.py`, `app/gui/frames/version_frame.py` _(2026-03-03)_

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

- **App version bumped to 2.1.0** — Phase 1 quick fixes: copy-button tooltips, audit
  label renames, and `05_Communications` auto-creation.
  `app/config.py` _(2026-03-04)_

- **Auto-create `05_Communications` folder on entity creation** — Added
  `"05_Communications"` to `REQUIRED_FOLDERS` in `schema.py` so `FEAProject.create()`
  creates the folder alongside `01_Source`, `02_Models`, `03_Runs`, `04_Results`, and
  `90_Scripts` from day one.
  `schema.py` _(2026-03-04)_

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

## Planned Improvements (v2.x)

Phased plan from colleague feedback, ordered easiest → hardest.

---

### Phase 3 — Layout & Resizing

- **Minimum table height (5 rows + headers) for small screens** — All summary `ttk.Treeview` tables
  (Versions in `EntityFrame`, Iterations in `VersionFrame`, Runs in `IterationFrame`) must display at
  least 5 data rows + the header row before any clipping occurs. Preferred approach: **Option B —
  per-table scroll** (each table already has a vertical scrollbar; lock `height=5` as the minimum and
  allow the table to grow with available space via `rowconfigure weight`). Option A (main-frame
  scrollbar on the content panel) is the fallback if per-table sizing proves insufficient on very
  small displays. _Decision required before implementation._
  `app/gui/frames/entity_frame.py`, `app/gui/frames/version_frame.py`,
  `app/gui/frames/iteration_frame.py`

- **Subframes vertical resizing** — Replace the static stacked layout inside content frames with
  `tk.PanedWindow` (orient=`"vertical"`) sashes so the user can drag to resize the metadata panel
  vs. the summary table, matching the resizable panel behaviour already present in
  `ManagePresetsDialog`. Target frames: `EntityFrame` (metadata ↕ versions table ↕ communications),
  `VersionFrame` (metadata ↕ iterations table ↕ audit log), `IterationFrame` (metadata ↕ runs table
  ↕ audit log). Sash positions persist in `AppSettings` per frame.
  `app/gui/frames/entity_frame.py`, `app/gui/frames/version_frame.py`,
  `app/gui/frames/iteration_frame.py`, `app/core/settings.py`

---

## Not Implemented

<!-- Sorted easiest → hardest. Format: **Feature** — description. -->

- **Multiple users — conflict management and UI refresh** — detect when another user has modified
  the same `version_log.yaml` while the current user has it open, surface a notification (user name
  + change summary), and offer a merge or reload path. The existing `_LockManager` only guards
  writes; there is no polling, file-watching, or change-detection mechanism. _Design decisions to
  investigate: polling interval vs. `watchdog` library; diff/merge strategy for simultaneous edits;
  notification widget design (toast? status bar?); how to refresh a frame mid-session without
  discarding in-progress user edits; conflict resolution policy (last-write-wins vs. manual merge)._
  `app/core/models.py`, `app/gui/main_window.py`, `app/gui/sidebar.py`, all content frames