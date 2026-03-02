"""
sidebar.py — Navigation Tree
==============================
Renders the collapsible hierarchy supporting multiple entities:

  EV24
   └─ Front Crossmember
       └─ V01  ● WIP
           └─ I01  IMPLICIT
               └─ Run 01  ● Converged

  EV24
   └─ Rear Crossmember
       └─ V01  ● WIP
           ...

Project codes are the top-level tree nodes; entities appear beneath them.
Multiple entities sharing the same project code are grouped under one node.

Status indicators use coloured ● text + ttk tag foreground colouring
instead of emoji, which render as hatch fills on Windows.
"""

from __future__ import annotations

import tkinter.ttk as ttk
import customtkinter as ctk
from typing import Callable, Optional

from app.core.models import FEAProject, _check_input_file, _check_production_artifacts
from app.gui.theme import (
    apply_sidebar_style, make_scrollbar,
    STATUS_COLORS, tokens,
)


# ---------------------------------------------------------------------------
# Status label text
# ---------------------------------------------------------------------------

_VERSION_STATUS_TEXT = {
    "WIP":        "● WIP",
    "production": "● Production",
    "deprecated": "● Deprecated",
}

_RUN_STATUS_TEXT = {
    "WIP":       "● WIP",
    "converged": "● Converged",
    "diverged":  "● Diverged",
    "partial":   "● Partial",
    "aborted":   "● Aborted",
}

_STATUS_TAG = {
    "WIP":        "tag_wip",
    "production": "tag_production",
    "deprecated": "tag_deprecated",
    "converged":  "tag_converged",
    "diverged":   "tag_diverged",
    "partial":    "tag_partial",
    "aborted":    "tag_aborted",
}

_ITER_STATUS_TAG = {
    "production": "tag_production",
    "deprecated": "tag_deprecated",
}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

class Sidebar(ctk.CTkFrame):
    """
    Left-panel navigation tree supporting multiple entities.

    Parameters
    ----------
    master          : parent widget
    on_select       : callback(node_type, *ids, entity_path)
    on_close        : callback(entity_path) — called when user closes an entity
    on_delete_run   : callback(entity_path, version_id, iter_id, run_id)
    width           : fixed pixel width
    """

    _SIDEBAR_WIDTH = 240

    def __init__(
        self,
        master,
        on_select:      Callable[..., None],
        on_close:       Callable[[str], None],
        on_delete_run:  Callable[[str, str, str, int], None],
        width: int = _SIDEBAR_WIDTH,
    ):
        super().__init__(master, width=width, corner_radius=0,
                         fg_color=["#F0F0F0", "#2B2B2B"])
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._on_select     = on_select
        self._on_close      = on_close
        self._on_delete_run = on_delete_run

        # node_id → (node_type, ...)
        self._node_map:     dict[str, tuple] = {}
        # entity_path → entity node id in the tree
        self._entity_nodes: dict[str, str]   = {}
        # project_code → project node id in the tree
        self._project_nodes: dict[str, str]  = {}
        # entity_path → project_code (for cleanup when removing/refreshing)
        self._entity_project: dict[str, str] = {}

        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, padx=(12, 4), pady=(12, 4), sticky="ew")
        hdr.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="NAVIGATOR",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr, text="⊟", width=24, height=24,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=["#1A1A1A", "#DCE4EE"],
            hover_color=("gray75", "gray30"),
            command=self._collapse_all,
        ).grid(row=0, column=1, padx=(0, 2))

        ctk.CTkButton(
            hdr, text="⊞", width=24, height=24,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            text_color=["#1A1A1A", "#DCE4EE"],
            hover_color=("gray75", "gray30"),
            command=self._expand_all,
        ).grid(row=0, column=2)

        tree_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_frame,
            show="tree",
            selectmode="browse",
            style="Sidebar.Treeview",
        )
        self._tree.grid(row=0, column=0, sticky="nsew")

        sb = make_scrollbar(tree_frame, "vertical", self._tree.yview)
        sb.grid(row=0, column=1, sticky="ns")
        self._tree.configure(yscrollcommand=sb.set)

        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self._tree.bind("<Button-3>",         self._on_right_click)

        self._suppress_select: bool = False

        apply_sidebar_style()
        self._configure_tags()
        ctk.AppearanceModeTracker.add(self._on_appearance_change)

    # ------------------------------------------------------------------
    # Tag configuration
    # ------------------------------------------------------------------

    def _configure_tags(self) -> None:
        for status, tag in _STATUS_TAG.items():
            color = STATUS_COLORS.get(status, "#888888")
            self._tree.tag_configure(tag, foreground=color)
        t = tokens()
        self._tree.tag_configure("tag_prod_marker", foreground=t["prod_marker"])
        # Project root nodes — bold, slightly larger
        self._tree.tag_configure(
            "tag_project",
            font=("Segoe UI", 12, "bold"),
            foreground=t["fg"],
        )
        # Entity nodes — slightly bolder than default
        self._tree.tag_configure(
            "tag_entity",
            font=("Segoe UI", 11, "bold"),
            foreground=t["fg"],
        )

    # ------------------------------------------------------------------
    # Populate — add or refresh a single entity
    # ------------------------------------------------------------------

    def _get_or_create_project_node(self, project_code: str) -> str:
        """Return the existing project node id for *project_code*, or create one."""
        if project_code in self._project_nodes:
            return self._project_nodes[project_code]

        # Insert sorted alphabetically among project nodes
        new_label = project_code.casefold()
        siblings = self._tree.get_children("")
        insert_index = len(siblings)
        for idx, node in enumerate(siblings):
            sibling_label = self._tree.item(node, "text").strip().casefold()
            if new_label < sibling_label:
                insert_index = idx
                break

        project_node = self._tree.insert(
            "", insert_index,
            text=f"  {project_code}",
            open=True,
            tags=("tag_project",),
        )
        self._project_nodes[project_code] = project_node
        self._node_map[project_node] = ("project", project_code)
        return project_node

    def _cleanup_project_node_if_empty(self, project_code: str) -> None:
        """Delete the project node if it has no entity children left."""
        pnode = self._project_nodes.get(project_code)
        if pnode and not self._tree.get_children(pnode):
            self._project_nodes.pop(project_code)
            self._node_map.pop(pnode, None)
            self._tree.delete(pnode)

    def add_entity(self, project: FEAProject) -> None:
        """
        Adds or refreshes one entity in the tree.
        If the entity is already present its subtree is rebuilt in place.
        """
        entity_path = str(project.path)

        # Remove existing entity node if present
        if entity_path in self._entity_nodes:
            old_node = self._entity_nodes.pop(entity_path)
            old_project_code = self._entity_project.pop(entity_path, None)

            # Clean up all node_map entries for this entity's subtree
            to_delete = [k for k, v in self._node_map.items()
                         if len(v) > 1 and v[1] == entity_path]
            to_delete.append(old_node)
            for k in to_delete:
                self._node_map.pop(k, None)
            self._tree.delete(old_node)

            # If the old project node is now empty, remove it too
            if old_project_code:
                self._cleanup_project_node_if_empty(old_project_code)

        e = project.entity
        project_code = e.project

        # Get or create the project node
        project_node = self._get_or_create_project_node(project_code)

        # Insert entity node under its project, sorted by entity name
        new_label = e.name.casefold()
        siblings = self._tree.get_children(project_node)
        insert_index = len(siblings)
        for idx, node in enumerate(siblings):
            sibling_label = self._tree.item(node, "text").strip().casefold()
            if new_label < sibling_label:
                insert_index = idx
                break

        entity_node = self._tree.insert(
            project_node, insert_index,
            text=f"  {e.name}",
            open=True,
            tags=("tag_entity",),
        )
        self._entity_nodes[entity_path]  = entity_node
        self._entity_project[entity_path] = project_code
        self._node_map[entity_node]       = ("entity", entity_path)

        for v in e.versions:
            status_val  = v.status.value
            status_text = _VERSION_STATUS_TEXT.get(status_val, status_val)
            tag         = _STATUS_TAG.get(status_val, "")

            v_node = self._tree.insert(
                entity_node, "end",
                text=f"  {v.id}  {status_text}",
                open=True,
                tags=(tag,),
            )
            self._node_map[v_node] = ("version", entity_path, v.id)

            for i in v.iterations:
                iter_status_val = i.status.value
                iter_tag        = _ITER_STATUS_TAG.get(iter_status_val, "")
                iter_tags       = (iter_tag,) if iter_tag else ()
                if iter_status_val == "deprecated":
                    status_suffix = "  ● Deprecated"
                elif iter_status_val == "production":
                    status_suffix = "  ● Production"
                else:
                    status_suffix = ""
                i_node = self._tree.insert(
                    v_node, "end",
                    text=f"  {i.id}  {i.solver_type.value}{status_suffix}",
                    open=True,
                    tags=iter_tags,
                )
                self._node_map[i_node] = ("iteration", entity_path, v.id, i.id)

                for run in i.runs:
                    run_status  = run.status.value
                    status_text = _RUN_STATUS_TEXT.get(run_status, run_status)
                    tag         = _STATUS_TAG.get(run_status, "")
                    prod_suffix = "  ★" if run.artifacts.is_production else ""
                    tags        = (tag, "tag_prod_marker") \
                                  if run.artifacts.is_production else (tag,)
                    if run.artifacts.is_production:
                        _warn = _check_production_artifacts(
                            project.path, i.solver_type, i.filename_base,
                            run.id, v.id, i.id,
                            run.artifacts.output,
                        )
                    else:
                        _warn = _check_input_file(
                            project.path, i.solver_type, i.filename_base,
                            run.id, v.id, i.id,
                        )
                    warn_suffix = "  ⚠" if _warn else ""

                    run_node = self._tree.insert(
                        i_node, "end",
                        text=f"  Run {run.id:02d}  {status_text}{prod_suffix}{warn_suffix}",
                        tags=tags,
                    )
                    self._node_map[run_node] = (
                        "run", entity_path, v.id, i.id, run.id)

    def remove_entity(self, entity_path: str) -> None:
        """Removes an entity and all its children from the tree."""
        node = self._entity_nodes.pop(entity_path, None)
        project_code = self._entity_project.pop(entity_path, None)
        if node:
            to_delete = [k for k, v in self._node_map.items()
                         if len(v) > 1 and v[1] == entity_path]
            to_delete.append(node)
            for k in to_delete:
                self._node_map.pop(k, None)
            self._tree.delete(node)

            # Remove empty project node
            if project_code:
                self._cleanup_project_node_if_empty(project_code)

    def refresh_entity(self, project: FEAProject) -> None:
        """Alias for add_entity — rebuilds the subtree in place."""
        self.add_entity(project)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def select_node(self, node_type: str, entity_path: str, *ids) -> None:
        """Programmatically select and scroll to the tree node matching the
        given payload, without triggering the selection callback.

        The flag is reset via after_idle so it stays True until after the
        queued <<TreeviewSelect>> event has been processed by the event loop.
        """
        target = (node_type, entity_path, *ids)
        for node_id, payload in self._node_map.items():
            if payload == target:
                self._suppress_select = True
                self._tree.selection_set(node_id)
                self._tree.see(node_id)
                self._tree.after_idle(
                    lambda: setattr(self, '_suppress_select', False)
                )
                return

    def _on_tree_select(self, _event) -> None:
        if self._suppress_select:
            return
        sel = self._tree.selection()
        if not sel:
            return
        payload = self._node_map.get(sel[0])
        if payload and payload[0] != "project":
            node_type, entity_path, *ids = payload
            self._on_select(node_type, entity_path, *ids)

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
    # Right-click context menu (expand / collapse / close entity)
    # ------------------------------------------------------------------

    def _make_context_menu(self) -> "tk.Menu":
        import tkinter as tk
        t = tokens()
        return tk.Menu(
            self, tearoff=0,
            bg=t["bg_secondary"],
            fg=t["fg"],
            activebackground=t["bg_selected"],
            activeforeground=t["fg_selected"],
            borderwidth=1,
            relief="flat",
            font=("Segoe UI", 10),
        )

    def _on_right_click(self, event) -> None:
        menu = self._make_context_menu()

        item = self._tree.identify_row(event.y)
        payload = self._node_map.get(item) if item else None

        if payload and payload[0] == "project":
            # Clicked on a project root node — per-project expand/collapse
            menu.add_command(label="Expand",   command=lambda: self._set_subtree_open(item, True))
            menu.add_command(label="Collapse", command=lambda: self._set_subtree_open(item, False))
        elif payload and payload[0] == "entity":
            # Clicked on an entity node — per-entity actions
            entity_path = payload[1]
            menu.add_command(label="Expand",   command=lambda: self._set_subtree_open(item, True))
            menu.add_command(label="Collapse", command=lambda: self._set_subtree_open(item, False))
            menu.add_separator()
            menu.add_command(label="Close Entity", command=lambda: self._on_close(entity_path))
        elif payload and payload[0] == "run":
            # Clicked on a run node — run-level actions
            _, entity_path, v_id, i_id, run_id = payload
            menu.add_command(
                label="Delete Run…",
                command=lambda ep=entity_path, v=v_id, i=i_id, r=run_id:
                    self._on_delete_run(ep, v, i, r),
            )
        else:
            # Clicked on empty space or a child node — global actions
            menu.add_command(label="Expand All",   command=self._expand_all)
            menu.add_command(label="Collapse All", command=self._collapse_all)

        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def _on_appearance_change(self, _mode: str) -> None:
        apply_sidebar_style()
        self._configure_tags()
