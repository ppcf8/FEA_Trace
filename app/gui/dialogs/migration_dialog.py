"""
dialogs/migration_dialog.py
"""
from __future__ import annotations

import customtkinter as ctk  # FIX: was missing entirely

from app.core.migration import MIGRATIONS, _migration_chain


class MigrationDialog(ctk.CTkToplevel):
    """
    Parameters
    ----------
    parent   : MainWindow
    raw      : raw YAML dict from the log file
    tool_ver : current tool schema version string

    Attributes
    ----------
    confirmed : bool — True if the user accepted the migration.
    """

    def __init__(self, parent, raw: dict, tool_ver: str):
        super().__init__(parent)
        self.title("Schema Migration Required")
        self.geometry("560x400")
        self.resizable(False, False)
        self.grab_set()

        self.confirmed = False
        self._raw      = raw
        self._tool_ver = tool_ver
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self,
            text="⚠   Major Schema Migration Required",
            font=ctk.CTkFont(size=17, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        log_ver = self._raw.get("schema_version", "0.0.0")
        ctk.CTkLabel(
            self,
            text=(
                f"This log was written with schema version {log_ver}.\n"
                f"The current tool requires schema version {self._tool_ver}.\n\n"
                "The following changes will be applied to the log file:"
            ),
            font=ctk.CTkFont(size=12),
            justify="left",
        ).grid(row=1, column=0, padx=24, pady=(0, 12), sticky="w")

        chain = _migration_chain(log_ver, self._tool_ver)
        changes_text = ""
        for step in chain:
            _, description, is_major = MIGRATIONS[step]
            prefix = "MAJOR" if is_major else "MINOR"
            changes_text += f"  [{prefix}]  {description}\n"

        changes_box = ctk.CTkTextbox(
            self, height=120, wrap="word",
            font=ctk.CTkFont(size=12, family="Courier New"),
            state="normal",
        )
        changes_box.grid(row=2, column=0, padx=24, sticky="ew")
        changes_box.insert("1.0", changes_text.strip() or "No details available.")
        changes_box.configure(state="disabled")

        backup_name = f"version_log_{log_ver.replace('.', '_')}.yaml"
        ctk.CTkLabel(
            self,
            text=(
                f"A backup of the original log will be saved as:\n"
                f"  {backup_name}\n"
                "in the same folder before any changes are made."
            ),
            font=ctk.CTkFont(size=12),
            justify="left",
        ).grid(row=3, column=0, padx=24, pady=(12, 0), sticky="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=24, pady=20, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame,
            text="Migrate Log",
            width=120,
            fg_color="#C0392B",
            command=self._on_confirm,
        ).pack(side="left")

    def _on_confirm(self) -> None:
        self.confirmed = True
        self.destroy()