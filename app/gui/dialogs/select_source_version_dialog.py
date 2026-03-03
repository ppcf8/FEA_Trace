"""
dialogs/select_source_version_dialog.py — Tree picker for assembly source versions.

Multi-select: the user can tick one version per entity simultaneously.
Checkboxes are rendered as ☐ / ☑ prefixes in the tree text.
"""
from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog
import customtkinter as ctk
from pathlib import Path

from app.config import SOURCE_FOLDER
from app.core.models import FEAProject
from app.gui.theme import apply_sidebar_style, tokens
from schema import VersionStatus


def _scan_step_files(entity_path: Path, version_id: str) -> list[Path]:
    """Return .step/.stp files for a given version.

    First looks in the per-version subfolder 01_Source/{version_id}/.
    Falls back to the flat 01_Source/ folder (legacy layout).
    """
    versioned = entity_path / SOURCE_FOLDER / version_id
    if versioned.is_dir():
        files = [f for f in versioned.iterdir()
                 if f.is_file() and f.suffix.lower() in {".step", ".stp"}]
        if files:
            return files
    flat = entity_path / SOURCE_FOLDER
    if flat.is_dir():
        return [f for f in flat.iterdir()
                if f.is_file() and f.suffix.lower() in {".step", ".stp"}]
    return []


_CHECK_OFF = "☐"
_CHECK_ON  = "☑"


class SelectSourceVersionDialog(ctk.CTkToplevel):
    """
    Tree picker that lets the user select one version per entity as assembly
    source components (multi-select via checkboxes).

    result: list[(entity_path, entity_name, project_code, version_id,
                  step_files: list[Path])]  — empty list means nothing selected;
            None means the dialog was cancelled.
    """

    def __init__(self, parent, session_projects: list[FEAProject], exclude_path: str):
        super().__init__(parent)
        self.title("Select Source Version")
        self.geometry("560x520")
        self.resizable(True, True)
        self.minsize(420, 380)
        self.grab_set()

        self._exclude_path   = str(Path(exclude_path)) if exclude_path else ""
        self._projects: list[FEAProject] = [
            p for p in session_projects
            if str(p.path) != self._exclude_path
        ]
        self._extra_projects: list[FEAProject] = []

        # node_id → (FEAProject, version_id, step_files, VersionStatus)
        self._version_nodes: dict[str, tuple] = {}
        # entity_path → node_id of the currently checked version (one per entity)
        self._entity_checked: dict[str, str]  = {}
        # Set of currently checked node_ids
        self._checked: set[str]               = set()

        self.result = None  # None = cancelled; list = confirmed (may be empty)

        self._build()
        apply_sidebar_style()
        self._configure_tree_tags()
        self._populate_tree()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── instruction ──────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text=(
                "Select one version per entity to use as an assembly component.\n"
                "All .step files from that version's 01_Source folder will be copied."
            ),
            font=ctk.CTkFont(size=12),
            justify="left", anchor="w", wraplength=520,
        ).grid(row=0, column=0, padx=16, pady=(16, 8), sticky="ew")

        # ── tree ──────────────────────────────────────────────────────────
        tree_outer = ctk.CTkFrame(self, fg_color="transparent")
        tree_outer.grid(row=1, column=0, sticky="nsew", padx=16)
        tree_outer.columnconfigure(0, weight=1)
        tree_outer.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_outer, show="tree", selectmode="browse",
            style="Sidebar.Treeview",
        )
        self._tree.grid(row=0, column=0, sticky="nsew")

        sb = ttk.Scrollbar(tree_outer, orient="vertical", command=self._tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=sb.set)

        # Left-click → checkbox toggle + file preview
        self._tree.bind("<Button-1>", self._on_click, add=True)
        # Right-click → expand / collapse context menu
        self._tree.bind("<Button-3>", self._on_right_click)

        # ── Add Entity button ─────────────────────────────────────────────
        ctk.CTkButton(
            tree_outer, text="Add Entity…", width=120, height=28,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._on_add_entity,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

        # ── file preview ──────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text="Files in selected version:",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=2, column=0, padx=16, pady=(12, 2), sticky="w")

        self._files_box = ctk.CTkTextbox(
            self, height=72, state="disabled",
            font=ctk.CTkFont(family="Courier New", size=11),
        )
        self._files_box.grid(row=3, column=0, padx=16, sticky="ew")

        # ── status ────────────────────────────────────────────────────────
        self._status_label = ctk.CTkLabel(
            self, text="", text_color="#E05555",
            font=ctk.CTkFont(size=11), anchor="w",
        )
        self._status_label.grid(row=4, column=0, padx=16, pady=(4, 0), sticky="w")

        # ── buttons ───────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=16, pady=16, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        self._add_btn = ctk.CTkButton(
            btn_frame, text="Add Selected (0)", width=150,
            state="disabled",
            command=self._on_confirm,
        )
        self._add_btn.pack(side="left")

    def _configure_tree_tags(self) -> None:
        t = tokens()
        self._tree.tag_configure(
            "entity",
            font=("Segoe UI", 11, "bold"),
            foreground=t["fg"],
        )
        self._tree.tag_configure(
            "version_ok",
            font=("Segoe UI", 11),
            foreground=t["fg"],
        )
        self._tree.tag_configure(
            "version_production",
            font=("Segoe UI", 11),
            foreground=t["prod_marker"],   # same gold/green as sidebar ★
        )
        self._tree.tag_configure(
            "version_empty",
            font=("Segoe UI", 11),
            foreground="#888888",
        )
        self._tree.tag_configure(
            "checked",
            font=("Segoe UI", 11),
            foreground="#2D8A4E",           # green when checked
        )

    # ------------------------------------------------------------------
    # Tree population
    # ------------------------------------------------------------------

    def _populate_tree(self) -> None:
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._version_nodes.clear()
        self._entity_checked.clear()
        self._checked.clear()
        self._update_add_button()

        all_projects = self._projects + self._extra_projects
        for proj in all_projects:
            entity = proj.entity
            entity_node = self._tree.insert(
                "", "end",
                text=f"  {entity.project} — {entity.name}",
                open=False,          # collapsed by default
                tags=("entity",),
            )
            for v in entity.versions:
                files      = _scan_step_files(proj.path, v.id)
                n          = len(files)
                is_prod    = v.status == VersionStatus.PRODUCTION
                is_deprecated = v.status == VersionStatus.DEPRECATED
                star       = "  ★" if is_prod else ""
                label      = f"  {_CHECK_OFF}  {v.id}{star}  ({n} file{'s' if n != 1 else ''})"

                if not n or is_deprecated:
                    tag = "version_empty"
                elif is_prod:
                    tag = "version_production"
                else:
                    tag = "version_ok"

                node = self._tree.insert(entity_node, "end", text=label, tags=(tag,))
                self._version_nodes[node] = (proj, v.id, files, v.status)

    # ------------------------------------------------------------------
    # Expand / Collapse helpers
    # ------------------------------------------------------------------

    def _set_subtree_open(self, node: str, state: bool) -> None:
        self._tree.item(node, open=state)
        for child in self._tree.get_children(node):
            self._set_subtree_open(child, state)

    def _expand_all(self) -> None:
        for node in self._tree.get_children(""):
            self._set_subtree_open(node, True)

    def _collapse_all(self) -> None:
        for node in self._tree.get_children(""):
            self._set_subtree_open(node, False)

    # ------------------------------------------------------------------
    # Right-click context menu
    # ------------------------------------------------------------------

    def _on_right_click(self, event: tk.Event) -> None:
        t = tokens()
        menu = tk.Menu(
            self, tearoff=0,
            bg=t["bg_secondary"],
            fg=t["fg"],
            activebackground=t["bg_selected"],
            activeforeground=t["fg_selected"],
            borderwidth=1, relief="flat",
            font=("Segoe UI", 10),
        )

        item = self._tree.identify_row(event.y)
        # Determine whether click landed on an entity (top-level) node
        is_entity = item and item not in self._version_nodes and item in {
            self._tree.parent(n) for n in self._version_nodes
        }

        if is_entity:
            menu.add_command(label="Expand",
                             command=lambda: self._set_subtree_open(item, True))
            menu.add_command(label="Collapse",
                             command=lambda: self._set_subtree_open(item, False))
            menu.add_separator()

        menu.add_command(label="Expand All",   command=self._expand_all)
        menu.add_command(label="Collapse All", command=self._collapse_all)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------
    # Click handling (checkbox toggle)
    # ------------------------------------------------------------------

    def _on_click(self, event: tk.Event) -> None:
        node = self._tree.identify_row(event.y)
        if not node or node not in self._version_nodes:
            return

        proj, version_id, files, vstatus = self._version_nodes[node]
        entity_path = str(proj.path)
        self._status_label.configure(text="")

        if not files:
            self._set_files_preview([])
            self._status_label.configure(
                text="This version has no .step/.stp files — cannot select.")
            return

        # Toggle checked state
        if node in self._checked:
            # Unchecking — clear preview
            self._checked.discard(node)
            self._entity_checked.pop(entity_path, None)
            self._set_node_label(node, False, version_id, files, vstatus)
            self._set_files_preview([])
        else:
            # Checking — uncheck previous version of same entity first
            prev = self._entity_checked.get(entity_path)
            if prev and prev in self._version_nodes:
                self._checked.discard(prev)
                _, p_vid, p_files, p_status = self._version_nodes[prev]
                self._set_node_label(prev, False, p_vid, p_files, p_status)

            self._checked.add(node)
            self._entity_checked[entity_path] = node
            self._set_node_label(node, True, version_id, files, vstatus)
            self._set_files_preview(files)

        self._update_add_button()

    def _set_node_label(self, node: str, checked: bool,
                        version_id: str, files: list[Path],
                        vstatus: VersionStatus) -> None:
        n      = len(files)
        check  = _CHECK_ON if checked else _CHECK_OFF
        is_prod = vstatus == VersionStatus.PRODUCTION
        star   = "  ★" if is_prod else ""
        label  = f"  {check}  {version_id}{star}  ({n} file{'s' if n != 1 else ''})"

        if checked:
            tag = "checked"
        elif not n or vstatus == VersionStatus.DEPRECATED:
            tag = "version_empty"
        elif is_prod:
            tag = "version_production"
        else:
            tag = "version_ok"

        self._tree.item(node, text=label, tags=(tag,))

    def _set_files_preview(self, files: list[Path]) -> None:
        self._files_box.configure(state="normal")
        self._files_box.delete("1.0", "end")
        if files:
            self._files_box.insert("end", "\n".join(f.name for f in files))
        self._files_box.configure(state="disabled")

    def _update_add_button(self) -> None:
        n = len(self._checked)
        self._add_btn.configure(
            text=f"Add Selected ({n})",
            state="normal" if n > 0 else "disabled",
        )

    # ------------------------------------------------------------------
    # Add Entity…
    # ------------------------------------------------------------------

    def _on_add_entity(self) -> None:
        folder = filedialog.askdirectory(parent=self, title="Select Entity Folder")
        if not folder:
            return
        folder_path = Path(folder)
        all_paths = {str(p.path) for p in self._projects + self._extra_projects}
        if str(folder_path) in all_paths:
            self._status_label.configure(text="Entity already in list.")
            return
        try:
            proj, _ = FEAProject.load(folder_path)
        except Exception as exc:
            self._status_label.configure(text=f"Could not load entity: {exc}")
            return
        if str(proj.path) == self._exclude_path:
            self._status_label.configure(text="Cannot use the current entity as a source.")
            return
        self._extra_projects.append(proj)
        self._status_label.configure(text="")
        self._populate_tree()
        apply_sidebar_style()
        self._configure_tree_tags()

    # ------------------------------------------------------------------
    # Confirm
    # ------------------------------------------------------------------

    def _on_confirm(self) -> None:
        selections = []
        for node in self._checked:
            if node not in self._version_nodes:
                continue
            proj, version_id, files, _ = self._version_nodes[node]
            if not files:
                continue
            selections.append((
                str(proj.path), proj.entity.name, proj.entity.project,
                version_id, files,
            ))
        self.result = selections
        self.destroy()
