"""
dialogs/edit_artifacts_dialog.py
"""

from __future__ import annotations

import customtkinter as ctk


class EditArtifactsDialog(ctk.CTkToplevel):
    """
    Dialog to edit the list of expected output file artifacts.

    result: list[str] (normalised extensions, e.g. [".h3d"]) | None if cancelled.
    """

    def __init__(self, parent, current: list[str]):
        super().__init__(parent)
        self.title("Edit Output Artifacts")
        self.geometry("340x300")
        self.resizable(False, False)
        self.grab_set()

        self.result = None
        self._build(current)
        self.wait_window()

    def _build(self, current: list[str]) -> None:
        self.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Edit Output Artifacts",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        ctk.CTkLabel(
            self, text="Extra artifacts beyond config defaults.\nOne extension per line  (e.g. .csv)",
            font=ctk.CTkFont(size=12), text_color="gray", justify="left", anchor="w",
        ).grid(row=1, column=0, padx=24, pady=(0, 8), sticky="w")

        self._textbox = ctk.CTkTextbox(self, width=280, height=100, wrap="none")
        self._textbox.grid(row=2, column=0, padx=24, sticky="ew")
        if current:
            self._textbox.insert("1.0", "\n".join(current))

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#E05555",
            font=ctk.CTkFont(size=12), anchor="w",
        )
        self._error_label.grid(row=3, column=0, padx=24, pady=(6, 0), sticky="w")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=4, column=0, padx=24, pady=16, sticky="e")

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100,
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Save", width=100,
            command=self._on_save,
        ).pack(side="left")

    def _on_save(self) -> None:
        raw = self._textbox.get("1.0", "end").strip()
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        result = []
        for ln in lines:
            if not ln.startswith("."):
                ln = f".{ln}"
            result.append(ln)
        self.result = result
        self.destroy()
