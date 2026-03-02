"""
dialogs/edit_entity_dialog.py
"""

from __future__ import annotations

import os
from tkinter import messagebox
import customtkinter as ctk

from schema import EntityRecord
from app.core.settings import get_settings_manager


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
            ("Project Code *", "_project_var"),
            ("Entity Name *",  "_name_var"),
            ("Owner Team *",   "_owner_var"),
            ("Created By *",   "_created_by_var"),
        ]

        self._vars: dict[str, ctk.StringVar] = {}
        self._project_combo: ctk.CTkComboBox | None = None
        self._name_combo:    ctk.CTkComboBox | None = None

        for row_i, (label, attr) in enumerate(fields, start=1):
            ctk.CTkLabel(
                form, text=label,
                font=ctk.CTkFont(size=12), anchor="w",
            ).grid(row=row_i, column=0, padx=(0, 12), pady=6, sticky="w")

            var = ctk.StringVar()
            self._vars[attr] = var
            setattr(self, attr, var)

            if attr in ("_project_var", "_name_var"):
                combo = ctk.CTkComboBox(form, variable=var, values=[], width=280)
                combo.grid(row=row_i, column=1, pady=6, sticky="ew")
                if attr == "_project_var":
                    self._project_combo = combo
                else:
                    self._name_combo = combo
            else:
                ctk.CTkEntry(form, textvariable=var, width=280).grid(
                    row=row_i, column=1, pady=6, sticky="ew")

        self._project_var.trace_add("write", self._on_project_changed)

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
            btn_frame, text="Save", width=100,
            command=self._on_confirm,
        ).pack(side="left")

    def _on_project_changed(self, *_) -> None:
        code = self._project_var.get().strip().upper()
        mgr = get_settings_manager()
        if self._project_combo is not None:
            self._project_combo.configure(values=mgr.project_codes())
        if self._name_combo is not None:
            self._name_combo.configure(values=mgr.entity_names_for(code))

    def _prefill(self) -> None:
        e = self._entity
        self._id_label.configure(text=e.id)
        self._name_var.set(e.name)
        self._project_var.set(e.project)
        self._owner_var.set(e.owner_team)
        self._created_by_var.set(e.created_by)
        self._on_project_changed()

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

        # Offer to save new values to presets
        mgr = get_settings_manager()
        presets = mgr.settings.project_presets
        is_new_project = project not in presets
        is_new_name    = name not in [e["name"] for e in presets.get(project, [])]
        if is_new_project or is_new_name:
            new_items = []
            if is_new_project:
                new_items.append(f"Project code:  {project}")
            if is_new_name:
                new_items.append(f"Entity name:   {name}")
            msg = (
                "New value(s) entered:\n\n"
                + "\n".join(f"  \u2022 {i}" for i in new_items)
                + "\n\nSave to presets?"
            )
            if messagebox.askyesno("Save to Presets", msg, parent=self):
                mgr.add_preset_entry(project, name, self._entity.id)
                mgr.save()

        self.result = (name, project, owner, created_by)
        self.destroy()
