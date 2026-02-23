"""
iteration_frame.py — Iteration Detail View
===========================================
Displayed when an Iteration node is selected in the sidebar.
Shows iteration metadata (including solver type and analysis types),
design changes list, the auto-generated filename base, and the run
summary table. Provides the entry point for registering a new Run.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
import customtkinter as ctk
from typing import Optional

from app.core.models import FEAProject
from app.gui.theme import apply_table_style, make_scrollbar, STATUS_COLORS, SOLVER_COLORS


# ---------------------------------------------------------------------------
# Column weight map (proportional autofit)
# ---------------------------------------------------------------------------

_COL_WEIGHTS = {
    "id":         1,
    "name":       7,
    "status":     3,
    "date":       3,
    "created_by": 3,
    "production": 1,
    "comments":   6,
}  # total = 24 units


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
        self._window      = window
        self._project:    Optional[FEAProject] = None
        self._version_id: Optional[str]        = None
        self._iter_id:    Optional[str]        = None
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)   # run table expands

        self._build_header()
        self._build_metadata_panel()
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

        self._solver_label = ctk.CTkLabel(
            title_row, text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6, anchor="center", padx=12, pady=4,
        )
        self._solver_label.grid(row=0, column=1, sticky="e")

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
            text="Copy",
            width=60, height=28,
            font=ctk.CTkFont(size=12),
            command=self._copy_base,
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

        # Design changes
        ctk.CTkLabel(
            panel, text="Design Changes",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw", width=110,
        ).grid(row=2, column=0, padx=(16, 4), pady=(0, 6), sticky="nw")

        self._changes_label = ctk.CTkLabel(
            panel, text="—",
            font=ctk.CTkFont(size=12),
            anchor="nw", justify="left", wraplength=540,
        )
        self._changes_label.grid(row=2, column=1, columnspan=3,
                                 padx=(0, 16), pady=(0, 6), sticky="w")

        # Created by / on
        fields = [("Created By", "_created_by"), ("Created On", "_created_on")]
        self._meta: dict[str, ctk.CTkLabel] = {}
        for col_i, (label, key) in enumerate(fields):
            ctk.CTkLabel(
                panel, text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w", width=110,
            ).grid(row=3, column=col_i * 2,
                   padx=(16, 4), pady=(0, 12), sticky="w")
            val = ctk.CTkLabel(
                panel, text="—",
                font=ctk.CTkFont(size=12), anchor="w",
            )
            val.grid(row=3, column=col_i * 2 + 1,
                     padx=(0, 24), pady=(0, 12), sticky="w")
            self._meta[key] = val

    def _build_run_table(self) -> None:
        section = ctk.CTkFrame(self, fg_color="transparent")
        section.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 8))
        section.columnconfigure(0, weight=1)
        section.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            section, text="Runs",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

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
        for col, (heading, anchor) in headings.items():
            self._table.heading(col, text=heading, anchor=anchor)
            self._table.column(col, width=60, anchor=anchor, stretch=False)

        for status, color in STATUS_COLORS.items():
            self._table.tag_configure(f"status_{status}", foreground=color)

        vsb = make_scrollbar(section, "vertical",   self._table.yview)
        hsb = make_scrollbar(section, "horizontal", self._table.xview)
        self._table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._table.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")

        self._section = section
        self._table.bind("<<TreeviewSelect>>", self._on_run_select)
        section.bind("<Configure>", self._resize_columns)
        apply_table_style("Iter.Treeview")
        ctk.AppearanceModeTracker.add(self._on_appearance_change)

    def _build_action_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", padx=24, pady=(4, 20))

        ctk.CTkButton(
            bar,
            text="+ New Run",
            width=120, height=36,
            font=ctk.CTkFont(size=13),
            command=self._on_new_run,
        ).pack(side="left")

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

        if i.design_changes:
            self._changes_label.configure(
                text="\n".join(f"• {c}" for c in i.design_changes))
        else:
            self._changes_label.configure(text="—")

        self._meta["_created_by"].configure(text=i.created_by)
        self._meta["_created_on"].configure(text=i.created_on)

        self._populate_table(i)

    def _populate_table(self, i) -> None:
        for row in self._table.get_children():
            self._table.delete(row)

        for run in i.runs:
            status_text = f"●  {run.status.value}"
            tag = f"status_{run.status.value}"
            prod  = "★" if run.artifacts.is_production else ""
            comments_short = run.comments.replace("\n", " ")
            if len(comments_short) > 40:
                comments_short = comments_short[:37] + "…"

            self._table.insert("", "end", iid=str(run.id), tags=(tag,), values=(
                f"{run.id:02d}",
                run.name,
                status_text,
                run.date,
                run.created_by,
                prod,
                comments_short,
            ))

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
