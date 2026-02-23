"""
main_window.py — Application Controller
========================================
Owns the top-level window, layout, status bar, file menu, and
frame switching. Supports multiple entities open simultaneously,
navigated through the sidebar. Session save/load handled here.
"""

from __future__ import annotations

import os
import yaml
import tkinter.ttk as ttk
import customtkinter as ctk
from pathlib import Path
from tkinter import filedialog
from typing import Optional

from schema import SCHEMA_VERSION
from app.config import APP_TITLE, APP_VERSION, WINDOW_SIZE, WINDOW_MIN_W, WINDOW_MIN_H, LOG_FILENAME
from app.core.models import FEAProject
from app.core.session import SessionManager, DEFAULT_SESSION_DIR
from app.gui.sidebar import Sidebar
from app.gui.frames.entity_frame import EntityFrame
from app.gui.frames.version_frame import VersionFrame
from app.gui.frames.representation_frame import RepresentationFrame
from app.gui.frames.iteration_frame import IterationFrame
from app.gui.frames.run_frame import RunFrame
from app.gui.frames.welcome_frame import WelcomeFrame


ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    """
    Root window. Manages:
      - Multi-entity project dict
      - Session file (save / load / save-as)
      - Sidebar routing
      - Frame switching
      - File dropdown menu
    """

    def __init__(self):
        super().__init__()
        # Switch to clam TTK base theme so custom heading/row colours
        # are honoured on Windows (the default 'vista' theme overrides them).
        ttk.Style(self).theme_use("clam")
        self.title(f"{APP_TITLE}  v{APP_VERSION}")
        self.geometry(WINDOW_SIZE)
        self.minsize(WINDOW_MIN_W, WINDOW_MIN_H)

        # Active projects — keyed by str(entity_path)
        self._projects:       dict[str, FEAProject] = {}
        self._active_path:    Optional[str]          = None
        self._session:        SessionManager         = SessionManager()
        self._frames:         dict[str, ctk.CTkFrame] = {}

        self._build_layout()
        self._show_frame("welcome")

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build_layout(self) -> None:
        self.rowconfigure(0, weight=0)   # menu bar
        self.rowconfigure(1, weight=0)   # toolbar
        self.rowconfigure(2, weight=1)   # content
        self.rowconfigure(3, weight=0)   # status bar
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        self._build_menubar()
        self._build_toolbar()
        self._build_sidebar()
        self._build_main_panel()
        self._build_status_bar()

    def _build_menubar(self) -> None:
        from CTkMenuBar import CTkMenuBar, CustomDropdownMenu

        menu = CTkMenuBar(master=self, bg_color=["gray60", "gray25"])
        menu.grid(row=0, column=0, columnspan=2, sticky="ew")

        file_btn = menu.add_cascade("  File  ")
        dropdown = CustomDropdownMenu(widget=file_btn)
        dropdown.add_option("New Entity",       command=self._on_new_entity)
        dropdown.add_option("Open Entity",      command=self._on_open_entity)
        dropdown.add_separator()
        dropdown.add_option("New Session",      command=self._on_new_session)
        dropdown.add_option("Open Session",     command=self._on_open_session)
        dropdown.add_option("Save Session",     command=self._on_save_session)
        dropdown.add_option("Save Session As…", command=self._on_save_session_as)

        settings_btn = menu.add_cascade("  Settings  ")
        settings_dd = CustomDropdownMenu(widget=settings_btn)
        appearance_sub = settings_dd.add_submenu("Appearance")
        appearance_sub.add_option("System",    command=lambda: ctk.set_appearance_mode("system"))
        appearance_sub.add_option("Light",     command=lambda: ctk.set_appearance_mode("light"))
        appearance_sub.add_option("Dark",      command=lambda: ctk.set_appearance_mode("dark"))

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self, height=48, corner_radius=0)
        bar.grid(row=1, column=0, columnspan=2, sticky="ew")
        bar.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            bar, text=APP_TITLE,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=10, sticky="w")

        # Session name label (centre)
        self._session_label = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(size=12),
        )
        self._session_label.grid(row=0, column=1, sticky="")

    def _build_sidebar(self) -> None:
        self._sidebar = Sidebar(
            self,
            on_select=self._on_sidebar_select,
            on_close=self._on_close_entity,
        )
        self._sidebar.grid(row=2, column=0, sticky="nsew")

    def _build_main_panel(self) -> None:
        self._main_panel = ctk.CTkFrame(
            self, corner_radius=0, fg_color="transparent")
        self._main_panel.grid(row=2, column=1, sticky="nsew")
        self._main_panel.rowconfigure(0, weight=1)
        self._main_panel.columnconfigure(0, weight=1)

        self._frames["welcome"]        = WelcomeFrame(self._main_panel, self)
        self._frames["entity"]         = EntityFrame(self._main_panel, self)
        self._frames["version"]        = VersionFrame(self._main_panel, self)
        self._frames["representation"] = RepresentationFrame(self._main_panel, self)
        self._frames["iteration"]      = IterationFrame(self._main_panel, self)
        self._frames["run"]            = RunFrame(self._main_panel, self)

        for f in self._frames.values():
            f.grid(row=0, column=0, sticky="nsew")

    def _build_status_bar(self) -> None:
        bar = ctk.CTkFrame(self, height=28, corner_radius=0)
        bar.grid(row=3, column=0, columnspan=2, sticky="ew")
        bar.columnconfigure(0, weight=1)

        self._status_var = ctk.StringVar(value="Ready")
        ctk.CTkLabel(
            bar, textvariable=self._status_var,
            font=ctk.CTkFont(size=12), anchor="w",
        ).grid(row=0, column=0, padx=12, pady=2, sticky="w")

        ctk.CTkLabel(
            bar, text=f"Schema {SCHEMA_VERSION}",
            font=ctk.CTkFont(size=11), anchor="e",
        ).grid(row=0, column=1, padx=12, pady=2, sticky="e")

    # ------------------------------------------------------------------
    # Frame switching
    # ------------------------------------------------------------------

    def _show_frame(self, key: str) -> None:
        self._frames.get(key, self._frames["welcome"]).tkraise()

    def show_entity(self, entity_path: str) -> None:
        proj = self._projects.get(entity_path)
        if proj:
            self._active_path = entity_path
            self._frames["entity"].load(proj)
            self._show_frame("entity")

    def show_version(self, entity_path: str, version_id: str) -> None:
        proj = self._projects.get(entity_path)
        if proj:
            self._active_path = entity_path
            self._frames["version"].load(proj, version_id)
            self._show_frame("version")

    def show_representation(self, entity_path: str,
                            version_id: str, rep_id: str) -> None:
        proj = self._projects.get(entity_path)
        if proj:
            self._active_path = entity_path
            self._frames["representation"].load(proj, version_id, rep_id)
            self._show_frame("representation")

    def show_iteration(self, entity_path: str,
                       version_id: str, rep_id: str, iter_id: str) -> None:
        proj = self._projects.get(entity_path)
        if proj:
            self._active_path = entity_path
            self._frames["iteration"].load(proj, version_id, rep_id, iter_id)
            self._show_frame("iteration")

    def show_run(self, entity_path: str,
                 version_id: str, rep_id: str, iter_id: str, run_id: int) -> None:
        proj = self._projects.get(entity_path)
        if proj:
            self._active_path = entity_path
            self._frames["run"].load(proj, version_id, rep_id, iter_id, run_id)
            self._show_frame("run")

    # ------------------------------------------------------------------
    # Sidebar routing
    # ------------------------------------------------------------------

    def _on_sidebar_select(self, node_type: str, entity_path: str, *ids) -> None:
        match node_type:
            case "entity":
                self.show_entity(entity_path)
            case "version":
                self.show_version(entity_path, *ids)
            case "representation":
                self.show_representation(entity_path, *ids)
            case "iteration":
                self.show_iteration(entity_path, *ids)
            case "run":
                v_id, r_id, i_id, run_id = ids
                self.show_run(entity_path, v_id, r_id, i_id, int(run_id))

    def refresh_sidebar(self) -> None:
        """Refreshes the active entity's subtree in the sidebar."""
        if self._active_path and self._active_path in self._projects:
            self._sidebar.refresh_entity(self._projects[self._active_path])

    # ------------------------------------------------------------------
    # Entity open / create / close
    # ------------------------------------------------------------------

    def _on_new_entity(self) -> None:
        from app.gui.dialogs.new_entity_dialog import NewEntityDialog
        dlg = NewEntityDialog(self)
        self.wait_window(dlg)
        if dlg.result is None:
            return
        self._create_project(dlg.params)

    def _on_open_entity(self) -> None:
        path = filedialog.askdirectory(title="Select Entity Folder")
        if path:
            self._load_project(Path(path))

    def _on_close_entity(self, entity_path: str) -> None:
        self._projects.pop(entity_path, None)
        self._sidebar.remove_entity(entity_path)
        self._session.remove_entity(entity_path)

        if self._active_path == entity_path:
            self._active_path = None
            if self._projects:
                # Switch to the last remaining entity
                last = list(self._projects.keys())[-1]
                self.show_entity(last)
            else:
                self._show_frame("welcome")

        self.set_status("Entity closed.")

    def _create_project(self, params: tuple) -> None:
        parent_dir, name, project, owner, created_by = params
        try:
            proj = FEAProject.create(parent_dir, name, project, owner, created_by)
        except Exception as exc:
            self._show_error("Create Entity Failed", str(exc))
            return

        path_str = str(proj.path)
        self._projects[path_str] = proj
        self._sidebar.add_entity(proj)
        self._session.add_entity(path_str)
        self._active_path = path_str
        self.show_entity(path_str)
        self.set_status(f"Entity '{name}' created successfully.")

    def _load_project(self, entity_path: Path) -> None:
        path_str = str(entity_path)
        if path_str in self._projects:
            # Already open — just switch to it
            self.show_entity(path_str)
            return

        log_path = entity_path / LOG_FILENAME

        # Migration check
        if log_path.exists():
            try:
                raw    = yaml.safe_load(log_path.read_text(encoding="utf-8"))
                status = self._check_migration(raw, entity_path, log_path)
                if status == "blocked":
                    return
            except Exception as exc:
                self._show_error("Migration Error", str(exc))
                return

        try:
            proj, warnings = FEAProject.load(entity_path)
        except Exception as exc:
            self._show_error("Load Failed", str(exc))
            return

        self._projects[path_str] = proj
        self._sidebar.add_entity(proj)
        self._session.add_entity(path_str)
        self._active_path = path_str
        self.show_entity(path_str)

        for w in warnings:
            self.set_status(f"Warning: {w}", warning=True)

        self.set_status(f"Opened: {proj.entity.name}")

    def _check_migration(self, raw: dict,
                         entity_path: Path, log_path: Path) -> str:
        """Returns 'ok' or 'blocked'."""
        from app.core.migration import check as mcheck, migrate, LogTooNew, MigrationRequired

        status = mcheck(raw, SCHEMA_VERSION)

        if status == "too_new":
            self._show_error("Log Too New",
                f"This log requires a newer version of {APP_TITLE}.\n"
                "Please update the application.")
            return "blocked"

        if status == "auto":
            try:
                _user = os.getlogin()
            except OSError:
                _user = os.environ.get("USERNAME", "unknown")
            raw, notes = migrate(raw, SCHEMA_VERSION, _user)
            log_path.write_text(
                yaml.dump(raw, allow_unicode=True,
                          sort_keys=False, default_flow_style=False),
                encoding="utf-8")
            self.set_status(f"Log auto-migrated: {'; '.join(notes)}")

        if status == "confirm":
            from app.gui.dialogs.migration_dialog import MigrationDialog
            dlg = MigrationDialog(self, raw, SCHEMA_VERSION)
            self.wait_window(dlg)
            if not dlg.confirmed:
                return "blocked"
            try:
                _user = os.getlogin()
            except OSError:
                _user = os.environ.get("USERNAME", "unknown")
            raw, notes = migrate(raw, SCHEMA_VERSION,
                                 _user, confirmed=True)
            log_path.write_text(
                yaml.dump(raw, allow_unicode=True,
                          sort_keys=False, default_flow_style=False),
                encoding="utf-8")
            self.set_status(f"Log migrated: {'; '.join(notes)}")

        return "ok"

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def _on_new_session(self) -> None:
        # Close all entities
        for path in list(self._projects.keys()):
            self._on_close_entity(path)
        self._session.clear()
        self._update_session_label()
        self._show_frame("welcome")
        self.set_status("New session started.")

    def _on_open_session(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Session File",
            initialdir=str(DEFAULT_SESSION_DIR),
            filetypes=[("FEA Trace Session", "*.featrace"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            entity_paths = self._session.load(path)
        except ValueError as exc:
            self._show_error("Open Session Failed", str(exc))
            return

        # Close current entities first
        for p in list(self._projects.keys()):
            self._on_close_entity(p)

        # Open each entity from the session
        for ep in entity_paths:
            self._load_project(Path(ep))

        self._update_session_label()
        self.set_status(f"Session loaded: {self._session.display_name}")

    def _on_save_session(self) -> None:
        if not self._session.has_file:
            self._on_save_session_as()
            return
        try:
            self._session.set_entities(list(self._projects.keys()))
            self._session.save()
            self.set_status(f"Session saved: {self._session.display_name}")
        except Exception as exc:
            self._show_error("Save Session Failed", str(exc))

    def _on_save_session_as(self) -> None:
        DEFAULT_SESSION_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            title="Save Session As",
            initialdir=str(DEFAULT_SESSION_DIR),
            defaultextension=".featrace",
            filetypes=[("FEA Trace Session", "*.featrace"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            self._session.set_entities(list(self._projects.keys()))
            self._session.save_as(path)
            self._update_session_label()
            self.set_status(f"Session saved: {self._session.display_name}")
        except Exception as exc:
            self._show_error("Save Session Failed", str(exc))

    def _update_session_label(self) -> None:
        self._session_label.configure(
            text=self._session.display_name if self._session.has_file else "")

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def set_status(self, message: str, warning: bool = False) -> None:
        prefix = "⚠  " if warning else "✓  "
        self._status_var.set(f"{prefix}{message}")

    # ------------------------------------------------------------------
    # Error dialog
    # ------------------------------------------------------------------

    def _show_error(self, title: str, message: str) -> None:
        from tkinter import messagebox
        messagebox.showerror(title, message, parent=self)
