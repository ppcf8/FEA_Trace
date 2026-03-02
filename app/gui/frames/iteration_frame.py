"""
iteration_frame.py — Iteration Detail View
===========================================
Displayed when an Iteration node is selected in the sidebar.
Shows iteration metadata (including solver type and analysis types),
the auto-generated filename base, and the run summary table. Provides the entry point for registering a new Run.
"""

from __future__ import annotations

import os
import platform
import subprocess
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont
import customtkinter as ctk
from pathlib import Path
from typing import Optional
from PIL import Image

from schema import IterationStatus, ITERATION_STATUS_TRANSITIONS, VersionStatus
from app.config import MODELS_FOLDER
from app.core.models import FEAProject
from app.gui.theme import (apply_table_style, make_scrollbar, STATUS_COLORS,
                           SOLVER_COLORS, add_hint, tokens,
                           parse_audit_note_extended, autofit_tree_columns,
                           show_audit_detail_popup)
from app.gui.hints import ITERATION_TOOLTIP

_ICONS_DIR = Path(__file__).parent.parent.parent / "assets" / "icons"
_IMG_COPY  = ctk.CTkImage(Image.open(_ICONS_DIR / "copy.png"), size=(18, 18))
_IMG_EDIT  = ctk.CTkImage(Image.open(_ICONS_DIR / "edit.png"), size=(16, 16))


# ---------------------------------------------------------------------------
# Column weight map (proportional autofit)
# ---------------------------------------------------------------------------

_ITER_STATUS_BADGE = {
    "WIP":        ("●  WIP",        "#4A90D9"),
    "production": ("●  Production", "#2D8A4E"),
    "deprecated": ("●  Deprecated", "#888888"),
}

_ITER_STATUS_LABELS = {
    IterationStatus.PRODUCTION: ("Promote to Production", "#2D8A4E"),
    IterationStatus.DEPRECATED: ("Mark Deprecated",       "#888888"),
    IterationStatus.WIP:        ("Revert to WIP",         "#4A90D9"),
}

_COL_WEIGHTS = {
    "id":         1,
    "name":       7,
    "status":     3,
    "date":       3,
    "created_by": 3,
    "production": 1,
    "comments":   6,
}  # total = 24 units

_NO_FILTER_COLS = frozenset({"comments"})
_DATE_COLS      = frozenset({"date"})


# ---------------------------------------------------------------------------
# IterationFrame
# ---------------------------------------------------------------------------

class IterationFrame(ctk.CTkFrame):
    """
    Parameters
    ----------
    master : parent widget (main panel)
    window : MainWindow reference
    """

    def __init__(self, master, window):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self._window       = window
        self._project:     Optional[FEAProject] = None
        self._version_id:  Optional[str]        = None
        self._iter_id:     Optional[str]        = None
        self._all_rows:    list[dict]    = []
        self._sort_col:    str | None    = None
        self._sort_reverse: bool         = False
        self._col_filters: dict[str, set[str]] = {}
        self._search_var:  ctk.StringVar        = ctk.StringVar()
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)   # run table expands

        self._build_header()
        self._build_metadata_panel()
        self._build_notes_panel()
        self._build_run_table()
        self._build_action_bar()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        hdr.columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(hdr, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            title_row, text="Iteration",
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="w")
        add_hint(self._title_label, ITERATION_TOOLTIP)

        self._solver_label = ctk.CTkLabel(
            title_row, text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6, anchor="center", padx=12, pady=4,
        )
        self._solver_label.grid(row=0, column=1, sticky="e", padx=(0, 8))

        self._status_badge = ctk.CTkLabel(
            title_row, text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6, anchor="center", padx=12, pady=4,
        )
        self._status_badge.grid(row=0, column=2, sticky="e")

        # Filename base pill — read-only, copy button alongside
        base_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        base_frame.grid(row=1, column=0, columnspan=2,
                        sticky="w", pady=(6, 0))

        ctk.CTkLabel(
            base_frame,
            text="Filename Base",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", width=110,
        ).pack(side="left")

        self._base_var = ctk.StringVar(value="—")
        base_entry = ctk.CTkEntry(
            base_frame,
            textvariable=self._base_var,
            state="readonly",
            width=400,
            font=ctk.CTkFont(size=12, family="Courier New"),
        )
        base_entry.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            base_frame,
            text="", image=_IMG_COPY,
            width=32, height=28,
            command=self._copy_base,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            base_frame,
            text="Open Folder",
            width=100, height=28,
            font=ctk.CTkFont(size=12),
            command=self._open_models_folder,
        ).pack(side="left")

    def _build_metadata_panel(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="ew", padx=24, pady=16)
        panel.columnconfigure(1, weight=1)

        # Description
        ctk.CTkLabel(
            panel, text="Description",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw", width=110,
        ).grid(row=0, column=0, padx=(16, 4), pady=(12, 6), sticky="nw")

        self._desc_label = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(size=12),
            anchor="nw", justify="left", wraplength=540,
        )
        self._desc_label.grid(row=0, column=1, columnspan=3,
                              padx=(0, 16), pady=(12, 6), sticky="w")

        # Analysis Types
        ctk.CTkLabel(
            panel, text="Analysis Types",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", width=110,
        ).grid(row=1, column=0, padx=(16, 4), pady=(0, 6), sticky="w")

        self._analysis_label = ctk.CTkLabel(
            panel, text="", font=ctk.CTkFont(size=12), anchor="w",
        )
        self._analysis_label.grid(row=1, column=1, columnspan=3,
                                  padx=(0, 16), pady=(0, 6), sticky="w")

        # Created by / on
        fields = [("Created By", "_created_by"), ("Created On", "_created_on")]
        self._meta: dict[str, ctk.CTkLabel] = {}
        for col_i, (label, key) in enumerate(fields):
            ctk.CTkLabel(
                panel, text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w", width=110,
            ).grid(row=2, column=col_i * 2,
                   padx=(16, 4), pady=(0, 6), sticky="w")
            val = ctk.CTkLabel(
                panel, text="—",
                font=ctk.CTkFont(size=12), anchor="w",
            )
            val.grid(row=2, column=col_i * 2 + 1,
                     padx=(0, 24), pady=(0, 6), sticky="w")
            self._meta[key] = val

        # Promoted On row (hidden until iteration is promoted)
        self._promoted_on_key = ctk.CTkLabel(
            panel, text="Promoted On",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", width=110,
        )
        self._promoted_on_key.grid(row=3, column=0, padx=(16, 4), pady=(0, 12), sticky="w")
        self._meta["_promoted_on"] = ctk.CTkLabel(
            panel, text="—", font=ctk.CTkFont(size=12), anchor="w")
        self._meta["_promoted_on"].grid(row=3, column=1, columnspan=3,
                                        padx=(0, 24), pady=(0, 12), sticky="w")
        self._promoted_on_key.grid_remove()
        self._meta["_promoted_on"].grid_remove()

        # Transition buttons + Edit (right column)
        self._transition_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._transition_frame.grid(row=0, column=4, rowspan=4,
                                    padx=(0, 16), pady=12, sticky="ne")

    def _build_notes_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
        panel.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            panel, text="Audit Log",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        # Placeholder shown when there are no audit entries
        self._notes_label = ctk.CTkLabel(
            panel, text="—",
            font=ctk.CTkFont(size=12), anchor="nw",
        )
        self._notes_label.grid(row=1, column=0, sticky="w")

        # Audit log table — full width, 5 columns, fixed height of 7 rows
        self._audit_panel = ctk.CTkFrame(panel, fg_color="transparent")
        self._audit_panel.columnconfigure(0, weight=1)

        self._audit_tree = ttk.Treeview(
            self._audit_panel, style="IterAudit.Treeview",
            columns=("event", "date", "by", "runs", "details"),
            show="headings", height=7,
        )
        self._audit_tree.heading("event",   text="Event",   anchor="center")
        self._audit_tree.heading("date",    text="Date",    anchor="w")
        self._audit_tree.heading("by",      text="By",      anchor="w")
        self._audit_tree.heading("runs",    text="Runs",    anchor="w")
        self._audit_tree.heading("details", text="Details", anchor="w")
        self._audit_tree.column("event",   width=160, minwidth=100, stretch=False, anchor="center")
        self._audit_tree.column("date",    width=140, minwidth=100, stretch=False, anchor="w")
        self._audit_tree.column("by",      width=90,  minwidth=60,  stretch=False, anchor="w")
        self._audit_tree.column("runs",    width=60,  minwidth=40,  stretch=False, anchor="w")
        self._audit_tree.column("details", width=200, minwidth=80,  stretch=True,  anchor="w")
        self._audit_tree.grid(row=0, column=0, sticky="ew")

        self._audit_sb = make_scrollbar(self._audit_panel, "vertical", self._audit_tree.yview)
        self._audit_tree.configure(yscrollcommand=self._audit_sb.set)

        self._audit_tree.bind("<Double-1>", self._on_audit_double_click)

    def _on_audit_double_click(self, event) -> None:
        tree = self._audit_tree
        if tree.identify_region(event.x, event.y) != "cell":
            return
        iid = tree.focus()
        if not iid:
            return
        values = tree.item(iid, "values")
        show_audit_detail_popup(
            self._window,
            ["Event", "Date", "By", "Runs", "Details"],
            values,
        )

    def _build_run_table(self) -> None:
        section = ctk.CTkFrame(self, fg_color="transparent")
        section.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 8))
        section.columnconfigure(0, weight=1)
        section.rowconfigure(2, weight=1)

        ctk.CTkLabel(
            section, text="Runs",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        # Search row
        search_row = ctk.CTkFrame(section, fg_color="transparent")
        search_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        search_row.columnconfigure(1, weight=1)
        ctk.CTkLabel(search_row, text="Search:", width=52,
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
        search_entry = ctk.CTkEntry(search_row, textvariable=self._search_var,
                                    placeholder_text="Filter all columns…",
                                    height=28, font=ctk.CTkFont(size=12))
        search_entry.grid(row=0, column=1, sticky="ew", padx=(4, 4))
        ctk.CTkButton(search_row, text="✕", width=28, height=28,
                      font=ctk.CTkFont(size=12),
                      command=lambda: self._search_var.set("")
                      ).grid(row=0, column=2, sticky="e")
        self._search_var.trace_add("write", lambda *_: self._refresh_table())

        cols = ("id", "name", "status", "date",
                "created_by", "production", "comments")
        self._table = ttk.Treeview(
            section, columns=cols, show="headings",
            selectmode="browse", height=8,
            style="Iter.Treeview",
        )

        headings = {
            "id":         ("ID",         "center"),
            "name":       ("Filename",   "w"),
            "status":     ("Status",     "w"),
            "date":       ("Date",       "w"),
            "created_by": ("Created By", "w"),
            "production": ("Prod",       "center"),
            "comments":   ("Comments",   "w"),
        }
        self._headings = headings
        self._col_order = tuple(_COL_WEIGHTS.keys())

        for col, (heading, anchor) in headings.items():
            self._table.heading(col, text=heading, anchor=anchor,
                                command=lambda c=col: self._on_sort(c))
            self._table.column(col, width=60, anchor=anchor, stretch=False)

        for status, color in STATUS_COLORS.items():
            self._table.tag_configure(f"status_{status}", foreground=color)

        vsb = make_scrollbar(section, "vertical",   self._table.yview)
        hsb = make_scrollbar(section, "horizontal", self._table.xview)
        self._table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._table.grid(row=2, column=0, sticky="nsew")
        vsb.grid(row=2, column=1, sticky="ns")
        hsb.grid(row=3, column=0, sticky="ew")

        self._section = section
        self._table.bind("<<TreeviewSelect>>", self._on_run_select)
        self._table.bind("<Button-3>", self._on_table_right_click)
        section.bind("<Configure>", self._resize_columns)
        apply_table_style("Iter.Treeview")
        ctk.AppearanceModeTracker.add(self._on_appearance_change)

    def _build_action_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=4, column=0, sticky="ew", padx=24, pady=(4, 20))

        self._new_run_btn = ctk.CTkButton(
            bar,
            text="+ New Run",
            width=120, height=36,
            font=ctk.CTkFont(size=13),
            command=self._on_new_run,
        )
        self._new_run_btn.pack(side="left")


    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(
        self,
        project:    FEAProject,
        version_id: str,
        iter_id:    str,
    ) -> None:
        self._project    = project
        self._version_id = version_id
        self._iter_id    = iter_id

        apply_table_style("Iter.Treeview")

        v = project._get_version(version_id)
        i = project._get_iteration(v, iter_id)

        self._title_label.configure(
            text=f"Iteration  {version_id} / {i.id}")

        solver_val = i.solver_type.value
        color      = SOLVER_COLORS.get(solver_val, "#444444")
        self._solver_label.configure(
            text=f"  {solver_val}  ",
            fg_color=color, text_color="#FFFFFF",
        )

        self._base_var.set(i.filename_base)
        self._desc_label.configure(text=i.description.strip())
        self._analysis_label.configure(
            text="  ·  ".join(i.analysis_types) if i.analysis_types else "—")

        self._meta["_created_by"].configure(text=i.created_by)
        self._meta["_created_on"].configure(text=i.created_on)

        if i.promoted_at:
            self._meta["_promoted_on"].configure(text=i.promoted_at)
            self._promoted_on_key.grid()
            self._meta["_promoted_on"].grid()
        else:
            self._promoted_on_key.grid_remove()
            self._meta["_promoted_on"].grid_remove()

        apply_table_style("IterAudit.Treeview")
        for item in self._audit_tree.get_children():
            self._audit_tree.delete(item)
        if i.notes:
            for note in reversed(i.notes):
                self._audit_tree.insert("", "end", values=parse_audit_note_extended(note))
            autofit_tree_columns(self._audit_tree)
            if len(i.notes) > 7:
                self._audit_sb.grid(row=0, column=1, sticky="ns")
            else:
                self._audit_sb.grid_remove()
            self._notes_label.grid_remove()
            self._audit_panel.grid(row=1, column=0, sticky="ew")
        else:
            self._audit_panel.grid_remove()
            self._notes_label.grid(row=1, column=0, sticky="w")

        # Status badge
        badge_text, badge_color = _ITER_STATUS_BADGE.get(
            i.status.value, (i.status.value, "#888888"))
        self._status_badge.configure(
            text=f"  {badge_text}  ",
            fg_color=badge_color, text_color="#FFFFFF",
        )

        is_version_wip  = (v.status == VersionStatus.WIP)
        is_iter_wip     = (i.status == IterationStatus.WIP)
        is_editable     = is_version_wip and is_iter_wip
        self._new_run_btn.configure(state="normal" if is_editable else "disabled")

        self._populate_transition_buttons(i.status, is_version_wip)

        self._all_rows     = []
        self._sort_col     = None
        self._sort_reverse = False
        self._col_filters  = {}
        self._search_var.set("")
        for col in self._col_order:
            self._update_heading(col)
        self._populate_table(i)

    def _populate_transition_buttons(
            self, current: IterationStatus, is_version_wip: bool) -> None:
        for w in self._transition_frame.winfo_children():
            w.destroy()

        self._edit_btn = ctk.CTkButton(
            self._transition_frame,
            image=_IMG_EDIT, text="Edit", compound="left",
            width=90, height=28,
            font=ctk.CTkFont(size=12),
            state="normal" if (is_version_wip and current == IterationStatus.WIP)
                           else "disabled",
            command=self._on_edit_iteration,
        )
        self._edit_btn.pack(anchor="e", pady=(0, 8))

        if not is_version_wip:
            return

        allowed = ITERATION_STATUS_TRANSITIONS.get(current, set())
        if not allowed:
            return

        ctk.CTkLabel(
            self._transition_frame,
            text="Change Status",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="e", pady=(0, 4))

        for target in allowed:
            label, color = _ITER_STATUS_LABELS.get(target, (target.value.title(), None))
            if target == IterationStatus.PRODUCTION:
                cmd = self._on_promote_iteration
            else:
                cmd = lambda t=target: self._on_iter_status_change(t)
            kwargs = dict(
                text=label, width=180, height=30,
                font=ctk.CTkFont(size=12),
                command=cmd,
            )
            if color:
                kwargs["fg_color"] = color
            ctk.CTkButton(self._transition_frame, **kwargs).pack(anchor="e", pady=2)

    def _on_iter_status_change(self, target: IterationStatus) -> None:
        if not all([self._project, self._version_id, self._iter_id]):
            return

        revert_reason = None
        if target == IterationStatus.WIP:
            from app.gui.dialogs.revert_reason_dialog import RevertReasonDialog
            dlg = RevertReasonDialog(self._window, self._iter_id, "Iteration")
            self._window.wait_window(dlg)
            if dlg.result is None:
                return
            revert_reason = dlg.result

        try:
            self._project.update_iteration_status(
                self._version_id, self._iter_id, target,
                revert_reason=revert_reason,
            )
        except Exception as exc:
            self._show_error("Status Change Failed", str(exc))
            return

        self._window.refresh_sidebar()
        self._window.set_status(f"Iteration {self._iter_id} → {target.value}")
        self.load(self._project, self._version_id, self._iter_id)

    def _on_promote_iteration(self) -> None:
        if not all([self._project, self._version_id, self._iter_id]):
            return
        from app.gui.dialogs.promote_to_production_dialog import PromoteToProductionDialog
        dlg = PromoteToProductionDialog(
            self._window, self._project, self._version_id, self._iter_id)
        self._window.wait_window(dlg)
        if dlg.result is None:
            return
        try:
            warnings = self._project.promote_iteration_to_production(
                self._version_id, self._iter_id, dlg.result)
        except Exception as exc:
            self._show_error("Promote Failed", str(exc))
            return

        # Offer to also mark the version as PRODUCTION if it is still WIP
        v = self._project._get_version(self._version_id)
        if v.status == VersionStatus.WIP:
            from tkinter import messagebox
            if messagebox.askyesno(
                "Mark Version as Production?",
                f"Version {self._version_id} is still WIP.\n\n"
                "Mark it as Production too? This will lock version edits "
                "and prevent new iterations.",
                parent=self._window,
            ):
                self._project.update_version_status(
                    self._version_id, VersionStatus.PRODUCTION)

        warn_count = sum(len(w) for w in warnings.values())
        msg = f"Iteration {self._iter_id} promoted to Production"
        if warn_count:
            msg += f" — {warn_count} artifact warning(s)"
        self._window.refresh_sidebar()
        self._window.set_status(msg)
        self.load(self._project, self._version_id, self._iter_id)

    def _populate_table(self, i) -> None:
        self._all_rows = []
        for run in i.runs:
            status_text    = f"●  {run.status.value}"
            tag            = f"status_{run.status.value}"
            prod           = "★" if run.artifacts.is_production else ""
            comments_short = run.comments.replace("\n", " ")
            if len(comments_short) > 40:
                comments_short = comments_short[:37] + "…"
            self._all_rows.append({
                "iid":    str(run.id),
                "values": (f"{run.id:02d}", run.name, status_text, run.date,
                           run.created_by, prod, comments_short),
                "tags":   (tag,),
            })
        self._refresh_table()

    def _refresh_table(self) -> None:
        rows  = self._all_rows
        query = self._search_var.get().strip().lower()
        if query:
            rows = [r for r in rows
                    if any(query in str(v).lower() for v in r["values"])]
        for col, allowed in self._col_filters.items():
            if allowed:
                idx = self._col_order.index(col)
                if col in _DATE_COLS:
                    rows = [r for r in rows
                            if str(r["values"][idx]).split(" ")[0] in allowed]
                else:
                    rows = [r for r in rows if str(r["values"][idx]) in allowed]
        if self._sort_col is not None:
            idx  = self._col_order.index(self._sort_col)
            rows = sorted(rows,
                          key=lambda r: str(r["values"][idx]).lower(),
                          reverse=self._sort_reverse)
        for row in self._table.get_children():
            self._table.delete(row)
        for r in rows:
            self._table.insert("", "end", iid=r["iid"],
                               tags=r["tags"], values=r["values"])

    def _on_sort(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col, self._sort_reverse = col, False
        for c in self._col_order:
            self._update_heading(c)
        self._refresh_table()

    def _on_table_right_click(self, event) -> None:
        region = self._table.identify_region(event.x, event.y)

        if region == "heading":
            col_id = self._table.identify_column(event.x)
            if not col_id or col_id == "#0":
                return
            col_name = self._col_order[int(col_id[1:]) - 1]
            if col_name in _NO_FILTER_COLS:
                return
            self._open_filter_popup(col_name, event.x_root, event.y_root)

        elif region == "cell":
            row_id = self._table.identify_row(event.y)
            if not row_id or not self._project:
                return
            run_id = int(row_id)
            v   = self._project._get_version(self._version_id)
            i   = self._project._get_iteration(v, self._iter_id)
            run = self._project._get_run(i, run_id)
            is_prod      = run.artifacts.is_production
            is_iter_depr = (i.status == IterationStatus.DEPRECATED)
            is_iter_prod = (i.status == IterationStatus.PRODUCTION)

            t    = tokens()
            menu = tk.Menu(
                self, tearoff=0,
                bg=t["bg_secondary"], fg=t["fg"],
                activebackground=t["bg_selected"],
                activeforeground=t["fg_selected"],
                borderwidth=1, relief="flat",
                font=("Segoe UI", 10),
            )
            menu.add_command(
                label=f"Delete Run {run_id:02d}…",
                state="disabled" if (is_prod or is_iter_depr or is_iter_prod) else "normal",
                command=lambda: self._window.request_delete_run(
                    str(self._project.path),
                    self._version_id,
                    self._iter_id,
                    run_id,
                ),
            )
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

    def _update_heading(self, col: str) -> None:
        lbl, _     = self._headings[col]
        sort_ind   = (" ▼" if self._sort_reverse else " ▲") if self._sort_col == col else ""
        filter_ind = " ⊿" if self._col_filters.get(col) else ""
        self._table.heading(col, text=f"{lbl}{sort_ind}{filter_ind}")

    def _open_filter_popup(self, col: str, x_root: int = 0, y_root: int = 0) -> None:
        col_idx = self._col_order.index(col)
        is_date = col in _DATE_COLS

        # Cascading: build candidates from all other active filters + search
        candidate_rows = self._all_rows
        query = self._search_var.get().strip().lower()
        if query:
            candidate_rows = [r for r in candidate_rows
                              if any(query in str(v).lower() for v in r["values"])]
        for other_col, allowed in self._col_filters.items():
            if other_col != col and allowed:
                other_idx = self._col_order.index(other_col)
                if other_col in _DATE_COLS:
                    candidate_rows = [r for r in candidate_rows
                                      if str(r["values"][other_idx]).split(" ")[0] in allowed]
                else:
                    candidate_rows = [r for r in candidate_rows
                                      if str(r["values"][other_idx]) in allowed]

        if is_date:
            raw_vals = {str(r["values"][col_idx]).split(" ")[0] for r in candidate_rows}
        else:
            raw_vals = {str(r["values"][col_idx]) for r in candidate_rows}
        unique_vals = sorted(raw_vals, key=str.lower)

        if not unique_vals:
            return
        current = self._col_filters.get(col, set())

        popup = ctk.CTkToplevel(self._window)
        popup.title(f"Filter: {self._headings[col][0]}")
        popup.resizable(True, True)
        popup.grab_set()
        popup.columnconfigure(0, weight=1)
        popup.rowconfigure(1, weight=1)

        h = min(40 * len(unique_vals) + 130, 400) + (34 if is_date else 0)
        _f = tkfont.Font(size=11)
        max_text_w = max((_f.measure(v if v else "(empty)") for v in unique_vals), default=0)
        popup_w = max(220, max_text_w + 80)
        popup.geometry(f"{popup_w}x{h}+{x_root}+{y_root}")
        popup.minsize(180, 150)

        quick = ctk.CTkFrame(popup, fg_color="transparent")
        quick.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        check_vars: dict[str, tk.IntVar] = {}

        ctk.CTkButton(quick, text="All", width=70, height=26,
                      font=ctk.CTkFont(size=11),
                      command=lambda: [v.set(1) for v in check_vars.values()]
                      ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(quick, text="None", width=70, height=26,
                      font=ctk.CTkFont(size=11),
                      command=lambda: [v.set(0) for v in check_vars.values()]
                      ).pack(side="left")

        scroll = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        if is_date:
            sort_desc = [True]  # default: newest → oldest

            def _rebuild_checkboxes():
                saved = {v: var.get() for v, var in check_vars.items()}
                for w in scroll.winfo_children():
                    w.destroy()
                check_vars.clear()
                for val in sorted(unique_vals, reverse=sort_desc[0]):
                    checked = saved.get(val, 1 if (not current or val in current) else 0)
                    var = tk.IntVar(value=checked)
                    check_vars[val] = var
                    ctk.CTkCheckBox(scroll, text=val if val else "(empty)",
                                    variable=var,
                                    font=ctk.CTkFont(size=11)).pack(anchor="w", pady=1)

            def _toggle_sort():
                sort_desc[0] = not sort_desc[0]
                sort_btn.configure(text="↓ Newest" if sort_desc[0] else "↑ Oldest")
                _rebuild_checkboxes()

            sort_btn = ctk.CTkButton(quick, text="↓ Newest", width=72, height=26,
                                     font=ctk.CTkFont(size=11),
                                     fg_color="transparent", border_width=1,
                                     text_color=["#1A1A1A", "#DCE4EE"],
                                     command=_toggle_sort)
            sort_btn.pack(side="left", padx=(4, 0))
            _rebuild_checkboxes()
        else:
            for val in unique_vals:
                checked = 1 if (not current or val in current) else 0
                var = tk.IntVar(value=checked)
                check_vars[val] = var
                ctk.CTkCheckBox(scroll, text=val if val else "(empty)",
                                variable=var,
                                font=ctk.CTkFont(size=11)).pack(anchor="w", pady=1)

        btn_row = ctk.CTkFrame(popup, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 8))

        def _apply():
            selected = {v for v, var in check_vars.items() if var.get()}
            if selected == set(unique_vals):
                self._col_filters.pop(col, None)
            else:
                self._col_filters[col] = selected
            self._update_heading(col)
            self._refresh_table()
            popup.destroy()

        ctk.CTkButton(btn_row, text="Apply", height=28, font=ctk.CTkFont(size=12),
                      command=_apply).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(btn_row, text="Cancel", height=28, font=ctk.CTkFont(size=12),
                      fg_color="transparent", border_width=1,
                      text_color=["#1A1A1A", "#DCE4EE"],
                      command=popup.destroy).pack(side="left", fill="x", expand=True)
        popup.bind("<Escape>", lambda e: popup.destroy())

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_run_select(self, _event) -> None:
        sel = self._table.selection()
        if sel and self._project:
            self._window.show_run(
                str(self._project.path),
                self._version_id,
                self._iter_id,
                int(sel[0]),
            )

    def _copy_base(self) -> None:
        val = self._base_var.get()
        if val and val != "—":
            self.clipboard_clear()
            self.clipboard_append(val)
            self._window.set_status("Filename base copied to clipboard.")

    def _on_new_run(self) -> None:
        if not all([self._project, self._version_id, self._iter_id]):
            return
        from app.gui.dialogs.new_run_dialog import NewRunDialog
        dlg = NewRunDialog(self._window)
        self._window.wait_window(dlg)
        if dlg.result is None:
            return

        created_by, comments = dlg.result
        try:
            run = self._project.add_run(
                self._version_id, self._iter_id,
                created_by, comments,
            )
        except Exception as exc:
            self._show_error("Create Run Failed", str(exc))
            return

        v = self._project._get_version(self._version_id)
        i = self._project._get_iteration(v, self._iter_id)
        self._populate_table(i)
        self._window.refresh_sidebar()
        self._window.set_status(
            f"Run {run.id:02d} registered — filename: {run.name}")

    def _on_edit_iteration(self) -> None:
        if not all([self._project, self._version_id, self._iter_id]):
            return
        from app.gui.dialogs.edit_iteration_dialog import EditIterationDialog
        v = self._project._get_version(self._version_id)
        i = self._project._get_iteration(v, self._iter_id)
        has_runs = len(i.runs) > 0
        dlg = EditIterationDialog(self._window, i, has_runs)
        self._window.wait_window(dlg)
        if dlg.result is None:
            return
        solver_type, analysis_types, description, created_by = dlg.result
        try:
            self._project.update_iteration_metadata(
                self._version_id, self._iter_id,
                solver_type, analysis_types, description, created_by,
            )
        except Exception as exc:
            self._show_error("Edit Iteration Failed", str(exc))
            return
        self.load(self._project, self._version_id, self._iter_id)
        self._window.refresh_sidebar()
        self._window.set_status(f"Iteration {self._iter_id} metadata updated.")

    def _open_models_folder(self) -> None:
        if not self._project:
            return
        folder = self._project.path / MODELS_FOLDER
        if not folder.is_dir():
            self._window.set_status(f"Folder not found: {folder}")
            return
        try:
            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])
        except Exception:
            self._window.set_status(f"Could not open folder: {folder}")

    # ------------------------------------------------------------------
    def _resize_columns(self, event=None) -> None:
        width = self._section.winfo_width()
        if width <= 1 or width == getattr(self, "_last_col_width", 0):
            return
        self._last_col_width = width
        available = max(width - 18, 100)   # 18 px for vertical scrollbar
        total = sum(_COL_WEIGHTS.values())
        for col, w in _COL_WEIGHTS.items():
            self._table.column(col, width=max(20, int(available * w / total)))

    def _on_appearance_change(self, _mode: str) -> None:
        apply_table_style("Iter.Treeview")

    def _show_error(self, title: str, message: str) -> None:
        from tkinter import messagebox
        messagebox.showerror(title, message, parent=self._window)
