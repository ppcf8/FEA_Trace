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
from app.gui.theme import apply_table_style


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
        self.geometry("680x420")
        self.resizable(True, True)
        self.grab_set()

        self._presets: dict[str, list[dict[str, str]]] = {}
        self._selected_code: str = ""

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

        # Row 1 — two-panel body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, padx=20, pady=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.columnconfigure(2, weight=2)
        body.rowconfigure(1, weight=1)

        # --- Left panel ---
        self._project_header = ctk.CTkLabel(
            body, text="Project Codes",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        )
        self._project_header.grid(row=0, column=0, sticky="w", pady=(0, 4))

        apply_table_style("Presets.Project.Treeview")
        self._project_tree = ttk.Treeview(
            body, style="Presets.Project.Treeview",
            show="tree", selectmode="browse",
        )
        self._project_tree.grid(row=1, column=0, sticky="nsew")
        self._project_tree.bind("<<TreeviewSelect>>", self._on_project_select)

        proj_btn_row = ctk.CTkFrame(body, fg_color="transparent")
        proj_btn_row.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        ctk.CTkButton(
            proj_btn_row, text="+ Add", width=72,
            command=self._add_project,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            proj_btn_row, text="− Del", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._del_project,
        ).pack(side="left")

        # --- Separator ---
        sep = ctk.CTkFrame(body, width=1, fg_color=["gray70", "gray35"])
        sep.grid(row=0, column=1, rowspan=3, sticky="ns", padx=12)

        # --- Right panel ---
        self._name_header = ctk.CTkLabel(
            body, text="Entity Names",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        )
        self._name_header.grid(row=0, column=2, sticky="w", pady=(0, 4))

        apply_table_style("Presets.Name.Treeview")
        self._name_tree = ttk.Treeview(
            body, style="Presets.Name.Treeview",
            columns=("name", "id"), show="headings", selectmode="browse",
        )
        self._name_tree.heading("name", text="Entity Name")
        self._name_tree.heading("id",   text="Entity ID")
        self._name_tree.column("name", width=180, stretch=True)
        self._name_tree.column("id",   width=100, stretch=False)
        self._name_tree.grid(row=1, column=2, sticky="nsew")

        name_btn_row = ctk.CTkFrame(body, fg_color="transparent")
        name_btn_row.grid(row=2, column=2, sticky="ew", pady=(4, 0))
        ctk.CTkButton(
            name_btn_row, text="+ Add", width=72,
            command=self._add_name,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            name_btn_row, text="− Del", width=72,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._del_name,
        ).pack(side="left")

        # Row 2 — action buttons
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, padx=20, pady=(12, 16), sticky="ew")
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
        self._refresh_project_list()

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

        dlg_name = ctk.CTkInputDialog(
            text=f"Entity name for \"{self._selected_code}\":",
            title="Add Entity Name",
        )
        name = dlg_name.get_input()
        if name is None:
            return
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

        dlg_id = ctk.CTkInputDialog(
            text="Entity ID (optional — leave blank to auto-generate):",
            title="Entity ID",
        )
        raw_id = dlg_id.get_input()
        entity_id = raw_id.strip().upper() if raw_id is not None else ""

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
        mgr.save()
        self.destroy()
