"""
frames/version_frame.py — Version Detail View
"""
from __future__ import annotations

import tkinter.ttk as ttk
import customtkinter as ctk
from typing import Optional

from schema import VersionStatus, VERSION_STATUS_TRANSITIONS
from app.core.models import FEAProject
from app.gui.theme import apply_table_style, make_scrollbar, add_hint
from app.gui.hints import VERSION_TOOLTIP


_STATUS_BADGE = {
    "WIP":        ("●  WIP",        "#4A90D9"),
    "production": ("●  Production", "#2D8A4E"),
    "deprecated": ("●  Deprecated", "#888888"),
}

_SOLVER_BADGE = {
    "IMPLICIT": "⚙  IMPLICIT",
    "EXPLICIT": "⚡  EXPLICIT",
    "MBD":      "🔗  MBD",
}

_COL_WEIGHTS = {
    "id":             1,
    "solver_type":    2,
    "analysis_types": 3,
    "description":    7,
    "runs":           1,
    "created_by":     3,
    "created_on":     3,
}  # total = 20 units


class VersionFrame(ctk.CTkFrame):

    def __init__(self, master, window):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self._window      = window
        self._project:    Optional[FEAProject] = None
        self._version_id: Optional[str]        = None
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._build_header()
        self._build_metadata_panel()
        self._build_notes_panel()
        self._build_iter_table()
        self._build_action_bar()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        hdr.columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            hdr, text="Version",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="w")
        add_hint(self._title_label, VERSION_TOOLTIP)

        self._status_badge = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6, padx=12, pady=4,
        )
        self._status_badge.grid(row=0, column=1, sticky="e")

    def _build_metadata_panel(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="ew", padx=24, pady=16)
        panel.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            panel, text="Intent",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw", width=100,
        ).grid(row=0, column=0, padx=(16, 4), pady=(12, 6), sticky="nw")

        self._intent_label = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(size=12),
            anchor="nw", justify="left", wraplength=600,
        )
        self._intent_label.grid(row=0, column=1, columnspan=3,
                                padx=(0, 16), pady=(12, 6), sticky="w")

        fields = [("Created By", "_created_by"), ("Created On", "_created_on")]
        self._meta: dict[str, ctk.CTkLabel] = {}
        for col_i, (label, key) in enumerate(fields):
            ctk.CTkLabel(
                panel, text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w", width=100,
            ).grid(row=1, column=col_i * 2, padx=(16, 4), pady=(0, 12), sticky="w")
            val = ctk.CTkLabel(panel, text="—", font=ctk.CTkFont(size=12), anchor="w")
            val.grid(row=1, column=col_i * 2 + 1,
                     padx=(0, 24), pady=(0, 12), sticky="w")
            self._meta[key] = val

        self._transition_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._transition_frame.grid(row=0, column=4, rowspan=2,
                                    padx=(0, 16), pady=12, sticky="ne")

    def _build_notes_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
        panel.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            panel, text="Notes",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw", width=100,
        ).grid(row=0, column=0, padx=(0, 4), sticky="nw")

        self._notes_label = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(size=12),
            anchor="nw", justify="left", wraplength=600,
        )
        self._notes_label.grid(row=0, column=1, sticky="w")

    def _build_iter_table(self) -> None:
        section = ctk.CTkFrame(self, fg_color="transparent")
        section.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 8))
        section.columnconfigure(0, weight=1)
        section.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            section, text="Iterations",
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        cols = ("id", "solver_type", "analysis_types",
                "description", "runs", "created_by", "created_on")
        self._table = ttk.Treeview(
            section, columns=cols, show="headings",
            selectmode="browse", height=7,
            style="Version.Treeview",
        )

        headings = {
            "id":             ("ID",          "center"),
            "solver_type":    ("Solver",      "w"),
            "analysis_types": ("Analysis",    "w"),
            "description":    ("Description", "w"),
            "runs":           ("Runs",        "center"),
            "created_by":     ("Created By",  "w"),
            "created_on":     ("Created On",  "w"),
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
        apply_table_style("Version.Treeview")
        ctk.AppearanceModeTracker.add(self._on_appearance_change)

    def _build_action_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=4, column=0, sticky="ew", padx=24, pady=(4, 20))

        ctk.CTkButton(
            bar, text="+ New Iteration",
            width=160, height=36,
            font=ctk.CTkFont(size=13),
            command=self._on_new_iteration,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, project: FEAProject, version_id: str) -> None:
        self._project    = project
        self._version_id = version_id

        v = project._get_version(version_id)

        apply_table_style("Version.Treeview")
        self._title_label.configure(text=f"Version  {v.id}")
        badge_text, badge_color = _STATUS_BADGE.get(
            v.status.value, (v.status.value, "#444444"))
        self._status_badge.configure(
            text=f"  {badge_text}  ",
            fg_color=badge_color, text_color="#FFFFFF",
        )
        self._intent_label.configure(text=v.intent.strip())
        self._meta["_created_by"].configure(text=v.created_by)
        self._meta["_created_on"].configure(text=v.created_on)

        notes_text = "\n".join(f"• {n}" for n in v.notes) if v.notes else "—"
        self._notes_label.configure(text=notes_text)

        self._populate_transition_buttons(v.status)
        self._populate_table(v)

    def _populate_transition_buttons(self, current: VersionStatus) -> None:
        for w in self._transition_frame.winfo_children():
            w.destroy()

        allowed = VERSION_STATUS_TRANSITIONS.get(current, set())
        if not allowed:
            ctk.CTkLabel(
                self._transition_frame,
                text="Terminal state — no transitions",
                font=ctk.CTkFont(size=11),
            ).pack()
            return

        ctk.CTkLabel(
            self._transition_frame,
            text="Change Status",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="e", pady=(0, 4))

        _LABELS = {
            VersionStatus.PRODUCTION: ("Promote to Production", "#2D8A4E"),
            VersionStatus.DEPRECATED: ("Mark Deprecated",       "#888888"),
            VersionStatus.WIP:        ("Revert to WIP",         "#4A90D9"),
        }
        for target in allowed:
            label, color = _LABELS.get(target, (target.value.title(), None))
            kwargs = dict(
                text=label, width=180, height=30,
                font=ctk.CTkFont(size=12),
                command=lambda t=target: self._on_status_change(t),
            )
            if color:
                kwargs["fg_color"] = color
            ctk.CTkButton(self._transition_frame, **kwargs).pack(anchor="e", pady=2)

    def _populate_table(self, v) -> None:
        for row in self._table.get_children():
            self._table.delete(row)

        for i in v.iterations:
            types  = ", ".join(i.analysis_types)
            desc   = i.description.strip().replace("\n", " ")
            if len(desc) > 55:
                desc = desc[:52] + "…"
            solver = _SOLVER_BADGE.get(i.solver_type.value, i.solver_type.value)
            self._table.insert("", "end", iid=i.id, values=(
                i.id, solver, types, desc,
                len(i.runs), i.created_by, i.created_on,
            ))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_iter_select(self, _event) -> None:
        sel = self._table.selection()
        if sel and self._project and self._version_id:
            self._window.show_iteration(
                str(self._project.path), self._version_id, sel[0])

    def _on_status_change(self, target: VersionStatus) -> None:
        if not self._project or not self._version_id:
            return

        revert_reason = None
        if target == VersionStatus.WIP:
            from app.gui.dialogs.revert_reason_dialog import RevertReasonDialog
            dlg = RevertReasonDialog(self._window, self._version_id)
            self._window.wait_window(dlg)
            if dlg.result is None:
                return
            revert_reason = dlg.result

        try:
            self._project.update_version_status(
                self._version_id, target, revert_reason=revert_reason)
        except Exception as exc:
            self._show_error("Status Change Failed", str(exc))
            return

        self._window.refresh_sidebar()
        self._window.set_status(f"Version {self._version_id} → {target.value}")
        self.load(self._project, self._version_id)

    def _on_new_iteration(self) -> None:
        if not self._project or not self._version_id:
            return
        from app.gui.dialogs.new_iteration_dialog import NewIterationDialog
        dlg = NewIterationDialog(self._window)
        self._window.wait_window(dlg)
        if dlg.result is None:
            return

        solver_type, analysis_types, description, created_by = dlg.result
        try:
            self._project.add_iteration(
                self._version_id, solver_type,
                analysis_types, description, created_by,
            )
        except Exception as exc:
            self._show_error("Create Iteration Failed", str(exc))
            return

        v = self._project._get_version(self._version_id)
        self._populate_table(v)
        self._window.refresh_sidebar()
        self._window.set_status("Iteration created successfully.")

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

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
        apply_table_style("Version.Treeview")

    def _show_error(self, title: str, message: str) -> None:
        from tkinter import messagebox
        messagebox.showerror(title, message, parent=self._window)
