"""
dialogs/missing_entities_dialog.py
====================================
Shown when a session file references entity folders that no longer exist
on disk.  Lets the user either load what was found, cancel, or remap a
common root prefix so that displaced entities can be resolved.
"""

from __future__ import annotations

import os
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk


class MissingEntitiesDialog(ctk.CTkToplevel):
    """
    Parameters
    ----------
    parent        : MainWindow
    valid_paths   : entity paths that already exist on disk
    missing_paths : entity paths that could not be found

    Attributes
    ----------
    result : list[str] | None
        None  — user cancelled; caller must not load the session.
        list  — final entity paths to open (found + any remapped).
    """

    def __init__(self, parent, valid_paths: list[str], missing_paths: list[str]):
        super().__init__(parent)
        self.title("Missing Entity Paths")
        self.resizable(False, False)
        self.grab_set()

        self.result: list[str] | None = None

        self._valid   = list(valid_paths)
        self._missing = list(missing_paths)
        self._resolved: list[str] = []

        self._build()
        self._centre(parent)

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # textbox expands

        # Row 0 — title
        ctk.CTkLabel(
            self,
            text="Missing Entity Paths",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 4), sticky="w")

        # Row 1 — subtitle
        n = len(self._missing)
        self._subtitle = ctk.CTkLabel(
            self,
            text=f"{n} path(s) in this session could not be found on disk:",
            font=ctk.CTkFont(size=12),
            text_color=["#555555", "#AAAAAA"],
            anchor="w",
        )
        self._subtitle.grid(row=1, column=0, padx=24, pady=(0, 6), sticky="w")

        # Row 2 — read-only textbox listing missing paths
        self._textbox = ctk.CTkTextbox(self, height=120, wrap="none", state="normal")
        self._textbox.grid(row=2, column=0, padx=24, sticky="nsew")
        self._refresh_textbox()
        self._textbox.configure(state="disabled")

        # Row 3 — common-prefix hint
        self._prefix_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=["#666666", "#999999"],
            anchor="w",
        )
        self._prefix_label.grid(row=3, column=0, padx=24, pady=(4, 0), sticky="w")
        self._refresh_prefix_label()

        # Row 4 — error label (hidden until needed)
        self._error_label = ctk.CTkLabel(
            self,
            text="",
            text_color="#E05555",
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        self._error_label.grid(row=4, column=0, padx=24, pady=(4, 0), sticky="w")

        # Row 5 — buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=24, pady=(12, 20), sticky="ew")
        btn_frame.columnconfigure(0, weight=1)  # pushes buttons to the right

        self._remap_btn = ctk.CTkButton(
            btn_frame,
            text="Remap Root Folder…",
            width=160,
            fg_color="transparent",
            border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._on_remap,
        )
        self._remap_btn.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).grid(row=0, column=1, padx=(8, 0))

        ctk.CTkButton(
            btn_frame,
            text="Load Anyway",
            width=120,
            fg_color="#4A90D9",
            command=self._on_load_anyway,
        ).grid(row=0, column=2, padx=(8, 0))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_textbox(self) -> None:
        self._textbox.configure(state="normal")
        self._textbox.delete("1.0", "end")
        self._textbox.insert("1.0", "\n".join(self._missing))
        self._textbox.configure(state="disabled")

    def _refresh_prefix_label(self) -> None:
        if not self._missing:
            self._prefix_label.configure(text="")
            return
        try:
            parents = [str(Path(p).parent) for p in self._missing]
            common = os.path.commonpath(parents)
            self._prefix_label.configure(text=f"Common prefix: {common}")
        except ValueError:
            # Paths span different drives
            self._prefix_label.configure(text="")

    def _centre(self, parent) -> None:
        parent.update_idletasks()
        w, h = 560, 360
        px = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        py = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{px}+{py}")

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------

    def _on_remap(self) -> None:
        # Determine old_root from parent directories of missing paths
        try:
            parents  = [str(Path(p).parent) for p in self._missing]
            old_root = Path(os.path.commonpath(parents))
        except ValueError:
            self._error_label.configure(
                text="Cannot remap: missing paths span different drives.")
            return

        new_root_str = filedialog.askdirectory(
            title=f"Replace '{old_root}' with…",
            parent=self,
        )
        if not new_root_str:
            return  # user dismissed the folder picker

        new_root = Path(new_root_str)

        newly_resolved: list[str] = []
        still_missing:  list[str] = []

        for p in self._missing:
            try:
                rel       = Path(p).relative_to(old_root)
                candidate = new_root / rel
                if candidate.is_dir():
                    newly_resolved.append(str(candidate))
                else:
                    still_missing.append(p)
            except ValueError:
                # Path not relative to old_root (shouldn't happen, but be safe)
                still_missing.append(p)

        self._resolved.extend(newly_resolved)

        if still_missing:
            self._missing = still_missing
            self._refresh_textbox()
            self._refresh_prefix_label()
            n = len(still_missing)
            self._error_label.configure(
                text=f"{n} path(s) still not found — try remapping again or load anyway.")
            # Update subtitle count
            self._subtitle.configure(
                text=f"{n} path(s) in this session could not be found on disk:")
        else:
            # All paths resolved — close with full result
            self.result = self._valid + self._resolved
            self.destroy()

    def _on_load_anyway(self) -> None:
        self.result = self._valid + self._resolved
        self.destroy()
