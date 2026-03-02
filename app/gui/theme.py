"""
app/gui/theme.py — Shared Visual Tokens & Helpers
===================================================
Single source of truth for colours, ttk table styling, and the
status indicator widget. Import from here — never hardcode colours
in individual frames.
"""

from __future__ import annotations

import re
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
    "prod_marker":  "#FFD580",
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
    "prod_marker":  "#B45309",
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
        bg = self.master.cget("bg") if hasattr(self.master, "cget") else tokens()["bg"]
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


# ---------------------------------------------------------------------------
# 5. Hover Tooltip
# ---------------------------------------------------------------------------

class Tooltip:
    """
    Attaches a hover tooltip to any tkinter widget.
    The popup appears after a short delay and disappears on mouse-out.

    Usage:
        Tooltip(label_widget, "Explain what this field means.")
    """

    _DELAY_MS = 600

    def __init__(self, widget: tk.Widget, text: str):
        self._widget = widget
        self._text   = text
        self._job:   str | None          = None
        self._win:   tk.Toplevel | None  = None

        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")

    def _on_enter(self, _event) -> None:
        self._job = self._widget.after(self._DELAY_MS, self._show)

    def _on_leave(self, _event) -> None:
        if self._job:
            self._widget.after_cancel(self._job)
            self._job = None
        self._hide()

    def _show(self) -> None:
        if self._win:
            return
        t = tokens()
        x = self._widget.winfo_rootx() + 10
        y = self._widget.winfo_rooty() + self._widget.winfo_height() + 4
        self._win = tk.Toplevel(self._widget)
        self._win.wm_overrideredirect(True)
        self._win.wm_geometry(f"+{x}+{y}")
        tk.Label(
            self._win,
            text=self._text,
            justify="left",
            background=t["bg_secondary"],
            foreground=t["fg"],
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 10),
            padx=8, pady=5,
            wraplength=320,
        ).pack()

    def _hide(self) -> None:
        if self._win:
            self._win.destroy()
            self._win = None


def add_hint(widget: tk.Widget, text: str) -> None:
    """Attach a hover tooltip to *widget*. Tooltip appears after ~600 ms."""
    Tooltip(widget, text)


# ---------------------------------------------------------------------------
# 6. Audit Note Parser
# ---------------------------------------------------------------------------

AUDIT_NOTE_PREFIXES = ("[Reverted", "[Promoted", "[REVERTED")


def parse_audit_note(note: str) -> tuple[str, str, str, str]:
    """
    Parse a system audit note into (event, date, by, details).

    Handles:
      [Promoted to Production] on {date} by {user} — Runs: {runs}
      [Reverted to WIP] from {status} on {date} by {user} — {reason}
      [REVERTED to WIP from {status} by {user} on {date}] {reason}  (legacy)
    """
    m = re.match(r'\[Promoted to Production\] on (.+?) by (.+?) — Runs: (.+)', note)
    if m:
        return "Promoted to Production", m.group(1), m.group(2), m.group(3)
    m = re.match(r'\[Reverted to WIP\] from (\S+) on (.+?) by (.+?) — (.+)', note)
    if m:
        return "Reverted to WIP", m.group(2), m.group(3), m.group(4)
    m = re.match(r'\[REVERTED to WIP from (\S+) by (.+?) on (.+?)\] (.+)', note)
    if m:
        return "Reverted to WIP", m.group(3), m.group(2), m.group(4)
    return "System Note", "", "", note


def parse_audit_note_extended(note: str) -> tuple[str, str, str, str, str]:
    """
    Parse a system audit note into (event, date, by, runs, details).
    Used by frame tables that show a dedicated Runs column.

    Promoted: runs = "01, 02"  details = ""
    Reverted: runs = ""        details = user reason only
    """
    m = re.match(r'\[Promoted to Production\] on (.+?) by (.+?) — Runs: (.+)', note)
    if m:
        runs = ", ".join(r.strip().replace("Run ", "").strip()
                         for r in m.group(3).split(","))
        return "Promoted to Production", m.group(1), m.group(2), runs, ""
    m = re.match(r'\[Reverted to WIP\] from (\S+) on (.+?) by (.+?) — (.+)', note)
    if m:
        return "Reverted to WIP", m.group(2), m.group(3), "", m.group(4)
    m = re.match(r'\[REVERTED to WIP from (\S+) by (.+?) on (.+?)\] (.+)', note)
    if m:
        return "Reverted to WIP", m.group(3), m.group(2), "", m.group(4)
    return "System Note", "", "", "", note


def autofit_tree_columns(tree: ttk.Treeview) -> None:
    """
    Resize each column to fit its heading and all row values.
    The last column keeps stretch=True to fill remaining space;
    all others are fixed at their measured width.
    """
    import tkinter.font as tkfont
    head_font = tkfont.Font(family="Segoe UI", size=11, weight="bold")
    cell_font = tkfont.Font(family="Segoe UI", size=11)
    pad = 20
    cols = list(tree["columns"])
    for idx, col in enumerate(cols):
        col_w = head_font.measure(tree.heading(col)["text"]) + pad
        for iid in tree.get_children():
            w = cell_font.measure(str(tree.set(iid, col))) + pad
            col_w = max(col_w, w)
        is_last = (idx == len(cols) - 1)
        tree.column(col, width=col_w, minwidth=max(col_w, 40), stretch=is_last)
