"""
sidebar.py — Navigation Tree
==============================
Renders the collapsible hierarchy supporting multiple entities:

  EV24 · Front Crossmember
   └─ V01  ● WIP
       └─ R01  IMPLICIT
           └─ I01
               └─ Run 01  ● Converged

  EV24 · Rear Crossmember
   └─ V01  ● WIP
       ...

Status indicators use coloured ● text + ttk tag foreground colouring
instead of emoji, which render as hatch fills on Windows.
"""

from __future__ import annotations

import tkinter.ttk as ttk
import customtkinter as ctk
from typing import Callable, Optional

from app.core.models import FEAProject
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


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

class Sidebar(ctk.CTkFrame):
    """
    Left-panel navigation tree supporting multiple entities.

    Parameters
    ----------
    master      : parent widget
    on_select   : callback(node_type, *ids, entity_path)
    on_close    : callback(entity_path) — called when user closes an entity
    width       : fixed pixel width
    """

    _SIDEBAR_WIDTH = 240

    def __init__(
        self,
        master,
        on_select: Callable[..., None],
        on_close:  Callable[[str], None],
        width: int = _SIDEBAR_WIDTH,
    ):
        super().__init__(master, width=width, corner_radius=0)
        self.pack_propagate(False)
        self.grid_propagate(False)

        self._on_select = on_select
        self._on_close  = on_close

        # node_id → (node_type, entity_path, *record_ids)
        self._node_map:    dict[str, tuple] = {}
        # entity_path → root node id in the tree
        self._entity_nodes: dict[str, str]  = {}

        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="NAVIGATOR",
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

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
        self._tree.tag_configure("tag_prod_marker", foreground="#FFD580")
        # Entity root nodes — slightly bolder appearance
        t = tokens()
        self._tree.tag_configure(
            "tag_entity",
            font=("Segoe UI", 11, "bold"),
            foreground=t["fg"],
        )

    # ------------------------------------------------------------------
    # Populate — add or refresh a single entity
    # ------------------------------------------------------------------

    def add_entity(self, project: FEAProject) -> None:
        """
        Adds or refreshes one entity in the tree.
        If the entity is already present its subtree is rebuilt in place.
        """
        entity_path = str(project.path)

        # Remove existing node if present
        if entity_path in self._entity_nodes:
            old_node = self._entity_nodes[entity_path]
            # Remove all node_map entries for this entity
            to_delete = [k for k, v in self._node_map.items()
                         if len(v) > 1 and v[1] == entity_path]
            to_delete.append(old_node)
            for k in to_delete:
                self._node_map.pop(k, None)
            self._tree.delete(old_node)

        e = project.entity

        entity_node = self._tree.insert(
            "", "end",
            text=f"  {e.project} · {e.name}",
            open=True,
            tags=("tag_entity",),
        )
        self._entity_nodes[entity_path] = entity_node
        self._node_map[entity_node]     = ("entity", entity_path)

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

            for r in v.representations:
                r_node = self._tree.insert(
                    v_node, "end",
                    text=f"  {r.id}  {r.solver_type.value}",
                    open=True,
                )
                self._node_map[r_node] = ("representation", entity_path, v.id, r.id)

                for i in r.iterations:
                    i_node = self._tree.insert(
                        r_node, "end",
                        text=f"  {i.id}",
                        open=True,
                    )
                    self._node_map[i_node] = ("iteration", entity_path, v.id, r.id, i.id)

                    for run in i.runs:
                        run_status  = run.status.value
                        status_text = _RUN_STATUS_TEXT.get(run_status, run_status)
                        tag         = _STATUS_TAG.get(run_status, "")
                        prod_suffix = "  ★" if run.artifacts.is_production else ""
                        tags        = (tag, "tag_prod_marker") \
                                      if run.artifacts.is_production else (tag,)

                        run_node = self._tree.insert(
                            i_node, "end",
                            text=f"  Run {run.id:02d}  {status_text}{prod_suffix}",
                            tags=tags,
                        )
                        self._node_map[run_node] = (
                            "run", entity_path, v.id, r.id, i.id, run.id)

    def remove_entity(self, entity_path: str) -> None:
        """Removes an entity and all its children from the tree."""
        node = self._entity_nodes.pop(entity_path, None)
        if node:
            to_delete = [k for k, v in self._node_map.items()
                         if len(v) > 1 and v[1] == entity_path]
            to_delete.append(node)
            for k in to_delete:
                self._node_map.pop(k, None)
            self._tree.delete(node)

    def refresh_entity(self, project: FEAProject) -> None:
        """Alias for add_entity — rebuilds the subtree in place."""
        self.add_entity(project)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_tree_select(self, _event) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        payload = self._node_map.get(sel[0])
        if payload:
            node_type, entity_path, *ids = payload
            self._on_select(node_type, entity_path, *ids)

    # ------------------------------------------------------------------
    # Right-click context menu (close entity)
    # ------------------------------------------------------------------

    def _on_right_click(self, event) -> None:
        item = self._tree.identify_row(event.y)
        if not item:
            return
        payload = self._node_map.get(item)
        if not payload or payload[0] != "entity":
            return

        entity_path = payload[1]
        import tkinter as tk
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="Close Entity",
            command=lambda: self._on_close(entity_path),
        )
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
