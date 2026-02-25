"""
dialogs/new_version_dialog.py
"""

from __future__ import annotations

import os
import customtkinter as ctk
from app.gui.hints import NEW_VERSION_SUBTITLE


class NewVersionDialog(ctk.CTkToplevel):
    """
    result: (description: str, notes: list[str], created_by: str) | None
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("New Version")
        self.geometry("520x440")
        self.resizable(False, False)
        self.grab_set()

        self.result = None
        self._build()
        try:
            self._created_by_var.set(os.getlogin())
        except OSError:
            self._created_by_var.set(os.environ.get("USERNAME", ""))

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="New Version",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 4), sticky="w")

        ctk.CTkLabel(
            self,
            text=NEW_VERSION_SUBTITLE,
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w",
            wraplength=472,
        ).grid(row=1, column=0, padx=24, pady=(0, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=24)
        form.columnconfigure(1, weight=1)

        # Description
        ctk.CTkLabel(
            form, text="Description *",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=0, column=0, padx=(0, 12), pady=(0, 6), sticky="nw")

        self._description_box = ctk.CTkTextbox(form, height=80, wrap="word")
        self._description_box.grid(row=0, column=1, pady=(0, 6), sticky="ew")

        # Notes (optional, one per line)
        ctk.CTkLabel(
            form, text="Notes",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=1, column=0, padx=(0, 12), pady=(6, 6), sticky="nw")

        self._notes_box = ctk.CTkTextbox(form, height=60, wrap="word")
        self._notes_box.grid(row=1, column=1, pady=(6, 6), sticky="ew")

        ctk.CTkLabel(
            form, text="One note per line.",
            font=ctk.CTkFont(size=11),
            text_color="gray", anchor="w",
        ).grid(row=2, column=1, sticky="w", pady=(0, 6))

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
        btn_frame.grid(row=4, column=0, padx=24, pady=20, sticky="e")

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
        description = self._description_box.get("1.0", "end").strip()
        notes_raw   = self._notes_box.get("1.0", "end").strip()
        created_by  = self._created_by_var.get().strip()

        if not description:
            self._error_label.configure(text="Description is required.")
            return
        if not created_by:
            self._error_label.configure(text="Created By is required.")
            return

        notes = [n.strip() for n in notes_raw.splitlines() if n.strip()]
        self.result = (description, notes, created_by)
        self.destroy()