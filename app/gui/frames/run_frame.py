"""
frames/run_frame.py — Run Detail View
"""
from __future__ import annotations

import tkinter.ttk as ttk
import customtkinter as ctk
from typing import Optional

from schema import RunStatus, RUN_STATUS_TRANSITIONS
from app.core.models import FEAProject


_STATUS_BADGE = {
    "WIP":       ("●  WIP",       "#4A90D9"),
    "converged": ("●  Converged", "#2D8A4E"),
    "diverged":  ("●  Diverged",  "#C0392B"),
    "partial":   ("●  Partial",   "#B8860B"),
    "aborted":   ("●  Aborted",   "#666666"),
}

_TRANSITION_LABELS: dict[RunStatus, tuple[str, str]] = {
    RunStatus.CONVERGED: ("Mark Converged", "#2D8A4E"),
    RunStatus.DIVERGED:  ("Mark Diverged",  "#C0392B"),
    RunStatus.PARTIAL:   ("Mark Partial",   "#B8860B"),
    RunStatus.ABORTED:   ("Mark Aborted",   "#666666"),
    RunStatus.WIP:       ("Re-open to WIP", "#4A90D9"),
}


class RunFrame(ctk.CTkFrame):

    def __init__(self, master, window):
        super().__init__(master, corner_radius=0, fg_color="transparent")
        self._window      = window
        self._project:    Optional[FEAProject] = None
        self._version_id: Optional[str]        = None
        self._iter_id:    Optional[str]        = None
        self._run_id:     Optional[int]        = None
        self._build()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        for r in range(5):
            self.rowconfigure(r, weight=0)
        self.rowconfigure(6, weight=1)

        self._build_header()
        self._build_metadata_panel()
        self._build_artifact_panel()
        self._build_warning_panel()
        self._build_status_panel()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 0))
        hdr.columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(hdr, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.columnconfigure(0, weight=1)

        self._title_label = ctk.CTkLabel(
            title_row, text="Run",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w",
        )
        self._title_label.grid(row=0, column=0, sticky="w")

        self._status_badge = ctk.CTkLabel(
            title_row, text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6, padx=12, pady=4,
        )
        self._status_badge.grid(row=0, column=1, sticky="e")

        fname_row = ctk.CTkFrame(hdr, fg_color="transparent")
        fname_row.grid(row=1, column=0, sticky="ew", pady=(10, 0))

        ctk.CTkLabel(
            fname_row, text="Solver Deck",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", width=90,
        ).pack(side="left")

        self._filename_var = ctk.StringVar(value="—")
        ctk.CTkEntry(
            fname_row,
            textvariable=self._filename_var,
            state="readonly",
            width=440,
            font=ctk.CTkFont(size=12, family="Courier New"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            fname_row, text="Copy Filename",
            width=140, height=32,
            font=ctk.CTkFont(size=12),
            command=self._copy_filename,
        ).pack(side="left")

    def _build_metadata_panel(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=1, column=0, sticky="ew", padx=24, pady=16)
        panel.columnconfigure(1, weight=1)

        self._meta: dict[str, ctk.CTkLabel] = {}
        for row_i, (label, key) in enumerate([("Date", "_date"),
                                               ("Created By", "_created_by")]):
            ctk.CTkLabel(
                panel, text=label,
                font=ctk.CTkFont(size=12, weight="bold"),
                anchor="w", width=100,
            ).grid(row=row_i, column=0, padx=(16, 4), pady=6, sticky="w")
            val = ctk.CTkLabel(panel, text="—", font=ctk.CTkFont(size=12), anchor="w")
            val.grid(row=row_i, column=1, padx=(0, 16), pady=6, sticky="w")
            self._meta[key] = val

        ctk.CTkLabel(
            panel, text="Comments",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="nw", width=100,
        ).grid(row=2, column=0, padx=(16, 4), pady=(6, 10), sticky="nw")

        self._comments_box = ctk.CTkTextbox(
            panel, height=60, wrap="word", font=ctk.CTkFont(size=12))
        self._comments_box.grid(row=2, column=1, columnspan=3,
                                padx=(0, 16), pady=(6, 10), sticky="ew")

        ctk.CTkButton(
            panel, text="Save Comments",
            width=130, height=28,
            font=ctk.CTkFont(size=12),
            command=self._on_save_comments,
        ).grid(row=3, column=1, padx=(0, 16), pady=(0, 10), sticky="w")

    def _build_artifact_panel(self) -> None:
        panel = ctk.CTkFrame(self)
        panel.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
        panel.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            panel, text="Artifacts",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=4, padx=16, pady=(12, 8), sticky="w")

        ctk.CTkLabel(
            panel, text="Input Files",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", width=100,
        ).grid(row=1, column=0, padx=(16, 4), pady=(0, 6), sticky="w")

        self._input_label = ctk.CTkLabel(
            panel, text="—",
            font=ctk.CTkFont(size=12, family="Courier New"), anchor="w",
        )
        self._input_label.grid(row=1, column=1, padx=(0, 24), pady=(0, 6), sticky="w")

        ctk.CTkLabel(
            panel, text="Output Files",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", width=100,
        ).grid(row=2, column=0, padx=(16, 4), pady=(0, 6), sticky="w")

        out_row = ctk.CTkFrame(panel, fg_color="transparent")
        out_row.grid(row=2, column=1, columnspan=3, padx=(0, 16), pady=(0, 6), sticky="ew")

        self._output_label = ctk.CTkLabel(
            out_row, text="—",
            font=ctk.CTkFont(size=12, family="Courier New"), anchor="w",
        )
        self._output_label.pack(side="left", padx=(0, 16))

        self._output_entry_var = ctk.StringVar()
        ctk.CTkEntry(
            out_row,
            textvariable=self._output_entry_var,
            placeholder_text="e.g.  .h3d",
            width=100,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            out_row, text="Add",
            width=60, height=28,
            font=ctk.CTkFont(size=12),
            command=self._on_add_output,
        ).pack(side="left")

        ctk.CTkLabel(
            panel, text="Production Run",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w", width=100,
        ).grid(row=3, column=0, padx=(16, 4), pady=(6, 12), sticky="w")

        prod_row = ctk.CTkFrame(panel, fg_color="transparent")
        prod_row.grid(row=3, column=1, columnspan=3,
                      padx=(0, 16), pady=(6, 12), sticky="w")

        self._production_var = ctk.BooleanVar()
        self._prod_switch = ctk.CTkSwitch(
            prod_row,
            text="Mark this run as supporting a production release",
            variable=self._production_var,
            font=ctk.CTkFont(size=12),
            command=self._on_production_toggle,
        )
        self._prod_switch.pack(side="left")

    def _build_warning_panel(self) -> None:
        self._warning_panel = ctk.CTkFrame(
            self, fg_color="#5C3A1E", corner_radius=8)

        ctk.CTkLabel(
            self._warning_panel,
            text="⚠   Production Artifact Warnings",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFD580", anchor="w",
        ).grid(row=0, column=0, padx=16, pady=(10, 4), sticky="w")

        self._warning_label = ctk.CTkLabel(
            self._warning_panel, text="",
            font=ctk.CTkFont(size=12),
            text_color="#FFD580", anchor="nw", justify="left",
        )
        self._warning_label.grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")

    def _show_warnings(self, warnings: list[str]) -> None:
        if not warnings:
            self._warning_panel.grid_remove()
            return
        self._warning_label.configure(
            text="\n".join(f"  • {w}" for w in warnings))
        self._warning_panel.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 8))

    def _build_status_panel(self) -> None:
        self._status_panel = ctk.CTkFrame(self)
        self._status_panel.grid(row=4, column=0, sticky="ew", padx=24, pady=(0, 20))
        self._status_panel.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self._status_panel, text="Update Status",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w",
        ).grid(row=0, column=0, padx=16, pady=(12, 8), sticky="w")

        self._transition_btn_frame = ctk.CTkFrame(
            self._status_panel, fg_color="transparent")
        self._transition_btn_frame.grid(
            row=1, column=0, padx=16, pady=(0, 12), sticky="w")

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self, project: FEAProject, version_id: str,
             iter_id: str, run_id: int) -> None:
        self._project    = project
        self._version_id = version_id
        self._iter_id    = iter_id
        self._run_id     = run_id

        v   = project._get_version(version_id)
        i   = project._get_iteration(v, iter_id)
        run = project._get_run(i, run_id)

        self._title_label.configure(
            text=f"Run  {version_id} / {iter_id} / {run_id:02d}")

        badge_text, badge_color = _STATUS_BADGE.get(
            run.status.value, (run.status.value, "#444444"))
        self._status_badge.configure(
            text=f"  {badge_text}  ",
            fg_color=badge_color, text_color="#FFFFFF",
        )

        self._filename_var.set(run.name)
        self._meta["_date"].configure(text=run.date)
        self._meta["_created_by"].configure(text=run.created_by)

        self._comments_box.delete("1.0", "end")
        if run.comments:
            self._comments_box.insert("1.0", run.comments)

        self._input_label.configure(
            text="  ".join(run.artifacts.input) if run.artifacts.input else "—")
        self._output_label.configure(
            text="  ".join(run.artifacts.output) if run.artifacts.output else "—")

        self._production_var.set(run.artifacts.is_production)

        if run.artifacts.is_production:
            from app.core.models import _check_production_artifacts
            warnings = _check_production_artifacts(
                project.path, i.solver_type, i.filename_base, run_id)
            self._show_warnings(warnings)
        else:
            self._warning_panel.grid_remove()

        self._populate_transition_buttons(run.status)

    # ------------------------------------------------------------------
    # Transition buttons
    # ------------------------------------------------------------------

    def _populate_transition_buttons(self, current: RunStatus) -> None:
        for w in self._transition_btn_frame.winfo_children():
            w.destroy()

        allowed = RUN_STATUS_TRANSITIONS.get(current, set())
        if not allowed:
            ctk.CTkLabel(
                self._transition_btn_frame,
                text="No transitions available.",
                font=ctk.CTkFont(size=12),
            ).pack(side="left")
            return

        for target in allowed:
            label, color = _TRANSITION_LABELS.get(
                target, (target.value.title(), "#444444"))
            ctk.CTkButton(
                self._transition_btn_frame,
                text=label,
                width=160, height=34,
                font=ctk.CTkFont(size=12),
                fg_color=color,
                command=lambda t=target: self._on_status_change(t),
            ).pack(side="left", padx=(0, 8))

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _copy_filename(self) -> None:
        val = self._filename_var.get()
        if val and val != "—":
            self.clipboard_clear()
            self.clipboard_append(val)
            self._window.set_status(f"Copied to clipboard: {val}")

    def _on_save_comments(self) -> None:
        if not self._project or self._run_id is None:
            return
        comments = self._comments_box.get("1.0", "end").strip()
        try:
            warnings = self._project.update_run_comments(
                self._version_id, self._iter_id, self._run_id,
                comments=comments,
                is_production=self._production_var.get(),
            )
            self._show_warnings(warnings)
            self._window.set_status("Comments saved.")
        except Exception as exc:
            self._show_error("Save Failed", str(exc))

    def _on_add_output(self) -> None:
        ext = self._output_entry_var.get().strip()
        if not ext:
            return
        if not ext.startswith("."):
            ext = f".{ext}"

        v   = self._project._get_version(self._version_id)
        i   = self._project._get_iteration(v, self._iter_id)
        run = self._project._get_run(i, self._run_id)

        if ext not in run.artifacts.output:
            new_output = run.artifacts.output + [ext]
            try:
                self._project.update_run_comments(
                    self._version_id, self._iter_id, self._run_id,
                    output_artifacts=new_output,
                    is_production=self._production_var.get(),
                )
            except Exception as exc:
                self._show_error("Save Failed", str(exc))
                return
            self._output_label.configure(text="  ".join(new_output))
        else:
            self._output_label.configure(text="  ".join(run.artifacts.output))
        self._output_entry_var.set("")
        self._window.set_status(f"Output artifact {ext} added.")

    def _on_production_toggle(self) -> None:
        if not self._project or self._run_id is None:
            return
        is_prod = self._production_var.get()
        try:
            warnings = self._project.update_production_flag(
                self._version_id, self._iter_id,
                self._run_id, is_prod,
            )
            self._show_warnings(warnings)
        except Exception as exc:
            self._show_error("Save Failed", str(exc))
            return

        self._window.set_status(
            f"Run marked as {'production' if is_prod else 'standard'}.")
        self._window.refresh_sidebar()

    def _on_status_change(self, target: RunStatus) -> None:
        if not self._project or self._run_id is None:
            return
        comments = self._comments_box.get("1.0", "end").strip()
        try:
            warnings = self._project.update_run_status(
                self._version_id, self._iter_id, self._run_id,
                target,
                comments=comments,
                is_production=self._production_var.get(),
            )
            self._show_warnings(warnings)
        except Exception as exc:
            self._show_error("Status Change Failed", str(exc))
            return

        self._window.refresh_sidebar()
        self._window.set_status(f"Run {self._run_id:02d} → {target.value}")
        self.load(self._project, self._version_id,
                  self._iter_id, self._run_id)

    def _show_error(self, title: str, message: str) -> None:
        from tkinter import messagebox
        messagebox.showerror(title, message, parent=self._window)
