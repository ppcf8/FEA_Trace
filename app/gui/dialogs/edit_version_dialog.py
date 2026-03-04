"""
dialogs/edit_version_dialog.py
"""

from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog
import customtkinter as ctk
from pathlib import Path
from typing import Optional

from schema import VersionRecord, SourceComponentRecord
from app.gui.theme import (apply_table_style, make_scrollbar,
                           AUDIT_NOTE_PREFIXES, parse_audit_note)

_SYSTEM_NOTE_PREFIXES = AUDIT_NOTE_PREFIXES


class EditVersionDialog(ctk.CTkToplevel):
    """
    Pre-filled edit dialog for an existing VersionRecord.

    Notes are split into user notes (editable) and system audit notes
    (read-only entries prefixed with "[Reverted", "[Promoted", or legacy "[REVERTED").
    On save, system notes are always preserved unchanged and appended after user notes.

    result: (description: str, notes: list[str], created_by: str,
             new_step_files: list[Path],
             source_components: list[SourceComponentRecord]) | None
    """

    def __init__(self, parent, version: VersionRecord,
                 project=None, session_projects: list = None):
        super().__init__(parent)
        self.title("Edit Version")
        self.resizable(True, True)
        self.grab_set()

        self.result            = None
        self._version          = version
        self._project          = project          # FEAProject | None
        self._session_projects = session_projects  # list[FEAProject] | None

        # Separate editable user notes from immutable system audit entries
        self._user_notes   = [n for n in version.notes
                               if not any(n.startswith(p) for p in _SYSTEM_NOTE_PREFIXES)]
        self._system_notes = [n for n in version.notes
                               if any(n.startswith(p) for p in _SYSTEM_NOTE_PREFIXES)]

        # Source-files state — start from existing components
        # Each entry: {"path": Path | None, "label": str, "sc": SourceComponentRecord | None}
        # Path is None for pre-existing components that are already on disk
        self._file_entries: list[dict] = []
        for sc in version.source_components:
            self._file_entries.append({
                "path": None,     # already on disk — not a new file to copy
                "label": f"From {sc.entity_name} / {sc.version_id}",
                "sc":   sc,
            })

        n_audit_rows = min(len(self._system_notes), 3)
        audit_h      = (25 + n_audit_rows * 28 + 30) if self._system_notes else 0
        height       = 560 + audit_h   # taller than before to fit source section
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

        # ── Description ──
        ctk.CTkLabel(
            form, text="Description *",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=0, column=0, padx=(0, 12), pady=(0, 6), sticky="nw")

        self._description_box = ctk.CTkTextbox(form, height=80, wrap="word")
        self._description_box.grid(row=0, column=1, pady=(0, 6), sticky="nsew")

        # ── Notes ──
        ctk.CTkLabel(
            form, text="Notes",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=1, column=0, padx=(0, 12), pady=(6, 6), sticky="nw")

        self._notes_box = ctk.CTkTextbox(form, height=60, wrap="word")
        self._notes_box.grid(row=1, column=1, pady=(6, 6), sticky="nsew")

        ctk.CTkLabel(
            form, text="One note per line.",
            font=ctk.CTkFont(size=11), text_color="gray", anchor="w",
        ).grid(row=2, column=1, sticky="w", pady=(0, 6))

        # ── Created By ──
        ctk.CTkLabel(
            form, text="Created By *",
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=3, column=0, padx=(0, 12), pady=6, sticky="w")

        self._created_by_var = ctk.StringVar()
        ctk.CTkEntry(form, textvariable=self._created_by_var,
                     width=200).grid(row=3, column=1, pady=6, sticky="w")

        # ── Source Files ──
        ctk.CTkLabel(
            form, text="Source Files",
            font=ctk.CTkFont(size=12), anchor="nw",
        ).grid(row=4, column=0, padx=(0, 12), pady=(10, 0), sticky="nw")

        src_right = ctk.CTkFrame(form, fg_color="transparent")
        src_right.grid(row=4, column=1, pady=(10, 0), sticky="ew")
        src_right.columnconfigure(0, weight=1)

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

        self._files_frame_outer = ctk.CTkScrollableFrame(
            src_right, height=100, fg_color=["#F5F5F5", "#2B2B2B"],
            corner_radius=6,
        )
        self._files_frame_outer.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self._files_frame_outer.columnconfigure(0, weight=1)

        # ── Log ──
        if self._system_notes:
            ctk.CTkLabel(
                form, text="Log",
                font=ctk.CTkFont(size=12), anchor="nw",
                text_color="gray",
            ).grid(row=5, column=0, padx=(0, 12), pady=(6, 4), sticky="nw")

            apply_table_style("Audit.Treeview")
            audit_wrap = ctk.CTkFrame(form, fg_color="transparent")
            audit_wrap.grid(row=5, column=1, pady=(6, 4), sticky="ew")
            audit_wrap.columnconfigure(0, weight=1)

            self._audit_tree = ttk.Treeview(
                audit_wrap, style="Audit.Treeview",
                columns=("event", "date", "by", "details"),
                show="headings", height=5,
            )
            self._audit_tree.heading("event",   text="Event",   anchor="center")
            self._audit_tree.heading("date",    text="Date",    anchor="w")
            self._audit_tree.heading("by",      text="By",      anchor="w")
            self._audit_tree.heading("details", text="Details", anchor="w")
            self._audit_tree.column("event",   width=160, minwidth=100, stretch=False, anchor="center")
            self._audit_tree.column("date",    width=135, minwidth=100, stretch=False, anchor="w")
            self._audit_tree.column("by",      width=75,  minwidth=50,  stretch=False, anchor="w")
            self._audit_tree.column("details", width=150, minwidth=80,  stretch=True,  anchor="w")
            self._audit_tree.grid(row=0, column=0, sticky="nsew")

            sb = make_scrollbar(audit_wrap, "vertical", self._audit_tree.yview)
            self._audit_tree.configure(yscrollcommand=sb.set)
            sb.grid(row=0, column=1, sticky="ns")

        # ── Error label ──
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#E05555",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self._error_label.grid(row=2, column=0, padx=24, pady=(8, 0), sticky="w")

        # ── Buttons ──
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
                ev, dt, by, details = parse_audit_note(note)
                self._audit_tree.insert("", "end", values=(ev, dt, by, details))

        self._refresh_file_list()

    # ------------------------------------------------------------------
    # File list management (mirrors NewVersionDialog)
    # ------------------------------------------------------------------

    def _refresh_file_list(self) -> None:
        for widget in self._files_frame_outer.winfo_children():
            widget.destroy()

        if not self._file_entries:
            ctk.CTkLabel(
                self._files_frame_outer,
                text="No source files.",
                font=ctk.CTkFont(size=11), text_color="gray",
            ).grid(row=0, column=0, padx=8, pady=8, sticky="w")
            return

        for idx, entry in enumerate(self._file_entries):
            row_frame = ctk.CTkFrame(self._files_frame_outer, fg_color="transparent")
            row_frame.grid(row=idx, column=0, sticky="ew", pady=1)
            row_frame.columnconfigure(1, weight=1)

            remove_lbl = ctk.CTkLabel(
                row_frame, text="✕", font=ctk.CTkFont(size=11),
                text_color="#E05555", cursor="hand2",
            )
            remove_lbl.grid(row=0, column=0, padx=(4, 6))
            remove_lbl.bind("<Button-1>", lambda _e, i=idx: self._remove_entry(i))

            # Display name: for existing components show count; for new files show filename
            if entry["sc"] is not None and entry["path"] is None:
                # Pre-existing component
                sc = entry["sc"]
                n  = len(sc.copied_files)
                display = f"{sc.version_id}  ({n} file{'s' if n != 1 else ''})"
            else:
                display = entry["path"].name if entry["path"] else "—"

            ctk.CTkLabel(
                row_frame, text=display,
                font=ctk.CTkFont(size=11), anchor="w",
            ).grid(row=0, column=1, sticky="w")

            ctk.CTkLabel(
                row_frame, text=f"  [{entry['label']}]",
                font=ctk.CTkFont(size=10), text_color="gray", anchor="w",
            ).grid(row=0, column=2, padx=(0, 4), sticky="w")

    def _remove_entry(self, idx: int) -> None:
        if 0 <= idx < len(self._file_entries):
            self._file_entries.pop(idx)
            self._refresh_file_list()

    def _add_files(self, paths: list[Path], label: str,
                   sc: Optional[SourceComponentRecord] = None) -> None:
        existing_paths = {e["path"] for e in self._file_entries if e["path"] is not None}
        for p in paths:
            if p not in existing_paths:
                self._file_entries.append({"path": p, "label": label, "sc": sc})
                existing_paths.add(p)
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
        exclude = str(self._project.path) if self._project else ""
        dlg = SelectSourceVersionDialog(self, self._session_projects, exclude)
        self.wait_window(dlg)
        if dlg.result is None:
            return
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

        user_notes = [n.strip() for n in notes_raw.splitlines() if n.strip()]
        all_notes  = user_notes + self._system_notes

        # New step files to copy (entries with a real path — not pre-existing components)
        new_step_files: list[Path] = [
            e["path"] for e in self._file_entries if e["path"] is not None
        ]

        # Full updated source_components list (deduplicated by entity_path+version_id)
        seen: set[tuple] = set()
        source_components: list[SourceComponentRecord] = []
        for entry in self._file_entries:
            if entry["sc"] is not None:
                sc  = entry["sc"]
                key = (sc.entity_path, sc.version_id)
                if key not in seen:
                    seen.add(key)
                    source_components.append(sc)

        self.result = (description, all_notes, created_by, new_step_files, source_components)
        self.destroy()
