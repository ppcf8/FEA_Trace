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
    params  : tuple | None — (parent_dir, entity_id, name, project, owner_team, created_by)
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("New Entity")
        self.geometry("520x480")
        self.resizable(False, False)
        self.grab_set()

        self.result: Path | None  = None
        self.params: tuple | None = None

        self._id_modified  = False
        self._updating_id  = False

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

        # Project Code is first per user request
        fields = [
            ("Project Code *", "_project"),
            ("Entity Name *",  "_name"),
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

        self._project_var    = self._vars["_project"]
        self._name_var       = self._vars["_name"]
        self._owner_var      = self._vars["_owner"]
        self._created_by_var = self._vars["_created_by"]

        # Entity ID — editable, auto-filled from name
        ctk.CTkLabel(
            form, text="Entity ID *",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=len(fields), column=0, padx=(0, 12), pady=6, sticky="w")

        self._id_var = ctk.StringVar()
        self._id_entry = ctk.CTkEntry(form, textvariable=self._id_var, width=140)
        self._id_entry.grid(row=len(fields), column=1, pady=6, sticky="w")

        self._name_var.trace_add("write", self._update_id_from_name)
        self._id_var.trace_add("write",   self._on_id_changed)

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
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Create", width=100,
            command=self._on_confirm,
        ).pack(side="left")

    def _update_id_from_name(self, *_) -> None:
        if self._id_modified:
            return
        name = self._name_var.get().strip()
        self._updating_id = True
        self._id_var.set(generate_entity_id(name) if name else "")
        self._updating_id = False

    def _on_id_changed(self, *_) -> None:
        if not self._updating_id:
            self._id_modified = True

    def _browse_dir(self) -> None:
        path = filedialog.askdirectory(title="Select Parent Directory")
        if path:
            self._dir_var.set(path)

    def _on_confirm(self) -> None:
        project    = self._project_var.get().strip().upper()
        name       = self._name_var.get().strip()
        owner      = self._owner_var.get().strip()
        created_by = self._created_by_var.get().strip()
        entity_id  = self._id_var.get().strip().upper()
        parent_dir = self._dir_var.get().strip()

        missing = [label for label, val in [
            ("Project Code",     project),
            ("Entity Name",      name),
            ("Owner Team",       owner),
            ("Created By",       created_by),
            ("Entity ID",        entity_id),
            ("Parent Directory", parent_dir),
        ] if not val]

        if missing:
            self._error_label.configure(
                text=f"Required: {', '.join(missing)}")
            return

        self.params = (parent_dir, entity_id, name, project, owner, created_by)
        self.result = Path(parent_dir) / f"{project}_{name.replace(' ', '_')}"
        self.destroy()
