"""
dialogs/new_entity_dialog.py
"""

from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog
import customtkinter as ctk

from schema import generate_entity_id


class NewEntityDialog(ctk.CTkToplevel):
    """
    Collects the information needed to create a new entity folder.

    result  : Path | None  — resolved entity folder path on confirm.
    params  : tuple | None — (parent_dir, name, project, owner_team, created_by)
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("New Entity")
        self.geometry("520x480")
        self.resizable(False, False)
        self.grab_set()

        self.result: Path | None  = None
        self.params: tuple | None = None

        self._build()
        try:
            self._created_by_var.set(os.getlogin())
        except OSError:
            self._created_by_var.set(os.environ.get("USERNAME", ""))

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="New Entity",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=24)
        form.columnconfigure(1, weight=1)

        fields = [
            ("Entity Name *",  "_name"),
            ("Project Code *", "_project"),
            ("Owner Team *",   "_owner"),
            ("Created By *",   "_created_by"),
        ]

        self._vars: dict[str, ctk.StringVar] = {}
        for row_i, (label, key) in enumerate(fields):
            ctk.CTkLabel(
                form, text=label,
                font=ctk.CTkFont(size=12), anchor="w",
            ).grid(row=row_i, column=0, padx=(0, 12), pady=6, sticky="w")

            var = ctk.StringVar()
            self._vars[key] = var
            ctk.CTkEntry(form, textvariable=var, width=280).grid(
                row=row_i, column=1, pady=6, sticky="ew")

        self._name_var       = self._vars["_name"]
        self._project_var    = self._vars["_project"]
        self._owner_var      = self._vars["_owner"]
        self._created_by_var = self._vars["_created_by"]

        # Entity ID preview
        ctk.CTkLabel(
            form, text="Entity ID Preview",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=len(fields), column=0, padx=(0, 12), pady=6, sticky="w")

        self._id_preview = ctk.CTkLabel(
            form, text="—",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        )
        self._id_preview.grid(row=len(fields), column=1, pady=6, sticky="w")
        self._name_var.trace_add("write", self._update_id_preview)

        # Parent directory
        ctk.CTkLabel(
            form, text="Parent Directory *",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=len(fields) + 1, column=0, padx=(0, 12), pady=6, sticky="w")

        dir_row = ctk.CTkFrame(form, fg_color="transparent")
        dir_row.grid(row=len(fields) + 1, column=1, pady=6, sticky="ew")
        dir_row.columnconfigure(0, weight=1)

        self._dir_var = ctk.StringVar()
        ctk.CTkEntry(dir_row, textvariable=self._dir_var,
                     state="readonly").grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(
            dir_row, text="Browse", width=72,
            command=self._browse_dir,
        ).grid(row=0, column=1, padx=(6, 0))

        # Error label
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#E05555",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self._error_label.grid(row=2, column=0, padx=24, pady=(8, 0), sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=3, column=0, padx=24, pady=20, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Create", width=100,
            command=self._on_confirm,
        ).pack(side="left")

    def _update_id_preview(self, *_) -> None:
        name = self._name_var.get().strip()
        self._id_preview.configure(
            text=generate_entity_id(name) if name else "—")

    def _browse_dir(self) -> None:
        path = filedialog.askdirectory(title="Select Parent Directory")
        if path:
            self._dir_var.set(path)

    def _on_confirm(self) -> None:
        name       = self._name_var.get().strip()
        project    = self._project_var.get().strip().upper()
        owner      = self._owner_var.get().strip()
        created_by = self._created_by_var.get().strip()
        parent_dir = self._dir_var.get().strip()

        missing = [label for label, val in [
            ("Entity Name",      name),
            ("Project Code",     project),
            ("Owner Team",       owner),
            ("Created By",       created_by),
            ("Parent Directory", parent_dir),
        ] if not val]

        if missing:
            self._error_label.configure(
                text=f"Required: {', '.join(missing)}")
            return

        self.params = (parent_dir, name, project, owner, created_by)
        self.result = Path(parent_dir) / f"{project}_{name.replace(' ', '_')}"
        self.destroy()