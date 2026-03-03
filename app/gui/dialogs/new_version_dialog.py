"""
dialogs/new_version_dialog.py
"""

from __future__ import annotations

import os
import tkinter as tk
import tkinter.filedialog as filedialog
import customtkinter as ctk
from pathlib import Path
from typing import Optional

from app.gui.hints import NEW_VERSION_SUBTITLE
from schema import SourceComponentRecord


class NewVersionDialog(ctk.CTkToplevel):
    """
    result: (description: str, notes: list[str], created_by: str,
             step_files: list[Path], source_components: list[SourceComponentRecord]) | None
    """

    def __init__(self, parent, session_projects: list = None):
        super().__init__(parent)
        self.title("New Version")
        self.geometry("520x640")
        self.resizable(False, True)
        self.grab_set()

        self._session_projects = session_projects  # list[FEAProject] or None
        self.result            = None

        # Internal state for source files
        # Each entry: {"path": Path, "label": str, "sc": SourceComponentRecord | None}
        self._file_entries: list[dict] = []

        self._build()
        try:
            self._created_by_var.set(os.getlogin())
        except OSError:
            self._created_by_var.set(os.environ.get("USERNAME", ""))

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # files section expands

        ctk.CTkLabel(
            self, text="New Version",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 4), sticky="w")

        ctk.CTkLabel(
            self,
            text=NEW_VERSION_SUBTITLE,
            font=ctk.CTkFont(size=12),
            justify="left", anchor="w",
            wraplength=472,
        ).grid(row=1, column=0, padx=24, pady=(0, 16), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=2, column=0, sticky="nsew", padx=24)
        form.columnconfigure(1, weight=1)

        # Description
        ctk.CTkLabel(
            form, text="Description *",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=0, column=0, padx=(0, 12), pady=(0, 6), sticky="nw")

        self._description_box = ctk.CTkTextbox(form, height=80, wrap="word")
        self._description_box.grid(row=0, column=1, pady=(0, 6), sticky="ew")

        # Notes
        ctk.CTkLabel(
            form, text="Notes",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=1, column=0, padx=(0, 12), pady=(6, 6), sticky="nw")

        self._notes_box = ctk.CTkTextbox(form, height=60, wrap="word")
        self._notes_box.grid(row=1, column=1, pady=(6, 6), sticky="ew")

        ctk.CTkLabel(
            form, text="One note per line.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w",
        ).grid(row=2, column=1, sticky="w", pady=(0, 6))

        # Created By
        ctk.CTkLabel(
            form, text="Created By *",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=3, column=0, padx=(0, 12), pady=6, sticky="w")

        self._created_by_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self._created_by_var,
                     width=200).grid(row=3, column=1, pady=6, sticky="w")

        # ── Source Files section ──────────────────────────────────────────
        ctk.CTkLabel(
            form, text="Source Files",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=4, column=0, padx=(0, 12), pady=(10, 0), sticky="nw")

        src_right = ctk.CTkFrame(form, fg_color="transparent")
        src_right.grid(row=4, column=1, pady=(10, 0), sticky="ew")
        src_right.columnconfigure(0, weight=1)

        # Buttons row
        btn_row = ctk.CTkFrame(src_right, fg_color="transparent")
        btn_row.grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            btn_row, text="Browse Files…", width=130, height=26,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._on_browse_files,
        ).pack(side="left", padx=(0, 6))

        self._assembly_btn = ctk.CTkButton(
            btn_row, text="Add Assembly Component…", width=200, height=26,
            font=ctk.CTkFont(size=12),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            state="normal" if self._session_projects is not None else "disabled",
            command=self._on_add_assembly,
        )
        self._assembly_btn.pack(side="left")

        # Scrollable file list
        self._files_frame_outer = ctk.CTkScrollableFrame(
            src_right, height=120, fg_color=["#F5F5F5", "#2B2B2B"],
            corner_radius=6,
        )
        self._files_frame_outer.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self._files_frame_outer.columnconfigure(0, weight=1)

        self._empty_label = ctk.CTkLabel(
            self._files_frame_outer,
            text="No files selected.",
            font=ctk.CTkFont(size=11), text_color="gray",
        )
        self._empty_label.grid(row=0, column=0, padx=8, pady=8, sticky="w")

        # ── Error label ──────────────────────────────────────────────────
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#E05555",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self._error_label.grid(row=3, column=0, padx=24, pady=(8, 0), sticky="w")

        # ── Buttons ──────────────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=24, pady=20, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Create", width=100,
            command=self._on_confirm,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # File list management
    # ------------------------------------------------------------------

    def _refresh_file_list(self) -> None:
        for widget in self._files_frame_outer.winfo_children():
            widget.destroy()

        if not self._file_entries:
            self._empty_label = ctk.CTkLabel(
                self._files_frame_outer,
                text="No files selected.",
                font=ctk.CTkFont(size=11), text_color="gray",
            )
            self._empty_label.grid(row=0, column=0, padx=8, pady=8, sticky="w")
            return

        for idx, entry in enumerate(self._file_entries):
            row_frame = ctk.CTkFrame(self._files_frame_outer, fg_color="transparent")
            row_frame.grid(row=idx, column=0, sticky="ew", pady=1)
            row_frame.columnconfigure(1, weight=1)

            ctk.CTkLabel(
                row_frame, text="✕", font=ctk.CTkFont(size=11),
                text_color="#E05555", cursor="hand2",
            ).grid(row=0, column=0, padx=(4, 6))
            # Bind click to removal
            lbl = row_frame.winfo_children()[0]
            lbl.bind("<Button-1>", lambda _e, i=idx: self._remove_entry(i))

            ctk.CTkLabel(
                row_frame,
                text=f"{entry['path'].name}",
                font=ctk.CTkFont(size=11),
                anchor="w",
            ).grid(row=0, column=1, sticky="w")

            ctk.CTkLabel(
                row_frame,
                text=f"  [{entry['label']}]",
                font=ctk.CTkFont(size=10), text_color="gray",
                anchor="w",
            ).grid(row=0, column=2, padx=(0, 4), sticky="w")

    def _remove_entry(self, idx: int) -> None:
        if 0 <= idx < len(self._file_entries):
            self._file_entries.pop(idx)
            self._refresh_file_list()

    def _add_files(self, paths: list[Path], label: str,
                   sc: Optional[SourceComponentRecord] = None) -> None:
        existing = {e["path"] for e in self._file_entries}
        for p in paths:
            if p not in existing:
                self._file_entries.append({"path": p, "label": label, "sc": sc})
                existing.add(p)
        self._refresh_file_list()

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_browse_files(self) -> None:
        raw = filedialog.askopenfilenames(
            parent=self,
            title="Select STEP files",
            filetypes=[
                ("STEP files", "*.step *.stp *.STEP *.STP"),
                ("All files",  "*.*"),
            ],
        )
        if raw:
            self._add_files([Path(p) for p in raw], "From filesystem")

    def _on_add_assembly(self) -> None:
        if self._session_projects is None:
            return
        from app.gui.dialogs.select_source_version_dialog import SelectSourceVersionDialog
        # We need the current entity path to exclude it; get it from the first frame
        # that loaded us (the parent chain leads back to MainWindow)
        exclude = ""
        # Try to find the active entity path via the parent hierarchy
        try:
            mw = self.master
            while mw is not None:
                if hasattr(mw, "_active_path"):
                    exclude = mw._active_path or ""
                    break
                mw = getattr(mw, "master", None)
        except Exception:
            pass

        dlg = SelectSourceVersionDialog(self, self._session_projects, exclude)
        self.wait_window(dlg)
        if dlg.result is None:
            return  # cancelled

        for entity_path, entity_name, project_code, version_id, step_files in dlg.result:
            sc = SourceComponentRecord(
                entity_path=entity_path, entity_name=entity_name,
                project_code=project_code, version_id=version_id,
                copied_files=[f.name for f in step_files],
            )
            self._add_files(step_files, f"From {entity_name} / {version_id}", sc=sc)

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

        notes = [n.strip() for n in notes_raw.splitlines() if n.strip()]

        step_files: list[Path] = [e["path"] for e in self._file_entries]

        # Build source_components (deduplicated by entity_path+version_id)
        seen: set[tuple] = set()
        source_components: list[SourceComponentRecord] = []
        for entry in self._file_entries:
            if entry["sc"] is not None:
                sc  = entry["sc"]
                key = (sc.entity_path, sc.version_id)
                if key not in seen:
                    seen.add(key)
                    source_components.append(sc)

        self.result = (description, notes, created_by, step_files, source_components)
        self.destroy()
