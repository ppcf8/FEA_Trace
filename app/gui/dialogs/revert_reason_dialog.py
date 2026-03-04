"""
dialogs/revert_reason_dialog.py
=================================
Shown when a user attempts to revert a Version or Iteration status back to WIP
from DEPRECATED, or when deprecating a Version or Iteration (requires a reason).
The reason is automatically appended to the entity's notes list with a timestamp.
"""

from __future__ import annotations

import customtkinter as ctk


class RevertReasonDialog(ctk.CTkToplevel):
    """
    Parameters
    ----------
    parent      : MainWindow
    entity_id   : displayed in the dialog title for clarity
    entity_type : "Version" (default) or "Iteration"
    mode        : "revert" (default) — revert to WIP
                  "deprecate"        — mark as Deprecated

    Attributes
    ----------
    result : str | None  — the reason text, or None if cancelled
    """

    def __init__(self, parent, entity_id: str,
                 entity_type: str = "Version", mode: str = "revert"):
        super().__init__(parent)
        self.geometry("480x280")
        self.resizable(False, False)
        self.grab_set()

        self.result: str | None = None
        self._build(entity_id, entity_type, mode)

    def _build(self, entity_id: str, entity_type: str, mode: str) -> None:
        self.columnconfigure(0, weight=1)

        if mode == "deprecate":
            self.title(f"Deprecate {entity_id}")
            heading = f"Deprecate {entity_id}"
            desc = (
                f"This action will deprecate the {entity_type.lower()}.\n"
                "A mandatory reason must be provided — it will be\n"
                f"permanently appended to the {entity_type.lower()} notes."
            )
            confirm_text = "Mark Deprecated"
            confirm_color = "#888888"
        else:
            self.title(f"Revert {entity_id} to WIP")
            heading = f"Revert {entity_id} to WIP"
            desc = (
                f"This action will revert the {entity_type.lower()} status to WIP.\n"
                "A mandatory reason must be provided — it will be\n"
                f"permanently appended to the {entity_type.lower()} notes."
            )
            confirm_text = "Revert to WIP"
            confirm_color = "#4A90D9"

        ctk.CTkLabel(
            self,
            text=heading,
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        ctk.CTkLabel(
            self,
            text=desc,
            font=ctk.CTkFont(size=12),
            justify="left",
        ).grid(row=1, column=0, padx=24, pady=(0, 12), sticky="w")

        ctk.CTkLabel(
            self, text="Reason *",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        ).grid(row=2, column=0, padx=24, pady=(0, 4), sticky="w")

        self._reason_box = ctk.CTkTextbox(self, height=60, wrap="word")
        self._reason_box.grid(row=3, column=0, padx=24, sticky="ew")

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#E05555",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self._error_label.grid(row=4, column=0, padx=24, pady=(6, 0), sticky="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=24, pady=16, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text=confirm_text, width=130,
            fg_color=confirm_color,
            command=self._on_confirm,
        ).pack(side="left")

    def _on_confirm(self) -> None:
        reason = self._reason_box.get("1.0", "end").strip()
        if not reason:
            self._error_label.configure(text="A reason is required.")
            return
        self.result = reason
        self.destroy()
