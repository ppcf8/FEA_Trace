"""
frames/version_frame.py — Version Detail View
"""
from __future__ import annotations

import tkinter as tk
import tkinter.ttk as ttk
import tkinter.font as tkfont
import customtkinter as ctk
from pathlib import Path
from typing import Optional
from PIL import Image

from schema import IterationStatus, VersionStatus, VERSION_STATUS_TRANSITIONS
from app.core.models import FEAProject
from app.gui.theme import apply_table_style, make_scrollbar, add_hint
from app.gui.hints import VERSION_TOOLTIP

_ICONS_DIR = Path(__file__).parent.parent.parent / "assets" / "icons"
_IMG_EDIT  = ctk.CTkImage(Image.open(_ICONS_DIR / "edit.png"), size=(16, 16))


_STATUS_BADGE = {
    "WIP":        ("●  WIP",        "#4A90D9"),
    "production": ("●  Production", "#2D8A4E"),
    "deprecated": ("●  Deprecated", "#888888"),
}

_SOLVER_BADGE = {
    "IMPLICIT": "⚙  IMPLICIT",
    "EXPLICIT": "⚡  EXPLICIT",
    "MBD":      "🔗  MBD",
}

_COL_WEIGHTS = {
    "id":             1,
    "status":         2,
    "solver_type":    2,
    "analysis_types": 3,
    "description":    7,
    "runs":           1,
    "created_by":     3,
    "created_on":     3,
}  # total = 22 units

_NO_FILTER_COLS   = frozenset({"description", "runs"})
_DATE_COLS        = frozenset({"created_on"})
_MULTI_VALUE_COLS = frozenset({"analysis_types"})

_ITER_STATUS_COLORS = {
    "WIP":        "#4A90D9",
    "production": "#2D8A4E",
    "deprecated": "#888888",
}


class VersionFrame(ctk.CTkFrame):

    def __init__(self, master, window):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self._window       = window
        self._project:     Optional[FEAProject] = None
        self._version_id:  Optional[str]        = None
        self._all_rows:    list[dict]    = []
        self._sort_col:    str | None    = None
        self._sort_reverse: bool         = False
        self._col_filters: dict[str, set[str]] = {}
        self._search_var:  ctk.StringVar        = ctk.StringVar()
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._build_header()
        self._build_metadata_panel()
        self._build_notes_panel()
        self._build_iter_table()
        self._build_action_bar()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        hdr.columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            hdr, text="Version",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="w")
        add_hint(self._title_label, VERSION_TOOLTIP)

        self._status_badge = ctk.CTkLabel(
            hdr, text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6, padx=12, pady=4,
        )
        self._status_badge.grid(row=0, column=1, sticky="e")

    def _build_metadata_panel(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="ew", padx=24, pady=16)
        panel.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            panel, text="Description",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw", width=100,
        ).grid(row=0, column=0, padx=(16, 4), pady=(12, 6), sticky="nw")

        self._description_label = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(size=12),
            anchor="nw", justify="left", wraplength=600,
        )
        self._description_label.grid(row=0, column=1, columnspan=3,
                                     padx=(0, 16), pady=(12, 6), sticky="nw")

        fields = [("Created By", "_created_by"), ("Created On", "_created_on")]
        self._meta: dict[str, ctk.CTkLabel] = {}
        for col_i, (label, key) in enumerate(fields):
            ctk.CTkLabel(
                panel, text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w", width=100,
            ).grid(row=1, column=col_i * 2, padx=(16, 4), pady=(0, 6), sticky="w")
            val = ctk.CTkLabel(panel, text="—", font=ctk.CTkFont(size=12), anchor="w")
            val.grid(row=1, column=col_i * 2 + 1,
                     padx=(0, 24), pady=(0, 6), sticky="w")
            self._meta[key] = val

        self._transition_frame = ctk.CTkFrame(panel, fg_color="transparent")
        self._transition_frame.grid(row=0, column=4, rowspan=2,
                                    padx=(0, 16), pady=12, sticky="ne")

    def _build_notes_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color="transparent")
        panel.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
        panel.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            panel, text="Notes",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw", width=100,
        ).grid(row=0, column=0, padx=(0, 4), sticky="nw")

        self._notes_label = ctk.CTkLabel(
            panel, text="",
            font=ctk.CTkFont(size=12),
            anchor="nw", justify="left", wraplength=600,
        )
        self._notes_label.grid(row=0, column=1, sticky="w")

    def _build_iter_table(self) -> None:
        section = ctk.CTkFrame(self, fg_color="transparent")
        section.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0, 8))
        section.columnconfigure(0, weight=1)
        section.rowconfigure(2, weight=1)

        ctk.CTkLabel(
            section, text="Iterations",
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        search_row = ctk.CTkFrame(section, fg_color="transparent")
        search_row.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        search_row.columnconfigure(1, weight=1)
        ctk.CTkLabel(search_row, text="Search:", width=52,
                     font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(
            search_row, textvariable=self._search_var,
            placeholder_text="Filter all columns…", height=28, font=ctk.CTkFont(size=12),
        ).grid(row=0, column=1, sticky="ew", padx=(4, 4))
        ctk.CTkButton(
            search_row, text="✕", width=28, height=28,
            font=ctk.CTkFont(size=12),
            command=lambda: self._search_var.set(""),
        ).grid(row=0, column=2)

        cols = ("id", "status", "solver_type", "analysis_types",
                "description", "runs", "created_by", "created_on")
        self._table = ttk.Treeview(
            section, columns=cols, show="headings",
            selectmode="browse", height=7,
            style="Version.Treeview",
        )

        headings = {
            "id":             ("ID",          "center"),
            "status":         ("Status",      "w"),
            "solver_type":    ("Solver",      "w"),
            "analysis_types": ("Analysis",    "w"),
            "description":    ("Description", "w"),
            "runs":           ("Runs",        "center"),
            "created_by":     ("Created By",  "w"),
            "created_on":     ("Created On",  "w"),
        }
        self._headings = headings
        self._col_order = tuple(_COL_WEIGHTS.keys())

        for status, color in _ITER_STATUS_COLORS.items():
            self._table.tag_configure(f"iter_status_{status}", foreground=color)

        for col, (heading, anchor) in headings.items():
            self._table.heading(col, text=heading, anchor=anchor,
                                command=lambda c=col: self._on_sort(c))
            self._table.column(col, width=60, anchor=anchor, stretch=False)

        vsb = make_scrollbar(section, "vertical",   self._table.yview)
        hsb = make_scrollbar(section, "horizontal", self._table.xview)
        self._table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._table.grid(row=2, column=0, sticky="nsew")
        vsb.grid(row=2, column=1, sticky="ns")
        hsb.grid(row=3, column=0, sticky="ew")

        self._section = section
        self._table.bind("<<TreeviewSelect>>", self._on_iter_select)
        self._table.bind("<Button-3>", self._on_heading_right_click)
        section.bind("<Configure>", self._resize_columns)
        apply_table_style("Version.Treeview")
        ctk.AppearanceModeTracker.add(self._on_appearance_change)
        self._search_var.trace_add("write", lambda *_: self._refresh_table())

    def _build_action_bar(self) -> None:
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=4, column=0, sticky="ew", padx=24, pady=(4, 20))

        self._new_iter_btn = ctk.CTkButton(
            bar, text="+ New Iteration",
            width=160, height=36,
            font=ctk.CTkFont(size=13),
            command=self._on_new_iteration,
        )
        self._new_iter_btn.pack(side="left")

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, project: FEAProject, version_id: str) -> None:
        self._project    = project
        self._version_id = version_id

        v = project._get_version(version_id)

        apply_table_style("Version.Treeview")
        self._title_label.configure(text=f"Version  {v.id}")
        badge_text, badge_color = _STATUS_BADGE.get(
            v.status.value, (v.status.value, "#444444"))
        self._status_badge.configure(
            text=f"  {badge_text}  ",
            fg_color=badge_color, text_color="#FFFFFF",
        )
        self._description_label.configure(text=v.description.strip())
        self._meta["_created_by"].configure(text=v.created_by)
        self._meta["_created_on"].configure(text=v.created_on)

        notes_text = "\n".join(f"• {n}" for n in v.notes) if v.notes else "—"
        self._notes_label.configure(text=notes_text)

        self._populate_transition_buttons(v.status)
        is_wip = v.status == VersionStatus.WIP
        self._new_iter_btn.configure(state="normal" if is_wip else "disabled")
        self._all_rows     = []
        self._sort_col     = None
        self._sort_reverse = False
        self._col_filters  = {}
        self._search_var.set("")
        for col in self._col_order:
            self._update_heading(col)
        self._populate_table(v)

    def _populate_transition_buttons(self, current: VersionStatus) -> None:
        for w in self._transition_frame.winfo_children():
            w.destroy()

        ctk.CTkButton(
            self._transition_frame,
            image=_IMG_EDIT, text="Edit", compound="left",
            width=90, height=28,
            font=ctk.CTkFont(size=12),
            state="normal" if current == VersionStatus.WIP else "disabled",
            command=self._on_edit_version,
        ).pack(anchor="e", pady=(0, 8))

        allowed = VERSION_STATUS_TRANSITIONS.get(current, set())
        if not allowed:
            ctk.CTkLabel(
                self._transition_frame,
                text="Terminal state — no transitions",
                font=ctk.CTkFont(size=11),
            ).pack()
            return

        ctk.CTkLabel(
            self._transition_frame,
            text="Change Status",
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(anchor="e", pady=(0, 4))

        _LABELS = {
            VersionStatus.PRODUCTION: ("Promote to Production", "#2D8A4E"),
            VersionStatus.DEPRECATED: ("Mark Deprecated",       "#888888"),
            VersionStatus.WIP:        ("Revert to WIP",         "#4A90D9"),
        }
        for target in allowed:
            label, color = _LABELS.get(target, (target.value.title(), None))
            kwargs = dict(
                text=label, width=180, height=30,
                font=ctk.CTkFont(size=12),
                command=lambda t=target: self._on_status_change(t),
            )
            if color:
                kwargs["fg_color"] = color
            ctk.CTkButton(self._transition_frame, **kwargs).pack(anchor="e", pady=2)

    def _populate_table(self, v) -> None:
        self._all_rows = []
        for i in v.iterations:
            types       = ", ".join(i.analysis_types)
            desc        = i.description.strip().replace("\n", " ")
            if len(desc) > 55:
                desc = desc[:52] + "…"
            solver      = _SOLVER_BADGE.get(i.solver_type.value, i.solver_type.value)
            status_val  = i.status.value
            status_text = f"●  {status_val}" if status_val != "WIP" else "WIP"
            tag         = f"iter_status_{status_val}"
            self._all_rows.append({
                "iid":    i.id,
                "values": (i.id, status_text, solver, types, desc,
                           len(i.runs), i.created_by, i.created_on),
                "tags":   (tag,),
            })
        self._refresh_table()

    def _refresh_table(self) -> None:
        rows  = self._all_rows
        query = self._search_var.get().strip().lower()
        if query:
            rows = [r for r in rows
                    if any(query in str(v).lower() for v in r["values"])]
        for col, allowed in self._col_filters.items():
            if allowed:
                idx = self._col_order.index(col)
                if col in _DATE_COLS:
                    rows = [r for r in rows
                            if str(r["values"][idx]).split(" ")[0] in allowed]
                elif col in _MULTI_VALUE_COLS:
                    rows = [r for r in rows
                            if any(v.strip() in allowed
                                   for v in str(r["values"][idx]).split(","))]
                else:
                    rows = [r for r in rows if str(r["values"][idx]) in allowed]
        if self._sort_col is not None:
            idx  = self._col_order.index(self._sort_col)
            rows = sorted(rows,
                          key=lambda r: str(r["values"][idx]).lower(),
                          reverse=self._sort_reverse)
        for row in self._table.get_children():
            self._table.delete(row)
        for r in rows:
            self._table.insert("", "end", iid=r["iid"],
                               tags=r["tags"], values=r["values"])

    def _on_sort(self, col: str) -> None:
        if self._sort_col == col:
            self._sort_reverse = not self._sort_reverse
        else:
            self._sort_col, self._sort_reverse = col, False
        for c in self._col_order:
            self._update_heading(c)
        self._refresh_table()

    def _on_heading_right_click(self, event) -> None:
        if self._table.identify_region(event.x, event.y) != "heading":
            return
        col_id = self._table.identify_column(event.x)
        if not col_id or col_id == "#0":
            return
        col_name = self._col_order[int(col_id[1:]) - 1]
        if col_name in _NO_FILTER_COLS:
            return
        self._open_filter_popup(col_name, event.x_root, event.y_root)

    def _update_heading(self, col: str) -> None:
        lbl, _     = self._headings[col]
        sort_ind   = (" ▼" if self._sort_reverse else " ▲") if self._sort_col == col else ""
        filter_ind = " ⊿" if self._col_filters.get(col) else ""
        self._table.heading(col, text=f"{lbl}{sort_ind}{filter_ind}")

    def _open_filter_popup(self, col: str, x_root: int = 0, y_root: int = 0) -> None:
        col_idx = self._col_order.index(col)
        is_date = col in _DATE_COLS

        # Cascading: build candidate rows from all filters except this col + search
        candidate_rows = self._all_rows
        query = self._search_var.get().strip().lower()
        if query:
            candidate_rows = [r for r in candidate_rows
                              if any(query in str(v).lower() for v in r["values"])]
        for other_col, allowed in self._col_filters.items():
            if other_col != col and allowed:
                other_idx = self._col_order.index(other_col)
                if other_col in _DATE_COLS:
                    candidate_rows = [r for r in candidate_rows
                                      if str(r["values"][other_idx]).split(" ")[0] in allowed]
                elif other_col in _MULTI_VALUE_COLS:
                    candidate_rows = [r for r in candidate_rows
                                      if any(v.strip() in allowed
                                             for v in str(r["values"][other_idx]).split(","))]
                else:
                    candidate_rows = [r for r in candidate_rows
                                      if str(r["values"][other_idx]) in allowed]

        is_multi = col in _MULTI_VALUE_COLS
        if is_date:
            raw_vals = {str(r["values"][col_idx]).split(" ")[0] for r in candidate_rows}
        elif is_multi:
            raw_vals = {v.strip()
                        for r in candidate_rows
                        for v in str(r["values"][col_idx]).split(",")
                        if v.strip()}
        else:
            raw_vals = {str(r["values"][col_idx]) for r in candidate_rows}
        unique_vals = sorted(raw_vals, key=str.lower)

        if not unique_vals:
            return
        current = self._col_filters.get(col, set())

        popup = ctk.CTkToplevel(self._window)
        popup.title(f"Filter: {self._headings[col][0]}")
        popup.resizable(True, True)
        popup.grab_set()
        popup.columnconfigure(0, weight=1)
        popup.rowconfigure(1, weight=1)

        h = min(40 * len(unique_vals) + 130, 400) + (34 if is_date else 0)
        _f = tkfont.Font(size=11)
        max_text_w = max((_f.measure(v if v else "(empty)") for v in unique_vals), default=0)
        popup_w = max(220, max_text_w + 80)
        popup.geometry(f"{popup_w}x{h}+{x_root}+{y_root}")
        popup.minsize(180, 150)

        quick = ctk.CTkFrame(popup, fg_color="transparent")
        quick.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        check_vars: dict[str, tk.IntVar] = {}

        ctk.CTkButton(quick, text="All", width=70, height=26,
                      font=ctk.CTkFont(size=11),
                      command=lambda: [v.set(1) for v in check_vars.values()]
                      ).pack(side="left", padx=(0, 4))
        ctk.CTkButton(quick, text="None", width=70, height=26,
                      font=ctk.CTkFont(size=11),
                      command=lambda: [v.set(0) for v in check_vars.values()]
                      ).pack(side="left")

        scroll = ctk.CTkScrollableFrame(popup, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        if is_date:
            sort_desc = [True]  # default: newest → oldest

            def _rebuild_checkboxes():
                saved = {v: var.get() for v, var in check_vars.items()}
                for w in scroll.winfo_children():
                    w.destroy()
                check_vars.clear()
                for val in sorted(unique_vals, reverse=sort_desc[0]):
                    checked = saved.get(val, 1 if (not current or val in current) else 0)
                    var = tk.IntVar(value=checked)
                    check_vars[val] = var
                    ctk.CTkCheckBox(scroll, text=val if val else "(empty)",
                                    variable=var,
                                    font=ctk.CTkFont(size=11)).pack(anchor="w", pady=1)

            def _toggle_sort():
                sort_desc[0] = not sort_desc[0]
                sort_btn.configure(text="↓ Newest" if sort_desc[0] else "↑ Oldest")
                _rebuild_checkboxes()

            sort_btn = ctk.CTkButton(quick, text="↓ Newest", width=72, height=26,
                                     font=ctk.CTkFont(size=11),
                                     fg_color="transparent", border_width=1,
                                     text_color=["#1A1A1A", "#DCE4EE"],
                                     command=_toggle_sort)
            sort_btn.pack(side="left", padx=(4, 0))
            _rebuild_checkboxes()
        else:
            for val in unique_vals:
                checked = 1 if (not current or val in current) else 0
                var = tk.IntVar(value=checked)
                check_vars[val] = var
                ctk.CTkCheckBox(scroll, text=val if val else "(empty)",
                                variable=var,
                                font=ctk.CTkFont(size=11)).pack(anchor="w", pady=1)

        btn_row = ctk.CTkFrame(popup, fg_color="transparent")
        btn_row.grid(row=2, column=0, sticky="ew", padx=8, pady=(2, 8))

        def _apply():
            selected = {v for v, var in check_vars.items() if var.get()}
            if selected == set(unique_vals):
                self._col_filters.pop(col, None)
            else:
                self._col_filters[col] = selected
            self._update_heading(col)
            self._refresh_table()
            popup.destroy()

        ctk.CTkButton(btn_row, text="Apply", height=28, font=ctk.CTkFont(size=12),
                      command=_apply).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(btn_row, text="Cancel", height=28, font=ctk.CTkFont(size=12),
                      fg_color="transparent", border_width=1,
                      text_color=["#1A1A1A", "#DCE4EE"],
                      command=popup.destroy).pack(side="left", fill="x", expand=True)
        popup.bind("<Escape>", lambda e: popup.destroy())

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _on_iter_select(self, _event) -> None:
        sel = self._table.selection()
        if sel and self._project and self._version_id:
            self._window.show_iteration(
                str(self._project.path), self._version_id, sel[0])

    def _on_status_change(self, target: VersionStatus) -> None:
        if not self._project or not self._version_id:
            return

        revert_reason = None
        if target == VersionStatus.WIP:
            from app.gui.dialogs.revert_reason_dialog import RevertReasonDialog
            dlg = RevertReasonDialog(self._window, self._version_id)
            self._window.wait_window(dlg)
            if dlg.result is None:
                return
            revert_reason = dlg.result

        try:
            self._project.update_version_status(
                self._version_id, target, revert_reason=revert_reason)
        except Exception as exc:
            self._show_error("Status Change Failed", str(exc))
            return

        self._window.refresh_sidebar()
        self._window.set_status(f"Version {self._version_id} → {target.value}")
        self.load(self._project, self._version_id)

    def _on_edit_version(self) -> None:
        if not self._project or not self._version_id:
            return
        from app.gui.dialogs.edit_version_dialog import EditVersionDialog
        v = self._project._get_version(self._version_id)
        dlg = EditVersionDialog(self._window, v)
        self._window.wait_window(dlg)
        if dlg.result is None:
            return
        description, notes, created_by = dlg.result
        try:
            self._project.update_version_metadata(self._version_id, description, notes, created_by)
        except Exception as exc:
            self._show_error("Edit Version Failed", str(exc))
            return
        self.load(self._project, self._version_id)
        self._window.set_status(f"Version {self._version_id} metadata updated.")

    def _on_new_iteration(self) -> None:
        if not self._project or not self._version_id:
            return
        from app.gui.dialogs.new_iteration_dialog import NewIterationDialog
        dlg = NewIterationDialog(self._window)
        self._window.wait_window(dlg)
        if dlg.result is None:
            return

        solver_type, analysis_types, description, created_by = dlg.result
        try:
            self._project.add_iteration(
                self._version_id, solver_type,
                analysis_types, description, created_by,
            )
        except Exception as exc:
            self._show_error("Create Iteration Failed", str(exc))
            return

        v = self._project._get_version(self._version_id)
        self._populate_table(v)
        self._window.refresh_sidebar()
        self._window.set_status("Iteration created successfully.")

    # ------------------------------------------------------------------
    # Styling
    # ------------------------------------------------------------------

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
        apply_table_style("Version.Treeview")

    def _show_error(self, title: str, message: str) -> None:
        from tkinter import messagebox
        messagebox.showerror(title, message, parent=self._window)
