"""
dialogs/manage_presets_dialog.py — Two-panel CRUD editor for project-code / entity-name presets.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk

from app.core.settings import get_settings_manager
from app.gui.theme import apply_table_style, make_scrollbar


class ManagePresetsDialog(ctk.CTkToplevel):
    """
    Structured editor for the project_presets mapping.

    Left panel  — project codes (single-column Treeview)
    Right panel — entity names + IDs for the selected project code

    Changes are held in a working copy and only committed on Save.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Manage Presets")
        self.geometry("680x580")
        self.resizable(True, True)
        self.grab_set()

        self._presets: dict[str, list[dict[str, str]]] = {}
        self._selected_code: str = ""
        self._analysis_types: list[str] = []
        self._content: ctk.CTkFrame | None = None
        self._top_minsize: int = 280
        self._drag_y: int = 0

        self._build()
        self._load_from_manager()

    # ------------------------------------------------------------------
    # Build layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Row 0 — title
        ctk.CTkLabel(
            self, text="Manage Presets",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(16, 8), sticky="w")

        # Row 1 — resizable content (custom CTK sash, no ttk.PanedWindow)
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, padx=20, pady=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=0, minsize=self._top_minsize)  # top: fixed
        content.rowconfigure(1, weight=0)                              # sash
        content.rowconfigure(2, weight=1)                              # bottom: fills rest
        self._content = content

        # ------------------------------------------------------------------ #
        # TOP SECTION — Project Codes (left) + Entity Names (right)
        # ------------------------------------------------------------------ #
        top = ctk.CTkFrame(content, fg_color="transparent")
        top.grid(row=0, column=0, sticky="nsew")
        top.grid_propagate(False)  # size controlled by rowconfigure, not by children
        top.columnconfigure(0, weight=1)
        top.columnconfigure(2, weight=2)
        top.rowconfigure(1, weight=1)

        # --- Left: project codes ---
        self._project_header = ctk.CTkLabel(
            top, text="Project Codes",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        )
        self._project_header.grid(row=0, column=0, sticky="w", pady=(0, 4))

        proj_wrap = ctk.CTkFrame(top, fg_color="transparent")
        proj_wrap.grid(row=1, column=0, sticky="nsew")
        proj_wrap.columnconfigure(0, weight=1)
        proj_wrap.rowconfigure(0, weight=1)

        apply_table_style("Presets.Project.Treeview")
        self._project_tree = ttk.Treeview(
            proj_wrap, style="Presets.Project.Treeview",
            show="tree", selectmode="browse",
        )
        self._project_tree.grid(row=0, column=0, sticky="nsew")
        proj_sb = make_scrollbar(proj_wrap, "vertical", self._project_tree.yview)
        self._project_tree.configure(yscrollcommand=proj_sb.set)
        proj_sb.grid(row=0, column=1, sticky="ns")
        self._project_tree.bind("<<TreeviewSelect>>", self._on_project_select)
        self._project_tree.bind("<Double-1>", lambda _e: self._edit_project())

        proj_btn_row = ctk.CTkFrame(top, fg_color="transparent")
        proj_btn_row.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkButton(
            proj_btn_row, text="+ Add", width=72,
            command=self._add_project,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            proj_btn_row, text="✎ Edit", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._edit_project,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            proj_btn_row, text="− Del", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._del_project,
        ).pack(side="left")

        # --- Separator ---
        sep = ctk.CTkFrame(top, width=1, fg_color=["gray70", "gray35"])
        sep.grid(row=0, column=1, rowspan=3, sticky="ns", padx=12)

        # --- Right: entity names ---
        self._name_header = ctk.CTkLabel(
            top, text="Entity Names",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        )
        self._name_header.grid(row=0, column=2, sticky="w", pady=(0, 4))

        name_wrap = ctk.CTkFrame(top, fg_color="transparent")
        name_wrap.grid(row=1, column=2, sticky="nsew")
        name_wrap.columnconfigure(0, weight=1)
        name_wrap.rowconfigure(0, weight=1)

        apply_table_style("Presets.Name.Treeview")
        self._name_tree = ttk.Treeview(
            name_wrap, style="Presets.Name.Treeview",
            columns=("name", "id"), show="headings", selectmode="browse",
        )
        self._name_tree.heading("name", text="Entity Name")
        self._name_tree.heading("id",   text="Entity ID")
        self._name_tree.column("name", width=180, stretch=True)
        self._name_tree.column("id",   width=100, stretch=False)
        self._name_tree.grid(row=0, column=0, sticky="nsew")
        name_sb = make_scrollbar(name_wrap, "vertical", self._name_tree.yview)
        self._name_tree.configure(yscrollcommand=name_sb.set)
        name_sb.grid(row=0, column=1, sticky="ns")
        self._name_tree.bind("<Double-1>", lambda _e: self._edit_name())

        name_btn_row = ctk.CTkFrame(top, fg_color="transparent")
        name_btn_row.grid(row=2, column=2, sticky="ew", pady=(4, 0))
        ctk.CTkButton(
            name_btn_row, text="+ Add", width=72,
            command=self._add_name,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            name_btn_row, text="✎ Edit", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._edit_name,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            name_btn_row, text="− Del", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._del_name,
        ).pack(side="left")

        # ------------------------------------------------------------------ #
        # SASH — custom CTK draggable divider
        # ------------------------------------------------------------------ #
        sash = ctk.CTkFrame(content, height=8, fg_color=["gray75", "gray30"])
        sash.configure(cursor="sb_v_double_arrow")
        sash.grid(row=1, column=0, sticky="ew", pady=(4, 4))
        sash.bind("<Button-1>", self._on_sash_press)
        sash.bind("<B1-Motion>", self._on_sash_drag)

        # ------------------------------------------------------------------ #
        # BOTTOM SECTION — Analysis Types
        # ------------------------------------------------------------------ #
        bottom = ctk.CTkFrame(content, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="nsew")
        bottom.grid_propagate(False)  # size controlled by remaining space, not by children
        bottom.columnconfigure(0, weight=1)
        bottom.rowconfigure(1, weight=1)

        ctk.CTkLabel(
            bottom, text="Analysis Types",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        anal_wrap = ctk.CTkFrame(bottom, fg_color="transparent")
        anal_wrap.grid(row=1, column=0, sticky="nsew")
        anal_wrap.columnconfigure(0, weight=1)
        anal_wrap.rowconfigure(0, weight=1)

        apply_table_style("Presets.Analysis.Treeview")
        self._analysis_tree = ttk.Treeview(
            anal_wrap, style="Presets.Analysis.Treeview",
            columns=("type",), show="headings", selectmode="browse",
        )
        self._analysis_tree.heading("type", text="Analysis Type")
        self._analysis_tree.column("type", width=300, stretch=True)
        self._analysis_tree.grid(row=0, column=0, sticky="nsew")
        anal_sb = make_scrollbar(anal_wrap, "vertical", self._analysis_tree.yview)
        self._analysis_tree.configure(yscrollcommand=anal_sb.set)
        anal_sb.grid(row=0, column=1, sticky="ns")

        analysis_btn_row = ctk.CTkFrame(bottom, fg_color="transparent")
        analysis_btn_row.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkButton(
            analysis_btn_row, text="+ Add", width=72,
            command=self._add_analysis,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            analysis_btn_row, text="✎ Edit", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._edit_analysis,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            analysis_btn_row, text="− Del", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._del_analysis,
        ).pack(side="left", padx=(0, 16))
        ctk.CTkButton(
            analysis_btn_row, text="↑ Up", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._move_analysis_up,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            analysis_btn_row, text="↓ Down", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._move_analysis_down,
        ).pack(side="left")

        # Row 2 — footer
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, padx=20, pady=(8, 16), sticky="ew")
        footer.columnconfigure(0, weight=1)

        ctk.CTkButton(
            footer, text="Import from file…", width=140,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._import_from_file,
        ).grid(row=0, column=0, sticky="w")

        btn_right = ctk.CTkFrame(footer, fg_color="transparent")
        btn_right.grid(row=0, column=1, sticky="e")
        ctk.CTkButton(
            btn_right, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(
            btn_right, text="Save", width=100,
            command=self._save,
        ).pack(side="left")

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _load_from_manager(self) -> None:
        mgr = get_settings_manager()
        self._presets = copy.deepcopy(mgr.settings.project_presets)
        self._analysis_types = mgr.get_analysis_types()
        self._refresh_project_list()
        self._refresh_analysis_list()

    # ------------------------------------------------------------------
    # Sash drag
    # ------------------------------------------------------------------

    def _on_sash_press(self, event) -> None:
        self._drag_y = event.y_root

    def _on_sash_drag(self, event) -> None:
        dy = event.y_root - self._drag_y
        self._drag_y = event.y_root
        new_h = max(100, self._top_minsize + dy)
        available = self._content.winfo_height()
        new_h = min(new_h, available - 120)  # keep bottom section ≥ 120 px
        self._top_minsize = new_h
        self._content.rowconfigure(0, minsize=new_h)

    def _refresh_project_list(self, select_code: str = "") -> None:
        self._project_tree.delete(*self._project_tree.get_children())
        for code in sorted(self._presets.keys()):
            self._project_tree.insert("", "end", iid=code, text=code)
        # Restore selection
        target = select_code or self._selected_code
        if target and target in self._presets:
            self._project_tree.selection_set(target)
            self._project_tree.focus(target)
        else:
            self._selected_code = ""
            self._refresh_name_list()

    def _refresh_name_list(self) -> None:
        self._name_tree.delete(*self._name_tree.get_children())
        header_text = (
            f"Entity Names ({self._selected_code})"
            if self._selected_code else "Entity Names"
        )
        self._name_header.configure(text=header_text)
        if self._selected_code and self._selected_code in self._presets:
            for entry in self._presets[self._selected_code]:
                self._name_tree.insert(
                    "", "end",
                    iid=entry["name"],
                    values=(entry["name"], entry.get("id", "")),
                )

    # ------------------------------------------------------------------
    # Input helper
    # ------------------------------------------------------------------

    def _ask_value(self, title: str, label: str, initial: str = "") -> str | None:
        """Single-field modal dialog with a pre-filled CTkEntry. Returns None if cancelled."""
        result: list[str | None] = [None]

        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.geometry("340x130")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.columnconfigure(0, weight=1)

        ctk.CTkLabel(dlg, text=label, anchor="w").grid(
            row=0, column=0, padx=16, pady=(14, 4), sticky="ew")

        var = ctk.StringVar(value=initial)
        entry = ctk.CTkEntry(dlg, textvariable=var)
        entry.grid(row=1, column=0, padx=16, sticky="ew")
        entry.focus_set()
        entry.select_range(0, "end")

        def _ok():
            result[0] = var.get()
            dlg.destroy()

        entry.bind("<Return>", lambda _e: _ok())
        entry.bind("<Escape>", lambda _e: dlg.destroy())

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=16, pady=12, sticky="e")
        ctk.CTkButton(
            btn_row, text="Cancel", width=80,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=dlg.destroy,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="OK", width=80, command=_ok).pack(side="left")

        dlg.wait_window()
        return result[0]

    def _ask_name_and_id(
        self, title: str,
        initial_name: str = "", initial_id: str = "",
    ) -> tuple[str, str] | None:
        """Two-field modal dialog for entity name + entity ID.

        Returns (name, id) on confirm, or None if cancelled.
        """
        result: list[tuple[str, str] | None] = [None]

        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.geometry("340x190")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.columnconfigure(0, weight=1)

        ctk.CTkLabel(dlg, text="Entity name:", anchor="w").grid(
            row=0, column=0, padx=16, pady=(14, 2), sticky="ew")
        name_var = ctk.StringVar(value=initial_name)
        name_entry = ctk.CTkEntry(dlg, textvariable=name_var)
        name_entry.grid(row=1, column=0, padx=16, sticky="ew")

        ctk.CTkLabel(dlg, text="Entity ID (optional — leave blank to auto-generate):",
                     anchor="w").grid(row=2, column=0, padx=16, pady=(10, 2), sticky="ew")
        id_var = ctk.StringVar(value=initial_id)
        id_entry = ctk.CTkEntry(dlg, textvariable=id_var)
        id_entry.grid(row=3, column=0, padx=16, sticky="ew")

        def _ok():
            result[0] = (name_var.get(), id_var.get().strip().upper())
            dlg.destroy()

        name_entry.bind("<Return>", lambda _e: id_entry.focus_set())
        id_entry.bind("<Return>",   lambda _e: _ok())
        dlg.bind("<Escape>", lambda _e: dlg.destroy())

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.grid(row=4, column=0, padx=16, pady=12, sticky="e")
        ctk.CTkButton(
            btn_row, text="Cancel", width=80,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=dlg.destroy,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(btn_row, text="OK", width=80, command=_ok).pack(side="left")

        name_entry.focus_set()
        if initial_name:
            name_entry.select_range(0, "end")
        dlg.wait_window()
        return result[0]

    # ------------------------------------------------------------------
    # Event handlers — left panel
    # ------------------------------------------------------------------

    def _on_project_select(self, _event=None) -> None:
        sel = self._project_tree.selection()
        self._selected_code = sel[0] if sel else ""
        self._refresh_name_list()

    def _add_project(self) -> None:
        dlg = ctk.CTkInputDialog(text="Enter new project code:", title="Add Project Code")
        value = dlg.get_input()
        if value is None:
            return
        code = value.strip().upper()
        if not code:
            return
        if code in self._presets:
            messagebox.showwarning(
                "Duplicate", f"Project code \"{code}\" already exists.",
                parent=self,
            )
            return
        self._presets[code] = []
        self._selected_code = code
        self._refresh_project_list(select_code=code)
        self._refresh_name_list()

    def _del_project(self) -> None:
        if not self._selected_code:
            return
        if not messagebox.askyesno(
            "Delete Project Code",
            f"Remove \"{self._selected_code}\" and all its entity names?",
            parent=self,
        ):
            return
        del self._presets[self._selected_code]
        self._selected_code = ""
        self._refresh_project_list()
        self._refresh_name_list()

    def _edit_project(self) -> None:
        if not self._selected_code:
            return
        new_code = self._ask_value(
            "Edit Project Code", "Project code:", self._selected_code)
        if new_code is None:
            return
        new_code = new_code.strip().upper()
        if not new_code or new_code == self._selected_code:
            return
        if new_code in self._presets:
            messagebox.showwarning(
                "Duplicate", f"Project code \"{new_code}\" already exists.",
                parent=self,
            )
            return
        # Rename: move entries under new key
        self._presets[new_code] = self._presets.pop(self._selected_code)
        self._selected_code = new_code
        self._refresh_project_list(select_code=new_code)
        self._refresh_name_list()

    # ------------------------------------------------------------------
    # Event handlers — right panel
    # ------------------------------------------------------------------

    def _add_name(self) -> None:
        if not self._selected_code:
            messagebox.showwarning(
                "No Project Selected",
                "Select a project code first.",
                parent=self,
            )
            return

        values = self._ask_name_and_id(f"Add Entry — {self._selected_code}")
        if values is None:
            return
        name, entity_id = values
        name = name.strip()
        if not name:
            return

        existing_names = [e["name"] for e in self._presets[self._selected_code]]
        if name in existing_names:
            messagebox.showwarning(
                "Duplicate",
                f"\"{name}\" already exists for {self._selected_code}.",
                parent=self,
            )
            return

        self._presets[self._selected_code].append({"name": name, "id": entity_id})
        self._refresh_name_list()

    def _del_name(self) -> None:
        if not self._selected_code:
            return
        sel = self._name_tree.selection()
        if not sel:
            return
        name = self._name_tree.set(sel[0], "name")
        entries = self._presets[self._selected_code]
        self._presets[self._selected_code] = [e for e in entries if e["name"] != name]
        self._refresh_name_list()

    def _edit_name(self) -> None:
        if not self._selected_code:
            return
        sel = self._name_tree.selection()
        if not sel:
            return
        old_name = self._name_tree.set(sel[0], "name")
        old_id   = self._name_tree.set(sel[0], "id")

        values = self._ask_name_and_id(
            f"Edit Entry — {self._selected_code}",
            initial_name=old_name,
            initial_id=old_id,
        )
        if values is None:
            return
        new_name, new_id = values
        new_name = new_name.strip()
        if not new_name:
            return

        entries = self._presets[self._selected_code]
        if new_name != old_name:
            existing_names = [e["name"] for e in entries if e["name"] != old_name]
            if new_name in existing_names:
                messagebox.showwarning(
                    "Duplicate",
                    f"\"{new_name}\" already exists for {self._selected_code}.",
                    parent=self,
                )
                return

        for entry in entries:
            if entry["name"] == old_name:
                entry["name"] = new_name
                entry["id"]   = new_id
                break
        self._refresh_name_list()
        # Re-select the edited row
        if new_name in self._name_tree.get_children():
            self._name_tree.selection_set(new_name)
            self._name_tree.focus(new_name)

    # ------------------------------------------------------------------
    # Analysis Types helpers
    # ------------------------------------------------------------------

    def _refresh_analysis_list(self, select_value: str = "") -> None:
        self._analysis_tree.delete(*self._analysis_tree.get_children())
        for atype in self._analysis_types:
            self._analysis_tree.insert("", "end", iid=atype, values=(atype,))
        target = select_value or ""
        if target and target in self._analysis_tree.get_children():
            self._analysis_tree.selection_set(target)
            self._analysis_tree.focus(target)

    def _add_analysis(self) -> None:
        value = self._ask_value("Add Analysis Type", "Analysis type name:")
        if value is None:
            return
        value = value.strip().upper()
        if not value:
            return
        if value in self._analysis_types:
            messagebox.showwarning(
                "Duplicate", f'"{value}" already exists.', parent=self)
            return
        self._analysis_types.append(value)
        self._refresh_analysis_list(select_value=value)

    def _edit_analysis(self) -> None:
        sel = self._analysis_tree.selection()
        if not sel:
            return
        old = sel[0]
        value = self._ask_value("Edit Analysis Type", "Analysis type name:", initial=old)
        if value is None:
            return
        value = value.strip().upper()
        if not value or value == old:
            return
        if value in self._analysis_types:
            messagebox.showwarning(
                "Duplicate", f'"{value}" already exists.', parent=self)
            return
        idx = self._analysis_types.index(old)
        self._analysis_types[idx] = value
        self._refresh_analysis_list(select_value=value)

    def _del_analysis(self) -> None:
        sel = self._analysis_tree.selection()
        if not sel:
            return
        value = sel[0]
        if not messagebox.askyesno(
            "Delete Analysis Type", f'Remove "{value}"?', parent=self
        ):
            return
        self._analysis_types.remove(value)
        self._refresh_analysis_list()

    def _move_analysis_up(self) -> None:
        sel = self._analysis_tree.selection()
        if not sel:
            return
        value = sel[0]
        idx = self._analysis_types.index(value)
        if idx == 0:
            return
        self._analysis_types[idx], self._analysis_types[idx - 1] = (
            self._analysis_types[idx - 1], self._analysis_types[idx]
        )
        self._refresh_analysis_list(select_value=value)

    def _move_analysis_down(self) -> None:
        sel = self._analysis_tree.selection()
        if not sel:
            return
        value = sel[0]
        idx = self._analysis_types.index(value)
        if idx == len(self._analysis_types) - 1:
            return
        self._analysis_types[idx], self._analysis_types[idx + 1] = (
            self._analysis_types[idx + 1], self._analysis_types[idx]
        )
        self._refresh_analysis_list(select_value=value)

    # ------------------------------------------------------------------
    # Import
    # ------------------------------------------------------------------

    def _import_from_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Import Presets from JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            parent=self,
        )
        if not path:
            return
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Import Failed", str(exc), parent=self)
            return

        incoming = raw.get("project_presets", {})
        if not isinstance(incoming, dict):
            messagebox.showerror(
                "Import Failed",
                "File does not contain a valid \"project_presets\" mapping.",
                parent=self,
            )
            return

        added_codes = 0
        added_names = 0
        for code, entries in incoming.items():
            code = str(code).strip().upper()
            if not code or not isinstance(entries, list):
                continue
            if code not in self._presets:
                self._presets[code] = []
                added_codes += 1
            existing_names = {e["name"] for e in self._presets[code]}
            for e in entries:
                if isinstance(e, str):
                    name, eid = e.strip(), ""
                elif isinstance(e, dict):
                    name = str(e.get("name", "")).strip()
                    eid  = str(e.get("id",   "")).strip()
                else:
                    continue
                if name and name not in existing_names:
                    self._presets[code].append({"name": name, "id": eid})
                    existing_names.add(name)
                    added_names += 1

        self._refresh_project_list()
        messagebox.showinfo(
            "Import Complete",
            f"Imported {added_codes} new project code(s) and {added_names} new name(s).",
            parent=self,
        )

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self) -> None:
        mgr = get_settings_manager()
        mgr.settings.project_presets = self._presets
        mgr.set_analysis_types(self._analysis_types)
        mgr.save()
        self.destroy()
