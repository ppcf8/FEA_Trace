"""
frames/entity_frame.py — Entity Detail View
"""
from __future__ import annotations

import os
import subprocess
import platform
import tkinter.ttk as ttk
import customtkinter as ctk
from typing import Optional
from pathlib import Path

from PIL import Image

from schema import VersionStatus, REQUIRED_FOLDERS
from app.core.models import FEAProject
from app.gui.theme import apply_table_style, make_scrollbar, STATUS_COLORS, tokens

_ICONS_DIR = Path(__file__).parent.parent.parent / "assets" / "icons"
_IMG_EDIT  = ctk.CTkImage(Image.open(_ICONS_DIR / "edit.png"), size=(16, 16))


_VERSION_STATUS_TEXT = {
    "WIP":        "● WIP",
    "production": "● Production",
    "deprecated": "● Deprecated",
}

_COL_WEIGHTS = {
    "id":         1,
    "status":     3,
    "intent":     8,
    "iterations": 1,
    "created_by": 3,
    "created_on": 3,
}  # total = 19 units


def _open_folder(path: Path) -> None:
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception:
        pass


class EntityFrame(ctk.CTkFrame):

    def __init__(self, master, window):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self._window  = window
        self._project: Optional[FEAProject] = None
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_header()
        self._build_metadata_panel()
        self._build_version_table()
        self._build_action_bar()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        hdr.columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            hdr, text="Entity",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="w")

        self._path_label = ctk.CTkLabel(
            hdr, text="", font=ctk.CTkFont(size=12), anchor="w",
        )
        self._path_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        ctk.CTkButton(
            hdr, text="Open Folder", width=110, height=32,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._on_open_folder,
        ).grid(row=0, column=1, padx=(12, 0), sticky="e")

    def _build_metadata_panel(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="ew", padx=24, pady=16)

        fields_left  = [("Entity ID",  "_id"),
                        ("Project",    "_project"),
                        ("Owner Team", "_owner")]
        fields_right = [("Created By", "_created_by"),
                        ("Created On", "_created_on")]

        self._meta: dict[str, ctk.CTkLabel] = {}

        for col_offset, fields in enumerate([fields_left, fields_right]):
            for row_i, (label, key) in enumerate(fields):
                ctk.CTkLabel(
                    panel, text=label,
                    font=ctk.CTkFont(size=12, weight="bold"),
                    anchor="w", width=100,
                ).grid(row=row_i, column=col_offset * 2,
                       padx=(16, 4), pady=6, sticky="w")

                val_label = ctk.CTkLabel(
                    panel, text="—",
                    font=ctk.CTkFont(size=12), anchor="w",
                )
                val_label.grid(row=row_i, column=col_offset * 2 + 1,
                               padx=(0, 24), pady=6, sticky="w")
                self._meta[key] = val_label

        self._edit_btn = ctk.CTkButton(
            panel, image=_IMG_EDIT, text="Edit", compound="left",
            width=90, height=28,
            font=ctk.CTkFont(size=12),
            command=self._on_edit_entity,
        )
        self._edit_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=8)

        ctk.CTkLabel(
            panel, text="Folder Health",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
        ).grid(row=3, column=0, padx=(16, 4), pady=(6, 10), sticky="w")

        self._health_label = ctk.CTkLabel(
            panel, text="", font=ctk.CTkFont(size=12), anchor="w",
        )
        self._health_label.grid(row=3, column=1, columnspan=3,
                                padx=(0, 16), pady=(6, 10), sticky="w")

    def _build_version_table(self) -> None:
        section = ctk.CTkFrame(self, fg_color="transparent")
        section.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 8))
        section.columnconfigure(0, weight=1)
        section.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            section, text="Versions",
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        cols = ("id", "status", "intent", "iterations",
                "created_by", "created_on")
        self._table = ttk.Treeview(
            section, columns=cols, show="headings",
            selectmode="browse", height=8,
            style="Entity.Treeview",
        )

        headings = {
            "id":         ("ID",         "center"),
            "status":     ("Status",     "w"),
            "intent":     ("Intent",     "w"),
            "iterations": ("Iters",      "center"),
            "created_by": ("Created By", "w"),
            "created_on": ("Created On", "w"),
        }
        for col, (heading, anchor) in headings.items():
            self._table.heading(col, text=heading, anchor=anchor)
            self._table.column(col, width=60, anchor=anchor, stretch=False)

        vsb = make_scrollbar(section, "vertical",   self._table.yview)
        hsb = make_scrollbar(section, "horizontal", self._table.xview)
        self._table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._table.grid(row=1, column=0, sticky="nsew")
        vsb.grid(row=1, column=1, sticky="ns")
        hsb.grid(row=2, column=0, sticky="ew")

        for status, color in STATUS_COLORS.items():
            self._table.tag_configure(f"status_{status}", foreground=color)

        self._section = section
        self._table.bind("<<TreeviewSelect>>", self._on_version_select)
        section.bind("<Configure>", self._resize_columns)
        apply_table_style("Entity.Treeview")
        ctk.AppearanceModeTracker.add(self._on_appearance_change)

    def _build_action_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=3, column=0, sticky="ew", padx=24, pady=(4, 20))

        ctk.CTkButton(
            bar, text="+ New Version", width=140, height=36,
            font=ctk.CTkFont(size=13),
            command=self._on_new_version,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, project: FEAProject) -> None:
        self._project = project
        e = project.entity

        self._title_label.configure(text=e.name)
        self._path_label.configure(text=str(project.path))
        self._meta["_id"].configure(text=e.id)
        self._meta["_project"].configure(text=e.project)
        self._meta["_owner"].configure(text=e.owner_team)
        self._meta["_created_by"].configure(text=e.created_by)
        self._meta["_created_on"].configure(text=e.created_on)

        missing = [f for f in REQUIRED_FOLDERS
                   if not (project.path / f).is_dir()]
        if missing:
            self._health_label.configure(
                text=f"⚠  Missing: {', '.join(missing)}")
        else:
            self._health_label.configure(
                text="✓  All required folders present")

        apply_table_style("Entity.Treeview")
        self._populate_table()

    def _populate_table(self) -> None:
        for row in self._table.get_children():
            self._table.delete(row)

        for v in self._project.entity.versions:
            status_val   = v.status.value
            status_text  = _VERSION_STATUS_TEXT.get(status_val, status_val)
            intent_short = v.intent.strip().replace("\n", " ")
            if len(intent_short) > 60:
                intent_short = intent_short[:57] + "…"

            tag = f"status_{status_val}"
            self._table.insert("", "end", iid=v.id, tags=(tag,), values=(
                v.id, status_text, intent_short,
                len(v.iterations), v.created_by, v.created_on,
            ))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_version_select(self, _event) -> None:
        sel = self._table.selection()
        if sel and self._project:
            # FIX Bug 1: pass entity_path as first argument
            self._window.show_version(str(self._project.path), sel[0])

    def _on_open_folder(self) -> None:
        if self._project:
            _open_folder(self._project.path)

    def _on_edit_entity(self) -> None:
        if self._project is None:
            return
        from app.gui.dialogs.edit_entity_dialog import EditEntityDialog
        dlg = EditEntityDialog(self._window, self._project.entity)
        self._window.wait_window(dlg)
        if dlg.result is None:
            return
        name, project, owner_team, created_by = dlg.result
        try:
            self._project.update_entity_metadata(name, project, owner_team, created_by)
        except Exception as exc:
            self._show_error("Edit Entity Failed", str(exc))
            return
        self.load(self._project)
        self._window.refresh_sidebar()
        self._window.set_status("Entity metadata updated.")

    def _on_new_version(self) -> None:
        if self._project is None:
            return
        from app.gui.dialogs.new_version_dialog import NewVersionDialog
        dlg = NewVersionDialog(self._window)
        self._window.wait_window(dlg)
        if dlg.result is None:
            return

        intent, notes, created_by = dlg.result
        try:
            self._project.add_version(intent, created_by, notes)
        except Exception as exc:
            self._show_error("Create Version Failed", str(exc))
            return

        self._populate_table()
        self._window.refresh_sidebar()
        self._window.set_status("Version created successfully.")

    def _resize_columns(self, event=None) -> None:
        width = self._section.winfo_width()
        if width <= 1 or width == getattr(self, "_last_col_width", 0):
            return
        self._last_col_width = width
        available = max(width - 18, 100)
        total = sum(_COL_WEIGHTS.values())
        for col, w in _COL_WEIGHTS.items():
            self._table.column(col, width=max(20, int(available * w / total)))

    def _on_appearance_change(self, _mode: str) -> None:
        apply_table_style("Entity.Treeview")
        for status, color in STATUS_COLORS.items():
            self._table.tag_configure(f"status_{status}", foreground=color)
        if self._project:
            self._populate_table()

    def _show_error(self, title: str, message: str) -> None:
        from tkinter import messagebox
        messagebox.showerror(title, message, parent=self._window)