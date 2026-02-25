"""
dialogs/new_iteration_dialog.py
"""

from __future__ import annotations

import os
import customtkinter as ctk
from app.gui.hints import NEW_ITERATION_SUBTITLE

from schema import SolverType


class NewIterationDialog(ctk.CTkToplevel):
    """
    result: (solver_type: SolverType, analysis_types: list[str],
             description: str, created_by: str) | None
    """

    _ANALYSIS_OPTIONS = [
        "NLSTAT", "LINEAR", "NORMAL MODES", "BUCKLING",
        "FATIGUE", "FREQ RESPONSE", "TRANSIENT",
        "CRASH", "QUASI-STATIC", "TOPOLOGY OPT",
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self.title("New Iteration")
        self.geometry("540x560")
        self.resizable(False, False)
        self.grab_set()

        self.result = None
        self._analysis_vars: dict[str, ctk.BooleanVar] = {}
        self._build()
        try:
            self._created_by_var.set(os.getlogin())
        except OSError:
            self._created_by_var.set(os.environ.get("USERNAME", ""))

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="New Iteration",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 4), sticky="w")

        ctk.CTkLabel(
            self,
            text=NEW_ITERATION_SUBTITLE,
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w",
            wraplength=492,
        ).grid(row=1, column=0, padx=24, pady=(0, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=24)
        form.columnconfigure(1, weight=1)

        # Solver type
        ctk.CTkLabel(
            form, text="Solver Type *",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=0, column=0, padx=(0, 12), pady=8, sticky="w")

        self._solver_var = ctk.StringVar(value="IMPLICIT")
        ctk.CTkSegmentedButton(
            form,
            values=["IMPLICIT", "EXPLICIT", "MBD"],
            variable=self._solver_var,
            width=280,
        ).grid(row=0, column=1, pady=8, sticky="w")

        # Analysis types
        ctk.CTkLabel(
            form, text="Analysis Types *",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=1, column=0, padx=(0, 12), pady=(8, 0), sticky="nw")

        checks = ctk.CTkFrame(form, fg_color="transparent")
        checks.grid(row=1, column=1, pady=(8, 0), sticky="w")

        for idx, atype in enumerate(self._ANALYSIS_OPTIONS):
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
        self._desc_box.grid(row=2, column=1, pady=(10, 6), sticky="ew")

        # Created By
        ctk.CTkLabel(
            form, text="Created By *",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=3, column=0, padx=(0, 12), pady=6, sticky="w")

        self._created_by_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self._created_by_var,
                     width=200).grid(row=3, column=1, pady=6, sticky="w")

        # Error
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#E05555",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self._error_label.grid(row=3, column=0, padx=24, pady=(8, 0), sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=24, pady=16, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Create", width=100,
            command=self._on_confirm,
        ).pack(side="left")

    def _on_confirm(self) -> None:
        solver_str   = self._solver_var.get()
        analysis     = [k for k, v in self._analysis_vars.items() if v.get()]
        description  = self._desc_box.get("1.0", "end").strip()
        created_by   = self._created_by_var.get().strip()

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
