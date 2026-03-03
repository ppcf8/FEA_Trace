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

import ctypes
import ctypes.wintypes
import html as _html_lib
import urllib.parse
import webbrowser

from PIL import Image

_ICONS_DIR = Path(__file__).parent.parent.parent / "assets" / "icons"
_IMG_COPY  = ctk.CTkImage(Image.open(_ICONS_DIR / "copy.png"), size=(14, 14))

_k32 = ctypes.windll.kernel32
_u32 = ctypes.windll.user32
# argtypes + restype must be set so 64-bit pointer values are never truncated
# or mis-converted to a 32-bit C int (which causes OverflowError on Win64).
_k32.GlobalAlloc.argtypes  = [ctypes.c_uint, ctypes.c_size_t]
_k32.GlobalAlloc.restype   = ctypes.c_void_p
_k32.GlobalLock.argtypes   = [ctypes.c_void_p]
_k32.GlobalLock.restype    = ctypes.c_void_p
_k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
_u32.OpenClipboard.argtypes    = [ctypes.c_void_p]
_u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]


def _set_html_clipboard(html_fragment: str) -> None:
    """Place an HTML fragment on the Windows clipboard using the CF_HTML format.

    Outlook (both Classic and New) reads CF_HTML on paste, so the fragment
    can include inline styles such as ``font-family: Courier New``.
    """
    CF_HTML = _u32.RegisterClipboardFormatW("HTML Format")

    header_tmpl = (
        "Version:0.9\r\n"
        "StartHTML:{sh:08d}\r\n"
        "EndHTML:{eh:08d}\r\n"
        "StartFragment:{sf:08d}\r\n"
        "EndFragment:{ef:08d}\r\n"
    )
    pre  = "<html><body>\r\n<!--StartFragment-->"
    post = "<!--EndFragment-->\r\n</body></html>"

    # Compute byte offsets using a zero-filled placeholder header first
    # (all offsets are exactly 8 digits, so the header length is constant).
    placeholder = header_tmpl.format(sh=0, eh=0, sf=0, ef=0)
    sh = len(placeholder.encode("utf-8"))
    sf = sh + len(pre.encode("utf-8"))
    ef = sf + len(html_fragment.encode("utf-8"))
    eh = ef + len(post.encode("utf-8"))

    header = header_tmpl.format(sh=sh, eh=eh, sf=sf, ef=ef)
    data   = (header + pre + html_fragment + post).encode("utf-8")

    GMEM_MOVEABLE = 0x0002
    h = _k32.GlobalAlloc(GMEM_MOVEABLE, len(data) + 1)
    if not h:
        raise RuntimeError("GlobalAlloc failed")
    ptr = _k32.GlobalLock(h)
    if not ptr:
        raise RuntimeError("GlobalLock failed")
    ctypes.memmove(ptr, data, len(data))
    _k32.GlobalUnlock(h)
    if not _u32.OpenClipboard(0):
        raise RuntimeError("OpenClipboard failed")
    _u32.EmptyClipboard()
    _u32.SetClipboardData(CF_HTML, h)
    _u32.CloseClipboard()


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
                    var.trace_add("write", lambda *_: self._on_selection_change())
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
        frame.rowconfigure(3, weight=1)  # body textbox expands

        # Subject
        ctk.CTkLabel(
            frame, text="Subject",
            font=ctk.CTkFont(size=12, weight="bold"), anchor="w",
        ).grid(row=0, column=0, padx=14, pady=(12, 2), sticky="w")
        self._subject_var = ctk.StringVar(value=self._build_default_subject(v, e))
        self._subject_var.trace_add("write", lambda *_: self._on_selection_change())
        ctk.CTkEntry(
            frame, textvariable=self._subject_var,
            font=ctk.CTkFont(size=12), height=32,
        ).grid(row=1, column=0, padx=14, pady=(0, 8), sticky="ew")

        # To — internal only, populated from .eml import (not shown in UI)
        self._to_var = ctk.StringVar()

        # Body header row (label + Copy + Regenerate buttons)
        body_hdr = ctk.CTkFrame(frame, fg_color="transparent")
        body_hdr.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 2))
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
        self._copy_btn = ctk.CTkButton(
            body_hdr, text=" Copy",
            image=_IMG_COPY, compound="left",
            width=72, height=22, font=ctk.CTkFont(size=10),
            fg_color="transparent", border_width=1,
            text_color=["#1A1A1A", "#DCE4EE"],
            command=self._on_copy_body,
        )
        self._copy_btn.pack(side="right", padx=(0, 6))

        # Body textbox — read-only; written programmatically via _refresh_body
        self._body_box = ctk.CTkTextbox(
            frame,
            font=ctk.CTkFont(size=11, family="Courier New"),
            wrap="none",
            state="disabled",
        )
        self._body_box.grid(row=3, column=0, padx=14, pady=(0, 12), sticky="nsew")

    # ------------------------------------------------------------------
    # Body generation
    # ------------------------------------------------------------------

    def _build_default_subject(self, v, e) -> str:
        return f"FEA Trace \u2014 {e.project} / {e.name} {v.id}"

    def _build_body(self) -> str:
        v   = self._project._get_version(self._version_id)
        e   = self._project.entity
        SEP = "=" * 65

        def _field(label: str, value: str) -> list[str]:
            """Label padded to 12 chars + ': ' prefix; continuation lines indent to match."""
            prefix = f"{label:<12}: "
            indent = " " * len(prefix)
            parts  = (value or "").split("\n")
            out    = [prefix + parts[0]]
            for part in parts[1:]:
                out.append(indent + part)
            return out

        def _indented_field(label: str, value: str, base_indent: str) -> list[str]:
            """Like _field but with a leading indent (used inside iteration blocks)."""
            prefix = f"{base_indent}{label}: "
            indent = " " * len(prefix)
            parts  = (value or "").split("\n")
            out    = [prefix + parts[0]]
            for part in parts[1:]:
                out.append(indent + part)
            return out

        lines = [SEP, "FEA Trace Output Report", SEP]
        lines += _field("Project",     e.project)
        lines += _field("Entity",      f"{e.name} [{e.id}]")
        lines += _field("Version",     v.id)
        lines += _field("Description", v.description or "")

        # Step files — scan the 01_Source/{version_id}/ folder on disk so that
        # files added via "Browse Files…" (which have no SourceComponentRecord)
        # are included alongside assembly-component files.
        src_folder = self._project.get_version_source_folder(self._version_id)
        if src_folder.is_dir():
            step_files = sorted(
                f.name for f in src_folder.iterdir()
                if f.is_file() and f.suffix.lower() in {".step", ".stp"}
            )
        else:
            step_files = []
        if step_files:
            lines += ["", "--- Step files ---"]
            for f in step_files:
                lines.append(f"- {f}")

        # Reported results
        lines += ["", "--- Reported Results ---"]

        iter_map: dict[str, object] = {i.id: i for i in v.iterations}
        selected: dict[str, list[int]] = {}
        for (iter_id, run_id), var in self._checks.items():
            if var.get():
                selected.setdefault(iter_id, []).append(run_id)

        if not selected:
            lines.append("(no runs selected)")
        else:
            for iter_id in sorted(selected):
                i        = iter_map[iter_id]
                run_ids  = selected[iter_id]
                last_run = max(i.runs, key=lambda r: r.id) if i.runs else None
                date_part = (
                    f"  (last run: {last_run.date.split(' ')[0]})" if last_run else ""
                )
                lines.append(f"- {iter_id}  [{i.status.value.upper()}]{date_part}")
                lines += _indented_field("Description", i.description or "", "  ")
                for run_id in sorted(run_ids):
                    lines.append(f"    - Run {run_id:02d}")

        lines += ["", SEP]
        return "\n".join(lines)

    def _refresh_body(self) -> None:
        body = self._build_body()
        self._body_box.configure(state="normal")
        self._body_box.delete("1.0", "end")
        self._body_box.insert("1.0", body)
        self._body_box.configure(state="disabled")

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

    def _on_selection_change(self) -> None:
        """Called whenever run checkboxes or subject change; updates save button and body."""
        self._update_save_btn()
        self._refresh_body()

    def _update_save_btn(self) -> None:
        has_runs = any(v.get() for v in self._checks.values())
        has_subj = bool(self._subject_var.get().strip())
        has_eml  = self._eml_source_path is not None
        self._save_btn.configure(
            state="normal" if (has_runs and has_subj and has_eml) else "disabled"
        )

    # ------------------------------------------------------------------
    # Button events
    # ------------------------------------------------------------------

    def _on_copy_body(self) -> None:
        """Copy the body to the clipboard as CF_HTML (Courier New) + plain text fallback."""
        self._error_label.configure(text="")
        body = self._body_box.get("1.0", "end").rstrip()
        html_fragment = (
            '<pre style="font-family: Courier New, monospace; font-size: 10pt;">'
            + _html_lib.escape(body)
            + "</pre>"
        )
        try:
            _set_html_clipboard(html_fragment)
            self._copy_btn.configure(text=" Copied!")
            self.after(2000, lambda: self._copy_btn.configure(text=" Copy"))
        except Exception as exc:
            self._error_label.configure(text=f"Clipboard error: {exc}")

    def _on_open_outlook(self) -> None:
        """Open a pre-filled draft in the system default mail client.

        Uses a mailto: URI (To + Subject only) so the correct mail app opens
        regardless of whether the user has New Outlook, Classic Outlook, or any
        other client.  The body is placed on the clipboard as CF_HTML so that
        a simple Ctrl+V in the compose window pastes it in Courier New.
        """
        self._error_label.configure(text="")
        self._import_label.configure(text="")
        subject = self._subject_var.get().strip()
        self._body_box.configure(state="normal")
        body    = self._body_box.get("1.0", "end").rstrip()
        self._body_box.configure(state="disabled")

        # Place body on clipboard as HTML so Outlook renders it in Courier New.
        html_fragment = (
            '<pre style="font-family: Courier New, monospace; font-size: 10pt;">'
            + _html_lib.escape(body)
            + "</pre>"
        )
        try:
            _set_html_clipboard(html_fragment)
            clipboard_ok = True
        except Exception as exc:
            clipboard_ok = False
            self._error_label.configure(text=f"Clipboard error: {exc}")

        # Open compose window with To + Subject pre-filled (body intentionally
        # omitted so the user pastes the formatted version from the clipboard).
        params = urllib.parse.urlencode(
            {"subject": subject},
            quote_via=urllib.parse.quote,
        )
        mailto = f"mailto:?{params}"
        try:
            webbrowser.open(mailto)
            self._outlook_opened = True
            self._outlook_btn.configure(text="Reopen in Outlook")
            if clipboard_ok:
                self._import_label.configure(
                    text="\u2713 Body copied to clipboard \u2014 paste with Ctrl+V in Outlook"
                )
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
        to_str  = self._to_var.get().strip()   # may be empty if .eml had no To header
        subject = self._subject_var.get().strip()
        if not subject:
            self._error_label.configure(text="Subject field is required.")
            return

        self._body_box.configure(state="normal")
        body_text = self._body_box.get("1.0", "end").rstrip()
        self._body_box.configure(state="disabled")
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
