# ═══════════════════════════════════════════════════════════════════════
# new_run_dialog.py
# ═══════════════════════════════════════════════════════════════════════
from __future__ import annotations

import os
import customtkinter as ctk
from app.gui.hints import NEW_RUN_SUBTITLE


class NewRunDialog(ctk.CTkToplevel):
    """
    result: (created_by: str, comments: str) | None
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("New Run")
        self.geometry("460x360")
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
            self, text="New Run",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 16), sticky="w")

        ctk.CTkLabel(
            self,
            text=NEW_RUN_SUBTITLE,
            font=ctk.CTkFont(size=12),
            justify="left",
            anchor="w",
            wraplength=412,
        ).grid(row=1, column=0, padx=24, pady=(0, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=24)
        form.columnconfigure(1, weight=1)

        # Created By
        ctk.CTkLabel(
            form, text="Created By *",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=0, column=0, padx=(0, 12), pady=6, sticky="w")

        self._created_by_var = ctk.StringVar()
        ctk.CTkEntry(
            form, textvariable=self._created_by_var, width=260,
        ).grid(row=0, column=1, pady=6, sticky="ew")

        # Comments
        ctk.CTkLabel(
            form, text="Comments",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=1, column=0, padx=(0, 12), pady=(6, 0), sticky="nw")

        self._comments_box = ctk.CTkTextbox(form, height=55, wrap="word")
        self._comments_box.grid(row=1, column=1, pady=(6, 0), sticky="ew")

        # Error
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#E05555",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self._error_label.grid(row=3, column=0, padx=24, pady=(8, 0), sticky="w")

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=24, pady=16, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Register Run", width=120,
            command=self._on_confirm,
        ).pack(side="left")

    def _on_confirm(self) -> None:
        created_by = self._created_by_var.get().strip()
        if not created_by:
            self._error_label.configure(text="Created By is required.")
            return
        comments = self._comments_box.get("1.0", "end").strip()
        self.result = (created_by, comments)
        self.destroy()