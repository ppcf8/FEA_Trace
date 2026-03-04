# FEA Trace — User Guide

> **Version 2.0.0** — Schema 2.8.0

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Installation](#2-installation)
3. [Core Concepts](#3-core-concepts)
4. [Quick Start: Exploring the Example Session](#4-quick-start-exploring-the-example-session)
5. [Walkthrough: Starting a New Project](#5-walkthrough-starting-a-new-project)
   - 5.1 [Create an Entity](#51-create-an-entity)
   - 5.2 [Add a Version](#52-add-a-version)
   - 5.3 [Add an Iteration](#53-add-an-iteration)
   - 5.4 [Add Runs and Track Status](#54-add-runs-and-track-status)
   - 5.5 [Promote to Production](#55-promote-to-production)
   - 5.6 [Send Output](#56-send-output)
6. [Session Management](#6-session-management)
7. [Sidebar Navigation](#7-sidebar-navigation)
8. [Tables: Sorting and Filtering](#8-tables-sorting-and-filtering)
9. [Artifact Validation](#9-artifact-validation)
10. [Presets](#10-presets)
11. [Assembly Components and Source Files](#11-assembly-components-and-source-files)
12. [Status Reference](#12-status-reference)
13. [Folder Structure on Disk](#13-folder-structure-on-disk)
14. [Tips](#14-tips)

---

## 1. Introduction

**FEA Trace** is a desktop tool for keeping a structured, searchable record of your Finite Element Analysis work. It gives each simulation a persistent, auditable home — without requiring a shared server, a complex database, or a disciplined naming convention memorised by everyone on the team.

### What problem does it solve?

In a typical FEA workflow it quickly becomes hard to answer questions like:

- *Which run was the one we sent to the stress team in September?*
- *Did we ever run a buckling check on the revised geometry?*
- *Which model version was officially signed off, and what were the key results?*
- *Where is the solver deck for the production run?*

FEA Trace answers all of these by keeping a YAML log file alongside each component's folder. Every version, iteration, run, and result is recorded with its status, timestamps, notes, and references to the actual files on disk.

### What it is not

FEA Trace is a **metadata tracker**, not a file manager or a version-control system. It records what you did and where the files are — it does not move, rename, or commit your solver decks automatically. You keep managing your project folders as you always have; FEA Trace adds a structured log on top.

---

## 2. Installation

FEA Trace ships as a single Windows executable — no Python installation required.

1. Copy `FEA_Trace.exe` to any folder (e.g. `C:\Tools\FEA_Trace\`).
2. Double-click `FEA_Trace.exe` to launch.
3. On first run, a `settings.json` file will be created automatically at `C:\Users\<you>\Documents\FEA_Trace\settings.json`.

> **Note:** Windows may show a SmartScreen warning on first launch because the executable is not signed. Click **"More info"** → **"Run anyway"** to proceed.

### System requirements

- Windows 10 or 11 (64-bit)
- No additional software required

---

## 3. Core Concepts

FEA Trace organises your work into a four-level hierarchy that maps directly to how FEA projects evolve.

```
Entity  ── the component or assembly being analysed
└── Version  ── a distinct model configuration (geometry revision, load update, etc.)
    └── Iteration  ── a specific solver setup within that version (solver type + analysis types)
        └── Run  ── a single solver execution, with status and results notes
```

### Entity

An **Entity** is the component or assembly you are analysing — for example, *Fuselage Frame*, *Wing Rib 7*, or *Landing Gear Strut*. It maps to a folder on disk and contains a single `version_log.yaml` file that records everything else.

Each entity belongs to a **Project Code** (e.g. `AERO`, `INTR`) so related components are grouped together in the navigator.

### Version

A **Version** represents a distinct model configuration — typically a geometry or load revision. When you update the geometry to REV B, add a rib stiffener, or incorporate new aerodynamic loads, that warrants a new version (V02, V03…).

Versions carry a description, notes, and a status: **WIP**, **Production**, or **Deprecated**.

### Iteration

An **Iteration** lives inside a version and defines *what kind of analysis you are running*: which solver (Implicit, Explicit, MBD) and which analysis types (Linear, Buckling, Fatigue, Normal Modes…). If you need both a linear static and a separate bird-strike (explicit transient) check on the same model, those are two different iterations.

Each iteration generates a **filename base** that is used to name your solver deck and output files:
```
{Project}_{EntityID}_{VersionID}{IterID}_{SolverType}
e.g.  AERO_FSLGFRM_V01I01_IMPLICIT
```

### Run

A **Run** is a single solver execution — one submission to the cluster (or local machine). Runs track the date, status, and your notes for that specific execution. Multiple runs exist naturally when you fix a boundary condition, update a load, refine a mesh, or re-run after discovering a modelling error.

Run statuses reflect what the solver returned: **WIP**, **Converged**, **Diverged**, **Partial**, or **Aborted**.

### The log file

Everything is stored in a single `version_log.yaml` file inside the entity's root folder. The app reads and writes this file directly — there is no central database. You can open the same entity on multiple machines as long as the folder is on a shared network drive.

---

## 4. Quick Start: Exploring the Example Session

A ready-made example session is included to let you explore all the main features without creating anything from scratch. The session contains three entities from a fictitious AERO project:

- **Fuselage Frame** (`AERO_FSLGFRM`) — two versions, multiple iterations and runs, V01 in Production
- **Wing Rib 7** (`AERO_WNGRB7`) — V01 in Production (fatigue + bird strike), V02 WIP
- **Interior Structure** (`INTR_STRL`) — a simpler entity to illustrate the INTR project group

### Opening the example session

1. Launch FEA Trace.
2. On the **Welcome** screen, click **Open Session** (or use **File → Open Session**).
3. Navigate to the `examples/` folder inside the FEA Trace installation and open `AERO_Examples.featrace`.
4. A **Missing Entities** dialog will appear — the session was created on a different machine so the stored paths won't match yours. Click **Remap Root Folder…**, select the `examples/` folder, and the app will rebase all three entity paths automatically.
5. Once all three paths are resolved, click **Load Anyway** to proceed.
6. The navigator (left panel) will populate with the three entities.

### Exploring the examples

- **Click any Version node** (e.g. `V01` under Fuselage Frame) to see its metadata, status, audit log, and communications record.
- **Click any Iteration node** to see the solver setup, filename base, and runs table.
- **Click any Run node** to see the run date, status, comments, and artifact check.
- **Right-click** nodes in the navigator for context-menu options (expand/collapse, close entity).
- Try **⊟** and **⊞** buttons in the NAVIGATOR header to collapse or expand the entire tree.

> **Tip:** The examples are read-only in the sense that no files will be modified unless you explicitly save. You can safely explore, sort tables, open popups, and navigate without changing anything.

---

## 5. Walkthrough: Starting a New Project

This section walks through the complete lifecycle of a new analysis: creating the entity, running the analysis, and promoting it to production.

### 5.1 Create an Entity

1. Click **New Entity** on the Welcome screen, or use **File → New Entity**.
2. Fill in the dialog:

   | Field | Example | Notes |
   |-------|---------|-------|
   | Project Code | `AERO` | Groups entities in the navigator. Pick from the dropdown or type a new one. |
   | Entity Name | `Fuselage Frame` | Human-readable name shown in the navigator. |
   | Entity ID | `FSLGFRM` | Short identifier used in filenames (auto-generated from the name, editable). |
   | Owner Team | `Structural Analysis` | Optional. |
   | Created By | *(auto-filled)* | Pre-filled from your Windows login name. |

3. Click **Create**. You will be prompted to browse for the entity's **root folder** — select (or create) the folder where the `version_log.yaml` will live, e.g.:
   ```
   \\server\projects\AERO\FuselageFrame\
   ```
4. The entity opens immediately in the right panel and appears in the navigator.

> **Presets:** If you use the same project codes and component names regularly, you can save them as presets — see [Section 10: Presets](#10-presets).

---

### 5.2 Add a Version

From the **Entity** panel:

1. Click **+ New Version** in the action bar.
2. Fill in:

   | Field | Example |
   |-------|---------|
   | Description | `Preliminary sizing model. 8mm global mesh, simplified BCs at STA 1740. Loads from LM-2025-031.` |
   | Notes | *(optional — any initial context)* |
   | Source Files | *(optional — see [Section 11](#11-assembly-components-and-source-files))* |

3. Click **Create**. The new version `V01` appears in the Versions table and in the navigator.

> **When to create a new version vs. a new iteration:** Create a new version when the model geometry, boundary conditions, or load set changes significantly enough that you want a clean break. Create a new iteration within the same version when you want to run a *different type of analysis* on the same model (e.g. add a buckling check alongside the linear static).

---

### 5.3 Add an Iteration

From the **Version** panel (click `V01` in the navigator):

1. Click **+ New Iteration**.
2. Fill in:

   | Field | Example | Notes |
   |-------|---------|-------|
   | Description | `Baseline linear static + normal modes. Coarse 8mm mesh.` | |
   | Solver Type | `IMPLICIT` | Determines the input deck extension and required output files. |
   | Analysis Types | `LINEAR`, `NORMAL MODES` | Multi-select from the list. |

3. Click **Create**. The iteration `I01` appears in the Iterations table and in the navigator under `V01`.

The app automatically generates the **filename base** for your solver deck:
```
AERO_FSLGFRM_V01I01_IMPLICIT
```
Use this as the base name for your `.fem` file (or `.rad` / `.xml` depending on solver type). This ensures every file for every run is uniquely named.

---

### 5.4 Add Runs and Track Status

From the **Iteration** panel (click `I01`):

1. Click **+ New Run**.
2. Enter the run date and any initial comments. Click **Create**.
3. The run appears in the Runs table as `Run 01 — WIP`.

**While the run is in progress**, keep the status as **WIP** and add notes to the Comments box (click the Edit button at the top-right of the Comments panel).

**After the solver finishes**, update the run status using the status buttons on the Run panel:

| Button | Use when |
|--------|----------|
| **Converged** | Solution converged, results are valid |
| **Diverged** | Solver diverged — no usable results |
| **Partial** | Solver ran but did not reach the end (partial results available) |
| **Aborted** | Job was killed before completion |

> **Reverting to WIP:** If you need to undo a terminal status (e.g. you accidentally marked a run as Converged), click **Revert to WIP**. You will be asked to enter a brief reason, which is saved to the run's audit trail.

**Artifact warnings:** When you open a Run panel, the app checks the run subfolder on disk for the expected input deck and output files. A yellow warning bar appears if any are missing; for production runs this bar turns red. See [Section 9](#9-artifact-validation) for details.

---

### 5.5 Promote to Production

Once analysis is complete and reviewed, you promote the iteration (and optionally the version) to Production. This locks the iteration against further edits and creates an audit trail.

#### Pre-conditions

- All runs in the iteration must have a terminal status (Converged, Diverged, Partial, or Aborted) — no WIP runs allowed.
- At least one run must be selected in the promotion dialog.

#### Steps

1. Navigate to the **Iteration** panel (click `I01` in the navigator).
2. Click **Promote to Production** (green button in the action bar).
3. The dialog shows all runs with checkboxes. Check the runs that represent the production result (typically the final converged run, or multiple runs if your report covers several load cases).
4. Click **Confirm**.
5. A prompt asks whether you also want to promote the parent **Version** to Production. Answer **Yes** if V01 is the version you are signing off; **No** if you expect to add more iterations first.

After promotion:
- The iteration shows `● Production` (green) in the navigator and a "Promoted On" date in the metadata.
- The Edit button and New Run button on the iteration are disabled.
- The production run's Edit and Artifacts Edit buttons are also locked.
- A `[Promoted to Production]` entry appears in the Audit Log table on the iteration panel.

#### Reverting to WIP

If you need to make changes after promotion (e.g. a load correction is discovered):

1. On the **Iteration** panel, click **Revert to WIP**.
2. Enter the reason (e.g. `Load at FS180 corrected per LM-2025-047`).
3. All production flags are cleared. The iteration returns to WIP and edits are re-enabled.
4. The revert reason is recorded as a `[Reverted to WIP]` entry in the Audit Log.

---

### 5.6 Send Output

When you are ready to share results with the stress team, structures group, or a client:

1. Navigate to the **Version** panel (click `V01`).
2. Click **Send Output** in the action bar.
3. In the dialog:
   - **Check the runs** you want to include in the report body.
   - **Edit the Subject** if needed (pre-filled with the version details).
   - Review the auto-generated **body** — a structured plain-text report.
4. Click **Open Draft in Outlook**. This opens a new Outlook compose window and simultaneously copies the body to your clipboard as Courier New-formatted text. Press **Ctrl+V** in the email body to paste it with fixed-width formatting.
5. Add recipients in Outlook and send.
6. Back in FEA Trace, use **Import Sent .eml…** to load the sent email file from your email client.
7. Click **Save Record**. The communication is stored in the YAML, the `.eml` file is copied to `05_Communications/`, and a `[Sent Output]` entry is added to the Version and Iteration audit logs.

The communication record is then visible on the **Entity** panel under **Communications**, with columns for Date, By, Version, Recipients, Subject, and attachment count.

---

## 6. Session Management

A **session** is a saved list of entities you have open simultaneously. Sessions are stored as `.featrace` files in `C:\Users\<you>\Documents\FEA_Trace\` by default.

### Typical workflow

| Action | How |
|--------|-----|
| Open a single entity | **File → Open Entity** or **Welcome → Open Entity** |
| Save the current set of open entities | **File → Save Session** (or **Ctrl+S** equivalent via the menu) |
| Re-open the same set next time | **File → Open Session** or **Welcome → Open Session** |
| Add an entity to the current session | **File → New Entity** or **Open Entity** |
| Remove an entity | Right-click its name in the navigator → **Close Entity** |

### Dirty state

The title bar session label shows an asterisk (`*`) when the session has unsaved changes (an entity was opened or closed since the last save). When you close the application with unsaved session changes, a prompt asks whether to save.

### Missing paths on open

If the `.featrace` file references entity folders that are no longer at the stored path (e.g. after a server folder reorganisation), a dialog lists the missing paths. You have three options:

- **Remap Root Folder…** — point to the new parent directory; the app rebases all missing paths automatically.
- **Load Anyway** — open only the entities that were found.
- **Cancel** — abort without loading.

---

## 7. Sidebar Navigation

The left-hand **Navigator** panel shows a tree of all open entities.

```
AERO                               ← Project node (right-click → Expand / Collapse)
 └─ Fuselage Frame                 ← Entity node  (right-click → Expand / Collapse / Close Entity)
     └─ V01  ● Production
         └─ I01  IMPLICIT  ● Production
             └─ Run 01  ● Converged  ★
             └─ Run 02  ● Converged  ★
         └─ I02  IMPLICIT  ● Deprecated
     └─ V02  ● WIP
         └─ I01  IMPLICIT
```

### Colours and symbols

| Symbol / colour | Meaning |
|-----------------|---------|
| Bold blue text (project node) | Project code — click to do nothing; right-click for expand/collapse |
| ● green | Production status |
| ● grey | Deprecated status |
| ● blue / coloured | WIP or run status (see [Status Reference](#12-status-reference)) |
| ★ | Production run (flagged in the Promote dialog) |
| ⚠ | Run subfolder is missing a required file |

### Tree controls

- **⊟ / ⊞** buttons in the NAVIGATOR header — collapse or expand the entire tree.
- **Right-click a project node** — Expand / Collapse that project.
- **Right-click an entity node** — Expand / Collapse that entity; Close Entity.
- **Right-click a run node** — Delete Run…
- **Right-click empty space** — Expand All / Collapse All (global).

### Selection behaviour

Clicking any node navigates to the corresponding panel on the right. The tree always stays in sync with the right panel — navigating via breadcrumbs or buttons in the content area automatically updates the tree selection.

---

## 8. Tables: Sorting and Filtering

Every summary table (Versions in Entity panel, Iterations in Version panel, Runs in Iteration panel, and Communications in Entity panel) supports sorting and filtering.

### Sorting

- **Left-click a column heading** to sort ascending. Click again to reverse (▲ / ▼ indicator in the heading).

### Filtering

- **Right-click a column heading** to open a filter popup with checkboxes (⊿ indicator in the heading when a filter is active).
- Select the values you want to see and click **Apply**.
- Filters from multiple columns combine as AND.
- The **Date** column offers a ↓ Newest / ↑ Oldest toggle inside the popup.
- The **To** column (Communications) splits comma-separated recipients into individual filter options.

### Search

A **Search:** bar above each table filters all columns simultaneously in real time. Click the **✕** button to clear.

All filters and the search bar reset when you navigate away and come back.

---

## 9. Artifact Validation

Every time you open a Run panel, the app checks whether the expected files exist in the run's subfolder on disk.

### What is checked

| Solver type | Required files (config default) |
|-------------|--------------------------------|
| IMPLICIT | `.fem` (input deck) + `.h3d` (results) |
| EXPLICIT | `.rad` (input deck) + `.h3d` + `.T01` |
| MBD | `.xml` (input deck) + `.h3d` |

You can also add **custom extensions** per run (e.g. `_nl.out`, `.op2`) via the **Edit** button on the Artifacts panel of the Run page.

### Warning panel colours

| Colour | Meaning |
|--------|---------|
| Amber | A non-production run has a missing file (informational) |
| Red | A production run has a missing file (critical — requires attention before sign-off) |

The **Navigator** also shows a ⚠ suffix on affected run nodes so you can spot issues without opening each run.

### Run subfolder path

The expected location for all run files is:
```
{entity_root_folder}\03_Runs\{VersionID}{IterID}_Run_{##}\
e.g.  \03_Runs\V01I01_Run_01\
```
This subfolder is created automatically when you add a new run. Copy your solver deck and output files there.

---

## 10. Presets

If you work on the same set of projects and components repeatedly, presets save you from typing the same project codes, entity names, and entity IDs every time.

### What is saved

- **Project codes** (e.g. `AERO`, `INTR`, `LDG`)
- **Entity names** with their corresponding **Entity IDs** (e.g. `Fuselage Frame` → `FSLGFRM`)

### How to manage presets

Go to **Settings → Manage Presets…**. The dialog has two panels:

- **Left:** Project codes. Use **+ Add**, **Edit**, or **Delete**.
- **Right:** Entity names + IDs for the selected project. Double-click any entry to edit.

You can also **Import from file…** to merge presets from a JSON file shared by a colleague.

### Auto-save from dialogs

When you create or edit an entity with a project code or name that is not yet in presets, a prompt automatically offers to save the new values. This keeps the presets list growing organically without manual management.

### Analysis Types presets

Go to **Settings → Manage Presets… → Analysis Types** (bottom section) to maintain a standard list of analysis type labels for the team. New and Edit Iteration dialogs read from this list.

---

## 11. Assembly Components and Source Files

When a version depends on CAD geometry from another component, you can record that relationship.

### Attaching source files to a version

In **New Version** or **Edit Version**:

- **Browse Files…** — pick one or more `.step` / `.stp` files from your local machine or network. They are copied into `{entity_root}\01_Source\{VersionID}\`.
- **Add Assembly Component…** — opens a tree picker showing all other entities currently open in your session. Select a version from another entity; its `.step` files are copied and the source relationship (entity name, project code, version ID, and file list) is stored in the YAML.

### Viewing source relationships

On the **Version** panel, an **Assembly Components** table (shown when not empty) lists all linked versions with their project, entity, version ID, and file count.

Click **Open Source Folder** in the action bar to open `01_Source/{VersionID}/` in Explorer.

### Why this matters

When you create a new version of Wing Rib 7 that references an updated Fuselage Frame geometry, linking the source ensures the YAML records exactly which version of the frame was used — critical for traceability in certification programmes.

---

## 12. Status Reference

### Version statuses

| Status | Meaning | Allowed transitions |
|--------|---------|---------------------|
| **WIP** | Work in progress | → Production, → Deprecated |
| **Production** | Signed-off model | → WIP (reason required) |
| **Deprecated** | Superseded, not valid | → WIP (reason required) |

> **Note:** Direct `Deprecated → Production` is not allowed. Revert to WIP first.

**Promoting a version to Production** requires at least one iteration within it to already be Production.

### Iteration statuses

| Status | Meaning | Allowed transitions |
|--------|---------|---------------------|
| **WIP** | Analysis in progress | → Production (via Promote dialog), → Deprecated |
| **Production** | Signed-off analysis | → WIP (reason required) |
| **Deprecated** | Superseded or invalid | → WIP (reason required) |

**Edit, New Run, Delete Run**, and run-level edits are all locked when an iteration is Production.

### Run statuses

| Status | Meaning | Allowed transitions |
|--------|---------|---------------------|
| **WIP** | Solver running or not yet submitted | → Converged, Diverged, Partial, Aborted |
| **Converged** | Solution converged | → WIP (reason required) |
| **Diverged** | Solver diverged | → WIP (reason required) |
| **Partial** | Partial results only | → WIP (reason required) |
| **Aborted** | Job killed before completion | → WIP (reason required) |

> A WIP run **cannot** be marked as Production. You must first give it a terminal status.

### Audit trail

Every status transition that requires a reason (all "Revert to WIP" actions) creates a `[Reverted to WIP]` entry in the **Audit Log** table visible on the Version and Iteration panels. Promotions create a `[Promoted to Production]` entry. These entries cannot be edited or deleted through the UI.

---

## 13. Folder Structure on Disk

FEA Trace does not dictate where you keep your entity folders. However, it does create a standard subfolder layout inside each entity root:

```
{entity_root}\
├── version_log.yaml           ← the log file (managed by FEA Trace)
├── 01_Source\
│   └── V01\                   ← CAD source files for V01
│       └── AERO_FSLGFRM_V01_assembly.step
├── 02_Models\                 ← your pre-processing / meshing files
├── 03_Runs\
│   ├── V01I01_Run_01\         ← solver deck + output files for V01, I01, Run 01
│   │   ├── AERO_FSLGFRM_V01I01_IMPLICIT_01.fem
│   │   └── AERO_FSLGFRM_V01I01_IMPLICIT_01.h3d
│   └── V01I01_Run_02\
│       ├── AERO_FSLGFRM_V01I01_IMPLICIT_02.fem
│       └── AERO_FSLGFRM_V01I01_IMPLICIT_02.h3d
├── 04_Results\                ← post-processing outputs, report screenshots, etc.
└── 05_Communications\         ← sent email .eml files (managed by FEA Trace)
    └── AERO_FSLGFRM_V01_sent_output_2025-10-05.eml
```

> **Run subfolders are created automatically** when you add a new run. You do not need to create `03_Runs\V01I01_Run_01\` manually.
>
> **`01_Source` and `05_Communications`** are managed by FEA Trace when you attach source files or save a communication record. All other folders (`02_Models`, `04_Results`) are yours to use as you see fit.

---

## 14. Tips

### Dark mode

Go to **Settings → Appearance** and choose **Dark** or **System** (follows your Windows theme).

### Copy solver deck name / path

On any **Run** panel, the Solver Deck row has two icon buttons:
- **Copy filename** — copies just `AERO_FSLGFRM_V01I01_IMPLICIT_01.fem` (useful for pasting into an HPC submission script).
- **Copy full path** — copies the complete path to the file (useful for referencing in reports).

### Open folder in Explorer

On the **Run** panel, click **Open Folder** to open the run subfolder in Windows Explorer. On the **Iteration** panel, click **Open Models Folder** to open `02_Models\`. On the **Version** panel, click **Open Source Folder** to open `01_Source\{VersionID}\`.

### Inline comment editing

Comments on a Run panel are read-only by default (to prevent accidental edits). Click the **Edit** button at the top-right of the Comments panel to enter edit mode. Use **Save** or **Cancel** when done.

### Working on a network drive

The app uses file locking (`.lock` files) to prevent simultaneous writes when multiple users have the same entity open. Stale locks older than 30 seconds are overridden automatically. For best results, only one person should have an entity open for editing at a time.

### Backup

Because all data is stored in plain `version_log.yaml` files, your normal folder backup or version-control process (network drive snapshots, Git LFS, etc.) also backs up all FEA Trace metadata automatically.

### Exporting to PDF

To share this guide as a PDF, convert it using [Pandoc](https://pandoc.org/):
```bash
pandoc USER_GUIDE.md -o USER_GUIDE.pdf --pdf-engine=xelatex
```
Or open it in **VS Code** with the "Markdown PDF" extension and export directly.

---

*FEA Trace v2.0.0 — developed by Pedro Ferreira (pedro.cferreira@ceiia.com)*
