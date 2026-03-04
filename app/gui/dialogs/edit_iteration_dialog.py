"""
dialogs/edit_iteration_dialog.py
"""

from __future__ import annotations

import tkinter.ttk as ttk
import customtkinter as ctk

from schema import SolverType, IterationRecord
from app.core.settings import get_settings_manager
from app.gui.theme import (apply_table_style, make_scrollbar,
                           AUDIT_NOTE_PREFIXES, parse_audit_note)

_SYSTEM_NOTE_PREFIXES = AUDIT_NOTE_PREFIXES


class EditIterationDialog(ctk.CTkToplevel):
    """
    Pre-filled edit dialog for an existing IterationRecord.

    result: (solver_type: SolverType, analysis_types: list[str],
             description: str, created_by: str) | None
    """

    def __init__(self, parent, iteration: IterationRecord, has_runs: bool):
        super().__init__(parent)
        self.title("Edit Iteration")
        self.resizable(True, True)
        self.grab_set()

        self.result = None
        self._iteration = iteration
        self._has_runs  = has_runs
        self._analysis_vars: dict[str, ctk.BooleanVar] = {}

        self._system_notes = [n for n in iteration.notes
                               if any(n.startswith(p) for p in _SYSTEM_NOTE_PREFIXES)]

        n_audit_rows = min(len(self._system_notes), 3)
        audit_h = (25 + n_audit_rows * 28 + 30) if self._system_notes else 0
        height = 560 + audit_h
        self.geometry(f"540x{height}")
        self.minsize(540, height)

        self._build()
        self._prefill()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="Edit Iteration",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, sticky="nsew", padx=24)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(2, weight=1)

        # Solver type
        ctk.CTkLabel(
            form, text="Solver Type *",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=0, column=0, padx=(0, 12), pady=8, sticky="w")

        solver_col = ctk.CTkFrame(form, fg_color="transparent")
        solver_col.grid(row=0, column=1, pady=8, sticky="w")

        self._solver_var = ctk.StringVar(value="IMPLICIT")
        self._solver_btn = ctk.CTkSegmentedButton(
            solver_col,
            values=["IMPLICIT", "EXPLICIT", "MBD"],
            variable=self._solver_var,
            width=280,
        )
        self._solver_btn.pack(anchor="w")

        if self._has_runs:
            self._solver_btn.configure(state="disabled")
            ctk.CTkLabel(
                solver_col,
                text="Solver type cannot be changed once runs exist.",
                font=ctk.CTkFont(size=11),
                text_color="gray", anchor="w",
            ).pack(anchor="w", pady=(2, 0))

        # Analysis types
        ctk.CTkLabel(
            form, text="Analysis Types *",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=1, column=0, padx=(0, 12), pady=(8, 0), sticky="nw")

        checks = ctk.CTkFrame(form, fg_color="transparent")
        checks.grid(row=1, column=1, pady=(8, 0), sticky="w")

        preset_types = get_settings_manager().get_analysis_types()
        extra = [t for t in self._iteration.analysis_types if t not in preset_types]
        analysis_options = preset_types + extra
        for idx, atype in enumerate(analysis_options):
            var = ctk.BooleanVar()
            self._analysis_vars[atype] = var
            ctk.CTkCheckBox(
                checks, text=atype, variable=var,
                font=ctk.CTkFont(size=12),
            ).grid(row=idx // 2, column=idx % 2,
                   padx=(0, 20), pady=2, sticky="w")

        # Description
        ctk.CTkLabel(
            form, text="Description *",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=2, column=0, padx=(0, 12), pady=(10, 6), sticky="nw")

        self._desc_box = ctk.CTkTextbox(form, height=60, wrap="word")
        self._desc_box.grid(row=2, column=1, pady=(10, 6), sticky="nsew")

        # Created By
        ctk.CTkLabel(
            form, text="Created By *",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=3, column=0, padx=(0, 12), pady=6, sticky="w")

        self._created_by_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self._created_by_var,
                     width=200).grid(row=3, column=1, pady=6, sticky="w")

        # Audit log (read-only table) — only shown when entries exist
        if self._system_notes:
            ctk.CTkLabel(
                form, text="Log",
                font=ctk.CTkFont(size=12), anchor="nw",
                text_color="gray",
            ).grid(row=4, column=0, padx=(0, 12), pady=(6, 4), sticky="nw")

            apply_table_style("Audit.Treeview")
            audit_wrap = ctk.CTkFrame(form, fg_color="transparent")
            audit_wrap.grid(row=4, column=1, pady=(6, 4), sticky="ew")
            audit_wrap.columnconfigure(0, weight=1)

            self._audit_tree = ttk.Treeview(
                audit_wrap, style="Audit.Treeview",
                columns=("event", "date", "by", "details"),
                show="headings", height=5,
            )
            self._audit_tree.heading("event",   text="Event",   anchor="center")
            self._audit_tree.heading("date",    text="Date",    anchor="w")
            self._audit_tree.heading("by",      text="By",      anchor="w")
            self._audit_tree.heading("details", text="Details", anchor="w")
            self._audit_tree.column("event",   width=160, minwidth=100, stretch=False, anchor="center")
            self._audit_tree.column("date",    width=135, minwidth=100, stretch=False, anchor="w")
            self._audit_tree.column("by",      width=75,  minwidth=50,  stretch=False, anchor="w")
            self._audit_tree.column("details", width=150, minwidth=80,  stretch=True,  anchor="w")
            self._audit_tree.grid(row=0, column=0, sticky="ew")

            sb = make_scrollbar(audit_wrap, "vertical", self._audit_tree.yview)
            self._audit_tree.configure(yscrollcommand=sb.set)
            sb.grid(row=0, column=1, sticky="ns")

        # Error label
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#E05555",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self._error_label.grid(row=2, column=0, padx=24, pady=(8, 0), sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=24, pady=16, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Save", width=100,
            command=self._on_confirm,
        ).pack(side="left")

    def _prefill(self) -> None:
        i = self._iteration
        self._solver_var.set(i.solver_type.value)
        for atype, var in self._analysis_vars.items():
            var.set(atype in i.analysis_types)
        self._desc_box.insert("1.0", i.description)
        self._created_by_var.set(i.created_by)

        if self._system_notes:
            for note in reversed(self._system_notes):
                ev, dt, by, details = parse_audit_note(note)
                self._audit_tree.insert("", "end", values=(ev, dt, by, details))

    def _on_confirm(self) -> None:
        solver_str  = self._solver_var.get()
        analysis    = [k for k, v in self._analysis_vars.items() if v.get()]
        description = self._desc_box.get("1.0", "end").strip()
        created_by  = self._created_by_var.get().strip()

        if not analysis:
            self._error_label.configure(
                text="Select at least one analysis type.")
            return
        if not description:
            self._error_label.configure(text="Description is required.")
            return
        if not created_by:
            self._error_label.configure(text="Created By is required.")
            return

        self.result = (SolverType(solver_str), analysis, description, created_by)
        self.destroy()
