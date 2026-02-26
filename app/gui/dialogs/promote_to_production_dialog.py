"""
dialogs/promote_to_production_dialog.py — Promote Version to Production Dialog
"""
from __future__ import annotations

import tkinter as tk
import customtkinter as ctk
from typing import Optional

from app.core.models import FEAProject


class PromoteToProductionDialog(ctk.CTkToplevel):
    """Dialog to select which runs support a production release.

    self.result is list[tuple[str, int]] | None.
    Each tuple is (iter_id, run_id).
    """

    def __init__(self, master, project: FEAProject, version_id: str):
        super().__init__(master)
        self.result: Optional[list] = None
        self._project    = project
        self._version_id = version_id
        self._checks: dict[tuple, ctk.BooleanVar] = {}

        v = project._get_version(version_id)
        self.title(f"Promote {version_id} to Production")
        self.resizable(True, True)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build(v)
        self._center()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, v) -> None:
        # Row 0 — title
        ctk.CTkLabel(
            self,
            text=f"Promote {self._version_id} to Production",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, padx=24, pady=(20, 4), sticky="ew")

        # Row 1 — subtitle
        ctk.CTkLabel(
            self,
            text="Select the runs that support this production release.",
            font=ctk.CTkFont(size=12),
            anchor="w",
            text_color=["#555555", "#AAAAAA"],
        ).grid(row=1, column=0, padx=24, pady=(0, 12), sticky="ew")

        # Row 2 — scrollable run list
        scroll = ctk.CTkScrollableFrame(self, height=240)
        scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 8))
        scroll.columnconfigure(0, weight=1)

        has_runs = False
        for i in v.iterations:
            if not i.runs:
                continue
            has_runs = True
            # Iteration header
            ctk.CTkLabel(
                scroll,
                text=f"{i.id}  ·  {i.solver_type.value}",
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w",
            ).pack(anchor="w", padx=(8, 0), pady=(8, 2))

            for run in i.runs:
                key = (i.id, run.id)
                var = ctk.BooleanVar(value=run.artifacts.is_production)
                self._checks[key] = var
                date_only = run.date.split(" ")[0]

                row_frame = ctk.CTkFrame(scroll, fg_color="transparent")
                row_frame.pack(anchor="w", padx=(24, 0), pady=2)

                ctk.CTkCheckBox(
                    row_frame, text="", variable=var, width=24,
                ).grid(row=0, column=0, padx=(0, 8))
                ctk.CTkLabel(
                    row_frame, text=f"Run {run.id:02d}",
                    font=ctk.CTkFont(size=12), width=52, anchor="w",
                ).grid(row=0, column=1)
                ctk.CTkLabel(
                    row_frame, text="·",
                    font=ctk.CTkFont(size=12),
                ).grid(row=0, column=2, padx=8)
                ctk.CTkLabel(
                    row_frame, text=run.status.value,
                    font=ctk.CTkFont(size=12), width=72, anchor="w",
                ).grid(row=0, column=3)
                ctk.CTkLabel(
                    row_frame, text="·",
                    font=ctk.CTkFont(size=12),
                ).grid(row=0, column=4, padx=8)
                ctk.CTkLabel(
                    row_frame, text=date_only,
                    font=ctk.CTkFont(size=12), anchor="w",
                ).grid(row=0, column=5)

        if not has_runs:
            ctk.CTkLabel(
                scroll,
                text="No runs found in this version.",
                font=ctk.CTkFont(size=12),
                text_color=["#888888", "#888888"],
                anchor="w",
            ).pack(anchor="w", padx=8, pady=8)

        # Row 3 — Select All / Clear All
        sel_row = ctk.CTkFrame(self, fg_color="transparent")
        sel_row.grid(row=3, column=0, sticky="w", padx=20, pady=(0, 4))
        ctk.CTkButton(
            sel_row, text="Select All",
            width=80, height=26,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=lambda: [v.set(True) for v in self._checks.values()],
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            sel_row, text="Clear All",
            width=80, height=26,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=lambda: [v.set(False) for v in self._checks.values()],
        ).pack(side="left")

        # Row 4 — error label (hidden initially)
        self._error_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=11),
            text_color="#E05555", anchor="w",
        )
        self._error_label.grid(row=4, column=0, padx=24, pady=(0, 4), sticky="ew")

        # Row 5 — Cancel / Promote buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=5, column=0, sticky="ew", padx=16, pady=(4, 20))

        ctk.CTkButton(
            btn_row, text="Cancel",
            width=100, height=34,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            btn_row, text="Promote",
            width=100, height=34,
            font=ctk.CTkFont(size=13),
            fg_color="#2D8A4E",
            command=self._on_confirm,
        ).pack(side="right")

        self.bind("<Escape>", lambda _: self.destroy())

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_confirm(self) -> None:
        self.result = [
            key for key, var in self._checks.items() if var.get()
        ]
        self.destroy()

    def _center(self) -> None:
        self.minsize(380, 300)
        self.update_idletasks()
        w, h   = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"+{x}+{y}")
