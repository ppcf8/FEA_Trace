"""
dialogs/edit_entity_dialog.py
"""

from __future__ import annotations

import os
import customtkinter as ctk

from schema import EntityRecord


class EditEntityDialog(ctk.CTkToplevel):
    """
    Pre-filled edit dialog for an existing EntityRecord.

    result: (name, project, owner_team, created_by) | None
    """

    def __init__(self, parent, entity: EntityRecord):
        super().__init__(parent)
        self.title("Edit Entity")
        self.geometry("520x360")
        self.resizable(False, False)
        self.grab_set()

        self.result = None
        self._entity = entity
        self._build()
        self._prefill()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Edit Entity",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=24)
        form.columnconfigure(1, weight=1)

        # Read-only Entity ID row
        ctk.CTkLabel(
            form, text="Entity ID",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=0, column=0, padx=(0, 12), pady=6, sticky="w")

        self._id_label = ctk.CTkLabel(
            form, text="—",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        )
        self._id_label.grid(row=0, column=1, pady=6, sticky="w")

        fields = [
            ("Entity Name *",  "_name_var"),
            ("Project Code *", "_project_var"),
            ("Owner Team *",   "_owner_var"),
            ("Created By *",   "_created_by_var"),
        ]

        self._vars: dict[str, ctk.StringVar] = {}
        for row_i, (label, attr) in enumerate(fields, start=1):
            ctk.CTkLabel(
                form, text=label,
                font=ctk.CTkFont(size=12), anchor="w",
            ).grid(row=row_i, column=0, padx=(0, 12), pady=6, sticky="w")

            var = ctk.StringVar()
            self._vars[attr] = var
            setattr(self, attr, var)
            ctk.CTkEntry(form, textvariable=var, width=280).grid(
                row=row_i, column=1, pady=6, sticky="ew")

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
            btn_frame, text="Save", width=100,
            command=self._on_confirm,
        ).pack(side="left")

    def _prefill(self) -> None:
        e = self._entity
        self._id_label.configure(text=e.id)
        self._name_var.set(e.name)
        self._project_var.set(e.project)
        self._owner_var.set(e.owner_team)
        self._created_by_var.set(e.created_by)

    def _on_confirm(self) -> None:
        name       = self._name_var.get().strip()
        project    = self._project_var.get().strip().upper()
        owner      = self._owner_var.get().strip()
        created_by = self._created_by_var.get().strip()

        missing = [label for label, val in [
            ("Entity Name",  name),
            ("Project Code", project),
            ("Owner Team",   owner),
            ("Created By",   created_by),
        ] if not val]

        if missing:
            self._error_label.configure(
                text=f"Required: {', '.join(missing)}")
            return

        self.result = (name, project, owner, created_by)
        self.destroy()
