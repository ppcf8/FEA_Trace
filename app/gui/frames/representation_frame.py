"""
representation_frame.py — Representation Detail View
"""

from __future__ import annotations

import tkinter.ttk as ttk
import customtkinter as ctk
from typing import Optional

from app.core.models import FEAProject
from app.gui.theme import apply_table_style, make_scrollbar, SOLVER_COLORS


_COL_WEIGHTS = {
    "id":             1,
    "description":    7,
    "design_changes": 4,
    "runs":           1,
    "created_by":     3,
    "created_on":     3,
}  # total = 19 units


class RepresentationFrame(ctk.CTkFrame):

    def __init__(self, master, window):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self._window      = window
        self._project:    Optional[FEAProject] = None
        self._entity_path: Optional[str]       = None
        self._version_id: Optional[str]        = None
        self._rep_id:     Optional[str]        = None
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_header()
        self._build_metadata_panel()
        self._build_iter_table()
        self._build_action_bar()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        hdr.columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            hdr, text="Representation",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="w")

        self._solver_label = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6, anchor="center", padx=12, pady=4,
        )
        self._solver_label.grid(row=0, column=1, sticky="e")

    def _build_metadata_panel(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="ew", padx=24, pady=16)
        panel.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            panel, text="Description",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw", width=110,
        ).grid(row=0, column=0, padx=(16, 4), pady=(12, 6), sticky="nw")

        self._desc_label = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(size=12),
            anchor="nw", justify="left", wraplength=580,
        )
        self._desc_label.grid(row=0, column=1, columnspan=5,
                              padx=(0, 16), pady=(12, 6), sticky="w")

        ctk.CTkLabel(
            panel, text="Analysis Types",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", width=110,
        ).grid(row=1, column=0, padx=(16, 4), pady=(0, 6), sticky="w")

        self._analysis_label = ctk.CTkLabel(
            panel, text="", font=ctk.CTkFont(size=12), anchor="w",
        )
        self._analysis_label.grid(row=1, column=1, columnspan=2,
                                  padx=(0, 24), pady=(0, 6), sticky="w")

        fields = [("Created By", "_created_by"), ("Created On", "_created_on")]
        self._meta: dict[str, ctk.CTkLabel] = {}
        for col_i, (label, key) in enumerate(fields):
            ctk.CTkLabel(
                panel, text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w", width=110,
            ).grid(row=1, column=3 + col_i * 2, padx=(16, 4), pady=(0, 6), sticky="w")
            val = ctk.CTkLabel(panel, text="—", font=ctk.CTkFont(size=12), anchor="w")
            val.grid(row=1, column=4 + col_i * 2, padx=(0, 16), pady=(0, 6), sticky="w")
            self._meta[key] = val

        ctk.CTkLabel(
            panel, text="Solver Note",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw", width=110,
        ).grid(row=2, column=0, padx=(16, 4), pady=(0, 12), sticky="nw")

        self._solver_note = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(size=12),
            anchor="nw", justify="left", wraplength=580,
        )
        self._solver_note.grid(row=2, column=1, columnspan=5,
                               padx=(0, 16), pady=(0, 12), sticky="w")

    def _build_iter_table(self) -> None:
        section = ctk.CTkFrame(self, fg_color="transparent")
        section.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 8))
        section.columnconfigure(0, weight=1)
        section.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            section, text="Iterations",
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        cols = ("id", "description", "design_changes", "runs",
                "created_by", "created_on")
        self._table = ttk.Treeview(
            section, columns=cols, show="headings",
            selectmode="browse", height=8,
            style="Rep.Treeview",
        )

        headings = {
            "id":             ("ID",             "center"),
            "description":    ("Description",    "w"),
            "design_changes": ("Design Changes", "w"),
            "runs":           ("Runs",           "center"),
            "created_by":     ("Created By",     "w"),
            "created_on":     ("Created On",     "w"),
        }
        for col, (heading, anchor) in headings.items():
            self._table.heading(col, text=heading, anchor=anchor)
            self._table.column(col, width=60, anchor=anchor, stretch=False)

        vsb = make_scrollbar(section, "vertical",   self._table.yview)
        hsb = make_scrollbar(section, "horizontal", self._table.xview)
        self._table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._table.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")

        self._section = section
        self._table.bind("<<TreeviewSelect>>", self._on_iter_select)
        section.bind("<Configure>", self._resize_columns)
        apply_table_style("Rep.Treeview")
        ctk.AppearanceModeTracker.add(self._on_appearance_change)

    def _build_action_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", padx=24, pady=(4, 20))

        ctk.CTkButton(
            bar, text="+ New Iteration", width=150, height=36,
            font=ctk.CTkFont(size=13),
            command=self._on_new_iteration,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, project: FEAProject, version_id: str, rep_id: str) -> None:
        self._project      = project
        self._entity_path  = str(project.path)
        self._version_id   = version_id
        self._rep_id       = rep_id

        v = project._get_version(version_id)
        r = project._get_representation(v, rep_id)

        self._title_label.configure(text=f"Representation  {v.id} / {r.id}")

        solver_val = r.solver_type.value
        color      = SOLVER_COLORS.get(solver_val, "#444444")
        self._solver_label.configure(
            text=f"  {solver_val}  ",
            fg_color=color, text_color="#FFFFFF",
        )

        self._desc_label.configure(text=r.description.strip())
        self._analysis_label.configure(
            text="  ·  ".join(r.analysis_types) if r.analysis_types else "—")
        self._meta["_created_by"].configure(text=r.created_by)
        self._meta["_created_on"].configure(text=r.created_on)

        _NOTES = {
            "IMPLICIT": "Solver deck extension: .fem  —  OptiStruct implicit analysis.",
            "EXPLICIT": "Solver deck extension: .rad  —  Radioss explicit analysis.",
            "MBD":      "Solver deck extension: .xml  —  MotionSolve multibody dynamics.",
        }
        self._solver_note.configure(text=_NOTES.get(solver_val, ""))

        apply_table_style("Rep.Treeview")
        self._populate_table(r)

    def _populate_table(self, r) -> None:
        for row in self._table.get_children():
            self._table.delete(row)

        for i in r.iterations:
            desc = i.description.strip().replace("\n", " ")
            if len(desc) > 55:
                desc = desc[:52] + "…"
            self._table.insert("", "end", iid=i.id, values=(
                i.id, desc, f"{len(i.design_changes)} change(s)",
                len(i.runs), i.created_by, i.created_on,
            ))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_iter_select(self, _event) -> None:
        sel = self._table.selection()
        if sel and self._project and self._entity_path:
            self._window.show_iteration(
                self._entity_path, self._version_id, self._rep_id, sel[0])

    def _on_new_iteration(self) -> None:
        if not self._project or not self._version_id or not self._rep_id:
            return
        from app.gui.dialogs.new_iteration_dialog import NewIterationDialog
        dlg = NewIterationDialog(self._window)
        self._window.wait_window(dlg)
        if dlg.result is None:
            return

        description, design_changes, created_by = dlg.result
        try:
            self._project.add_iteration(
                self._version_id, self._rep_id,
                description, created_by, design_changes,
            )
        except Exception as exc:
            self._show_error("Create Iteration Failed", str(exc))
            return

        v = self._project._get_version(self._version_id)
        r = self._project._get_representation(v, self._rep_id)
        self._populate_table(r)
        self._window.refresh_sidebar()
        self._window.set_status("Iteration created successfully.")

    def _resize_columns(self, event=None) -> None:
        width = self._section.winfo_width()
        if width <= 1 or width == getattr(self, "_last_col_width", 0):
            return
        self._last_col_width = width
        available = max(width - 18, 100)
        total = sum(_COL_WEIGHTS.values())
        for col, w in _COL_WEIGHTS.items():
            self._table.column(col, width=max(20, int(available * w / total)))

    def _on_appearance_change(self, _mode: str) -> None:
        apply_table_style("Rep.Treeview")

    def _show_error(self, title: str, message: str) -> None:
        from tkinter import messagebox
        messagebox.showerror(title, message, parent=self._window)
