"""
app/gui/theme.py — Shared Visual Tokens & Helpers
===================================================
Single source of truth for colours, ttk table styling, and the
status indicator widget. Import from here — never hardcode colours
in individual frames.
"""

from __future__ import annotations

import re
from pathlib import Path
import tkinter as tk
import tkinter.ttk as ttk
import customtkinter as ctk
from PIL import Image

_ICONS_DIR = Path(__file__).parent.parent / "assets" / "icons"
_IMG_DOCS  = ctk.CTkImage(Image.open(_ICONS_DIR / "docs.png"), size=(16, 16))


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

AUDIT_NOTE_PREFIXES = ("[Reverted", "[Promoted", "[REVERTED", "[Sent Output")


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
    m = re.match(r'\[Sent Output\] on (.+?) by (.+?) — To: (.+?) — Subject: (.+)', note)
    if m:
        return "Sent Output", m.group(1), m.group(2), f"To: {m.group(3)} — Subject: {m.group(4)}"
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
        return "Reverted to WIP", m.group(2), m.group(3), "—", m.group(4)
    m = re.match(r'\[REVERTED to WIP from (\S+) by (.+?) on (.+?)\] (.+)', note)
    if m:
        return "Reverted to WIP", m.group(3), m.group(2), "—", m.group(4)
    m = re.match(r'\[Sent Output\] on (.+?) by (.+?) — To: (.+?) — Subject: (.+)', note)
    if m:
        return "Sent Output", m.group(1), m.group(2), "—", f"To: {m.group(3)} — Subject: {m.group(4)}"
    return "System Note", "", "", "—", note


def show_audit_detail_popup(parent, col_names: list[str], values: tuple,
                            open_file_label: str = "",
                            open_file_path: str = "",
                            import_eml_callback=None) -> None:
    """
    Open a read-only popup showing all fields of one audit log row.
    The last field named "Details" is rendered as a wrapped textbox.
    Call from a <Double-1> handler on an audit Treeview.

    open_file_label:      column label for the row that gets a file action.
    open_file_path:       non-empty → docs-icon button that calls os.startfile().
    import_eml_callback:  callable() → bool; shown when open_file_path is empty
                          so the user can attach a .eml after the fact.
                          Return True to close the popup automatically.
    """
    import os

    popup = ctk.CTkToplevel(parent)
    popup.title("Audit Entry")
    popup.grab_set()
    popup.resizable(True, True)
    popup.geometry("520x1")   # lock width; height is auto-measured below

    # Obtain the actual Tk background so tk.Label widgets blend in.
    popup.update_idletasks()
    bg = popup.cget("bg")
    fg = tokens()["fg"]

    # Plain tk.Frame: pack(fill="x") makes it 520 px wide so winfo_reqheight()
    # measures at the correct width.  CTkFrame does not report reqheight
    # accurately for its packed Tk children.
    container = tk.Frame(popup, bg=bg)
    container.pack(fill="x")

    # tk.Frame + tk.Label gives pixel-precise anchor/alignment vs CTkLabel.
    form = tk.Frame(container, bg=bg)
    form.pack(fill="x", expand=False, padx=20, pady=16)
    form.columnconfigure(1, weight=1)

    for row_idx, (label, val) in enumerate(zip(col_names, values)):
        tk.Label(
            form, text=f"{label}:",
            font=("Segoe UI", 12, "bold"),
            fg=fg, bg=bg,
            anchor="ne", justify="right",
            width=10,
        ).grid(row=row_idx, column=0, padx=(0, 10), pady=(6, 0), sticky="ne")

        if label == "Details":
            form.rowconfigure(row_idx, weight=1)
            box = ctk.CTkTextbox(form, height=80, wrap="word")
            box.grid(row=row_idx, column=1, sticky="nsew", pady=(6, 0))
            box.insert("1.0", val)
            box.configure(state="disabled")
        elif label == open_file_label and (open_file_path or import_eml_callback):
            cell = tk.Frame(form, bg=bg)
            cell.grid(row=row_idx, column=1, sticky="nw", pady=(6, 0))
            tk.Label(
                cell, text=val,
                font=("Segoe UI", 12),
                fg=fg, bg=bg,
                anchor="nw",
            ).pack(side="left")

            if open_file_path and val not in ("\u2014", ""):
                # File already stored — show docs icon to open it.
                def _open(p=open_file_path):
                    try:
                        os.startfile(p)
                    except Exception:
                        pass

                ctk.CTkButton(
                    cell, image=_IMG_DOCS, text="", width=28, height=24,
                    command=_open,
                ).pack(side="left", padx=(8, 0))
            elif import_eml_callback:
                # No file yet — offer to import one.
                def _import():
                    if import_eml_callback():
                        popup.destroy()

                ctk.CTkButton(
                    cell, text="Import .eml…", height=24,
                    font=ctk.CTkFont(size=11),
                    command=_import,
                ).pack(side="left", padx=(8, 0))
        else:
            tk.Label(
                form, text=val,
                font=("Segoe UI", 12),
                fg=fg, bg=bg,
                anchor="nw", justify="left", wraplength=370,
            ).grid(row=row_idx, column=1, sticky="nw", pady=(6, 0))

    ctk.CTkButton(container, text="Close", width=80,
                  command=popup.destroy).pack(pady=(8, 16))

    # winfo_reqheight() on the tk.Frame gives the content's natural height,
    # unaffected by the window's current size.
    container.update_idletasks()
    popup.geometry(f"520x{container.winfo_reqheight()}")


def show_comm_detail_popup(parent, comm, comms_dir,
                           version_id: str = "",
                           on_add_eml=None,
                           on_files_changed=None) -> None:
    """
    Rich detail popup for a CommunicationRecord.

    comm:             CommunicationRecord (eml_filenames: list[str])
    comms_dir:        Path — entity's 05_Communications/ folder
    version_id:       shown as 'Version' row when non-empty
    on_add_eml:       callable(dest_filename: str) — called after a new .eml
                      is copied to comms_dir; caller appends dest to
                      comm.eml_filenames and persists.
    on_files_changed: callable() — called after any file op (UI refresh).
    """
    import os
    import datetime
    import shutil
    import tkinter.filedialog as fd
    from pathlib import Path as _Path

    popup = ctk.CTkToplevel(parent)
    popup.title("Communication Detail")
    popup.grab_set()
    popup.resizable(True, True)
    popup.geometry("520x1")   # lock width; height auto-measured below

    popup.update_idletasks()
    bg = popup.cget("bg")
    fg = tokens()["fg"]
    fg_muted = tokens()["fg_muted"]

    # Plain tk.Frame container — see show_audit_detail_popup for rationale.
    container = tk.Frame(popup, bg=bg)
    container.pack(fill="x")

    form = tk.Frame(container, bg=bg)
    form.pack(fill="x", expand=False, padx=20, pady=16)
    form.columnconfigure(1, weight=1)

    static_fields = [("Date", comm.sent_at), ("By", comm.sent_by)]
    if version_id:
        static_fields.append(("Version", version_id))
    static_fields += [("To", comm.to), ("Subject", comm.subject)]

    for row_idx, (label, val) in enumerate(static_fields):
        tk.Label(
            form, text=f"{label}:",
            font=("Segoe UI", 12, "bold"),
            fg=fg, bg=bg, anchor="ne", justify="right", width=10,
        ).grid(row=row_idx, column=0, padx=(0, 10), pady=(6, 0), sticky="ne")
        tk.Label(
            form, text=val,
            font=("Segoe UI", 12),
            fg=fg, bg=bg, anchor="nw", justify="left", wraplength=370,
        ).grid(row=row_idx, column=1, sticky="nw", pady=(6, 0))

    # .eml files section
    files_row = len(static_fields)
    tk.Label(
        form, text=".eml:",
        font=("Segoe UI", 12, "bold"),
        fg=fg, bg=bg, anchor="ne", justify="right", width=10,
    ).grid(row=files_row, column=0, padx=(0, 10), pady=(6, 0), sticky="ne")

    files_frame = tk.Frame(form, bg=bg)
    files_frame.grid(row=files_row, column=1, sticky="nw", pady=(6, 0))

    def _resize():
        """Re-measure the container and update the popup height."""
        container.update_idletasks()
        popup.geometry(f"520x{container.winfo_reqheight()}")

    def _unique_dest(d: _Path, base: str) -> str:
        """Return a filename that doesn't exist in d; appends _2, _3, … as needed."""
        stem, n = base[:-4], 2  # strip .eml
        dest = base
        while (d / dest).exists():
            dest = f"{stem}_{n}.eml"
            n += 1
        return dest

    def _rebuild_files():
        for w in files_frame.winfo_children():
            w.destroy()
        filenames = getattr(comm, "eml_filenames", [])
        if not filenames:
            tk.Label(files_frame, text="\u2014",
                     font=("Segoe UI", 12), fg=fg, bg=bg).pack(anchor="w")
        else:
            for fname in filenames:
                fpath = _Path(comms_dir) / fname
                row_f = tk.Frame(files_frame, bg=bg)
                row_f.pack(fill="x", pady=(0, 2))
                exists = fpath.exists()
                tk.Label(row_f, text=fname,
                         font=("Segoe UI", 10),
                         fg=fg if exists else fg_muted, bg=bg).pack(side="left")
                if exists:
                    def _open(p=str(fpath)):
                        try:
                            os.startfile(p)
                        except Exception:
                            pass
                    ctk.CTkButton(
                        row_f, image=_IMG_DOCS, text="", width=28, height=24,
                        command=_open,
                    ).pack(side="left", padx=(6, 0))
                else:
                    tk.Label(row_f, text="(missing)",
                             font=("Segoe UI", 10, "italic"),
                             fg=fg_muted, bg=bg).pack(side="left", padx=(4, 0))

                    def _restore(d=_Path(comms_dir), f=fname):
                        path = fd.askopenfilename(
                            title=f"Restore {f}",
                            filetypes=[(".eml files", "*.eml")],
                        )
                        if not path:
                            return
                        d.mkdir(exist_ok=True)
                        shutil.copy2(path, d / f)
                        _rebuild_files()
                        _resize()
                        if on_files_changed:
                            on_files_changed()

                    ctk.CTkButton(
                        row_f, text="Restore\u2026", height=22,
                        font=ctk.CTkFont(size=10),
                        command=_restore,
                    ).pack(side="left", padx=(6, 0))

        def _add_eml():
            path = fd.askopenfilename(
                title="Add .eml File",
                filetypes=[(".eml files", "*.eml")],
            )
            if not path:
                return
            d = _Path(comms_dir)
            d.mkdir(exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_subj = "".join(
                ch if ch not in r'\/:*?"<>|' else "_"
                for ch in comm.subject
            )[:60].strip()
            dest = _unique_dest(d, f"{ts}_{safe_subj}.eml")
            shutil.copy2(path, d / dest)
            if on_add_eml:
                on_add_eml(dest)
            _rebuild_files()
            _resize()
            if on_files_changed:
                on_files_changed()

        ctk.CTkButton(
            files_frame, text="+ Add .eml", height=26,
            font=ctk.CTkFont(size=11),
            command=_add_eml,
        ).pack(anchor="w", pady=(4, 0))

    _rebuild_files()

    ctk.CTkButton(container, text="Close", width=80,
                  command=popup.destroy).pack(pady=(8, 16))

    _resize()


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
