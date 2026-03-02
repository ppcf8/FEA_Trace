"""
dialogs/edit_version_dialog.py
"""

from __future__ import annotations

import re
import tkinter.ttk as ttk
import customtkinter as ctk

from schema import VersionRecord
from app.gui.theme import apply_table_style, make_scrollbar

_SYSTEM_NOTE_PREFIXES = ("[Reverted", "[Promoted", "[REVERTED")


def _parse_audit_note(note: str) -> tuple[str, str, str, str]:
    """Parse a system audit note into (event, date, by, details)."""
    m = re.match(r'\[Promoted to Production\] on (.+?) by (.+?) — Runs: (.+)', note)
    if m:
        return "Promoted", m.group(1), m.group(2), m.group(3)
    m = re.match(r'\[Reverted to WIP\] from (\S+) on (.+?) by (.+?) — (.+)', note)
    if m:
        return "Reverted", m.group(2), m.group(3), f"from {m.group(1)} — {m.group(4)}"
    m = re.match(r'\[REVERTED to WIP from (\S+) by (.+?) on (.+?)\] (.+)', note)
    if m:
        return "Reverted", m.group(3), m.group(2), f"from {m.group(1)} — {m.group(4)}"
    return "System", "", "", note


class EditVersionDialog(ctk.CTkToplevel):
    """
    Pre-filled edit dialog for an existing VersionRecord.

    Notes are split into user notes (editable) and system audit notes
    (read-only entries prefixed with "[Reverted", "[Promoted", or legacy "[REVERTED").
    On save, system notes are always preserved unchanged and appended after user notes.

    result: (description: str, notes: list[str], created_by: str) | None
    """

    def __init__(self, parent, version: VersionRecord):
        super().__init__(parent)
        self.title("Edit Version")
        self.resizable(True, True)
        self.grab_set()

        self.result = None
        self._version = version

        # Separate editable user notes from immutable system audit entries
        self._user_notes   = [n for n in version.notes
                               if not any(n.startswith(p) for p in _SYSTEM_NOTE_PREFIXES)]
        self._system_notes = [n for n in version.notes
                               if any(n.startswith(p) for p in _SYSTEM_NOTE_PREFIXES)]

        n_audit_rows = min(len(self._system_notes), 3)
        audit_h = (25 + n_audit_rows * 28 + 30) if self._system_notes else 0  # heading + rows + label/padding
        height = 440 + audit_h
        self.geometry(f"520x{height}")
        self.minsize(520, height)

        self._build()
        self._prefill()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self, text="Edit Version",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, sticky="nsew", padx=24)
        form.columnconfigure(1, weight=1)
        form.rowconfigure(0, weight=1)
        form.rowconfigure(1, weight=1)

        # Description
        ctk.CTkLabel(
            form, text="Description *",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=0, column=0, padx=(0, 12), pady=(0, 6), sticky="nw")

        self._description_box = ctk.CTkTextbox(form, height=80, wrap="word")
        self._description_box.grid(row=0, column=1, pady=(0, 6), sticky="nsew")

        # Notes (user-editable)
        ctk.CTkLabel(
            form, text="Notes",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=1, column=0, padx=(0, 12), pady=(6, 6), sticky="nw")

        self._notes_box = ctk.CTkTextbox(form, height=60, wrap="word")
        self._notes_box.grid(row=1, column=1, pady=(6, 6), sticky="nsew")

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

        # Audit log (read-only table) — only shown when entries exist
        if self._system_notes:
            ctk.CTkLabel(
                form, text="Audit Log",
                font=ctk.CTkFont(size=12), anchor="nw",
                text_color="gray",
            ).grid(row=4, column=0, padx=(0, 12), pady=(6, 4), sticky="nw")

            apply_table_style("Audit.Treeview")
            audit_wrap = ctk.CTkFrame(form, fg_color="transparent")
            audit_wrap.grid(row=4, column=1, pady=(6, 4), sticky="ew")
            audit_wrap.columnconfigure(0, weight=1)

            n_rows = min(len(self._system_notes), 3)
            self._audit_tree = ttk.Treeview(
                audit_wrap, style="Audit.Treeview",
                columns=("event", "date", "by", "details"),
                show="headings", height=n_rows,
            )
            self._audit_tree.heading("event",   text="Event",   anchor="w")
            self._audit_tree.heading("date",    text="Date",    anchor="w")
            self._audit_tree.heading("by",      text="By",      anchor="w")
            self._audit_tree.heading("details", text="Details", anchor="w")
            self._audit_tree.column("event",   width=80,  minwidth=60,  stretch=False, anchor="w")
            self._audit_tree.column("date",    width=135, minwidth=100, stretch=False, anchor="w")
            self._audit_tree.column("by",      width=75,  minwidth=50,  stretch=False, anchor="w")
            self._audit_tree.column("details", width=150, minwidth=80,  stretch=True,  anchor="w")
            self._audit_tree.grid(row=0, column=0, sticky="ew")

            if len(self._system_notes) > 3:
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
        self._description_box.insert("1.0", v.description)
        if self._user_notes:
            self._notes_box.insert("1.0", "\n".join(self._user_notes))
        self._created_by_var.set(v.created_by)

        if self._system_notes:
            for note in reversed(self._system_notes):
                ev, dt, by, details = _parse_audit_note(note)
                self._audit_tree.insert("", "end", values=(ev, dt, by, details))

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

        user_notes = [n.strip() for n in notes_raw.splitlines() if n.strip()]
        # System notes are always appended unchanged after user notes
        all_notes = user_notes + self._system_notes
        self.result = (description, all_notes, created_by)
        self.destroy()
