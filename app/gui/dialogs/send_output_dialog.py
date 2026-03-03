"""
dialogs/send_output_dialog.py — Send Output (Email) Dialog
"""
from __future__ import annotations

import email as _email_mod
import email.header as _email_header
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

import customtkinter as ctk
from tkinter import filedialog

from app.config import COMMUNICATIONS_FOLDER, TIMESTAMP_FORMAT
from app.core.models import FEAProject
from schema import CommunicationRecord, RunStatus, IterationStatus

import urllib.parse
import webbrowser


def _current_user() -> str:
    try:
        return os.getlogin()
    except Exception:
        return os.environ.get("USERNAME", "unknown")


def _now() -> str:
    return datetime.now().strftime(TIMESTAMP_FORMAT)


class SendOutputDialog(ctk.CTkToplevel):
    """Dialog to compose and log a 'Send Output' communication for a version.

    self.result is CommunicationRecord | None.
    """

    def __init__(self, master, project: FEAProject, version_id: str):
        super().__init__(master)
        self.result: Optional[CommunicationRecord] = None
        self._project         = project
        self._version_id      = version_id
        self._eml_source_path: Optional[Path] = None
        self._checks: dict[tuple[str, int], ctk.BooleanVar] = {}  # (iter_id, run_id) → var
        self._outlook_opened  = False

        v = project._get_version(version_id)
        e = project.entity

        self.title(f"Send Output — {e.project} / {e.name} {version_id}")
        self.resizable(True, True)
        self.grab_set()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        self._build(v, e)
        self._refresh_body()
        self._update_save_btn()
        self._center()

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def _build(self, v, e) -> None:
        # Row 0 — header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 4))
        ctk.CTkLabel(
            hdr,
            text="Send Output",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).pack(side="left")
        ctk.CTkLabel(
            hdr,
            text=f"  {e.project} / {e.name} — {v.id}",
            font=ctk.CTkFont(size=13),
            text_color=["#555555", "#AAAAAA"],
            anchor="w",
        ).pack(side="left", pady=(4, 0))

        # Row 1 — two-column content area
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)
        content.columnconfigure(0, weight=1, minsize=280)
        content.columnconfigure(1, weight=2, minsize=360)
        content.rowconfigure(0, weight=1)

        self._build_run_panel(content, v)
        self._build_compose_panel(content, v, e)

        # Row 2 — .eml import info
        self._import_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=11),
            text_color=["#2D8A4E", "#5DC97C"],
            anchor="w",
        )
        self._import_label.grid(row=2, column=0, padx=24, pady=(0, 2), sticky="ew")

        # Row 3 — error label
        self._error_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=11),
            text_color="#E05555",
            anchor="w",
        )
        self._error_label.grid(row=3, column=0, padx=24, pady=(0, 4), sticky="ew")

        # Row 4 — action buttons
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=4, column=0, sticky="ew", padx=16, pady=(4, 20))

        ctk.CTkButton(
            btn_row, text="Cancel",
            width=90, height=34,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self.destroy,
        ).pack(side="right", padx=(6, 0))

        self._save_btn = ctk.CTkButton(
            btn_row, text="Save Record",
            width=110, height=34,
            font=ctk.CTkFont(size=13),
            fg_color="#2D8A4E",
            state="disabled",
            command=self._on_save,
        )
        self._save_btn.pack(side="right", padx=(6, 0))

        self._import_btn = ctk.CTkButton(
            btn_row, text="Import Sent .eml\u2026",
            width=148, height=34,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._on_import_eml,
        )
        self._import_btn.pack(side="right", padx=(6, 0))

        self._outlook_btn = ctk.CTkButton(
            btn_row, text="Open Draft in Outlook",
            width=168, height=34,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._on_open_outlook,
        )
        self._outlook_btn.pack(side="left")

        self.bind("<Escape>", lambda _: self.destroy())

    def _build_run_panel(self, parent, v) -> None:
        frame = ctk.CTkFrame(parent, fg_color=["#EBEBEB", "#2A2A2A"], corner_radius=8)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        # Panel title + Select All / None
        title_row = ctk.CTkFrame(frame, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            title_row, text="Select Runs",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(side="left")
        ctk.CTkButton(
            title_row, text="None",
            width=40, height=22, font=ctk.CTkFont(size=11),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._clear_all,
        ).pack(side="right")
        ctk.CTkButton(
            title_row, text="All",
            width=36, height=22, font=ctk.CTkFont(size=11),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._select_all,
        ).pack(side="right", padx=(0, 4))

        # Scrollable run list
        scroll = ctk.CTkScrollableFrame(frame, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 8))
        scroll.columnconfigure(0, weight=1)

        has_sendable = False
        for i in v.iterations:
            if i.status == IterationStatus.DEPRECATED:
                continue

            # Iteration header
            iter_hdr = ctk.CTkFrame(scroll, fg_color="transparent")
            iter_hdr.pack(fill="x", padx=4, pady=(8, 1))
            solver_abbr = i.solver_type.value
            desc = i.description if i.description else i.id
            ctk.CTkLabel(
                iter_hdr,
                text=f"{i.id} — {desc}  [{solver_abbr}]",
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w",
                wraplength=230,
            ).pack(anchor="w")

            if not i.runs:
                ctk.CTkLabel(
                    scroll, text="  (no runs)",
                    font=ctk.CTkFont(size=10),
                    text_color=["#888888", "#666666"],
                    anchor="w",
                ).pack(anchor="w", padx=12)
                continue

            for run in i.runs:
                is_wip = (run.status == RunStatus.WIP)
                if not is_wip:
                    has_sendable = True
                var = ctk.BooleanVar(value=(not is_wip and run.status.value == "converged"))
                if not is_wip:
                    var.trace_add("write", lambda *_: self._update_save_btn())
                    self._checks[(i.id, run.id)] = var

                row_f = ctk.CTkFrame(scroll, fg_color="transparent")
                row_f.pack(anchor="w", padx=(8, 4), pady=1)

                chk = ctk.CTkCheckBox(
                    row_f, text="", variable=var, width=22,
                    state="disabled" if is_wip else "normal",
                )
                chk.grid(row=0, column=0, padx=(0, 6))

                run_color = ["#888888", "#666666"] if is_wip else ["#1A1A1A", "#DCE4EE"]
                ctk.CTkLabel(
                    row_f, text=f"Run {run.id:02d}",
                    font=ctk.CTkFont(size=11), width=48, anchor="w",
                    text_color=run_color,
                ).grid(row=0, column=1)

                status_colors = self._status_color(run.status.value)
                ctk.CTkLabel(
                    row_f, text=run.status.value,
                    font=ctk.CTkFont(size=11), width=72, anchor="w",
                    text_color=status_colors,
                ).grid(row=0, column=2, padx=(4, 0))

                date_only = run.date.split(" ")[0]
                ctk.CTkLabel(
                    row_f, text=date_only,
                    font=ctk.CTkFont(size=10),
                    text_color=["#666666", "#999999"],
                    anchor="w",
                ).grid(row=0, column=3, padx=(8, 0))

        if not has_sendable:
            ctk.CTkLabel(
                scroll,
                text="No sendable runs in this version.\n(All runs are WIP.)",
                font=ctk.CTkFont(size=11),
                text_color=["#888888", "#666666"],
                anchor="w",
                justify="left",
            ).pack(anchor="w", padx=12, pady=12)

    def _build_compose_panel(self, parent, v, e) -> None:
        frame = ctk.CTkFrame(parent, fg_color=["#EBEBEB", "#2A2A2A"], corner_radius=8)
        frame.grid(row=0, column=1, sticky="nsew", pady=0)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(5, weight=1)  # body textbox expands

        # Subject
        ctk.CTkLabel(
            frame, text="Subject",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")
        self._subject_var = ctk.StringVar(value=self._build_default_subject(v, e))
        self._subject_var.trace_add("write", lambda *_: self._update_save_btn())
        ctk.CTkEntry(
            frame, textvariable=self._subject_var,
            font=ctk.CTkFont(size=12), height=32,
        ).grid(row=1, column=0, padx=14, pady=(0, 8), sticky="ew")

        # To
        ctk.CTkLabel(
            frame, text="To  (comma-separated)",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        ).grid(row=2, column=0, padx=14, pady=(0, 2), sticky="w")
        self._to_var = ctk.StringVar()
        self._to_var.trace_add("write", lambda *_: self._update_save_btn())
        ctk.CTkEntry(
            frame, textvariable=self._to_var,
            placeholder_text="colleague@company.com, ...",
            font=ctk.CTkFont(size=12), height=32,
        ).grid(row=3, column=0, padx=14, pady=(0, 8), sticky="ew")

        # Body header row (label + Regenerate button)
        body_hdr = ctk.CTkFrame(frame, fg_color="transparent")
        body_hdr.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 2))
        ctk.CTkLabel(
            body_hdr, text="Body",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        ).pack(side="left")
        ctk.CTkButton(
            body_hdr, text="\u27f3 Regenerate",
            width=100, height=22, font=ctk.CTkFont(size=10),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._refresh_body,
        ).pack(side="right")

        # Body textbox
        self._body_box = ctk.CTkTextbox(
            frame,
            font=ctk.CTkFont(size=11, family="Courier New"),
            wrap="none",
        )
        self._body_box.grid(row=5, column=0, padx=14, pady=(0, 12), sticky="nsew")

    # ------------------------------------------------------------------
    # Body generation
    # ------------------------------------------------------------------

    def _build_default_subject(self, v, e) -> str:
        return f"FEA Trace \u2014 {e.project} / {e.name} {v.id}"

    def _build_body(self) -> str:
        v       = self._project._get_version(self._version_id)
        e       = self._project.entity
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        user    = _current_user()

        lines = [
            "FEA Trace Output Report",
            "=======================",
            f"Project  : {e.project}",
            f"Entity   : {e.name} [{e.id}]",
            f"Version  : {v.id} \u2014 {v.description}",
            f"Generated: {now_str} by {user}",
            "",
            "--- Selected Results ---",
            "",
        ]

        iter_map: dict[str, object] = {i.id: i for i in v.iterations}
        run_map:  dict[tuple, object] = {
            (i.id, run.id): run for i in v.iterations for run in i.runs
        }
        selected: dict[str, list] = {}
        for (iter_id, run_id), var in self._checks.items():
            if var.get():
                selected.setdefault(iter_id, []).append(
                    (iter_map[iter_id], run_map[(iter_id, run_id)])
                )

        if not selected:
            lines.append("(no runs selected)")
        else:
            for iter_id in sorted(selected):
                pairs = selected[iter_id]
                if not pairs:
                    continue
                i = pairs[0][0]
                lines.append(
                    f"[{i.id} \u2014 {i.description}]  ({i.solver_type.value})"
                )
                for _, run in sorted(pairs, key=lambda x: x[1].id):
                    date_only = run.date.split(" ")[0]
                    lines.append(
                        f"  \u2022 Run {run.id:02d}  {run.status.value.upper():<12}({date_only})"
                    )
                lines.append("")

        from app.gui.theme import AUDIT_NOTE_PREFIXES
        user_notes = [n for n in v.notes if not n.startswith(AUDIT_NOTE_PREFIXES)]
        if user_notes:
            lines += ["--- Version Notes ---"] + user_notes + [""]

        return "\n".join(lines)

    def _refresh_body(self) -> None:
        body = self._build_body()
        self._body_box.delete("1.0", "end")
        self._body_box.insert("1.0", body)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _status_color(status: str) -> list:
        from app.gui.theme import STATUS_COLORS
        color = STATUS_COLORS.get(status, "#888888")
        return [color, color]

    def _selected_run_refs(self) -> list[str]:
        return [
            f"{self._version_id}{iter_id} Run {run_id:02d}"
            for (iter_id, run_id), var in self._checks.items()
            if var.get()
        ]

    def _selected_iter_ids(self) -> set[str]:
        return {iter_id for (iter_id, _), var in self._checks.items() if var.get()}

    def _select_all(self) -> None:
        for var in self._checks.values():
            var.set(True)

    def _clear_all(self) -> None:
        for var in self._checks.values():
            var.set(False)

    def _update_save_btn(self) -> None:
        has_runs = any(v.get() for v in self._checks.values())
        has_to   = bool(self._to_var.get().strip())
        has_subj = bool(self._subject_var.get().strip())
        has_eml  = self._eml_source_path is not None
        self._save_btn.configure(
            state="normal" if (has_runs and has_to and has_subj and has_eml) else "disabled"
        )

    # ------------------------------------------------------------------
    # Button events
    # ------------------------------------------------------------------

    def _on_open_outlook(self) -> None:
        """Open a pre-filled draft in the system default mail client.

        Uses a mailto: URI so the correct mail app opens regardless of whether
        the user has New Outlook, Classic Outlook, or any other client
        """
        self._error_label.configure(text="")
        subject = self._subject_var.get().strip()
        to_str  = self._to_var.get().strip()
        body    = self._body_box.get("1.0", "end").rstrip()

        # Encode subject and body; webbrowser.open → ShellExecute on Windows
        # which has no practical length limit for mailto: URIs.
        params  = urllib.parse.urlencode(
            {"subject": subject, "body": body},
            quote_via=urllib.parse.quote,
        )
        mailto  = f"mailto:{urllib.parse.quote(to_str)}?{params}"
        try:
            webbrowser.open(mailto)
            self._outlook_opened = True
            self._outlook_btn.configure(text="Reopen in Outlook")
        except Exception as exc:
            self._error_label.configure(text=f"Could not open mail client: {exc}")

    def _on_import_eml(self) -> None:
        self._error_label.configure(text="")
        path_str = filedialog.askopenfilename(
            parent=self,
            title="Import Sent .eml",
            filetypes=[("Email files", "*.eml"), ("All files", "*.*")],
        )
        if not path_str:
            return
        eml_path = Path(path_str)
        try:
            with eml_path.open("rb") as f:
                # compat32 policy (default) returns plain strings for all headers,
                # which is more reliable than policy.default with Outlook .eml files.
                msg = _email_mod.message_from_binary_file(f)

            def _decode(raw: str) -> str:
                """Decode RFC 2047 encoded words and normalise whitespace."""
                parts = _email_header.decode_header(raw)
                chunks = []
                for part, charset in parts:
                    if isinstance(part, bytes):
                        chunks.append(part.decode(charset or "utf-8", errors="replace"))
                    else:
                        chunks.append(part)
                return " ".join("".join(chunks).split())

            to_parsed   = _decode(msg.get("To",      ""))
            subj_parsed = _decode(msg.get("Subject", ""))
            if to_parsed:
                self._to_var.set(to_parsed)
            if subj_parsed:
                self._subject_var.set(subj_parsed)
            self._eml_source_path = eml_path
            self._import_label.configure(text=f"Imported: {eml_path.name}")
            self._update_save_btn()
        except Exception as exc:
            self._error_label.configure(text=f"Could not parse .eml: {exc}")
            self._eml_source_path = None

    def _on_save(self) -> None:
        self._error_label.configure(text="")
        run_refs = self._selected_run_refs()
        if not run_refs:
            self._error_label.configure(text="Select at least one run.")
            return
        to_str  = self._to_var.get().strip()
        subject = self._subject_var.get().strip()
        if not to_str or not subject:
            self._error_label.configure(text="To and Subject fields are required.")
            return

        body_text    = self._body_box.get("1.0", "end").rstrip()
        body_summary = body_text[:500] if body_text else ""

        # Copy .eml to entity communications folder
        eml_filenames = []
        if self._eml_source_path and self._eml_source_path.exists():
            comms_dir = self._project.path / COMMUNICATIONS_FOLDER
            comms_dir.mkdir(exist_ok=True)
            ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_subj = "".join(c if c not in r'\/:*?"<>|' else "_"
                                for c in subject)[:60].strip()
            base = f"{ts}_{safe_subj}.eml"
            stem, n = base[:-4], 2
            dest_name = base
            while (comms_dir / dest_name).exists():
                dest_name = f"{stem}_{n}.eml"
                n += 1
            shutil.copy2(self._eml_source_path, comms_dir / dest_name)
            eml_filenames = [dest_name]

        sent_at = _now()
        sent_by = _current_user()
        record  = CommunicationRecord(
            sent_at=sent_at, sent_by=sent_by,
            to=to_str, subject=subject,
            body_summary=body_summary,
            eml_filenames=eml_filenames,
            run_refs=run_refs,
        )
        note = (
            f"[Sent Output] on {sent_at} by {sent_by} "
            f"\u2014 To: {to_str} \u2014 Subject: {subject}"
        )
        iter_notes = {iid: note for iid in self._selected_iter_ids()}

        try:
            self._project.add_communication(
                self._version_id, record, note, iter_notes)
        except Exception as exc:
            self._error_label.configure(text=f"Save error: {exc}")
            return

        self.result = record
        self.destroy()

    # ------------------------------------------------------------------
    # Geometry
    # ------------------------------------------------------------------

    def _center(self) -> None:
        self.minsize(720, 520)
        self.geometry("940x660")
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h   = self.winfo_width(), self.winfo_height()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
