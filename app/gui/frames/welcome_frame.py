"""
welcome_frame.py — Welcome Screen
===================================
Displayed on startup before any entity is opened.
Provides quick-access buttons for the two primary entry points and
a brief description of the tool's purpose.

No project data is needed or used here.
"""

from __future__ import annotations

import customtkinter as ctk
from app.config import APP_TITLE


class WelcomeFrame(ctk.CTkFrame):
    """
    Shown when no entity is loaded.

    Parameters
    ----------
    master : parent widget (main panel)
    window : MainWindow reference — used to trigger New / Open actions
    """

    def __init__(self, master, window):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self._window = window
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        # Single centred column
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)   # spacer top
        self.rowconfigure(1, weight=0)   # content
        self.rowconfigure(2, weight=1)   # spacer bottom

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0)
        content.columnconfigure(0, weight=1)

        # App name
        ctk.CTkLabel(
            content,
            text=APP_TITLE,
            font=ctk.CTkFont(size=36, weight="bold"),
            anchor="center",
        ).grid(row=0, column=0, pady=(0, 8))

        # Tagline
        ctk.CTkLabel(
            content,
            text="FEA Versioning & Traceability",
            font=ctk.CTkFont(size=16),
            anchor="center",
        ).grid(row=1, column=0, pady=(0, 48))

        # Divider
        ctk.CTkFrame(
            content, height=1, width=320,
        ).grid(row=2, column=0, pady=(0, 48))

        # Action buttons
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=3, column=0, pady=(0, 32))

        ctk.CTkButton(
            btn_frame,
            text="New Entity",
            width=160,
            height=44,
            font=ctk.CTkFont(size=14),
            command=self._window._on_new_entity,
        ).pack(side="left", padx=12)

        ctk.CTkButton(
            btn_frame,
            text="Open Entity",
            width=160,
            height=44,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=2,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._window._on_open_entity,
        ).pack(side="left", padx=12)

        ctk.CTkButton(
            btn_frame,
            text="Open Session",
            width=160,
            height=44,
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            border_width=2,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._window._on_open_session,
        ).pack(side="left", padx=12)

        # Hint text
        ctk.CTkLabel(
            content,
            text=(
                "Create a new entity to start tracking a component or assembly,\n"
                "or open an existing entity folder or session to continue work."
            ),
            font=ctk.CTkFont(size=13),
            justify="center",
        ).grid(row=4, column=0)
