"""
app/gui/theme.py — Shared Visual Tokens & Helpers
===================================================
Single source of truth for colours, ttk table styling, and the
status indicator widget. Import from here — never hardcode colours
in individual frames.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
import customtkinter as ctk


# ---------------------------------------------------------------------------
# 1. Colour Tokens
# ---------------------------------------------------------------------------

_DARK = {
    "bg":           "#2B2B2B",
    "bg_secondary": "#333333",
    "bg_selected":  "#1F6AA5",
    "fg":           "#DCE4EE",
    "fg_selected":  "#FFFFFF",
    "fg_muted":     "#9BA3AF",
    "border":       "#3D3D3D",
    "header_bg":    "#242424",
}

_LIGHT = {
    "bg":           "#F0F0F0",
    "bg_secondary": "#E5E5E5",
    "bg_selected":  "#3B8ED0",
    "fg":           "#1A1A1A",
    "fg_selected":  "#FFFFFF",
    "fg_muted":     "#555555",
    "border":       "#CCCCCC",
    "header_bg":    "#DCDCDC",
}

# Status colours — consistent across sidebar, badges, buttons
STATUS_COLORS = {
    # Version status
    "WIP":        "#4A90D9",
    "production": "#2D8A4E",
    "deprecated": "#888888",
    # Run status
    "converged":  "#2D8A4E",
    "diverged":   "#C0392B",
    "partial":    "#B8860B",
    "aborted":    "#666666",
}

# Solver pill colours
SOLVER_COLORS = {
    "IMPLICIT": "#2D6A9F",
    "EXPLICIT": "#8A3D00",
    "MBD":      "#2D6B3A",
}


def tokens() -> dict:
    """Returns the colour token dict for the current appearance mode."""
    return _DARK if ctk.get_appearance_mode() == "Dark" else _LIGHT


# ---------------------------------------------------------------------------
# 2. Status Indicator Widget
# ---------------------------------------------------------------------------

class StatusDot(tk.Canvas):
    """
    A small filled circle indicating a status value.
    Replaces emoji circles which render inconsistently on Windows.

    Usage:
        dot = StatusDot(parent, status="converged")
        dot.pack(side="left")
    """

    SIZE = 12   # diameter in pixels

    def __init__(self, parent, status: str, **kwargs):
        super().__init__(
            parent,
            width=self.SIZE,
            height=self.SIZE,
            highlightthickness=0,
            bd=0,
            **kwargs,
        )
        self._status = status
        self._draw()

    def _draw(self) -> None:
        self.delete("all")
        # Match canvas background to parent so it looks transparent
        bg = self.master.cget("bg") if hasattr(self.master, "cget") else "#2B2B2B"
        self.configure(bg=bg)
        color = STATUS_COLORS.get(self._status, "#888888")
        pad = 1
        self.create_oval(
            pad, pad,
            self.SIZE - pad, self.SIZE - pad,
            fill=color, outline=color,
        )

    def update_status(self, status: str) -> None:
        self._status = status
        self._draw()


# ---------------------------------------------------------------------------
# 3. TTK Table Style
# ---------------------------------------------------------------------------

def apply_table_style(style_name: str) -> None:
    """
    Applies a fully themed ttk.Treeview style for the current appearance mode.
    Call this on every frame load (not just __init__) so theme switches apply.

    Args:
        style_name: e.g. "Entity.Treeview" — must be unique per frame to
                    avoid cross-frame style bleed.
    """
    t = tokens()
    s = ttk.Style()

    s.configure(
        style_name,
        background=t["bg"],
        foreground=t["fg"],
        fieldbackground=t["bg"],
        rowheight=28,
        font=("Segoe UI", 11),
        borderwidth=0,
        relief="flat",
    )
    s.configure(
        f"{style_name}.Heading",
        background=t["header_bg"],
        foreground=t["fg"],
        font=("Segoe UI", 11, "bold"),
        relief="flat",
        borderwidth=0,
        padding=(8, 6),
    )
    s.map(
        style_name,
        background=[("selected", t["bg_selected"])],
        foreground=[("selected", t["fg_selected"])],
    )
    # Remove the focus dotted border that looks dated
    s.layout(style_name, [
        ("Treeview.treearea", {"sticky": "nswe"}),
    ])


def apply_sidebar_style() -> None:
    """Sidebar tree style — narrower rows, no heading."""
    t = tokens()
    s = ttk.Style()

    s.configure(
        "Sidebar.Treeview",
        background=t["bg"],
        foreground=t["fg"],
        fieldbackground=t["bg"],
        rowheight=30,
        font=("Segoe UI", 11),
        borderwidth=0,
        relief="flat",
        indent=16,
    )
    s.map(
        "Sidebar.Treeview",
        background=[("selected", t["bg_selected"])],
        foreground=[("selected", t["fg_selected"])],
    )
    s.layout("Sidebar.Treeview", [
        ("Treeview.treearea", {"sticky": "nswe"}),
    ])


# ---------------------------------------------------------------------------
# 4. CTkScrollbar helper
# ---------------------------------------------------------------------------

def make_scrollbar(parent, orient: str, command) -> ctk.CTkScrollbar:
    """
    Creates a themed CTkScrollbar. Use instead of ttk.Scrollbar everywhere.
    """
    return ctk.CTkScrollbar(parent, orientation=orient, command=command)
