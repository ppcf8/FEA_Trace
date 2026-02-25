"""
dialogs/edit_version_dialog.py
"""

from __future__ import annotations

import customtkinter as ctk

from schema import VersionRecord

_REVERT_PREFIX = "[REVERTED"


class EditVersionDialog(ctk.CTkToplevel):
    """
    Pre-filled edit dialog for an existing VersionRecord.

    Notes are split into user notes (editable) and system/revert notes
    (read-only audit entries prefixed with "[REVERTED").  On save, system
    notes are always preserved unchanged and appended after user notes.

    result: (intent: str, notes: list[str], created_by: str) | None
    """

    def __init__(self, parent, version: VersionRecord):
        super().__init__(parent)
        self.title("Edit Version")
        self.resizable(False, False)
        self.grab_set()

        self.result = None
        self._version = version

        # Separate editable user notes from immutable system/revert entries
        self._user_notes   = [n for n in version.notes
                               if not n.startswith(_REVERT_PREFIX)]
        self._system_notes = [n for n in version.notes
                               if n.startswith(_REVERT_PREFIX)]

        height = 440 + (110 if self._system_notes else 0)
        self.geometry(f"520x{height}")

        self._build()
        self._prefill()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Edit Version",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, sticky="ew", padx=24)
        form.columnconfigure(1, weight=1)

        # Intent
        ctk.CTkLabel(
            form, text="Intent *",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=0, column=0, padx=(0, 12), pady=(0, 6), sticky="nw")

        self._intent_box = ctk.CTkTextbox(form, height=80, wrap="word")
        self._intent_box.grid(row=0, column=1, pady=(0, 6), sticky="ew")

        # Notes (user-editable)
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

        # Revert audit log (read-only) — only shown when entries exist
        if self._system_notes:
            ctk.CTkLabel(
                form, text="Revert Log",
                font=ctk.CTkFont(size=12), anchor="nw",
                text_color="gray",
            ).grid(row=4, column=0, padx=(0, 12), pady=(6, 6), sticky="nw")

            self._revert_box = ctk.CTkTextbox(form, height=70, wrap="word")
            self._revert_box.grid(row=4, column=1, pady=(6, 6), sticky="ew")

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

    def _prefill(self) -> None:
        v = self._version
        self._intent_box.insert("1.0", v.intent)
        if self._user_notes:
            self._notes_box.insert("1.0", "\n".join(self._user_notes))
        self._created_by_var.set(v.created_by)

        if self._system_notes:
            self._revert_box.insert("1.0", "\n".join(self._system_notes))
            self._revert_box.configure(state="disabled")

    def _on_confirm(self) -> None:
        intent     = self._intent_box.get("1.0", "end").strip()
        notes_raw  = self._notes_box.get("1.0", "end").strip()
        created_by = self._created_by_var.get().strip()

        if not intent:
            self._error_label.configure(text="Intent is required.")
            return
        if not created_by:
            self._error_label.configure(text="Created By is required.")
            return

        user_notes = [n.strip() for n in notes_raw.splitlines() if n.strip()]
        # System notes are always appended unchanged after user notes
        all_notes = user_notes + self._system_notes
        self.result = (intent, all_notes, created_by)
        self.destroy()
